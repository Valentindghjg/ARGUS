"""Offline Ed25519 entitlement verification; no checkout or customer data."""
from __future__ import annotations

from base64 import b64decode, b64encode
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PRODUCT_ID = "account-compass-pro"
FORMAT = 1
LICENSE_FILE = "license.json"
BUNDLED_PUBLIC_KEY = Path(__file__).with_name("data") / "license_public_key.pem"
PRO_FEATURES = frozenset({"encrypted_backup", "review_reminders", "security_reports"})
FIELDS = frozenset({"format", "license_id", "product", "edition", "issued_at", "expires_at", "features", "signature"})
LICENSE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{15,79}\Z")


class LicenseError(ValueError):
    """A local entitlement is missing, invalid, expired or not trusted."""


def _time(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 40:
        raise LicenseError("Invalid license date")
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LicenseError("Invalid license date") from exc
    if result.tzinfo is None:
        raise LicenseError("Invalid license date")
    return result.astimezone(timezone.utc)


def _payload(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != FIELDS:
        raise LicenseError("Invalid license format")
    if document["format"] != FORMAT or document["product"] != PRODUCT_ID or document["edition"] != "pro":
        raise LicenseError("License is for a different product")
    if not isinstance(document["license_id"], str) or not LICENSE_ID.fullmatch(document["license_id"]):
        raise LicenseError("Invalid license identifier")
    issued = _time(document["issued_at"])
    expires = document["expires_at"]
    if expires is not None:
        expires = _time(expires)
        if expires <= issued:
            raise LicenseError("Invalid license expiry")
    features = document["features"]
    if not isinstance(features, list) or not features or len(features) > len(PRO_FEATURES):
        raise LicenseError("Invalid license features")
    if any(not isinstance(feature, str) for feature in features) or len(set(features)) != len(features) or not set(features) <= PRO_FEATURES:
        raise LicenseError("Invalid license features")
    if not isinstance(document["signature"], str) or len(document["signature"]) > 256:
        raise LicenseError("Invalid license signature")
    return {key: document[key] for key in sorted(FIELDS - {"signature"})}


def canonical_payload(document: dict) -> bytes:
    """Canonical bytes signed by the publisher; excludes the signature itself."""
    return json.dumps(_payload(document), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _public_key(value: bytes) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(value)
    except (TypeError, ValueError) as exc:
        raise LicenseError("Invalid bundled license public key") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise LicenseError("Bundled license key must use Ed25519")
    return key


def verify(document: dict, public_key: bytes, now: datetime | None = None) -> dict:
    """Return a minimal Pro entitlement or raise LicenseError without logging data."""
    payload = _payload(document)
    try:
        signature = b64decode(document["signature"], validate=True)
        _public_key(public_key).verify(signature, canonical_payload(document))
    except (InvalidSignature, ValueError) as exc:
        raise LicenseError("License signature is invalid") from exc
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    expires = payload["expires_at"]
    if expires is not None and _time(expires) <= current:
        raise LicenseError("License has expired")
    return {"edition": "pro", "license_id": payload["license_id"], "expires_at": expires,
            "features": list(payload["features"])}


def issue(payload: dict, private_key: bytes) -> dict:
    """Publisher-only helper. Keep its Ed25519 private key outside this project."""
    unsigned = {**payload, "format": FORMAT, "product": PRODUCT_ID, "edition": "pro", "signature": ""}
    canonical = canonical_payload(unsigned)
    try:
        key = serialization.load_pem_private_key(private_key, password=None)
    except (TypeError, ValueError) as exc:
        raise LicenseError("Invalid publisher private key") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise LicenseError("Publisher private key must use Ed25519")
    return {**unsigned, "signature": b64encode(key.sign(canonical)).decode("ascii")}


def read_document(path: Path) -> dict:
    if path.is_symlink() or path.stat().st_size > 16 * 1024:
        raise LicenseError("Invalid license file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LicenseError("Invalid license file") from exc
    if not isinstance(document, dict):
        raise LicenseError("Invalid license file")
    return document


def license_status(data_dir: Path, public_key_path: Path = BUNDLED_PUBLIC_KEY) -> dict:
    """Local status safe for display; it contains no purchaser identity or secret."""
    if not public_key_path.is_file() or public_key_path.is_symlink():
        return {"edition": "free", "state": "not_configured", "activation_enabled": False,
                "message": "Pro licensing is not configured in this build."}
    path = data_dir / LICENSE_FILE
    if not path.exists():
        return {"edition": "free", "state": "missing", "activation_enabled": True,
                "message": "Account Compass Free is active."}
    try:
        entitlement = verify(read_document(path), public_key_path.read_bytes())
    except (LicenseError, OSError):
        return {"edition": "free", "state": "invalid", "activation_enabled": True,
                "message": "The local Pro license could not be verified."}
    return {**entitlement, "state": "active", "activation_enabled": True,
            "message": "Account Compass Pro is active."}


def activate(data_dir: Path, document: dict, public_key_path: Path = BUNDLED_PUBLIC_KEY) -> dict:
    """Verify first, then atomically replace only the private local license file."""
    if not public_key_path.is_file() or public_key_path.is_symlink():
        raise LicenseError("Pro licensing is not configured in this build")
    verify(document, public_key_path.read_bytes())
    destination = data_dir / LICENSE_FILE
    if destination.is_symlink():
        raise LicenseError("Invalid local license path")
    content = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=".license-", dir=data_dir, text=True)
    try:
        if os.name == "posix":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, destination)
        if os.name == "posix":
            destination.chmod(0o600)
    except OSError:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return license_status(data_dir, public_key_path)
