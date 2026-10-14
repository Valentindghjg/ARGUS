"""Private SQLite storage of evidence metadata, never message bodies or secrets."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

from .analysis import ANALYSIS_VERSION, Evidence, LABELS, english_caveat, normalize_email
from .registry import Registry

CHECKLIST = ("reviewed", "saved_in_bitwarden", "password_changed", "login_tested", "mfa_checked")


def now():
    return datetime.now(timezone.utc).isoformat()


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
        self.registry = registry
        with self.connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
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
                UNIQUE(fingerprint, sender_domain, signal)
              );
              CREATE INDEX IF NOT EXISTS evidence_provider ON evidence(provider_id);
            """)
            # Additive migration for inventories created by earlier local versions.
            columns = {row["name"] for row in db.execute("PRAGMA table_info(accounts)")}
            if "manual_email" not in columns:
                db.execute("ALTER TABLE accounts ADD COLUMN manual_email TEXT")
            evidence_columns = {row["name"] for row in db.execute("PRAGMA table_info(evidence)")}
            if "rule_version" not in evidence_columns:
                db.execute("ALTER TABLE evidence ADD COLUMN rule_version INTEGER NOT NULL DEFAULT 1")
            # A message's raw fingerprint is its identity across rule/catalogue revisions.
            indexes = {row["name"] for row in db.execute("PRAGMA index_list(evidence)")}
            if "evidence_fingerprint" not in indexes:
                db.execute("DELETE FROM evidence WHERE id NOT IN (SELECT MIN(id) FROM evidence GROUP BY fingerprint)")
                db.execute("CREATE UNIQUE INDEX evidence_fingerprint ON evidence(fingerprint)")
            db.executemany("INSERT OR IGNORE INTO accounts(provider_id,updated) VALUES (?,?)",
                           [(p, now()) for p in registry.providers])
        if os.name == "posix":
            self.path.chmod(0o600)

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

    def meta(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def configure(self, emails: list[str], demo=False):
        normalized = sorted({normalize_email(x) for x in emails})
        if not normalized:
            raise ValueError("At least one own email address is required")
        previous = self.meta("emails")
        if previous and previous != normalized:
            raise ValueError("A different initial address scope requires a new data directory; use add-email to add aliases")
        self.set_meta("emails", normalized)
        self.set_meta("demo", bool(demo))

    def add_emails(self, emails: list[str]):
        if not isinstance(emails, list) or not emails or any(not isinstance(e, str) for e in emails):
            raise ValueError("Specify your own email addresses as a list")
        extra = {normalize_email(e) for e in emails}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT value FROM meta WHERE key='emails'").fetchone()
            demo = db.execute("SELECT value FROM meta WHERE key='demo'").fetchone()
            if not current or (demo and json.loads(demo[0])):
                raise ValueError("Aliases require an initialized personal profile")
            previous = set(json.loads(current[0]))
            merged = sorted(previous | extra)
            if len(merged) > 64:
                raise ValueError("A profile supports up to 64 own addresses")
            added = sorted(extra - previous)
            if added:
                db.execute("UPDATE meta SET value=? WHERE key='emails'", (json.dumps(merged),))
                db.execute("INSERT INTO meta VALUES ('imap_cursors','{}') ON CONFLICT(key) DO UPDATE SET value='{}'")
        return added

    def add_evidence(self, evidence: Evidence) -> bool:
        return self.record_analysis(evidence.fingerprint, evidence) == "new"

    def record_analysis(self, fingerprint: str, evidence: Evidence | None, *, expected_emails=None):
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
                    return "removed"
                return "ignored"
            fields = ("provider_id", "sender_domain", "registered_email", "signal", "score", "date", "caveat", "rule_version")
            values = (evidence.provider_id, evidence.sender_domain, evidence.registered_email,
                      evidence.signal, evidence.score, evidence.date, evidence.caveat, ANALYSIS_VERSION)
            if previous and tuple(previous[f] for f in fields) == values:
                return "duplicate"
            db.execute("""INSERT INTO evidence
              (provider_id,sender_domain,registered_email,signal,score,fingerprint,date,source,caveat,rule_version)
              VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fingerprint) DO UPDATE SET
                provider_id=excluded.provider_id, sender_domain=excluded.sender_domain,
                registered_email=excluded.registered_email, signal=excluded.signal,
                score=excluded.score, date=excluded.date, caveat=excluded.caveat,
                rule_version=excluded.rule_version""", (
                evidence.provider_id, evidence.sender_domain, evidence.registered_email,
                evidence.signal, evidence.score, evidence.fingerprint, evidence.date,
                evidence.source, evidence.caveat, ANALYSIS_VERSION,
            ))
            return "updated" if previous else "new"

    def snapshot(self, language="en"):
        with self.connect() as db:
            states = {r["provider_id"]: dict(r) for r in db.execute("SELECT * FROM accounts")}
            evidences = [dict(r) for r in db.execute("SELECT * FROM evidence ORDER BY score DESC,id DESC")]
        grouped = {}
        candidates = {}
        stale_evidence = 0
        for e in evidences:
            e.pop("fingerprint")
            e["caveat"] = english_caveat(e["caveat"])
            e["outdated"] = e["rule_version"] < ANALYSIS_VERSION
            if e["outdated"]:
                stale_evidence += 1
                e["score"] = min(e["score"], 35)
                e["registered_email"] = None
            e["reason"] = LABELS[e["signal"]]
            if e["outdated"]:
                e["reason"] = "Older evidence; reanalyze the original message locally"
            if e["provider_id"]:
                grouped.setdefault(e["provider_id"], []).append(e)
            else:
                candidates.setdefault(e["sender_domain"], []).append(e)
        accounts = []
        for provider_id, provider in self.registry.providers.items():
            state = states[provider_id]
            found = sorted(grouped.get(provider_id, []), key=lambda e: (e["outdated"], -e["score"], -e["id"]))
            score = max((e["score"] for e in found), default=0)
            classification = "confirmed" if state["confirmed"] else "probable" if score >= 60 else "unknown"
            checklist = {key: bool(json.loads(state["checklist"]).get(key, False)) for key in CHECKLIST}
            accounts.append({
                **provider.public(), "classification": classification, "score": score,
                "confidence": "manually confirmed" if state["confirmed"] else "high" if score >= 85 else "medium" if score >= 60 else "low" if found else "no evidence",
                "registered_emails": sorted(({e["registered_email"] for e in found if e["registered_email"]} |
                                             ({state["manual_email"]} if state["manual_email"] else set()))),
                "manual_email": state["manual_email"],
                "reason": "You confirmed that this account exists" if state["confirmed"] else found[0]["reason"] if found else "No local evidence; account existence is unknown",
                "evidence": found[:30], "evidence_count": len(found), "status": state["status"],
                "priority": state["priority_override"] or provider.priority,
                "checklist": checklist, "login_method": state["login_method"], "updated": state["updated"],
            })
        rank = {"critical": 0, "high": 1, "normal": 2}
        accounts.sort(key=lambda a: (a["classification"] == "unknown", a["status"] == "done", rank[a["priority"]], a["name"].casefold()))
        found = [a for a in accounts if a["classification"] != "unknown"]
        done = sum(a["status"] == "done" for a in found)
        snapshot = {
            "accounts": accounts,
            "candidates": [{"domain": domain, "evidence": items[:10], "website": None,
                            "classification": "unknown", "reason": "Unverified sender domain; extend the catalog"}
                           for domain, items in sorted(candidates.items())],
            "summary": {"providers": len(accounts), "found": len(found), "confirmed": sum(a["classification"] == "confirmed" for a in accounts),
                        "probable": sum(a["classification"] == "probable" for a in accounts), "unknown": len(accounts) - len(found),
                        "done": done, "high_priority": sum(a["priority"] in {"high", "critical"} and a["status"] != "done" for a in found),
                        "progress": round(done * 100 / len(found)) if found else 0},
            "emails": self.meta("emails", []), "demo": self.meta("demo", False),
            "last_scan": self.meta("last_scan"),
            "stale_evidence": stale_evidence, "analysis_version": ANALYSIS_VERSION,
        }
        from .product import public_product
        snapshot["product"] = public_product()
        from .i18n import localize_snapshot
        return localize_snapshot(snapshot, language)

    def update_account(self, provider_id: str, change: dict):
        allowed = {"checklist", "status", "priority", "login_method", "registered_email"}
        if provider_id not in self.registry.providers or set(change) - allowed:
            raise ValueError("Invalid account update")
        with self.connect() as db:
            state = dict(db.execute("SELECT * FROM accounts WHERE provider_id=?", (provider_id,)).fetchone())
            checklist = json.loads(state["checklist"])
            if "checklist" in change:
                additions = change["checklist"]
                if not isinstance(additions, dict) or set(additions) - set(CHECKLIST) or any(type(v) is not bool for v in additions.values()):
                    raise ValueError("Invalid checklist")
                checklist.update(additions)
            method = change.get("login_method", state["login_method"])
            manual_email = change.get("registered_email", state["manual_email"])
            if manual_email is not None:
                if not isinstance(manual_email, str):
                    raise ValueError("Invalid sign-in address")
                manual_email = normalize_email(manual_email) if manual_email else None
                if manual_email and manual_email not in self.meta("emails", []):
                    raise ValueError("Use only explicitly configured own addresses")
            if method not in {"password", "sso", "passkey"}:
                raise ValueError("Invalid sign-in method")
            priority = change.get("priority", state["priority_override"])
            if priority not in {None, "normal", "high", "critical"}:
                raise ValueError("Invalid priority")
            status = change.get("status", state["status"])
            if status not in {"pending", "in_progress", "done", "skipped"}:
                raise ValueError("Invalid status")
            required = ["reviewed", "saved_in_bitwarden", "login_tested"]
            if method == "password":
                required.append("password_changed")
            if status == "done" and not all(checklist.get(k) for k in required):
                if "status" in change:
                    raise ValueError("Check the required steps before marking this account done")
                status = "in_progress"
            if status == "pending" and any(checklist.values()):
                status = "in_progress"
            db.execute("""UPDATE accounts SET confirmed=?,status=?,checklist=?,priority_override=?,login_method=?,manual_email=?,updated=?
                          WHERE provider_id=?""", (int(checklist.get("reviewed", False)), status,
                          json.dumps(checklist), priority, method, manual_email, now(), provider_id))

    def known_fingerprints(self):
        with self.connect() as db:
            return {r[0] for r in db.execute("SELECT fingerprint FROM evidence")}
