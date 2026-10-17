# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Private SQLite storage of evidence metadata, never message bodies or secrets."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

from .errors import UserFacingError
from .analysis import ANALYSIS_VERSION, FEATURES, KINDS, LABELS, Evidence, english_caveat, normalize_email
from .instances import (SCHEMA as INSTANCE_SCHEMA, defer_in_queue, direct_identity, insert_instance, migrate_instances,
                        owned_emails, read_steps, rebuild_from_v1, synchronize_instances, write_step)
from .registry import Registry
from .review import SCHEMA as REVIEW_SCHEMA
from .identity import SCHEMA as IDENTITY_SCHEMA, explain_priorities, load as load_identity
from .jobs import SCHEMA as JOBS_SCHEMA
from .imports import SCHEMA as IMPORTS_SCHEMA
from .changes import ChangeBatch, planning
from .digest import acknowledge, change_digest, next_revision, return_summary, review_mark, undo_acknowledge
from .states import (DECISIONS, LEGACY_CHECKLIST, LEGACY_STEPS, REJECT_REASONS, STEPS, default_steps,
                     evidence_level, legacy_checklist, legacy_classification, legacy_status, progress,
                     review_date, valid_step_state)

# The 1.x checklist keys; the API and snapshot keep them for one major version.
CHECKLIST = LEGACY_CHECKLIST

# Bump with every change to stored data. Opening an older profile first saves
# an automatic backup; a profile from a newer ARGUS is never opened.
#   1: account identities, rule versions, unique fingerprints, snoozes (1.9-1.16)
#   2: ADR-0001 axes: decision, dated steps, planning only in the worklist, change log
#   3: rule features per clue (plan E1); older clues gain them on their next import
#   4: reversible sender-domain exclusions and relations between own addresses (E4, A9)
SCHEMA_VERSION = 8


def now():
    return datetime.now(timezone.utc).isoformat()


# Plan E2: a clue older than two years may describe an account that changed or
# was closed since. It is only labelled, never deleted.
HISTORICAL_DAYS = 730


def clue_age_days(value):
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - moment).days)


CORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY,
  provider_id TEXT,
  sender_domain TEXT NOT NULL,
  registered_email TEXT,
  signal TEXT NOT NULL,
  score INTEGER NOT NULL,
  fingerprint TEXT NOT NULL,
  date TEXT,
  source TEXT NOT NULL,
  caveat TEXT,
  rule_version INTEGER NOT NULL DEFAULT 1,
  features TEXT,
  created_rev INTEGER NOT NULL DEFAULT 0,
  changed_rev INTEGER NOT NULL DEFAULT 0,
  UNIQUE(fingerprint, sender_domain, signal)
);
CREATE INDEX IF NOT EXISTS evidence_provider ON evidence(provider_id);
"""

# Provider-wide progress tables from before 1.9. New profiles never create
# them; migrate_instances reads them once from older profiles.
LEGACY_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
  provider_id TEXT PRIMARY KEY,
  confirmed INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  checklist TEXT NOT NULL DEFAULT '{}',
  priority_override TEXT,
  login_method TEXT NOT NULL DEFAULT 'password',
  manual_email TEXT,
  updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS work_queue (
  provider_id TEXT PRIMARY KEY,
  position INTEGER NOT NULL,
  deferred INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bitwarden_handoffs (
  id TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  email TEXT NOT NULL,
  state TEXT NOT NULL,
  operation_id TEXT NOT NULL,
  lease_until REAL NOT NULL DEFAULT 0,
  vault_item_id TEXT,
  updated TEXT NOT NULL,
  UNIQUE(provider_id, email)
);
"""


UNCHANGED = object()


def atomic_meta_update(store, key, change):
    """Read, change and write one meta value under SQLite's cross-process lock.

    ``change(value)`` receives the decoded value (``None`` when missing) and
    returns ``(new_value, result)``; ``UNCHANGED`` skips the write. Duck-typed
    stores without ``connect`` (focused unit-test doubles) fall back to
    ``meta``/``set_meta`` and are therefore single-process only.
    """
    connect = getattr(store, "connect", None)
    if not callable(connect):
        value, result = change(store.meta(key))
        if value is not UNCHANGED:
            store.set_meta(key, value)
        return result
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        value, result = change(json.loads(row[0]) if row else None)
        if value is not UNCHANGED:
            db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (key, json.dumps(value, ensure_ascii=False)))
        return result


