# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""The account state model of ADR-0001 in one place.

Five independent axes per account, each with exactly one owner:

A. evidence  (automatic, never stored)  none · weak · probable · stale
B. decision  (person)    undecided · confirmed · rejected (+ reason), dated
C. steps     (person)    identity, vault, password, signin_test, mfa_recovery,
                         each open · done · not_applicable (vault also prepared)
D. planning  (person)    worklist position and deferral, in instance_work_queue
E. external  (automatic after approval)  Bitwarden journal, scans

Progress and the next step are derived for display and never stored. A
completed progress records only the person's own steps; it is no security
guarantee.
"""
from datetime import date, timedelta
import json

from .errors import UserFacingError

DECISIONS = ("undecided", "confirmed", "rejected")
REJECT_REASONS = ("not_mine", "not_an_account", "closed")
STEPS = ("identity", "vault", "password", "signin_test", "mfa_recovery")
STEP_STATES = ("open", "done", "not_applicable", "prepared")
# Every step must be done or, where allowed, explicitly not applicable. Only the
# password (single sign-on, passkey) and MFA/recovery (not offered or not used)
# can be not applicable, so "complete" always means each question was answered.
REQUIRED_STEPS = STEPS
EVIDENCE_LEVELS = ("none", "weak", "probable", "stale")
PROBABLE_SCORE = 60

# Checklist keys of the 1.x API and snapshot, kept for one major version.
LEGACY_STEPS = {"saved_in_bitwarden": "vault", "password_changed": "password",
                "login_tested": "signin_test", "mfa_checked": "mfa_recovery"}
LEGACY_CHECKLIST = ("reviewed", "saved_in_bitwarden", "password_changed", "login_tested", "mfa_checked")


def valid_step_state(step, state):
    if step not in STEPS or state not in STEP_STATES:
        return False
    if state == "prepared":
        return step == "vault"
    if state == "not_applicable":
        # Only a sign-in without a separate password, or no MFA offered, can skip a step.
        return step in {"password", "mfa_recovery"}
    return True


def review_date(value, today=None):
    """A local review date for a step (A10): a calendar day within the next five years."""
    # The person's own calendar day, the same one the date field showed them.
    today = today or date.today()
    if not isinstance(value, str):
        raise UserFacingError("Choose a review date within the next five years")
    try:
        chosen = date.fromisoformat(value)
    except ValueError as exc:
        raise UserFacingError("Choose a review date within the next five years") from exc
    if not today < chosen <= today + timedelta(days=5 * 366):
        raise UserFacingError("Choose a review date within the next five years")
    return chosen.isoformat()


def default_steps(login_method="password"):
    steps = {step: {"state": "open", "done_at": None, "review_after": None} for step in STEPS}
    if login_method != "password":
        steps["password"]["state"] = "not_applicable"
    return steps


def evidence_level(evidence):
    """Axis A from the account's own evidence rows (already capped for stale rows)."""
    if not evidence:
        return "none"
    if all(item.get("outdated") for item in evidence):
        return "stale"
    return "probable" if max(item["score"] for item in evidence) >= PROBABLE_SCORE else "weak"


def progress(decision, steps, review_required=False):
    """Derived: not_started, in_progress or complete, with the completion time."""
    required = [step for step in REQUIRED_STEPS if steps[step]["state"] != "not_applicable"]
    if (decision == "confirmed" and not review_required
            and all(steps[step]["state"] == "done" for step in required)):
        times = [steps[step]["done_at"] for step in required if steps[step]["done_at"]]
        return "complete", max(times) if times else None
    started = decision == "confirmed" or any(item["state"] in {"done", "prepared"} for item in steps.values())
    return ("in_progress" if started else "not_started"), None


def legacy_reviewed(decision, steps):
    """The 1.x "reviewed" box meant: this account exists, and I checked its sign-in."""
    return decision == "confirmed" and steps["identity"]["state"] == "done"


def legacy_checklist(decision, steps):
    checklist = {"reviewed": legacy_reviewed(decision, steps)}
    for key, step in LEGACY_STEPS.items():
        checklist[key] = steps[step]["state"] == "done"
    return checklist


def legacy_status(progress_value, deferred):
    if progress_value == "complete":
        return "done"
    if deferred:
        return "skipped"
    return "in_progress" if progress_value == "in_progress" else "pending"


def legacy_classification(decision, level):
    if decision == "confirmed":
        return "confirmed"
    if decision == "rejected":
        return "unknown"
    return "probable" if level == "probable" else "unknown"


def from_legacy(state, journal_created):
    """Map one 1.x account row to (decision, decided_at, steps) for the migration.

    The 1.x "reviewed" box covered both existence and sign-in, so it confirms
    the decision and the identity step (identity stays open while an identity
    review is pending). A completed 1.x account has every step done; its MFA
    step, which 1.x let the person leave unticked, becomes not applicable
    rather than claimed. A vault item ARGUS created stays "prepared" until the
    person confirms the password is stored, unless the account was done.
    """
    try:
        checklist = json_checklist(state["checklist"])
    except ValueError:
        checklist = {}
    updated = state.get("updated")
    done = state.get("status") == "done"
    reviewed = bool(checklist.get("reviewed") or state.get("confirmed"))
    decision = "confirmed" if reviewed or done else "undecided"
    steps = default_steps(state.get("login_method") or "password")

    def mark(step, flag):
        if flag:
            steps[step].update(state="done", done_at=updated)

    mark("identity", (reviewed or done) and not state.get("identity_review_required"))
    if checklist.get("saved_in_bitwarden"):
        if journal_created and not done:
            steps["vault"].update(state="prepared", done_at=updated)
        else:
            mark("vault", True)
    if steps["password"]["state"] != "not_applicable":
        mark("password", checklist.get("password_changed") or done)
    mark("signin_test", checklist.get("login_tested") or done)
    mark("mfa_recovery", checklist.get("mfa_checked"))
    if done:
        mark("vault", True)
        if steps["mfa_recovery"]["state"] == "open":
            steps["mfa_recovery"].update(state="not_applicable", done_at=updated)
    return decision, (updated if decision == "confirmed" else None), steps


def json_checklist(value):
    data = json.loads(value) if isinstance(value, str) else value
    if not isinstance(data, dict):
        raise ValueError("Invalid checklist")
    return data
