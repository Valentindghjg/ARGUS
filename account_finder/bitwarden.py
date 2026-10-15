"""Password-free Bitwarden import formats and an opt-in official CLI handoff."""
from datetime import datetime, timezone
import base64
import json
import os
import shutil
import subprocess
from pathlib import Path
import uuid

from .store import Store, write_private
from .i18n import translate, validate_language
from . import handoffs


def make_export(store: Store, ids: list[str], language="en"):
    validate_language(language)
    if not isinstance(ids, list) or not ids or len(ids) > 10_000 or any(not isinstance(x, str) for x in ids):
        raise ValueError("An explicit selection is required")
    accounts = {a["id"]: a for a in store.snapshot(language)["accounts"]}
    selected = []
    for provider_id in dict.fromkeys(ids):
        account = accounts.get(provider_id)
        if not account or account["classification"] == "unknown":
            raise ValueError("Export only discovered accounts not already assigned in Bitwarden")
        if account.get("identity_review_required"):
            raise handoffs.HandoffError("Review this account's sign-in identity before transferring it.")
        if account["checklist"]["saved_in_bitwarden"]:
            raise ValueError("Export only discovered accounts not already assigned in Bitwarden")
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
                "notes": translate("Account-Finder: {classification}; review manually.\nEvidence: {reason}\nNo password exported. Generate a new password directly in Bitwarden and set it at the provider.",
                                   language, classification=translate(account["classification"], language), reason=account["reason"]),
                "fields": [{"name": "Account-Finder-ID", "value": account["id"], "type": 0},
                           {"name": "ARGUS-Provider-ID", "value": account["provider_id"], "type": 0}],
                "login": {"uris": [{"match": None, "uri": account["website"]}],
                          "username": email, "password": "", "totp": None},
                "collectionIds": [],
            })
    if not items:
        raise ValueError("Export only discovered accounts not already assigned in Bitwarden")
    return {"encrypted": False, "folders": [{"id": folder_id, "name": "Account-Finder · " + stamp}], "items": items}


def export_file(store: Store, path: Path, ids: list[str], language="en"):
    result = make_export(store, ids, language)
    # Never overwrite an existing export or a vault file.
    write_private(path, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return len(result["items"])


class BitwardenCliError(ValueError):
    """Safe failure that can be shown without exposing CLI output."""


def _run_cli(arguments: list[str], environment: dict[str, str], runner):
    """Run the official CLI without a shell and never surface its stdout/stderr."""
    try:
        result = runner(["bw", *arguments], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, env=environment, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BitwardenCliError("The Bitwarden CLI could not be started.") from exc
    if result.returncode:
        raise BitwardenCliError("Bitwarden did not accept the local vault request. Check that it is unlocked.")
    return result.stdout


def add_to_unlocked_cli(store: Store, ids: list[str], language="en", *, runner=subprocess.run, environment=None):
    """Create selected password-free items through an already-unlocked official CLI.

    The user must unlock Bitwarden before launching ARGUS. No master password,
    generated password, CLI output or session value is written to disk or returned.
    Existing vault items are never read, changed or overwritten.
    """
    validate_language(language)
    if store.meta("demo", False):
        raise BitwardenCliError("Direct Bitwarden transfer is disabled in the synthetic demo.")
    exported = make_export(store, ids, language)
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
        raise BitwardenCliError("Bitwarden must be unlocked before adding selected items.")

    created = 0
    completed_providers = []
    items_by_provider: dict[str, list[dict]] = {}
    for item in exported["items"]:
        provider_id = next(field["value"] for field in item["fields"] if field["name"] == "Account-Finder-ID")
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
                output = _run_cli(["create", "item", encoded], environment, runner)
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
