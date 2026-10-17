# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""One visible job model, a global pause and a minimal activity log (plan A24, A25, A27).

Every import and scan is a job with one state (ADR-0001, section 3.4):
running · paused · completed · completed_with_gaps · failed · cancelled ·
needs_approval. A waiting scheduled scan is shown from its schedule, so no
background work stays hidden. The global pause blocks new jobs and stops
running ones between two messages; it never undoes what already happened
outside ARGUS. The activity log keeps time, job type, result and counts only:
no message text, secrets, addresses or CLI output, and it is kept short.
"""
from datetime import datetime, timedelta, timezone
import json
import uuid

from .errors import UserFacingError

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  source TEXT NOT NULL,
  state TEXT NOT NULL,
  started_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  finished_at TEXT,
  counts TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  event TEXT NOT NULL,
  kind TEXT,
  outcome TEXT,
  counts TEXT NOT NULL DEFAULT '{}'
);
"""
PAUSE = "automation_paused"
KINDS = ("import", "imap_scan", "scheduled_scan", "folder_watch", "bitwarden_check", "bitwarden_write")
# "uncertain" marks an external write whose result is unknown; it blocks a blind retry (priority 12).
STATES = ("running", "paused", "completed", "completed_with_gaps", "failed", "cancelled", "needs_approval", "uncertain")
EVENTS = ("job_finished", "automation_paused", "automation_resumed", "approval_granted", "approval_revoked",
          "approval_refused")
COUNT_KEYS = ("processed", "evidence", "updated_evidence", "removed_evidence", "duplicates", "skipped", "errors",
              "headers_only", "items", "unchanged")
KEEP_JOBS = 100
KEEP_ACTIVITY = 500
KEEP_DAYS = 180
# A running job that has not reported for this long was interrupted (closed window, crash).
STALE_AFTER = timedelta(minutes=10)


class JobPaused(UserFacingError):
    """The global pause stopped a running job between two messages."""


class JobCancelled(Exception):
    """A running job lost its approval or lease and stopped; it ends as "cancelled", not "failed"."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _counts(values):
    return json.dumps({key: values[key] for key in COUNT_KEYS if type(values.get(key)) is int and values[key] >= 0})


def paused(db):
    row = db.execute("SELECT value FROM meta WHERE key=?", (PAUSE,)).fetchone()
    return json.loads(row[0]) if row else None


def require_running(db):
    """Refuse a new job while automation is paused."""
    if paused(db):
        raise UserFacingError("Automation is paused; resume it before starting new jobs")


def set_paused(db, pause):
    current = paused(db)
    if pause and not current:
        db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   (PAUSE, json.dumps({"at": _now()})))
        record(db, "automation_paused")
    elif not pause and current:
        db.execute("DELETE FROM meta WHERE key=?", (PAUSE,))
        record(db, "automation_resumed")


def record(db, event, kind=None, outcome=None, counts=None):
    """Append one activity entry and keep the log short."""
    if event not in EVENTS or (kind is not None and kind not in KINDS):
        raise ValueError("Invalid activity entry")
    db.execute("INSERT INTO activity(at,event,kind,outcome,counts) VALUES (?,?,?,?,?)",
               (_now(), event, kind, outcome, _counts(counts or {})))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    db.execute("""DELETE FROM activity WHERE at < ? OR id <= (
                    SELECT id FROM activity ORDER BY id DESC LIMIT 1 OFFSET ?)""", (cutoff, KEEP_ACTIVITY))


def start(db, job_id, kind, source):
    if kind not in KINDS:
        raise ValueError("Invalid job")
    moment = _now()
    db.execute("""INSERT INTO jobs(id,kind,source,state,started_at,updated_at) VALUES (?,?,?,'running',?,?)
                  ON CONFLICT(id) DO NOTHING""", (job_id, kind, source[:20], moment, moment))
    db.execute("DELETE FROM jobs WHERE id NOT IN (SELECT id FROM jobs ORDER BY started_at DESC LIMIT ?)", (KEEP_JOBS,))


def update(db, job_id, counts):
    db.execute("UPDATE jobs SET counts=?,updated_at=? WHERE id=? AND state='running'", (_counts(counts), _now(), job_id))


def finish(db, job_id, state, counts):
    if state not in STATES or state == "running":
        raise ValueError("Invalid job state")
    row = db.execute("SELECT kind,state FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None or row["state"] != "running":
        return
    moment = _now()
    db.execute("UPDATE jobs SET state=?,counts=?,updated_at=?,finished_at=? WHERE id=?",
               (state, _counts(counts), moment, moment, job_id))
    record(db, "job_finished", row["kind"], state, counts)


def single(db, kind, outcome, counts=None):
    """A short job that starts and ends in one call (Bitwarden check or transfer)."""
    job_id = str(uuid.uuid4())
    start(db, job_id, kind, kind)
    finish(db, job_id, outcome, counts or {})


def overview(db, schedule=None, limit=20, watch=None):
    """Jobs, waiting work, pause state and recent activity for the control view (D5)."""
    now = datetime.now(timezone.utc)
    jobs = []
    for row in db.execute("SELECT * FROM jobs ORDER BY started_at DESC LIMIT ?", (limit,)):
        state = row["state"]
        if state == "running" and now - datetime.fromisoformat(row["updated_at"]) > STALE_AFTER:
            state = "interrupted"
        jobs.append({"id": row["id"], "kind": row["kind"], "source": row["source"], "state": state,
                     "started_at": row["started_at"], "finished_at": row["finished_at"],
                     "counts": json.loads(row["counts"])})
    waiting = []
    if schedule and schedule.get("enabled") and schedule.get("next_run_at"):
        waiting.append({"kind": "scheduled_scan", "next_run_at": datetime.fromtimestamp(
            schedule["next_run_at"], timezone.utc).isoformat()})
    if watch and watch.get("enabled") and watch.get("next_run_at"):
        waiting.append({"kind": "folder_watch", "next_run_at": datetime.fromtimestamp(
            watch["next_run_at"], timezone.utc).isoformat()})
    activity = [{"at": row["at"], "event": row["event"], "kind": row["kind"], "outcome": row["outcome"],
                 "counts": json.loads(row["counts"])}
                for row in db.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 50")]
    return {"paused": paused(db), "jobs": jobs, "waiting": waiting, "activity": activity}
