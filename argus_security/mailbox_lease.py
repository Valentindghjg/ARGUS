# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Cross-process exclusivity for the mailbox session of one profile.

Manual ``scan-imap`` runs and scheduled scans both hold this lease while they
are connected, so a profile never opens two IMAP sessions at once. The lease
record is metadata only: a random token, the run kind and an expiry time.
"""
from __future__ import annotations

import time
from typing import Any, Callable
from uuid import uuid4

from .imap_client import MailboxError
from .store import UNCHANGED, atomic_meta_update

LEASE_KEY = "imap_mailbox_lease"
LEASE_SECONDS = 5 * 60
# Renew well before expiry; between messages at most this often.
RENEW_SECONDS = 15
KINDS = frozenset({"manual", "scheduled"})


class MailboxBusy(MailboxError):
    """Another ARGUS process currently holds this profile's mailbox."""


class LeaseLost(MailboxError):
    """This process no longer holds the mailbox lease and must stop."""


def _active(value: Any, moment: float) -> bool:
    """A malformed or expired record never blocks a new session."""
    return (isinstance(value, dict) and isinstance(value.get("token"), str)
            and value.get("kind") in KINDS and type(value.get("lease_until")) in {int, float}
            and value["lease_until"] > moment)


class MailboxLease:
    """Acquire before connecting, ``keep_alive`` between messages, then release."""

    def __init__(self, store, *, kind: str, clock: Callable[[], float] | None = None):
        if kind not in KINDS:
            raise ValueError("Invalid mailbox lease kind")
        self.store = store
        self.kind = kind
        self.clock = clock if clock is not None else time.time
        self.token: str | None = None
        self._renewed = 0.0

    def acquire(self) -> "MailboxLease":
        token, moment = str(uuid4()), self.clock()

        def claim(value):
            if _active(value, moment):
                return UNCHANGED, False
            return {"token": token, "kind": self.kind, "lease_until": moment + LEASE_SECONDS}, True

        if not atomic_meta_update(self.store, LEASE_KEY, claim):
            raise MailboxBusy("Another ARGUS mailbox scan for this profile is running. Try again when it has finished.")
        self.token, self._renewed = token, moment
        return self

    def keep_alive(self) -> None:
        token, moment = self.token, self.clock()
        if token is None:
            raise LeaseLost("The mailbox scan stopped because another ARGUS process took over this mailbox. Saved progress is preserved.")
        if moment - self._renewed < RENEW_SECONDS:
            return

        def renew(value):
            # An expired lease may still be renewed while nobody else took it.
            if not isinstance(value, dict) or value.get("token") != token:
                return UNCHANGED, False
            return {**value, "lease_until": moment + LEASE_SECONDS}, True

        if not atomic_meta_update(self.store, LEASE_KEY, renew):
            self.token = None
            raise LeaseLost("The mailbox scan stopped because another ARGUS process took over this mailbox. Saved progress is preserved.")
        self._renewed = moment

    def release(self) -> None:
        token, self.token = self.token, None
        if token is None:
            return

        def free(value):
            if isinstance(value, dict) and value.get("token") == token:
                return None, True
            return UNCHANGED, False

        atomic_meta_update(self.store, LEASE_KEY, free)

    def __enter__(self) -> "MailboxLease":
        return self.acquire()

    def __exit__(self, *exc_info) -> None:
        self.release()
