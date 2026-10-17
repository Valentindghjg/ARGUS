# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Confirmed identity relations (plan A17, B6) and explained priorities (D3).

Two relations, both stated by the person and never inferred from emails or
website visits:

- an account signs in with another account (single sign-on), and
- the mailbox of an own address is hosted by an account, so password resets
  for every account with that address arrive there.

Accounts that others depend on in this way are treated as critical, with the
reason shown. A priority the person chooses always wins. Priorities are a work
aid that orders tasks; they are not a measured likelihood of attack.
"""
from .errors import UserFacingError

SCHEMA = """
CREATE TABLE IF NOT EXISTS sign_in_links (
  account_id TEXT PRIMARY KEY,
  provider_account TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mailbox_accounts (
  address TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""
LEVELS = ("normal", "high", "critical")


def _account(db, account_id):
    if not isinstance(account_id, str):
        return None
    return db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()


def _confirmed_provider(db, account_id):
    row = _account(db, account_id)
    if row is None or row["decision"] != "confirmed":
        raise UserFacingError("Choose an account you confirmed yourself")
    return row


def link_sign_in(db, account_id, provider_account, moment):
    """Record that ``account_id`` signs in with ``provider_account``, or remove it with None."""
    row = _account(db, account_id)
    if row is None:
        raise UserFacingError("Invalid account update")
    if provider_account is None:
        db.execute("DELETE FROM sign_in_links WHERE account_id=?", (account_id,))
        return
    if row["login_method"] != "sso":
        raise UserFacingError("Set the sign-in method to single sign-on first")
    _confirmed_provider(db, provider_account)
    # Walk the existing chain: the provider must not already depend on this account.
    current, seen = provider_account, set()
    while current is not None and current not in seen:
        if current == account_id:
            raise UserFacingError("An account cannot sign in with itself, directly or through others")
        seen.add(current)
        link = db.execute("SELECT provider_account FROM sign_in_links WHERE account_id=?", (current,)).fetchone()
        current = link[0] if link else None
    db.execute("""INSERT INTO sign_in_links(account_id,provider_account,created_at) VALUES (?,?,?)
                  ON CONFLICT(account_id) DO UPDATE SET provider_account=excluded.provider_account,
                  created_at=excluded.created_at""", (account_id, provider_account, moment))


def set_mailbox(db, address, account_id, owned, moment):
    """Record which account hosts the mailbox of an own address, or remove it with None."""
    if address not in owned:
        raise UserFacingError("Use only explicitly configured own addresses")
    if account_id is None:
        db.execute("DELETE FROM mailbox_accounts WHERE address=?", (address,))
        return
    _confirmed_provider(db, account_id)
    db.execute("""INSERT INTO mailbox_accounts(address,account_id,created_at) VALUES (?,?,?)
                  ON CONFLICT(address) DO UPDATE SET account_id=excluded.account_id,created_at=excluded.created_at""",
               (address, account_id, moment))


def load(db):
    return {"sign_in": {row["account_id"]: row["provider_account"] for row in db.execute("SELECT * FROM sign_in_links")},
            "mailboxes": {row["address"]: row["account_id"] for row in db.execute("SELECT * FROM mailbox_accounts")}}


def explain_priorities(accounts, relations):
    """Set each account's priority and its reasons from the catalog, relations and the person's choice.

    A relation counts only while it is valid: the dependent account still uses
    single sign-on and the identity account is still confirmed. Inactive
    relations stay listed so the person can remove them.
    """
    by_id = {account["id"]: account for account in accounts}
    confirmed = {account["id"] for account in accounts if account["decision"] == "confirmed"}
    sign_in = {}
    for account_id, provider in relations["sign_in"].items():
        account = by_id.get(account_id)
        active = bool(account) and account["login_method"] == "sso" and provider in confirmed
        sign_in[account_id] = {"account_id": account_id, "provider_account": provider, "active": active}
    mailboxes = {address: {"address": address, "account_id": holder, "active": holder in confirmed}
                 for address, holder in relations["mailboxes"].items()}
    for account in accounts:
        reasons = [{"code": "catalog", "level": account["catalog_priority"]}]
        level = account["catalog_priority"]
        users = [link["account_id"] for link in sign_in.values()
                 if link["active"] and link["provider_account"] == account["id"]]
        hosted = sorted(entry["address"] for entry in mailboxes.values()
                        if entry["active"] and entry["account_id"] == account["id"])
        resets = [other["id"] for other in accounts
                  if other["id"] != account["id"] and other["decision"] != "rejected"
                  and other["identity_email"] in hosted]
        if hosted:
            reasons.append({"code": "mailbox", "addresses": hosted, "count": len(resets)})
            level = "critical"
        if users:
            reasons.append({"code": "sso_provider", "count": len(users)})
            level = "critical"
        link = sign_in.get(account["id"])
        if link and link["active"]:
            reasons.append({"code": "signs_in_with", "account_id": link["provider_account"]})
        if account["priority_override"]:
            reasons.append({"code": "override", "level": account["priority_override"]})
        account["automatic_priority"] = level
        account["priority"] = account["priority_override"] or level
        account["priority_reasons"] = reasons
        account["dependents"] = len(set(users) | set(resets))
        account["signs_in_with"] = link["provider_account"] if link else None
    return {"sign_in": sorted(sign_in.values(), key=lambda link: link["account_id"]),
            "mailboxes": sorted(mailboxes.values(), key=lambda entry: entry["address"])}
