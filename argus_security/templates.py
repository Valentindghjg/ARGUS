# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Reusable task templates (plan A22, P4).

A template is plain data, never a script or a browser macro: which accounts it
covers (catalog categories, a minimum priority, only confirmed ones) and what
it plans for them (add them to the worklist, a review date for chosen steps).
Applying a template first shows exactly which accounts it touches, then makes
one local change that can be undone. It never acts at a provider.
"""
from datetime import datetime, timedelta, timezone
import re

from .errors import UserFacingError
from .states import STEPS

KEY = "templates"
RANK = {"normal": 0, "high": 1, "critical": 2}
BUILTIN = {
    "yearly-important": {"name": "Yearly check of important accounts",
                         "categories": [], "min_priority": "high", "confirmed_only": True,
                         "worklist": True, "review_steps": ["identity", "mfa_recovery"], "review_days": 365},
    "finance-recovery": {"name": "Recovery check for finance accounts",
                         "categories": ["Finance"], "min_priority": "normal", "confirmed_only": True,
                         "worklist": True, "review_steps": ["mfa_recovery"], "review_days": 180},
}
FIELDS = {"name", "categories", "min_priority", "confirmed_only", "worklist", "review_steps", "review_days"}


def validate(data, categories):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise UserFacingError("Fill in every part of the template")
    name = data["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 for c in name):
        raise UserFacingError("Use a template name with 1 to 80 characters")
    if (not isinstance(data["categories"], list) or len(data["categories"]) > 20
            or any(category not in categories for category in data["categories"])):
        raise UserFacingError("Choose categories from the catalog")
    if data["min_priority"] not in RANK or type(data["confirmed_only"]) is not bool or type(data["worklist"]) is not bool:
        raise UserFacingError("Fill in every part of the template")
    steps, days = data["review_steps"], data["review_days"]
    if not isinstance(steps, list) or any(step not in STEPS for step in steps) or len(set(steps)) != len(steps):
        raise UserFacingError("Choose review steps from the checklist")
    if steps and (type(days) is not int or not 7 <= days <= 1825):
        raise UserFacingError("Choose a review date between 7 days and 5 years ahead")
    if not steps and days is not None:
        raise UserFacingError("Choose review steps from the checklist")
    if not data["worklist"] and not steps:
        raise UserFacingError("A template must add to the worklist or set a review date")
    return {**data, "name": name.strip()}


def custom(store):
    value = store.meta(KEY)
    return value if isinstance(value, dict) else {}


def all_templates(store):
    return {**{key: {**value, "builtin": True} for key, value in BUILTIN.items()},
            **{key: {**value, "builtin": False} for key, value in custom(store).items()}}


def save(store, data, categories):
    template = validate(data, categories)
    templates = custom(store)
    if len(templates) >= 50:
        raise UserFacingError("Keep at most 50 own templates")
    ident = "mine-" + (re.sub(r"[^a-z0-9]+", "-", template["name"].casefold()).strip("-")[:40] or "template")
    base, suffix = ident, 2
    while ident in templates or ident in BUILTIN:
        ident, suffix = f"{base}-{suffix}", suffix + 1
    store.set_meta(KEY, {**templates, ident: template})
    return ident


def delete(store, ident):
    templates = custom(store)
    if ident not in templates:
        raise UserFacingError("Only templates you created can be deleted")
    del templates[ident]
    store.set_meta(KEY, templates)


def select(accounts, template):
    """The accounts a template covers; rejected and evidence-free accounts never are."""
    return [account for account in accounts
            if account["classification"] != "unknown" and account["decision"] != "rejected"
            and (not template["categories"] or account["category"] in template["categories"])
            and RANK[account["priority"]] >= RANK[template["min_priority"]]
            and (not template["confirmed_only"] or account["decision"] == "confirmed")]


def preview(accounts, template, queued):
    covered = select(accounts, template)
    review_date = ((datetime.now(timezone.utc).date() + timedelta(days=template["review_days"])).isoformat()
                   if template["review_steps"] else None)
    return {"accounts": [account["id"] for account in covered],
            "worklist_additions": [account["id"] for account in covered if template["worklist"] and account["id"] not in queued],
            "review_date": review_date, "review_steps": template["review_steps"]}

