"""Private SQLite storage of evidence metadata, never message bodies or secrets."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

from .analysis import ANALYSIS_VERSION, Evidence, LABELS, english_caveat, normalize_email
from .instances import (SCHEMA as INSTANCE_SCHEMA, direct_identity, insert_instance,
                        migrate_instances, owned_emails, synchronize_instances)
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
            db.executescript(INSTANCE_SCHEMA)
            db.execute("BEGIN IMMEDIATE")
            migrate_instances(db, registry)
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
            synchronize_instances(db, self.registry, {evidence.provider_id})
            return "updated" if previous else "new"

    def snapshot(self, language="en"):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            synchronize_instances(db, self.registry)
            states = {}
            for row in db.execute("SELECT * FROM account_instances ORDER BY rowid"):
                states.setdefault(row["provider_id"], []).append(dict(row))
            evidences = [dict(r) for r in db.execute("SELECT * FROM evidence ORDER BY score DESC,id DESC")]
            own = owned_emails(db)
        grouped = {}
        unassigned = {}
        candidates = {}
        stale_evidence = 0
        for e in evidences:
            identity = direct_identity(e, own)
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
                "confirmed": 0, "status": "pending", "checklist": "{}",
                "priority_override": None, "login_method": "password", "manual_email": None,
                "updated": None,
            }]
            provider_clues = sorted(unassigned.get(provider_id, []), key=lambda e: (e["outdated"], -e["score"], -e["id"]))
            for state in provider_states:
                email = state["identity_email"]
                found = grouped.get((provider_id, email), []) if state["canonical"] and email else []
                found = sorted(found, key=lambda e: (e["outdated"], -e["score"], -e["id"]))
                score = max((e["score"] for e in found), default=0)
                classification = "confirmed" if state["confirmed"] else "probable" if score >= 60 else "unknown"
                checklist = {key: bool(json.loads(state["checklist"]).get(key, False)) for key in CHECKLIST}
                accounts.append({
                    **provider.public(), "id": state["id"], "provider_id": provider_id,
                    "identity_email": email, "label": state["label"],
                    "display_name": provider.name + (" · " + state["label"] if state["label"] else ""),
                    "identity_review_required": bool(state["identity_review_required"]),
                    "classification": classification, "score": score,
                    "confidence": "manually confirmed" if state["confirmed"] else "high" if score >= 85 else "medium" if score >= 60 else "low" if found else "no evidence",
                    "registered_emails": [email] if email else [], "manual_email": state["manual_email"],
                    "reason": "You confirmed that this account exists" if state["confirmed"] else found[0]["reason"] if found else "No local evidence; account existence is unknown",
                    "evidence": found[:30], "evidence_count": len(found),
                    "unassigned_evidence": provider_clues[:30], "unassigned_evidence_count": len(provider_clues),
                    "status": state["status"], "priority": state["priority_override"] or provider.priority,
                    "checklist": checklist, "login_method": state["login_method"], "updated": state["updated"],
                })
        rank = {"critical": 0, "high": 1, "normal": 2}
        accounts.sort(key=lambda a: (a["classification"] == "unknown", a["status"] == "done", rank[a["priority"]], a["name"].casefold()))
        found = [a for a in accounts if a["classification"] != "unknown"]
        done = sum(a["status"] == "done" and not a["identity_review_required"] for a in found)
        snapshot = {
            "accounts": accounts,
            "candidates": [{"domain": domain, "evidence": items[:10], "website": None,
                            "classification": "unknown", "reason": "Unverified sender domain; extend the catalog"}
                           for domain, items in sorted(candidates.items())],
            "summary": {"providers": len(self.registry.providers), "found": len(found),
                        "services_found": len({a["provider_id"] for a in found}), "instances_found": len(found),
                        "confirmed": sum(a["classification"] == "confirmed" for a in accounts),
                        "probable": sum(a["classification"] == "probable" for a in accounts), "unknown": len(accounts) - len(found),
                        "done": done, "high_priority": sum(a["priority"] in {"high", "critical"} and
                            (a["status"] != "done" or a["identity_review_required"]) for a in found),
                        "progress": round(done * 100 / len(found)) if found else 0},
            "emails": self.meta("emails", []), "demo": self.meta("demo", False),
            "last_scan": self.meta("last_scan"),
            "stale_evidence": stale_evidence, "analysis_version": ANALYSIS_VERSION,
        }
        from .product import public_product
        snapshot["product"] = public_product(self.data_dir)
        from .workflow import worklist_snapshot
        from .handoffs import handoff_snapshot
        snapshot["workflow"] = worklist_snapshot(self, accounts)
        snapshot["bitwarden_handoffs"] = handoff_snapshot(self)
        from .i18n import localize_snapshot
        return localize_snapshot(snapshot, language)

    def activate_license(self, document: dict):
        from .licensing import activate
        return activate(self.data_dir, document)

    def update_account(self, account_id: str, change: dict):
        allowed = {"checklist", "status", "priority", "login_method", "registered_email", "label"}
        if not isinstance(account_id, str) or not isinstance(change, dict) or set(change) - allowed:
            raise ValueError("Invalid account update")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
            if row is None:
                if account_id not in self.registry.providers:
                    raise ValueError("Invalid account update")
                insert_instance(db, account_id, ident=account_id)
                row = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
            state = dict(row)
            checklist = json.loads(state["checklist"])
            if "checklist" in change:
                additions = change["checklist"]
                if not isinstance(additions, dict) or set(additions) - set(CHECKLIST) or any(type(v) is not bool for v in additions.values()):
                    raise ValueError("Invalid checklist")
                checklist.update(additions)
            method = change.get("login_method", state["login_method"])
            manual_email, identity_email = state["manual_email"], state["identity_email"]
            review = state["identity_review_required"]
            if "registered_email" in change:
                proposed = change["registered_email"]
                if proposed is not None and not isinstance(proposed, str):
                    raise ValueError("Invalid sign-in address")
                proposed = normalize_email(proposed) if proposed else None
                if proposed and proposed not in owned_emails(db):
                    raise ValueError("Use only explicitly configured own addresses")
                if identity_email and proposed != identity_email:
                    raise ValueError("An existing account's sign-in address cannot be reassigned; add a separate account")
                if proposed and not identity_email:
                    if db.execute("SELECT 1 FROM instance_bitwarden_handoffs WHERE account_id=?", (account_id,)).fetchone():
                        raise ValueError("An account with a Bitwarden transfer cannot be assigned a different identity; add a separate account")
                    if db.execute("SELECT 1 FROM account_instances WHERE provider_id=? AND identity_email=? AND canonical=1 AND id<>?", (state["provider_id"], proposed, account_id)).fetchone():
                        raise ValueError("That sign-in address already belongs to a separate account")
                    identity_email, review = proposed, 0
                manual_email = proposed
            label = change.get("label", state["label"])
            label = self._account_label(label)
            if not state["canonical"] and not label:
                raise ValueError("Use a unique label for accounts with the same sign-in address")
            peers = db.execute("SELECT label FROM account_instances WHERE provider_id=? AND identity_email IS ? AND id<>?",
                               (state["provider_id"], identity_email, account_id)).fetchall()
            if label and any(peer["label"].casefold() == label.casefold() for peer in peers):
                raise ValueError("Use a unique label for accounts with the same sign-in address")
            if method not in {"password", "sso", "passkey"}:
                raise ValueError("Invalid sign-in method")
            priority = change.get("priority", state["priority_override"])
            if priority not in {None, "normal", "high", "critical"}:
                raise ValueError("Invalid priority")
            status = change.get("status", state["status"])
            if status not in {"pending", "in_progress", "done", "skipped"}:
                raise ValueError("Invalid status")
            if change.get("status") == "done" and review:
                raise ValueError("Identify this account before marking it done")
            required = ["reviewed", "saved_in_bitwarden", "login_tested"]
            if method == "password":
                required.append("password_changed")
            if status == "done" and not all(checklist.get(k) for k in required):
                if "status" in change:
                    raise ValueError("Check the required steps before marking this account done")
                status = "in_progress"
            if status == "pending" and any(checklist.values()):
                status = "in_progress"
            db.execute("""UPDATE account_instances SET confirmed=?,status=?,checklist=?,priority_override=?,login_method=?,manual_email=?,
                          identity_email=?,identity_review_required=?,label=?,updated=? WHERE id=?""",
                       (int(checklist.get("reviewed", False)), status, json.dumps(checklist), priority,
                        method, manual_email, identity_email, review, label, now(), account_id))

    @staticmethod
    def _account_label(value):
        if not isinstance(value, str) or len(value) > 80 or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("Account labels must contain at most 80 characters and no control characters")
        return value.strip()

    def create_account(self, data: dict):
        """Add one user-confirmed local identity; this never creates an online account."""
        if (not isinstance(data, dict) or set(data) != {"provider_id", "email", "label", "confirmed"}
                or data["confirmed"] is not True or not isinstance(data["provider_id"], str)
                or data["provider_id"] not in self.registry.providers or not isinstance(data["email"], str)):
            raise ValueError("Confirm the provider and your own sign-in address")
        provider_id, label = data["provider_id"], self._account_label(data["label"])
        email = normalize_email(data["email"]) if data["email"] else None
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if email and email not in owned_emails(db):
                raise ValueError("Use only explicitly configured own addresses")
            matches = db.execute("SELECT * FROM account_instances WHERE provider_id=? AND identity_email IS ?", (provider_id, email)).fetchall()
            if matches and (not label or any(row["label"].casefold() == label.casefold() for row in matches)):
                raise ValueError("Use a unique label for accounts with the same sign-in address")
            canonical = not any(row["canonical"] for row in matches)
            ident = insert_instance(db, provider_id, email, canonical=canonical, label=label,
                                    manual=True, state={"confirmed": 1, "status": "in_progress",
                                                        "checklist": json.dumps({"reviewed": True})})
        return ident

    def known_fingerprints(self):
        with self.connect() as db:
            return {r[0] for r in db.execute("SELECT fingerprint FROM evidence")}
