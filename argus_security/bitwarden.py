# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Password-free Bitwarden import formats and an opt-in official CLI handoff."""
from datetime import datetime, timezone
import base64
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import uuid

from .errors import UserFacingError
from .store import Store, write_private
from .i18n import translate, validate_language
from . import handoffs

# Custom field that links a vault item to its local ARGUS account. Items created
# before the ARGUS rename carry the legacy name; the read-only audit accepts both.
ACCOUNT_FIELD = "ARGUS-Account-ID"
LEGACY_ACCOUNT_FIELDS = frozenset({ACCOUNT_FIELD, "Account-Finder-ID"})


def make_export(store: Store, ids: list[str], language="en"):
    validate_language(language)
    if not isinstance(ids, list) or not ids or len(ids) > 10_000 or any(not isinstance(x, str) for x in ids):
        raise UserFacingError("An explicit selection is required")
    accounts = {a["id"]: a for a in store.snapshot(language)["accounts"]}
    selected = []
    for provider_id in dict.fromkeys(ids):
        account = accounts.get(provider_id)
        if not account or account["classification"] == "unknown":
            raise UserFacingError("Export only discovered accounts not already assigned in Bitwarden")
        if account.get("identity_review_required"):
            raise handoffs.HandoffError("Review this account's sign-in identity before transferring it.")
        if account["checklist"]["saved_in_bitwarden"]:
            raise UserFacingError("Export only discovered accounts not already assigned in Bitwarden")
        selected.append(account)
    folder_id = str(uuid.uuid4())
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    items = []
    previous = {(entry["account_id"], entry["email"]): entry["state"]
                for entry in handoffs.handoff_snapshot(store)}
    for account in selected:
        # Every selection is one durable account, with at most one sign-in
        # identity. Sibling accounts never inherit assignment or completion.
        for email in account["registered_emails"] or [""]:
            state = previous.get((account["id"], email))
            if state in {"running", "uncertain"}:
                raise handoffs.HandoffError("Check the unresolved Bitwarden transfer before trying again.")
            if state == "created":
                continue
            items.append({
                "id": str(uuid.uuid4()), "organizationId": None, "folderId": folder_id,
                "type": 1, "reprompt": 0,
                "name": account["name"] + (" · " + account["label"] if account.get("label") else ""), "favorite": False,
                "notes": translate("ARGUS: {classification}; review manually.\nEvidence: {reason}\nNo password exported. Generate a new password directly in Bitwarden and set it at the provider.",
                                   language, classification=translate(account["classification"], language), reason=account["reason"]),
                "fields": [{"name": ACCOUNT_FIELD, "value": account["id"], "type": 0},
                           {"name": "ARGUS-Provider-ID", "value": account["provider_id"], "type": 0}],
                "login": {"uris": [{"match": None, "uri": account["website"]}],
                          "username": email, "password": "", "totp": None},
                "collectionIds": [],
            })
    if not items:
        raise UserFacingError("Export only discovered accounts not already assigned in Bitwarden")
    return {"encrypted": False, "folders": [{"id": folder_id, "name": "ARGUS · " + stamp}], "items": items}