def private_dir(path: Path):
    if path.is_symlink():
        raise ValueError("The data directory must not be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)


def write_private(path: Path, content: str):
    # Do not change permissions of an existing user-chosen parent (e.g. /tmp).
    if path.parent.is_symlink():
        raise ValueError("The export directory must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive creation avoids replacing exports and following existing symlinks.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)


class Store:
    def __init__(self, data_dir: Path, registry: Registry):
        self.data_dir = data_dir.resolve()
        if data_dir.is_symlink():
            raise ValueError("The data directory must not be a symlink")
        private_dir(self.data_dir)
        self.path = self.data_dir / "accounts.sqlite3"
        if self.path.is_symlink():
            raise ValueError("The database must not be a symlink")
        from .catalog import PERSONAL_CATALOG
        self.registry = registry.with_personal(self.data_dir / PERSONAL_CATALOG)
        self._backup_before_migration()
        registry = self.registry
        with self.connect() as db:
            db.executescript(CORE_SCHEMA)
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "accounts" in tables:
                # A pre-1.9 profile keeps its original tables as the one-time
                # migration source; complete any that older versions lacked.
                db.executescript(LEGACY_SCHEMA)
                columns = {row["name"] for row in db.execute("PRAGMA table_info(accounts)")}
                if "manual_email" not in columns:
                    db.execute("ALTER TABLE accounts ADD COLUMN manual_email TEXT")
            evidence_columns = {row["name"] for row in db.execute("PRAGMA table_info(evidence)")}
            if "rule_version" not in evidence_columns:
                db.execute("ALTER TABLE evidence ADD COLUMN rule_version INTEGER NOT NULL DEFAULT 1")
            if "features" not in evidence_columns:
                db.execute("ALTER TABLE evidence ADD COLUMN features TEXT")
            # Plan A1/A2: clues stored before revisions existed count as already seen (revision 0).
            for column in ("created_rev", "changed_rev"):
                if column not in evidence_columns:
                    db.execute(f"ALTER TABLE evidence ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0")
            # A message's raw fingerprint is its identity across rule/catalogue revisions.
            indexes = {row["name"] for row in db.execute("PRAGMA index_list(evidence)")}
            if "evidence_fingerprint" not in indexes:
                db.execute("DELETE FROM evidence WHERE id NOT IN (SELECT MIN(id) FROM evidence GROUP BY fingerprint)")
                db.execute("CREATE UNIQUE INDEX evidence_fingerprint ON evidence(fingerprint)")
            db.executescript(INSTANCE_SCHEMA)
            db.executescript(REVIEW_SCHEMA)
            db.executescript(IDENTITY_SCHEMA)
            db.executescript(JOBS_SCHEMA)
            db.executescript(IMPORTS_SCHEMA)
            queue_columns = {row["name"] for row in db.execute("PRAGMA table_info(instance_work_queue)")}
            if "resume_after" not in queue_columns:
                db.execute("ALTER TABLE instance_work_queue ADD COLUMN resume_after TEXT")
            instance_columns = {row["name"] for row in db.execute("PRAGMA table_info(account_instances)")}
            db.execute("BEGIN IMMEDIATE")
            if "checklist" in instance_columns:
                rebuild_from_v1(db)
            migrate_instances(db, registry)
            db.execute("INSERT INTO meta VALUES ('schema_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (json.dumps(SCHEMA_VERSION),))
        if os.name == "posix":
            self.path.chmod(0o600)

    def _backup_before_migration(self):
        """Save the untouched profile before this version changes its database."""
        from .backup import create_backup, schema_version
        if not self.path.is_file() or self.path.stat().st_size == 0:
            return
        stored = schema_version(self.path)
        if stored is not None and stored > SCHEMA_VERSION:
            raise UserFacingError("This profile was updated by a newer ARGUS version; update ARGUS first")
        if stored != SCHEMA_VERSION:
            create_backup(self.data_dir, reason="pre-migration", label=f"v{stored or 0}-to-v{SCHEMA_VERSION}")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def set_meta(self, key, value):
        with self.connect() as db:
            db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (key, json.dumps(value, ensure_ascii=False)))

    def set_imap_cursor(self, cursor_key, cursor):
        """Merge one IMAP checkpoint without replacing other folders' cursors."""
        if not isinstance(cursor_key, str) or not isinstance(cursor, dict):
            raise ValueError("Invalid IMAP cursor")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT value FROM meta WHERE key='imap_cursors'").fetchone()
            cursors = json.loads(row[0]) if row else {}
            if not isinstance(cursors, dict):
                cursors = {}
            cursors[cursor_key] = cursor
            db.execute("INSERT INTO meta VALUES ('imap_cursors',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (json.dumps(cursors, ensure_ascii=False),))

    def meta(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def configure(self, emails: list[str], demo=False):
        normalized = sorted({normalize_email(x) for x in emails})
        if not normalized:
            raise UserFacingError("At least one own email address is required")
        previous = self.meta("emails")
        if previous and previous != normalized and not (demo and self.meta("demo", False)):
            raise UserFacingError("A different initial address scope requires a new data directory; use add-email to add aliases")
        self.set_meta("emails", normalized)
        self.set_meta("demo", bool(demo))

    def add_emails(self, emails: list[str]):
        if not isinstance(emails, list) or not emails or any(not isinstance(e, str) for e in emails):
            raise UserFacingError("Specify your own email addresses as a list")
        extra = {normalize_email(e) for e in emails}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT value FROM meta WHERE key='emails'").fetchone()
            demo = db.execute("SELECT value FROM meta WHERE key='demo'").fetchone()
            if not current or (demo and json.loads(demo[0])):
                raise UserFacingError("Aliases require an initialized personal profile")
            previous = set(json.loads(current[0]))
            merged = sorted(previous | extra)
            if len(merged) > 64:
                raise UserFacingError("A profile supports up to 64 own addresses")
            added = sorted(extra - previous)
            if added:
                db.execute("UPDATE meta SET value=? WHERE key='emails'", (json.dumps(merged),))
                db.execute("INSERT INTO meta VALUES ('imap_cursors','{}') ON CONFLICT(key) DO UPDATE SET value='{}'")
        return added

    def add_evidence(self, evidence: Evidence) -> bool:
        return self.record_analysis(evidence.fingerprint, evidence) == "new"

    def record_analysis(self, fingerprint: str, evidence: Evidence | None, *, expected_emails=None, changes=None):
        """Store one message's analysis. ``changes`` collects what current rules changed (plan E6)."""
        if evidence and evidence.fingerprint != fingerprint:
            raise ValueError("The message fingerprint does not match")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if expected_emails is not None:
                row = db.execute("SELECT value FROM meta WHERE key='emails'").fetchone()
                if not row or set(json.loads(row[0])) != set(expected_emails):
                    return "scope_changed"
            previous = db.execute("SELECT * FROM evidence WHERE fingerprint=?", (fingerprint,)).fetchone()
            if evidence is None:
                if previous:
                    db.execute("DELETE FROM evidence WHERE fingerprint=?", (fingerprint,))
                    if changes is not None:
                        changes.append({"provider_id": previous["provider_id"], "sender_domain": previous["sender_domain"],
                                        "old_reason": LABELS.get(previous["signal"]), "new_reason": None,
                                        "old_score": previous["score"], "new_score": None})
                    return "removed"
                return "ignored"
            features = json.dumps(sorted(set(evidence.features) & FEATURES))
            fields = ("provider_id", "sender_domain", "registered_email", "signal", "score", "date", "caveat",
                      "rule_version", "features")
            values = (evidence.provider_id, evidence.sender_domain, evidence.registered_email,
                      evidence.signal, evidence.score, evidence.date, evidence.caveat, ANALYSIS_VERSION, features)
            if previous and tuple(previous[f] for f in fields) == values:
                # Plan A2: the same message with the same result is never presented again.
                return "duplicate"
            revision = next_revision(db)
            db.execute("""INSERT INTO evidence
              (provider_id,sender_domain,registered_email,signal,score,fingerprint,date,source,caveat,rule_version,features,
               created_rev,changed_rev)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fingerprint) DO UPDATE SET
                provider_id=excluded.provider_id, sender_domain=excluded.sender_domain,
                registered_email=excluded.registered_email, signal=excluded.signal,
                score=excluded.score, date=excluded.date, caveat=excluded.caveat,
                rule_version=excluded.rule_version, features=excluded.features, changed_rev=excluded.changed_rev""", (
                evidence.provider_id, evidence.sender_domain, evidence.registered_email,
                evidence.signal, evidence.score, evidence.fingerprint, evidence.date,
                evidence.source, evidence.caveat, ANALYSIS_VERSION, features, revision, revision,
            ))
            synchronize_instances(db, self.registry, {evidence.provider_id})
            if previous and changes is not None and (previous["signal"], previous["score"], previous["provider_id"]) != (
                    evidence.signal, evidence.score, evidence.provider_id):
                changes.append({"provider_id": evidence.provider_id, "sender_domain": evidence.sender_domain,
                                "old_reason": LABELS.get(previous["signal"]), "new_reason": LABELS.get(evidence.signal),
                                "old_score": previous["score"], "new_score": evidence.score})
            return "updated" if previous else "new"

    def snapshot(self, language="en"):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            synchronize_instances(db, self.registry)
            states = {}
            for row in db.execute("SELECT * FROM account_instances ORDER BY rowid"):
                states.setdefault(row["provider_id"], []).append(dict(row))
            step_rows = {}
            for row in db.execute("SELECT * FROM account_steps"):
                step_rows.setdefault(row["account_id"], {})[row["step"]] = {
                    "state": row["state"], "done_at": row["done_at"], "review_after": row["review_after"]}
            queue = {row["account_id"]: dict(row) for row in db.execute("SELECT * FROM instance_work_queue")}
            from .review import exclusions, relations
            excluded = exclusions(db)
            related = relations(db)
            identity_relations = load_identity(db)
            evidences = [dict(r) for r in db.execute("SELECT * FROM evidence ORDER BY score DESC,id DESC")]
            own = owned_emails(db)
            mark = review_mark(db)
            revision = db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()
        from .catalog import categories as catalog_categories, personal_providers
        from .registry import is_shared_sender
        from .workflow import effectively_deferred, utcnow
        moment = utcnow()
        today = moment.date().isoformat()
        grouped = {}
        unassigned = {}
        candidates = {}
        stale_evidence = 0
        for e in evidences:
            identity = direct_identity(e, own)
            e.pop("fingerprint")
            e["caveat"] = english_caveat(e["caveat"])
            # Plan E1/E2: why it counts, what kind of clue it is and how old it is.
            e["kind"] = KINDS.get(e["signal"], "account")
            try:
                e["features"] = [item for item in json.loads(e["features"] or "null") or [] if item in FEATURES]
            except (TypeError, ValueError):
                e["features"] = []
            e["age_days"] = clue_age_days(e["date"])
            e["historical"] = e["age_days"] is not None and e["age_days"] > HISTORICAL_DAYS
            e["outdated"] = e["rule_version"] < ANALYSIS_VERSION
            if e["outdated"]:
                stale_evidence += 1
                e["score"] = min(e["score"], 35)
                e["registered_email"] = None
            e["reason"] = LABELS[e["signal"]]
            if e["outdated"]:
                e["reason"] = "Older evidence; reanalyze the original message locally"
            if e["provider_id"]:
                if identity:
                    grouped.setdefault((e["provider_id"], identity), []).append(e)
                else:
                    e["registered_email"] = None
                    # Ambiguous or inconsistent historical rows may retain a
                    # strong stored score. They cannot prove an individual
                    # identity until the original mail is analyzed again.
                    e["score"] = min(e["score"], 35)
                    unassigned.setdefault(e["provider_id"], []).append(e)
            else:
                candidates.setdefault(e["sender_domain"], []).append(e)
        accounts = []
        for provider_id, provider in self.registry.providers.items():
            provider_states = states.get(provider_id) or [{
                "id": provider_id, "provider_id": provider_id, "identity_email": None,
                "canonical": 1, "label": "", "identity_review_required": 0,
                "priority_override": None, "login_method": "password", "manual_email": None,
                "decision": "undecided", "decision_reason": None, "decided_at": None,
                "decided_evidence_id": None, "updated": None,
            }]
            provider_clues = sorted(unassigned.get(provider_id, []), key=lambda e: (e["outdated"], -e["score"], -e["id"]))
            for state in provider_states:
                email = state["identity_email"]
                found = grouped.get((provider_id, email), []) if state["canonical"] and email else []
                found = sorted(found, key=lambda e: (e["outdated"], -e["score"], -e["id"]))
                score = max((e["score"] for e in found), default=0)
                decision = state["decision"]
                steps = default_steps(state["login_method"])
                steps.update(step_rows.get(state["id"], {}))
                review = bool(state["identity_review_required"])
                level = evidence_level(found)
                progress_value, completed_at = progress(decision, steps, review)
                planned = queue.get(state["id"])
                deferred = bool(planned) and effectively_deferred(planned, moment)
                confirmed = decision == "confirmed"
                evidence_reason = found[0]["reason"] if found else "No local evidence; account existence is unknown"
                accounts.append({
                    **provider.public(), "id": state["id"], "provider_id": provider_id,
                    "identity_email": email, "label": state["label"],
                    "display_name": provider.name + (" · " + state["label"] if state["label"] else ""),
                    "identity_review_required": review,
                    # ADR-0001 axes: A evidence, B decision, C steps; progress is derived.
                    "evidence_level": level, "evidence_reason": evidence_reason, "score": score,
                    "decision": decision, "decision_reason": state["decision_reason"], "decided_at": state["decided_at"],
                    "reconsider": decision == "rejected" and any(
                        e["id"] > (state["decided_evidence_id"] or 0) and e["score"] >= 60 and not e["outdated"] for e in found),
                    "steps": steps, "progress": progress_value, "completed_at": completed_at,
                    "reviews_due": sorted(step for step, value in steps.items()
                                          if value["review_after"] and value["review_after"] <= today),
                    "in_worklist": bool(planned), "deferred": deferred,
                    "registered_emails": [email] if email else [], "manual_email": state["manual_email"],
                    "evidence": found[:30], "evidence_count": len(found),
                    "latest_clue_at": max((e["date"] for e in found if e["date"]), default=None),
                    "historical": bool(found) and all(e["historical"] for e in found),
                    "unassigned_evidence": provider_clues[:30], "unassigned_evidence_count": len(provider_clues),
                    # Derived with its reasons in explain_priorities (plan D3).
                    "priority": state["priority_override"] or provider.priority,
                    "catalog_priority": provider.priority, "priority_override": state["priority_override"],
                    "login_method": state["login_method"], "updated": state["updated"],
                    # 1.x compatibility fields, derived from the axes above (ADR-0001, section 4).
                    "classification": legacy_classification(decision, level),
                    "status": legacy_status(progress_value, deferred),
                    "checklist": legacy_checklist(decision, steps),
                    "confidence": "manually confirmed" if confirmed else "high" if score >= 85 else "medium" if score >= 60 else "low" if found else "no evidence",
                    "reason": "You confirmed that this account exists" if confirmed else evidence_reason,
                })
        identity_links = explain_priorities(accounts, identity_relations)
        rank = {"critical": 0, "high": 1, "normal": 2}
        accounts.sort(key=lambda a: (a["classification"] == "unknown", a["status"] == "done", rank[a["priority"]], a["name"].casefold()))
        found = [a for a in accounts if a["classification"] != "unknown"]
        done = sum(a["status"] == "done" and not a["identity_review_required"] for a in found)
        snapshot = {
            "accounts": accounts,
            "candidates": [{"domain": domain, "evidence": items[:10], "website": None, "shared_sender": is_shared_sender(domain),
                            # A domain added to the catalog later stays here until its emails are imported again.
                            "catalog_match": getattr(self.registry.match(domain), "name", None),
                            "classification": "unknown", "reason": "Unverified sender domain; extend the catalog"}
                           for domain, items in sorted(candidates.items())
                           if domain not in {entry["domain"] for entry in excluded}],
            "exclusions": excluded, "relations": related, "identity_links": identity_links,
            "catalog": {"personal": personal_providers(self.registry), "categories": catalog_categories(self.registry),
                        # Plan E6: clues stored before a catalog addition need their original email again.
                        "reanalysis": sum(1 for e in evidences if not e["provider_id"] and self.registry.match(e["sender_domain"]))},
            "summary": {"providers": len(self.registry.providers), "found": len(found),
                        "services_found": len({a["provider_id"] for a in found}), "instances_found": len(found),
                        "confirmed": sum(a["classification"] == "confirmed" for a in accounts),
                        "rejected": sum(a["decision"] == "rejected" for a in accounts),
                        "clues": len(evidences),
                        "probable": sum(a["classification"] == "probable" for a in accounts), "unknown": len(accounts) - len(found),
                        "done": done, "high_priority": sum(a["priority"] in {"high", "critical"} and
                            (a["status"] != "done" or a["identity_review_required"]) for a in found),
                        "progress": round(done * 100 / len(found)) if found else 0},
            "emails": self.meta("emails", []), "demo": self.meta("demo", False),
            "last_scan": self._last_scan(),
            "stale_evidence": stale_evidence, "analysis_version": ANALYSIS_VERSION,
        }
        from .workflow import next_step, worklist_snapshot
        from .handoffs import handoff_snapshot
        for account in accounts:
            account["next_step"] = next_step(account)
        snapshot["workflow"] = worklist_snapshot(self, accounts)
        snapshot["bitwarden_handoffs"] = handoff_snapshot(self)
        from .summary import next_task, result_summary
        from .review import unclear_items
        for account in accounts:
            email = account["identity_email"]
            account["related_addresses"] = [entry for entry in related if email and email in {entry["address"], entry["other"]}]
        snapshot["unclear"] = unclear_items(snapshot)
        snapshot["result"] = result_summary(snapshot)
        snapshot["next_task"] = next_task(snapshot)
        snapshot["changes"] = change_digest(snapshot, evidences, mark, json.loads(revision[0]) if revision else 0)
        snapshot["return_summary"] = return_summary(snapshot)
        from . import jobs, reviews, sessions
        with self.connect() as db:
            rule, session = reviews.load_rule(db), sessions.load(db)
            snapshot["automation_paused"] = jobs.paused(db)
        if snapshot["automation_paused"]:
            # Plan A28: a pause stays clearly visible in the one summary.
            snapshot["return_summary"]["items"].insert(0, {"kind": "paused", "count": None})
        proposals = reviews.proposals(accounts, rule)
        for account in accounts:
            account["review_proposal"] = proposals.get(account["id"])
        snapshot["review_rule"] = rule
        snapshot["session"] = sessions.report(session, accounts)
        from .i18n import localize_snapshot
        return localize_snapshot(snapshot, language)

    def _last_scan(self):
        from .guidance import scan_next_steps
        scan = self.meta("last_scan")
        if isinstance(scan, dict):
            scan["next_steps"] = scan_next_steps(scan)
        return scan

    def update_account(self, account_id: str, change: dict):
        """Apply one person's change; every decision, step and planning change is logged.

        Accepts the 1.x keys: "checklist" maps to the decision and the steps
        (states.LEGACY_STEPS); "status": "done" checks that every required step
        is done (an unticked MFA box becomes not applicable, as 1.x allowed);
        "status": "skipped" defers the account in the worklist.
        """
        allowed = {"checklist", "status", "priority", "login_method", "registered_email", "label"}
        if not isinstance(account_id, str) or not isinstance(change, dict) or set(change) - allowed:
            raise UserFacingError("Invalid account update")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
            if row is None:
                if account_id not in self.registry.providers:
                    raise UserFacingError("Invalid account update")
                insert_instance(db, account_id, ident=account_id)
                row = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
            state = dict(row)
            moment = now()
            steps = read_steps(db, account_id, state["login_method"])
            new_steps = {step: dict(value) for step, value in steps.items()}
            decision = {"decision": state["decision"], "reason": state["decision_reason"], "decided_at": state["decided_at"]}
            new_decision = dict(decision)
            review = state["identity_review_required"]

            def set_step(step, done):
                current = new_steps[step]
                if done and current["state"] != "done":
                    current.update(state="done", done_at=moment)
                elif not done and current["state"] in {"done", "prepared"}:
                    current.update(state="open", done_at=None)

            if "checklist" in change:
                additions = change["checklist"]
                if not isinstance(additions, dict) or set(additions) - set(CHECKLIST) or any(type(v) is not bool for v in additions.values()):
                    raise UserFacingError("Invalid checklist")
                if "reviewed" in additions:
                    if additions["reviewed"]:
                        if new_decision["decision"] != "confirmed":
                            new_decision = {"decision": "confirmed", "reason": None, "decided_at": moment}
                    else:
                        new_decision = {"decision": "undecided", "reason": None, "decided_at": None}
                    set_step("identity", additions["reviewed"] and not review)
                for key, step in LEGACY_STEPS.items():
                    if key in additions and new_steps[step]["state"] != "not_applicable":
                        set_step(step, additions[key])
            method = change.get("login_method", state["login_method"])
            if method not in {"password", "sso", "passkey"}:
                raise UserFacingError("Invalid sign-in method")
            if method != state["login_method"]:
                # Without a separate password, the password step does not apply.
                if method == "password":
                    new_steps["password"] = {"state": "open", "done_at": None, "review_after": new_steps["password"]["review_after"]}
                else:
                    new_steps["password"] = {"state": "not_applicable", "done_at": None, "review_after": new_steps["password"]["review_after"]}
            manual_email, identity_email = state["manual_email"], state["identity_email"]
            if "registered_email" in change:
                proposed = change["registered_email"]
                if proposed is not None and not isinstance(proposed, str):
                    raise UserFacingError("Invalid sign-in address")
                proposed = normalize_email(proposed) if proposed else None
                if proposed and proposed not in owned_emails(db):
                    raise UserFacingError("Use only explicitly configured own addresses")
                if identity_email and proposed != identity_email:
                    raise UserFacingError("An existing account's sign-in address cannot be reassigned; add a separate account")
                if proposed and not identity_email:
                    if db.execute("SELECT 1 FROM instance_bitwarden_handoffs WHERE account_id=?", (account_id,)).fetchone():
                        raise UserFacingError("An account with a Bitwarden transfer cannot be assigned a different identity; add a separate account")
                    if db.execute("SELECT 1 FROM account_instances WHERE provider_id=? AND identity_email=? AND canonical=1 AND id<>?", (state["provider_id"], proposed, account_id)).fetchone():
                        raise UserFacingError("That sign-in address already belongs to a separate account")
                    identity_email, review = proposed, 0
                    # Choosing the address is the person's own identity check.
                    set_step("identity", True)
                manual_email = proposed
            label = change.get("label", state["label"])
            label = self._account_label(label)
            if not state["canonical"] and not label:
                raise UserFacingError("Use a unique label for accounts with the same sign-in address")
            peers = db.execute("SELECT label FROM account_instances WHERE provider_id=? AND identity_email IS ? AND id<>?",
                               (state["provider_id"], identity_email, account_id)).fetchall()
            if label and any(peer["label"].casefold() == label.casefold() for peer in peers):
                raise UserFacingError("Use a unique label for accounts with the same sign-in address")
            priority = change.get("priority", state["priority_override"])
            if priority not in {None, "normal", "high", "critical"}:
                raise UserFacingError("Invalid priority")
            status = change.get("status")
            if status is not None and status not in {"pending", "in_progress", "done", "skipped"}:
                raise UserFacingError("Invalid status")
            if status == "done":
                if review:
                    raise UserFacingError("Identify this account before marking it done")
                # 1.x let a person finish without the MFA box; that choice is
                # recorded as "not applicable", never as reviewed.
                if new_steps["mfa_recovery"]["state"] == "open":
                    new_steps["mfa_recovery"] = {**new_steps["mfa_recovery"], "state": "not_applicable", "done_at": moment}
                if progress(new_decision["decision"], new_steps, bool(review))[0] != "complete":
                    raise UserFacingError("Check the required steps before marking this account done")
            batch = ChangeBatch(db)
            if new_decision != decision:
                decided_evidence = db.execute("SELECT COALESCE(MAX(id),0) FROM evidence").fetchone()[0]
                batch.record(account_id, "decision", decision, new_decision)
            else:
                decided_evidence = state["decided_evidence_id"]
            for step, value in new_steps.items():
                if value != steps[step]:
                    write_step(db, account_id, step, value)
                    batch.record(account_id, "step:" + step, steps[step], value)
            if status == "skipped":
                before = planning(db, account_id)
                defer_in_queue(db, account_id)
                batch.record(account_id, "planning", before, planning(db, account_id))
            db.execute("""UPDATE account_instances SET priority_override=?,login_method=?,manual_email=?,identity_email=?,
                          identity_review_required=?,label=?,decision=?,decision_reason=?,decided_at=?,
                          decided_evidence_id=?,updated=? WHERE id=?""",
                       (priority, method, manual_email, identity_email, review, label, new_decision["decision"],
                        new_decision["reason"], new_decision["decided_at"], decided_evidence, moment, account_id))
            batch.close()

    def _account_row(self, db, account_id):
        if not isinstance(account_id, str):
            raise UserFacingError("Invalid account update")
        row = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
        if row is None:
            if account_id not in self.registry.providers:
                raise UserFacingError("Invalid account update")
            insert_instance(db, account_id, ident=account_id)
            row = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
        return dict(row)

    def decide(self, account_id, decision, reason=None):
        """Axis B: the person confirms, rejects (with a reason) or reopens an account.

        Rejecting takes the account out of the worklist in the same logged batch,
        so one undo brings both back. Evidence is never changed.
        """
        if decision not in DECISIONS:
            raise UserFacingError("Choose confirmed, rejected or undecided")
        if (decision == "rejected") != (reason is not None) or (reason is not None and reason not in REJECT_REASONS):
            raise UserFacingError("Choose why this is not your account")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._account_row(db, account_id)
            old = {"decision": state["decision"], "reason": state["decision_reason"], "decided_at": state["decided_at"]}
            if old["decision"] == decision and old["reason"] == reason:
                return {"ok": True, "batch": None}
            new = {"decision": decision, "reason": reason, "decided_at": None if decision == "undecided" else now()}
            batch = ChangeBatch(db)
            batch.record(account_id, "decision", old, new)
            mark = db.execute("SELECT COALESCE(MAX(id),0) FROM evidence").fetchone()[0]
            db.execute("""UPDATE account_instances SET decision=?,decision_reason=?,decided_at=?,decided_evidence_id=?,
                          updated=? WHERE id=?""", (decision, reason, new["decided_at"], mark, now(), account_id))
            if decision == "rejected":
                before = planning(db, account_id)
                db.execute("DELETE FROM instance_work_queue WHERE account_id=?", (account_id,))
                batch.record(account_id, "planning", before, planning(db, account_id))
            return {"ok": True, "batch": batch.close()}

    def set_step(self, account_id, step, *, state=UNCHANGED, review_after=UNCHANGED):
        """Axis C: the person sets one step, or a local review date for it (A10).

        "prepared" is only ever set by a confirmed Bitwarden creation, and an
        account under identity review cannot have its identity step done.
        """
        if step not in STEPS:
            raise UserFacingError("Choose a valid security step")
        if state is not UNCHANGED and (state == "prepared" or not valid_step_state(step, state)):
            raise UserFacingError("This step cannot take that state")
        if review_after is not UNCHANGED and review_after is not None:
            review_after = review_date(review_after)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            account = self._account_row(db, account_id)
            if step == "identity" and state == "done" and account["identity_review_required"]:
                raise UserFacingError("Identify this account before marking it done")
            if step == "password" and state is not UNCHANGED and (state == "not_applicable") != (account["login_method"] != "password"):
                raise UserFacingError("The password step follows the sign-in method")
            current = read_steps(db, account_id, account["login_method"])[step]
            new = dict(current)
            if state is not UNCHANGED and state != current["state"]:
                new.update(state=state, done_at=None if state == "open" else now())
            if review_after is not UNCHANGED:
                new["review_after"] = review_after
            batch = ChangeBatch(db)
            if new != current:
                write_step(db, account_id, step, new)
                batch.record(account_id, "step:" + step, current, new)
                db.execute("UPDATE account_instances SET updated=? WHERE id=?", (now(), account_id))
            return {"ok": True, "batch": batch.close()}

    def link_sign_in(self, account_id, provider_account):
        """Record which confirmed account this one signs in with (plan A17, B6); None removes it."""
        from .identity import link_sign_in
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            link_sign_in(db, account_id, provider_account, now())
        return {"ok": True}

    def set_mailbox(self, address, account_id):
        """Record which confirmed account hosts the mailbox of an own address; None removes it."""
        from .identity import set_mailbox
        address = normalize_email(address) if isinstance(address, str) else None
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            set_mailbox(db, address, account_id, owned_emails(db), now())
        return {"ok": True}

    def set_automation_paused(self, pause):
        """Plan A27: block new jobs and stop running ones between two messages, or resume."""
        from .jobs import set_paused
        if type(pause) is not bool:
            raise UserFacingError("Choose pause or resume")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            set_paused(db, pause)
        return {"ok": True}

    def ensure_not_paused(self):
        """Refuse to prepare a new job while automation is paused (checked again when it starts)."""
        from .jobs import require_running
        with self.connect() as db:
            require_running(db)

    def record_activity(self, event, kind=None, outcome=None, counts=None):
        from .jobs import record
        with self.connect() as db:
            record(db, event, kind, outcome, counts)

    def control_overview(self, schedule=None):
        """Jobs, waiting work, the pause and recent activity in one place (plan D5)."""
        from .jobs import overview
        with self.connect() as db:
            return overview(db, schedule)

    def set_review_rule(self, months, scope=None):
        """Save the person's rule for proposing review dates (plan A10); None switches it off."""
        from .reviews import set_rule
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return {"rule": set_rule(db, months, scope)}

    def apply_review_proposals(self, ids):
        """Set each proposed review date as an ordinary, undoable step change."""
        if not isinstance(ids, list) or not ids or len(ids) > 10_000 or any(not isinstance(i, str) for i in ids):
            raise UserFacingError("Choose accounts with a suggested review date")
        from .reviews import REVIEW_STEP
        proposals = {account["id"]: account["review_proposal"] for account in self.snapshot()["accounts"]}
        if any(not proposals.get(account_id) for account_id in ids):
            raise UserFacingError("Choose accounts with a suggested review date")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            batch = ChangeBatch(db)
            for account_id in dict.fromkeys(ids):
                account = self._account_row(db, account_id)
                current = read_steps(db, account_id, account["login_method"])[REVIEW_STEP]
                new = {**current, "review_after": review_date(proposals[account_id])}
                write_step(db, account_id, REVIEW_STEP, new)
                batch.record(account_id, "step:" + REVIEW_STEP, current, new)
            return {"ok": True, "batch": batch.close()}

    def start_session(self, size):
        """Choose one or three ready worklist tasks to work on now (plan A8)."""
        from .sessions import start
        workflow = self.snapshot()["workflow"]
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return {"session": start(db, size, workflow, now())}

    def end_session(self):
        from .sessions import end
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            end(db)
        return {"ok": True}

    def session_report_text(self, language="en"):
        from .sessions import report_text
        session = self.snapshot()["session"]
        if not session:
            raise UserFacingError("There is no session to report")
        return report_text(session, language)

    def acknowledge_changes(self, revision):
        """Mark the changes the person saw as reviewed (plan A1); decisions stay untouched."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            acknowledge(db, revision, now())
        return {"ok": True}

    def undo_acknowledge_changes(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            undo_acknowledge(db)
        return {"ok": True}

    def add_provider(self, data):
        """Add a provider to this profile's own catalog (plan E5)."""
        from .catalog import add_provider
        return {"id": add_provider(self, data)}

    def remove_provider(self, ident):
        from .catalog import remove_provider
        remove_provider(self, ident)
        return {"ok": True}

    def exclude_domain(self, domain, reason):
        """Hide clues of one sender domain outside the catalog from the review (A9)."""
        from .review import exclude_domain
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return {"domain": exclude_domain(db, domain, reason, now())}

    def remove_exclusion(self, domain):
        from .review import remove_exclusion
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            remove_exclusion(db, domain)
        return {"ok": True}

    def relate_addresses(self, address, other, kind):
        """Record how two own addresses relate (E4); accounts stay separate."""
        from .review import relate
        if not isinstance(address, str) or not isinstance(other, str):
            raise UserFacingError("Relate two different addresses of your own")
        address, other = normalize_email(address), normalize_email(other)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            relate(db, address, other, kind, owned_emails(db), now())
        return {"ok": True}

    def remove_relation(self, address, other):
        from .review import remove_relation
        if not isinstance(address, str) or not isinstance(other, str):
            raise UserFacingError("These addresses have no saved relation")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            remove_relation(db, normalize_email(address), normalize_email(other))
        return {"ok": True}

    def undo(self, batch=None):
        """Revert one logged local change (ADR-0001, rule 3); external effects stay."""
        from .changes import undo
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return undo(db, batch)

    def recent_changes(self, limit=20):
        from .changes import recent
        if type(limit) is not int or not 1 <= limit <= 200:
            raise UserFacingError("Invalid account update")
        with self.connect() as db:
            return recent(db, limit)

    @staticmethod
    def _account_label(value):
        if not isinstance(value, str) or len(value) > 80 or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise UserFacingError("Account labels must contain at most 80 characters and no control characters")
        return value.strip()

    def create_account(self, data: dict):
        """Add one user-confirmed local identity; this never creates an online account."""
        if (not isinstance(data, dict) or set(data) != {"provider_id", "email", "label", "confirmed"}
                or data["confirmed"] is not True or not isinstance(data["provider_id"], str)
                or data["provider_id"] not in self.registry.providers or not isinstance(data["email"], str)):
            raise UserFacingError("Confirm the provider and your own sign-in address")
        provider_id, label = data["provider_id"], self._account_label(data["label"])
        email = normalize_email(data["email"]) if data["email"] else None
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if email and email not in owned_emails(db):
                raise UserFacingError("Use only explicitly configured own addresses")
            matches = db.execute("SELECT * FROM account_instances WHERE provider_id=? AND identity_email IS ?", (provider_id, email)).fetchall()
            if matches and (not label or any(row["label"].casefold() == label.casefold() for row in matches)):
                raise UserFacingError("Use a unique label for accounts with the same sign-in address")
            canonical = not any(row["canonical"] for row in matches)
            # The person verified the account and its sign-in in the same step.
            moment = now()
            steps = default_steps()
            steps["identity"].update(state="done", done_at=moment)
            ident = insert_instance(db, provider_id, email, canonical=canonical, label=label, manual=True,
                                    decision="confirmed", decided_at=moment, steps=steps)
        return ident

