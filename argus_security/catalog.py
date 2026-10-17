# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""The profile's own catalog additions (plan E5), validated like the built-in catalog.

An addition is a provider with a name, an official HTTPS website, a category
and its sender domains. It lives in ``my-providers.json`` inside the private
profile, never in the shared catalog, and no DNS or web request checks it.
Shared sending services are refused, because they send mail for many
companies. Clues that arrived before an addition need their original email
again; ARGUS cannot re-read a message it never stored.
"""
import json
import os
from pathlib import Path
import re
import tempfile

from .errors import UserFacingError
from .registry import Registry, is_shared_sender, normalize_domain

PERSONAL_CATALOG = "my-providers.json"
PRIORITIES = ("normal", "high", "critical")


def _personal_rows(path: Path):
    if not path.is_file() or path.is_symlink():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["providers"] if isinstance(data, dict) else data)


def _write_private(path: Path, rows):
    fd, temporary = tempfile.mkstemp(prefix=".my-providers-", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"providers": rows}, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        if os.name == "posix":
            os.chmod(temporary, 0o600)
        return Path(temporary)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _slug(name):
    return (re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")[:60] or "provider") + "-mine"


def add_provider(store, data):
    """Validate one addition against the full catalog and save it atomically."""
    shape = {"name", "website", "category", "domains", "priority"}
    if not isinstance(data, dict) or set(data) != shape:
        raise UserFacingError("Fill in name, website, category, domains and priority")
    name, website, category, priority = data["name"], data["website"], data["category"], data["priority"]
    domains = data["domains"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100 or any(ord(c) < 32 for c in name):
        raise UserFacingError("Use a provider name with 1 to 100 characters")
    categories = {provider.category for provider in store.registry.providers.values() if provider.source == "builtin"}
    if category not in categories:
        raise UserFacingError("Choose one of the existing categories")
    if priority not in PRIORITIES:
        raise UserFacingError("Invalid priority")
    if not isinstance(domains, list) or not 1 <= len(domains) <= 5 or any(not isinstance(d, str) for d in domains):
        raise UserFacingError("Add between one and five sender domains")
    domains = [normalize_domain(domain) for domain in domains]
    if any(is_shared_sender(domain) for domain in domains):
        raise UserFacingError("A shared sending service sends mail for many companies; it cannot identify a provider")
    if not isinstance(website, str):
        raise UserFacingError("The official website must be an HTTPS address")
    ident = _slug(name)
    taken = set(store.registry.providers)
    suffix = 2
    while ident in taken:
        ident, suffix = f"{_slug(name)}-{suffix}", suffix + 1
    row = {"id": ident, "name": name.strip(), "website": website, "category": category,
           "domains": domains, "priority": priority}
    # A sub-domain of a catalog provider would take its mail away from it.
    if any(store.registry.match(domain) for domain in domains):
        raise UserFacingError("This domain already belongs to a provider in the catalog")
    try:
        store.registry.check_addition(row)
    except UserFacingError:
        raise
    except ValueError as exc:
        # The registry's own texts may contain data; show only fixed messages.
        message = str(exc)
        if message.startswith("Ambiguous domain in the catalog"):
            raise UserFacingError("This domain already belongs to a provider in the catalog") from None
        if message == "Provider links must be valid HTTPS URLs":
            raise UserFacingError("The official website must be an HTTPS address") from None
        if message == "The link is outside the provider domains":
            raise UserFacingError("The official website must belong to one of the sender domains") from None
        raise UserFacingError("Check the provider details") from None
    target = store.data_dir / PERSONAL_CATALOG
    candidate = _write_private(target, _personal_rows(target) + [row])
    try:
        os.replace(candidate, target)
    finally:
        candidate.unlink(missing_ok=True)
    store.registry = Registry(store.registry.custom, target)
    return ident


def remove_provider(store, ident):
    """Remove an addition that no clue, decision or step refers to yet, or one the catalog now skips."""
    provider = store.registry.providers.get(ident) if isinstance(ident, str) else None
    skipped = isinstance(ident, str) and any(entry["id"] == ident for entry in store.registry.skipped_personal)
    if not skipped and (provider is None or provider.source != "personal"):
        raise UserFacingError("Only providers you added yourself can be removed")
    with store.connect() as db:
        used = (db.execute("SELECT 1 FROM evidence WHERE provider_id=?", (ident,)).fetchone()
                or db.execute("""SELECT 1 FROM account_instances WHERE provider_id=? AND (decision<>'undecided'
                                 OR EXISTS (SELECT 1 FROM account_steps s WHERE s.account_id=account_instances.id))""",
                              (ident,)).fetchone())
    if used and not skipped:
        raise UserFacingError("This provider already has clues or your decisions; keep it or reject the account instead")
    target = store.data_dir / PERSONAL_CATALOG
    rows = [row for row in _personal_rows(target) if row.get("id") != ident]
    candidate = _write_private(target, rows)
    try:
        os.replace(candidate, target)
    finally:
        candidate.unlink(missing_ok=True)
    store.registry = Registry(store.registry.custom, target)


def personal_providers(registry):
    return [provider.public() for provider in registry.providers.values() if provider.source == "personal"]


def categories(registry):
    return sorted({provider.category for provider in registry.providers.values() if provider.source == "builtin"})