def export_file(store: Store, path: Path, ids: list[str], language="en"):
    result = make_export(store, ids, language)
    # Never overwrite an existing export or a vault file.
    write_private(path, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return len(result["items"])


class BitwardenCliError(UserFacingError):
    """Safe failure that can be shown without exposing CLI output."""


def _run_cli(arguments: list[str], environment: dict[str, str], runner, stdin_data: str | None = None):
    """Run the official CLI without a shell and never surface its stdout/stderr.

    Item payloads travel through stdin (``bw create item`` reads its encoded
    JSON there when no argument is given), so account names and sign-in
    addresses never appear in the process list that other local users can read.
    """
    source = {"input": stdin_data} if stdin_data is not None else {"stdin": subprocess.DEVNULL}
    try:
        result = runner(["bw", *arguments], **source, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, env=environment, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BitwardenCliError("The Bitwarden CLI could not be started.") from exc
    if result.returncode:
        raise BitwardenCliError("Bitwarden did not accept the local vault request. Check that it is unlocked.")
    return result.stdout


def _unlocked_environment(store: Store, environment, runner):
    if store.meta("demo", False):
        raise BitwardenCliError("Direct Bitwarden transfer is disabled in the synthetic demo.")
    environment = dict(os.environ if environment is None else environment)
    if not environment.get("BW_SESSION"):
        raise BitwardenCliError("Unlock Bitwarden first, then start ARGUS from that same terminal session.")
    if not shutil.which("bw"):
        raise BitwardenCliError("The official Bitwarden CLI is not installed or not on PATH.")
    try:
        status = json.loads(_run_cli(["status"], environment, runner))
    except json.JSONDecodeError as exc:
        raise BitwardenCliError("The Bitwarden CLI returned an unexpected status.") from exc
    if not isinstance(status, dict) or status.get("status") != "unlocked":
        raise BitwardenCliError("Bitwarden must be unlocked before continuing.")
    return environment


def _audit_accounts(store: Store, ids: list[str], language):
    validate_language(language)
    if not isinstance(ids, list) or not ids or len(ids) > 10_000 or any(not isinstance(item, str) for item in ids):
        raise UserFacingError("An explicit selection is required")
    accounts = {account["id"]: account for account in store.snapshot(language)["accounts"]}
    selected = []
    for account_id in dict.fromkeys(ids):
        account = accounts.get(account_id)
        if not account or account["classification"] == "unknown":
            raise UserFacingError("Select discovered accounts for the Bitwarden check")
        if account.get("identity_review_required"):
            raise handoffs.HandoffError("Review this account's sign-in identity before checking Bitwarden.")
        selected.append(account)
    return selected


def _host(value):
    if not isinstance(value, str):
        return ""
    parsed = urlparse(value if "://" in value else "https://" + value)
    return (parsed.hostname or "").casefold()


def _audit_result(account, items):
    """Return only a small match summary; never retain vault fields or secrets."""
    official_host = _host(account["website"])
    email = (account["identity_email"] or account["manual_email"] or "").casefold()
    exact = possible = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = item.get("fields") if isinstance(item.get("fields"), list) else []
        argus_id = next((field.get("value") for field in fields if isinstance(field, dict)
                         and field.get("name") in LEGACY_ACCOUNT_FIELDS), None)
        if argus_id == account["id"]:
            exact += 1
            continue
        login = item.get("login") if isinstance(item.get("login"), dict) else {}
        uris = login.get("uris") if isinstance(login.get("uris"), list) else []
        hosts = {_host(uri.get("uri")) for uri in uris if isinstance(uri, dict)}
        same_host = bool(official_host and official_host in hosts)
        same_email = bool(email and isinstance(login.get("username"), str)
                          and login["username"].casefold() == email)
        if same_host and same_email:
            exact += 1
        elif same_host or (isinstance(item.get("name"), str)
                           and item["name"].casefold() == account["name"].casefold()):
            possible += 1
    return {"account_id": account["id"], "match": "found" if exact else "possible" if possible else "none",
            "count": exact or possible}


def audit_unlocked_cli(store: Store, ids: list[str], language="en", *, runner=subprocess.run, environment=None):
    """Check selected account metadata in an already-unlocked vault without writes.

    Bitwarden's CLI response can contain password fields. They are examined only
    inside this function to derive a tiny local result and are neither persisted,
    logged nor returned to the browser.
    """
    selected = _audit_accounts(store, ids, language)
    environment = _unlocked_environment(store, environment, runner)
    results = []
    for account in selected:
        try:
            payload = json.loads(_run_cli(["list", "items", "--search", account["name"]], environment, runner))
        except json.JSONDecodeError as exc:
            raise BitwardenCliError("The Bitwarden CLI returned an unexpected vault response.") from exc
        if not isinstance(payload, list) or len(payload) > 10_000:
            raise BitwardenCliError("The Bitwarden CLI returned an unexpected vault response.")
        results.append(_audit_result(account, payload))
    return {"accounts": results}


def add_to_unlocked_cli(store: Store, ids: list[str], language="en", *, runner=subprocess.run, environment=None):
    """Create selected password-free items through an already-unlocked official CLI.

    The user must unlock Bitwarden before launching ARGUS. No master password,
    generated password, CLI output or session value is written to disk or returned.
    Existing vault items are never read, changed or overwritten.
    """
    validate_language(language)
    exported = make_export(store, ids, language)
    environment = _unlocked_environment(store, environment, runner)

    created = 0
    completed_providers = []
    items_by_provider: dict[str, list[dict]] = {}
    for item in exported["items"]:
        provider_id = next(field["value"] for field in item["fields"] if field["name"] == ACCOUNT_FIELD)
        items_by_provider.setdefault(provider_id, []).append(item)

    for provider_id, items in items_by_provider.items():
        for item in items:
            attempt = handoffs.reserve(store, provider_id, item["login"]["username"])
            if attempt is None:
                continue
            # Keep the item intentionally password-free. Its encoded payload is only
            # metadata and is discarded immediately after the CLI accepts it.
            document = {
                "type": 1, "name": item["name"], "favorite": False,
                "notes": item["notes"], "fields": [*item["fields"],
                    {"name": "ARGUS-Transfer-ID", "value": attempt["operation_id"], "type": 0}],
                "login": {"uris": item["login"]["uris"], "username": item["login"]["username"],
                          "password": None, "totp": None},
            }
            encoded = base64.b64encode(json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).decode("ascii")
            try:
                output = _run_cli(["create", "item"], environment, runner, stdin_data=encoded)
                result = json.loads(output)
                item_id = str(uuid.UUID(result["id"]))
            except (BitwardenCliError, ValueError, KeyError, TypeError, AttributeError):
                # Even a failed process may have committed the server-side write.
                handoffs.finish(store, attempt, "uncertain")
                return {"items": created, "providers": completed_providers, "status": "needs_review"}
            handoffs.finish(store, attempt, "created", item_id)
            created += 1
        if handoffs.mark_assigned_if_complete(store, provider_id):
            completed_providers.append(provider_id)
    return {"items": created, "providers": completed_providers, "status": "completed"}
