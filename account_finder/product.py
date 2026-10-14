"""Public product and edition metadata; deliberately no billing or tracking."""

CURRENT_EDITION = {
    "id": "free",
    "name": "Account Compass Free",
    "commercial_status": "pro_in_development",
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


def public_product(data_dir=None) -> dict:
    """Return only non-personal product facts for the local dashboard or CLI."""
    from .licensing import license_status
    license_info = license_status(data_dir) if data_dir else {
        "edition": "free", "state": "not_configured", "activation_enabled": False,
        "message": "Pro licensing is not configured in this build.",
    }
    return {
        **CURRENT_EDITION,
        "free_features": list(CURRENT_EDITION["free_features"]),
        "pro_preview": list(CURRENT_EDITION["pro_preview"]),
        "current_edition": license_info["edition"],
        "license": license_info,
    }
