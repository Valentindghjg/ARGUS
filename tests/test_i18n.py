"""User language choices must not alter detection, accounts or password safety."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from argus_security.analysis import ANALYSIS_VERSION
from argus_security.bitwarden import make_export
from argus_security.cli import main, parser
from argus_security.discovery import discover
from argus_security.i18n import catalog, cli_language, localize_discovery, translate
from argus_security.registry import Registry
from argus_security.scan import load_demo, scan_messages, synthetic_mail
from argus_security.store import Store


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(Path(self.directory.name) / "demo", Registry())
        load_demo(self.store)

    def test_both_snapshots_preserve_data_and_detection_version(self):
        self.store.update_account("steam", {"checklist": {"reviewed": True}, "registered_email": "demo@example.invalid"})
        with self.store.connect() as db:
            before = [tuple(row) for row in db.execute("SELECT * FROM evidence ORDER BY id")]
        english = self.store.snapshot("en")
        german = self.store.snapshot("de")
        self.assertEqual(english["summary"], german["summary"])
        self.assertEqual(german["analysis_version"], ANALYSIS_VERSION)
        for en, de in zip(english["accounts"], german["accounts"]):
            for field in ["id", "classification", "score", "category", "website", "registered_emails", "manual_email", "checklist", "status"]:
                self.assertEqual(en[field], de[field])
        finance = next(a for a in german["accounts"] if a["id"] == "paypal")
        self.assertEqual(finance["category_label"], "Finanzen")
        self.assertEqual(finance["reason"], "Von dir als vorhanden bestätigt")
        self.assertEqual(self.store.snapshot("en"), english)
        with self.store.connect() as db:
            after = [tuple(row) for row in db.execute("SELECT * FROM evidence ORDER BY id")]
        self.assertEqual(before, after)

    def test_detection_uses_german_and_english_in_either_interface(self):
        messages = [synthetic_mail("notify@tiktok.com", "Deine Registrierung ist abgeschlossen", ""),
                    synthetic_mail("notify@zoom.us", "Your account has been created", "")]
        scan_messages(self.store, messages)
        for language in ["en", "de"]:
            accounts = {a["id"]: a for a in self.store.snapshot(language)["accounts"]}
            self.assertEqual(accounts["tiktok"]["classification"], "probable")
            self.assertEqual(accounts["zoom"]["classification"], "probable")

    def test_composite_caveats_translate_without_losing_uncertainty(self):
        text = "Generic welcome with advertising indicators; review manually; Only headers analyzed (message exceeds size limit)"
        german = translate(text, "de")
        self.assertIn("Werbemerkmalen; manuell prüfen", german)
        self.assertIn("Nur Header", german)
        self.assertEqual(translate(text, "en"), text)

    def test_bitwarden_notes_localized_but_ids_urls_and_empty_passwords_stable(self):
        en = make_export(self.store, ["steam"], "en")["items"][0]
        de = make_export(self.store, ["steam"], "de")["items"][0]
        self.assertIn("Evidence:", en["notes"])
        self.assertIn("Beleg:", de["notes"])
        self.assertIn("Kein Passwort exportiert", de["notes"])
        for field in ["login", "name", "fields"]:
            self.assertEqual(en[field], de[field])
        self.assertEqual(de["login"]["password"], "")

    def test_unsupported_export_language_rejected(self):
        with self.assertRaises(ValueError):
            make_export(self.store, ["steam"], "fr")

    def test_cli_help_including_subcommands_has_selected_language(self):
        self.assertIn("Lokales ARGUS-Account-Inventar", parser("de").format_help())
        self.assertIn("ARGUS local account inventory", parser("en").format_help())
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as exited:
            main(["--language", "de", "scan-imap", "--help"])
        self.assertEqual(exited.exception.code, 0)
        self.assertIn("Verbindung zum konfigurierten IMAP-Host", output.getvalue())
        self.assertIn("Optionen:", output.getvalue())

    def test_cli_german_errors_still_require_explicit_imap_authorization(self):
        error = StringIO()
        with redirect_stderr(error), patch("argus_security.cli.getpass.getpass") as secret:
            result = main(["--language", "de", "--data-dir", str(self.store.data_dir), "scan-imap"])
        self.assertEqual(result, 2)
        self.assertIn("Keine Verbindung erlaubt", error.getvalue())
        secret.assert_not_called()

    def test_german_cli_export_formats_count_and_preserves_existing_file(self):
        destination = Path(self.directory.name) / "export.json"
        argv = ["--language", "de", "--data-dir", str(self.store.data_dir), "bitwarden-export", str(destination), "--id", "steam"]
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(argv), 0)
        self.assertIn("1 Metadaten-Einträge", output.getvalue())
        self.assertEqual(json.loads(destination.read_text())["items"][0]["login"]["password"], "")
        before = destination.read_bytes()
        with redirect_stderr(output):
            self.assertEqual(main(argv), 2)
        self.assertEqual(before, destination.read_bytes())
        self.assertIn("nicht überschrieben", output.getvalue())

    def test_language_autodetection_and_explicit_override(self):
        with patch("argus_security.i18n.locale.getlocale", return_value=("de_DE", "UTF-8")):
            self.assertEqual(cli_language([]), "de")
            self.assertEqual(cli_language(["--language=en", "--help"]), "en")
        with patch("argus_security.i18n.locale.getlocale", return_value=("fr_FR", "UTF-8")):
            self.assertEqual(cli_language([]), "en")

    def test_offline_discovery_translation_does_not_change_domain_or_network_policy(self):
        result = discover("example.invalid")
        localized = localize_discovery(result, "de")
        self.assertEqual(localized["domain"], result["domain"])
        self.assertFalse(localized["network"])
        self.assertIn("Offline.", localized["note"])
        self.assertIn("eigener Domain", localized["note"])

    def test_translation_placeholders_are_consistent(self):
        for english, german in catalog()["de"].items():
            with self.subTest(message=english):
                self.assertEqual(set(re.findall(r"\{([^}]+)\}", english)), set(re.findall(r"\{([^}]+)\}", german)))

    def test_user_facing_errors_have_german_entries(self):
        """Typed errors reach the CLI or dashboard verbatim and are translated there."""
        import ast
        typed = {"LicenseError", "CredentialError", "MailboxError", "BitwardenCliError", "HandoffError", "DNSError",
                 "UserFacingError", "MailboxBusy", "LeaseLost"}
        # Raised only by the publisher's offline license-issuing script.
        publisher_only = {"Invalid publisher private key", "Publisher private key must use Ed25519"}
        missing = []
        for path in sorted((Path(__file__).resolve().parents[1] / "argus_security").glob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
                        and isinstance(node.exc.func, ast.Name) and node.exc.func.id in typed):
                    # Shown verbatim to users: only constant texts, never data.
                    if not node.exc.args or not isinstance(node.exc.args[0], ast.Constant):
                        missing.append(f"{path.name}:{node.lineno}: non-constant message")
                        continue
                    message = node.exc.args[0].value
                    if message not in catalog()["de"] and message not in publisher_only:
                        missing.append(f"{path.name}:{node.lineno}: {message}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
