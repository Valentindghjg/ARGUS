import json
from email.message import EmailMessage
from pathlib import Path
import tempfile
import unittest

from account_finder.analysis import analyze, MAX_MESSAGE_BYTES, normalize_email
from account_finder.registry import Registry
from account_finder.scan import synthetic_mail


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def inspect(self, sender="notify@github.com", subject="Your account has been created", body="Your account has been created.", **kw):
        return analyze(synthetic_mail(sender, subject, body, **kw), self.registry, ["demo@example.invalid"])

    def test_catalogue_minimum_and_requested_services(self):
        self.assertGreaterEqual(len(self.registry.providers), 500)
        for ident in ["instagram", "tiktok", "snapchat", "facebook", "x", "reddit", "discord", "telegram", "skype", "steam", "epic", "ubisoft", "ea", "playstation", "xbox", "riot", "amazon", "ebay", "idealo", "zalando", "temu", "aliexpress", "netflix", "spotify", "disney", "twitch", "google", "apple", "microsoft", "adobe", "github", "paypal", "klarna", "linear", "wealthfront", "hostelworld", "yazio", "coffeemeetsbagel"]:
            self.assertIn(ident, self.registry.providers)

    def test_expanded_catalogue_uses_exact_roots_and_more_specific_subdomains(self):
        self.assertEqual(self.registry.match("mail.wealthfront.com").id, "wealthfront")
        self.assertEqual(self.registry.match("billing.hostelworld.com").id, "hostelworld")
        self.assertEqual(self.registry.match("notify.firebase.google.com").id, "firebase")
        self.assertEqual(self.registry.match("firebase.google.com.attacker.example"), None)

    def test_completed_registration(self):
        e = self.inspect()
        self.assertEqual((e.provider_id, e.signal, e.score), ("github", "account_created", 90))
        self.assertEqual(e.registered_email, "demo@example.invalid")

    def test_transactional_signup_variants(self):
        for subject in ["Thanks for signing up", "Thank you for registering", "Danke für deine Registrierung"]:
            self.assertEqual(self.inspect(subject=subject, body="").signal, "account_created")

    def test_german_password_and_login(self):
        for subject, signal in [("Dein Passwort wurde geändert", "password_changed"), ("Neue Anmeldung", "login_activity"), ("Deine Registrierung ist abgeschlossen", "account_created")]:
            self.assertEqual(self.inspect(subject=subject, body="").signal, signal)

    def test_newsletter_is_not_account(self):
        for subject, body in [("Welcome", "Newsletter special offers"), ("Verify your email", "Confirm your email to subscribe to the newsletter"), ("Welcome to your account", "Special offers")]:
            e = self.inspect(subject=subject, body=body, newsletter=True)
            self.assertEqual((e.signal, e.score), ("newsletter", 0))
            self.assertIsNone(e.registered_email)

    def test_security_notice_may_have_unsubscribe(self):
        e = self.inspect(subject="Your password has been changed", body="Your password has been changed", newsletter=True)
        self.assertEqual(e.signal, "password_changed")
        self.assertGreaterEqual(e.score, 85)

    def test_reset_request_and_guest_order_weak(self):
        for subject, signal in [("Reset your password", "reset_requested"), ("Bestellbestätigung", "order_only")]:
            e = self.inspect(subject=subject, body="")
            self.assertEqual(e.signal, signal)
            self.assertLess(e.score, 60)
            self.assertIsNone(e.registered_email)

    def test_domain_boundaries_and_display_name(self):
        self.assertIsNone(self.registry.match("github.com.attacker.example"))
        self.assertIsNone(self.registry.match("notgithub.com"))
        self.assertEqual(self.registry.match("notifications.github.com").id, "github")
        e = self.inspect(sender='"GitHub" <sender@attacker.example>')
        self.assertIsNone(e.provider_id)

    def test_unrelated_recipient_and_self_sent(self):
        self.assertIsNone(self.inspect(recipient="someone@example.invalid"))
        self.assertIsNone(self.inspect(sender="demo@example.invalid"))

    def test_forwarded_message_is_weak_no_registered_email(self):
        e = self.inspect(subject="Fwd: Your account has been created")
        self.assertLess(e.score, 60)
        self.assertIsNone(e.registered_email)

    def test_delivery_only_is_ambiguous(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "", recipient="someone@example.invalid")
        raw = b"Delivered-To: demo@example.invalid\n" + raw
        e = analyze(raw, self.registry, ["demo@example.invalid"])
        self.assertLess(e.score, 60)
        self.assertIsNone(e.registered_email)

    def test_html_local_no_script_or_url_detection(self):
        e = self.inspect(subject="Notice", body="<script>Your password has been changed</script><p>Your account has been created</p><img src='https://tracker.example/pixel'>", html=True)
        self.assertEqual(e.signal, "account_created")
        self.assertIsNone(self.inspect(subject="Notice", body="https://example.invalid/your-account-has-been-created"))

    def test_attached_registration_not_evidence(self):
        message = EmailMessage()
        message["From"] = "notify@github.com"
        message["To"] = "demo@example.invalid"
        message["Subject"] = "Document"
        message.set_content("Please read the attachment")
        message.add_attachment(b"Your account has been created", maintype="text", subtype="plain", filename="attachment.txt")
        self.assertIsNone(analyze(message.as_bytes(), self.registry, ["demo@example.invalid"]))

    def test_duplicate_from_and_big_message_rejected(self):
        raw = b"From: other@paypal.com\n" + synthetic_mail("notify@github.com", "Your account has been created", "")
        self.assertIsNone(analyze(raw, self.registry, ["demo@example.invalid"]))
        self.assertIsNone(analyze(b"a" * (MAX_MESSAGE_BYTES + 1), self.registry, ["demo@example.invalid"]))

    def test_aliases_explicit_and_no_plus_stripping(self):
        self.assertEqual(normalize_email("Name+Shopping@EXAMPLE.COM"), "name+shopping@example.com")
        with self.assertRaises(ValueError):
            normalize_email("bad\naddress@example.com")

    def test_headers_only_strength_capped(self):
        raw = b"X-Account-Finder-Headers-Only: yes\n" + synthetic_mail("notify@github.com", "Your password has been changed", "")
        e = analyze(raw, self.registry, ["demo@example.invalid"])
        self.assertEqual(e.score, 70)
        self.assertIn("headers", e.caveat)

    def test_extend_catalogue_and_reject_unsafe_links(self):
        row = {"id":"myservice","name":"My Service","website":"https://myservice.example/","category":"Eigene Dienste","domains":["myservice.example"]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extra.json"
            path.write_text(json.dumps([row]))
            self.assertEqual(Registry(path).match("mail.myservice.example").id, "myservice")
            for url in ["http://myservice.example/", "javascript:alert(1)", "https://myservice.example.attacker.example/", "https://user@myservice.example/"]:
                row["website"] = url
                path.write_text(json.dumps([row]))
                with self.assertRaises(ValueError):
                    Registry(path)


if __name__ == "__main__":
    unittest.main()
