"""Official Bitwarden JSON import format, with no password generation or vault API."""
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .store import Store, write_private
from .i18n import translate, validate_language


def make_export(store: Store, ids: list[str], language="en"):
    validate_language(language)
    if not isinstance(ids, list) or not ids or len(ids) > len(store.registry.providers) or any(not isinstance(x, str) for x in ids):
        raise ValueError("An explicit selection is required")
    accounts = {a["id"]: a for a in store.snapshot(language)["accounts"]}
    selected = []
    for provider_id in dict.fromkeys(ids):
        account = accounts.get(provider_id)
        if not account or account["classification"] == "unknown" or account["checklist"]["saved_in_bitwarden"]:
            raise ValueError("Export only discovered accounts not already assigned in Bitwarden")
        selected.append(account)
    folder_id = str(uuid.uuid4())
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    items = []
    for account in selected:
        # Multiple explicitly configured aliases can have distinct accounts.
        for email in account["registered_emails"] or [""]:
            items.append({
                "id": str(uuid.uuid4()), "organizationId": None, "folderId": folder_id,
                "type": 1, "reprompt": 0, "name": account["name"], "favorite": False,
                "notes": translate("Account-Finder: {classification}; review manually.\nEvidence: {reason}\nNo password exported. Generate a new password directly in Bitwarden and set it at the provider.",
                                   language, classification=translate(account["classification"], language), reason=account["reason"]),
                "fields": [{"name": "Account-Finder-ID", "value": account["id"], "type": 0}],
                "login": {"uris": [{"match": None, "uri": account["website"]}],
                          "username": email, "password": "", "totp": None},
                "collectionIds": [],
            })
    return {"encrypted": False, "folders": [{"id": folder_id, "name": "Account-Finder · " + stamp}], "items": items}


def export_file(store: Store, path: Path, ids: list[str], language="en"):
    result = make_export(store, ids, language)
    # Never overwrite an existing export or a vault file.
    write_private(path, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return len(result["items"])
