# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Synthetic detection benchmark (plan G5).

Runs the invented messages in ``benchmarks/detection-cases.json`` through the
same analysis as an import and compares each outcome with the case's ground
truth and with what the case documents. It shows typical hits, false alarms
and known limits of the rules. The cases are synthetic, so the numbers are not
proof of accuracy on real mailboxes.

Usage: python scripts/benchmark.py [--json] [--cases PATH]
Exits with 1 when an outcome differs from the documented one or a gap between
truth and outcome has no documented limit.
"""
import argparse
from collections import Counter
from email.message import EmailMessage
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from argus_security.analysis import HEADERS_ONLY_MARKER, analyze  # noqa: E402
from argus_security.registry import Registry  # noqa: E402
from argus_security.states import PROBABLE_SCORE  # noqa: E402

CASES = ROOT / "benchmarks" / "detection-cases.json"
DISCLAIMER = ("Synthetic cases only. The result shows how the rules treat typical hits, false alarms and "
              "edge cases; it is not proof of accuracy on real mailboxes.")
OTHER = "someone@example.invalid"
# Outcomes in the order a person sees them: counted, kept for review, ignored.
OUTCOMES = ("probable", "weak", "unknown_domain", "none")


def build(mail, own):
    """One invented message; recipients are placeholders, never real addresses."""
    names = {"own": own[0], "second": own[1], "other": OTHER}
    message = EmailMessage()
    message["From"] = names.get(mail["from"], mail["from"])
    message["To"] = ", ".join(names[name] for name in mail["to"])
    if mail.get("cc"):
        message["Cc"] = ", ".join(names[name] for name in mail["cc"])
    message["Subject"] = mail["subject"]
    message["Date"] = "Mon, 05 Oct 2026 10:00:00 +0000"
    if mail.get("list"):
        message["List-Unsubscribe"] = "<https://example.invalid/unsubscribe>"
    if mail.get("headers_only"):
        message[HEADERS_ONLY_MARKER.decode("ascii")] = "yes"
    if mail.get("html"):
        message.set_content("<p>" + mail["body"] + "</p>", subtype="html")
    else:
        message.set_content(mail["body"])
    return message.as_bytes()


def outcome(evidence):
    if evidence is None:
        return "none"
    if evidence.provider_id is None:
        return "unknown_domain"
    return "probable" if evidence.score >= PROBABLE_SCORE else "weak"


def gap(truth, result):
    """A real account that leaves no trace, or a non-account counted as probable."""
    return (truth == "account" and result == "none") or (truth == "no_account" and result == "probable")


def run(path=CASES, registry=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    registry = registry or Registry()
    rows, problems = [], []
    for case in data["cases"]:
        evidence = analyze(build(case["mail"], data["own"]), registry, data["own"])
        result = {"outcome": outcome(evidence)}
        if evidence is not None:
            result.update(signal=evidence.signal, assigned=evidence.registered_email is not None)
        expected = case["expect"]
        if any(result.get(key) != value for key, value in expected.items()):
            problems.append(f"{case['id']}: expected {expected}, got {result}")
        if gap(case["truth"], result["outcome"]) != bool(case.get("limit")):
            problems.append(f"{case['id']}: a gap between truth and outcome needs a documented limit, and only a gap")
        rows.append({"id": case["id"], "group": case["group"], "truth": case["truth"], **result,
                     "note": case.get("note"), "limit": case.get("limit")})
    totals = {truth: dict(Counter(row["outcome"] for row in rows if row["truth"] == truth))
              for truth in ("account", "no_account", "unclear")}
    return {"about": DISCLAIMER, "cases": rows, "totals": totals, "problems": problems,
            "limits": [{"id": row["id"], "limit": row["limit"]} for row in rows if row["limit"]]}


def text_report(report):
    lines = [DISCLAIMER, ""]
    account, other = report["totals"]["account"], report["totals"]["no_account"]
    lines.append(f"Real accounts ({sum(account.values())}): {account.get('probable', 0)} counted as probable, "
                 f"{account.get('weak', 0) + account.get('unknown_domain', 0)} kept for review, "
                 f"{account.get('none', 0)} missed")
    lines.append(f"Not an account ({sum(other.values())}): {other.get('probable', 0)} false alarm(s), "
                 f"{other.get('weak', 0) + other.get('unknown_domain', 0)} kept for review, "
                 f"{other.get('none', 0)} ignored")
    unclear = report["totals"]["unclear"]
    lines.append(f"Unclear by nature ({sum(unclear.values())}): "
                 + ", ".join(f"{unclear[key]} {key}" for key in OUTCOMES if key in unclear))
    lines.append("")
    for row in report["cases"]:
        lines.append(f"  {row['group']:<28} {row['id']:<32} {row['truth']:<11} -> {row['outcome']}")
    lines.append("")
    lines.append("Known limits:")
    lines.extend(f"  {entry['id']}: {entry['limit']}" for entry in report["limits"])
    if report["problems"]:
        lines.append("")
        lines.append("Differences from the documented outcome:")
        lines.extend(f"  {problem}" for problem in report["problems"])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    parser.add_argument("--cases", type=Path, default=CASES, help="benchmark case file")
    args = parser.parse_args(argv)
    report = run(args.cases)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else text_report(report))
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
