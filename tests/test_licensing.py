from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from argus_security.licensing import LicenseError, activate, issue, license_status, read_document, verify


class LicensingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        key = Ed25519PrivateKey.generate()
        self.private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption())
        self.public = self.root / "public.pem"
        self.public.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                               serialization.PublicFormat.SubjectPublicKeyInfo))

    def document(self, **changes):
        payload = {"license_id": "pro_test_license_12345", "issued_at": "2026-01-01T00:00:00Z",
                   "expires_at": None, "features": ["encrypted_backup", "security_reports"]}
        payload.update(changes)
        return issue(payload, self.private)

    def test_valid_license_is_verified_and_activated_privately(self):
        document = self.document()
        verified = verify(document, self.public.read_bytes(), datetime(2026, 2, 1, tzinfo=timezone.utc))
        self.assertEqual(verified["edition"], "pro")
        status = activate(self.root, document, self.public)
        self.assertEqual(status["state"], "active")
        self.assertEqual(read_document(self.root / "license.json"), document)
        if os.name == "posix":
            self.assertEqual((self.root / "license.json").stat().st_mode & 0o777, 0o600)

    def test_tampered_or_expired_license_is_not_accepted(self):
        tampered = self.document()
        tampered["features"] = ["review_reminders"]
        with self.assertRaises(LicenseError):
            verify(tampered, self.public.read_bytes())
        expired = self.document(expires_at="2026-01-02T00:00:00Z")
        with self.assertRaises(LicenseError):
            verify(expired, self.public.read_bytes(), datetime(2026, 2, 1, tzinfo=timezone.utc))

    def test_unconfigured_or_invalid_local_license_stays_free(self):
        self.assertEqual(license_status(self.root, self.root / "missing.pem")["state"], "not_configured")
        (self.root / "license.json").write_text("{}", encoding="utf-8")
        self.assertEqual(license_status(self.root, self.public)["state"], "invalid")


if __name__ == "__main__":
    unittest.main()
