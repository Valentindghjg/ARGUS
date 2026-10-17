# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Process only what changed, within a budget, and continue safely (plan A13, A14, A15).

A message counts as already processed when its content fingerprint was
analyzed before under the same conditions: the same own addresses, the same
catalog and the same rules. File names or dates are never used for this. Any
change to those conditions analyzes every message again. The index stores
fingerprints only, never message content. A budget limits how much new work
one run does; a run that hits it ends as "limited", never as complete, and the
next run of the same source continues where it stopped.
"""
from hashlib import sha256
import json

from .errors import UserFacingError

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_messages (
  fingerprint TEXT NOT NULL,
  scope TEXT NOT NULL,
  PRIMARY KEY(fingerprint, scope)
);
"""
MAX_BUDGET_MESSAGES = 1_000_000
MAX_BUDGET_MEGABYTES = 100_000


def scope_key(emails, registry, analysis_version):
    """Everything that can change an analysis result, as one digest."""
    catalog = sorted((provider.id, provider.domains) for provider in registry.providers.values())
    return sha256(json.dumps({"emails": sorted(emails), "catalog": catalog, "rules": analysis_version},
                             sort_keys=True).encode("utf-8")).hexdigest()


def known(db, fingerprint, scope):
    return db.execute("SELECT 1 FROM processed_messages WHERE fingerprint=? AND scope=?",
                      (fingerprint, scope)).fetchone() is not None


def remember(db, fingerprint, scope):
    db.execute("INSERT OR IGNORE INTO processed_messages(fingerprint,scope) VALUES (?,?)", (fingerprint, scope))


def forget_other_scopes(db, scope):
    """Fingerprints from earlier conditions can never match again; drop them."""
    db.execute("DELETE FROM processed_messages WHERE scope<>?", (scope,))


def budget(max_messages=None, max_megabytes=None):
    """A validated processing budget for one run, or None for no limit."""
    if max_messages is None and max_megabytes is None:
        return None
    if max_messages is not None and (type(max_messages) is not int or not 1 <= max_messages <= MAX_BUDGET_MESSAGES):
        raise UserFacingError("The message budget must be between 1 and 1000000")
    if max_megabytes is not None and (type(max_megabytes) is not int or not 1 <= max_megabytes <= MAX_BUDGET_MEGABYTES):
        raise UserFacingError("The size budget must be between 1 and 100000 MB")
    return {"messages": max_messages, "bytes": max_megabytes * 1024 * 1024 if max_megabytes else None}
