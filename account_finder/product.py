"""Public product and edition metadata; deliberately no billing or tracking."""

CURRENT_EDITION = {
    "id": "free",
    "name": "Account Compass Free",
    "commercial_status": "pro_preview",
    "billing": "not_configured",
    "telemetry": False,
    "free_features": (
        "Local account inventory and 527-provider catalog",
        "Local EML, mbox, Maildir and opt-in read-only IMAP analysis",
        "Security checklists and password-free Bitwarden metadata",
    ),
    "pro_preview": (
        "Local encrypted backup and recovery workflow",
        "Scheduled local review reminders",
        "Advanced personal security reports",
    ),
}


def public_product() -> dict:
    """Return only non-personal product facts for the local dashboard or CLI."""
    return {
        **CURRENT_EDITION,
        "free_features": list(CURRENT_EDITION["free_features"]),
        "pro_preview": list(CURRENT_EDITION["pro_preview"]),
    }
