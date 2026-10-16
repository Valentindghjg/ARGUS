# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""An honest result summary (plan F3) and one reasoned next task (plan D1).

Both are derived from a snapshot and never stored. The summary counts only what
the imported emails show and names unclear items and gaps; it never claims that
every account was found. The next task is local work for the person; ARGUS
never acts at a provider.
"""

# Imports that stopped early need attention; skipped or unreadable messages are
# reported in the summary but are not a task the person can always resolve.
UNFINISHED_SCANS = {"partial", "limited"}


def result_summary(snapshot):
    accounts = snapshot["accounts"]
    scan = snapshot.get("last_scan") if isinstance(snapshot.get("last_scan"), dict) else {}
    unassigned = {account["provider_id"]: account["unassigned_evidence_count"] for account in accounts}
    live = [account for account in accounts if account["decision"] != "rejected"]
    return {
        "messages_processed": scan.get("processed", 0) if not scan.get("running") else None,
        "clues": snapshot["summary"]["clues"],
        "accounts_with_evidence": sum(account["evidence_level"] != "none" for account in live),
        "confirmed": sum(account["decision"] == "confirmed" for account in accounts),
        "rejected": sum(account["decision"] == "rejected" for account in accounts),
        "to_decide": sum(account["decision"] == "undecided" and account["evidence_level"] == "probable"
                         for account in accounts),
        "complete": sum(account["progress"] == "complete" for account in live),
        "unclear": {"identity_reviews": sum(account["identity_review_required"] for account in live),
                    "unassigned_clues": sum(unassigned.values()),
                    "unknown_domains": len(snapshot["candidates"])},
        "gaps": {"skipped": scan.get("skipped", 0), "errors": scan.get("errors", 0),
                 "headers_only": scan.get("headers_only", 0), "older_clues": snapshot["stale_evidence"],
                 "unfinished": scan.get("result") in UNFINISHED_SCANS or bool(scan.get("scope_changed"))},
    }


def next_task(snapshot):
    """The single next local task, most urgent first, with the account it concerns."""
    accounts = [account for account in snapshot["accounts"] if account["decision"] != "rejected"]
    by_id = {account["id"]: account for account in accounts}
    result = snapshot["result"]
    workflow = snapshot["workflow"]

    def task(kind, count=None, account=None):
        return {"kind": kind, "count": count, "account_id": account}

    if not result["clues"] and not snapshot.get("last_scan"):
        return task("import")
    if result["gaps"]["unfinished"]:
        return task("scan_gaps")
    review = [account["id"] for account in accounts if account["identity_review_required"]]
    if review:
        return task("identify", len(review), review[0])
    unclear = [entry for entry in snapshot["bitwarden_handoffs"] if entry["state"] in {"running", "uncertain"}]
    if unclear:
        return task("handoff", len(unclear), unclear[0]["account_id"])
    due = [account["id"] for account in accounts if account["reviews_due"]]
    if due:
        return task("review_due", len(due), due[0])
    if workflow["current"] in by_id and not workflow["paused"]:
        return task("continue", None, workflow["current"])
    undecided = [account["id"] for account in accounts
                 if account["decision"] == "undecided" and account["evidence_level"] == "probable"]
    if undecided:
        suggested = workflow["suggested"] if workflow["suggested"] in undecided else undecided[0]
        return task("decide", len(undecided), suggested)
    if workflow["suggested"] in by_id:
        return task("secure", None, workflow["suggested"])
    return task("done")
