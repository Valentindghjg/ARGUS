# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
import http.client
from contextlib import closing
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from argus_security.registry import Registry
from argus_security.scan import synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / "data", Registry())
        cls.store.configure(["demo@example.invalid"])
        cls.server = DashboardServer(cls.store, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, path, method="GET", body=None, authorized=True, headers=None):
        h = {"Authorization":"Bearer " + self.server.token} if authorized else {}
        h.update(headers or {})
        with closing(http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)) as connection:
            connection.request(method, path, body=body, headers=h)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()

    def test_authenticated_snapshot(self):
        status, _, data = self.request("/api/accounts")
        self.assertEqual(status,200)
        snapshot = json.loads(data)
        self.assertGreaterEqual(snapshot["summary"]["providers"],500)
        self.assertNotIn("product", snapshot)
        # Every feature is free; there is no license route to call.
        self.assertEqual(self.request("/api/license/activate", "POST", "{}",
                                      headers={"Content-Type": "application/json"})[0], 404)
        self.assertEqual(snapshot["background_scan"], {"enabled": False, "authorized": False,
                                                        "interval_seconds": 86400, "limit": 500,
                                                        "next_run_at": None, "last_started_at": None,
                                                        "last_finished_at": None, "last_result": None,
                                                        "last_error": None, "running": False,
                                                        "target_confirmed": False})

    def test_errors_carry_a_constant_next_step(self):
        status, _, body = self.request("/api/accounts/github", "PATCH", json.dumps({"status": "done"}),
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body), {
            "error": "Check the required steps before marking this account done",
            "hint": "Required: verified by you, assigned in Bitwarden, sign-in tested and, for password sign-ins, a new password."})
        # Messages without a known next step stay unchanged.
        self.assertEqual(json.loads(self.request("/api/unknown")[2]), {"error": "Not found"})

    def test_api_requires_token(self):
        self.assertEqual(self.request("/api/accounts",authorized=False)[0],401)
        self.assertEqual(self.request("/api/accounts",headers={"Authorization":"Bearer wrong"})[0],401)
        self.assertEqual(self.request("/api/accounts",headers={"Authorization":"Bearer ä"})[0],401)

    def test_manual_account_creation_is_explicit_and_local(self):
        headers = {"Content-Type": "application/json"}
        data = {"provider_id": "github", "email": "demo@example.invalid",
                "label": "Separate local profile", "confirmed": True}
        payload = json.dumps(data)
        self.assertEqual(self.request("/api/accounts", "POST", payload, authorized=False, headers=headers)[0], 401)
        self.assertEqual(self.request("/api/accounts", "POST", payload,
                                     headers={**headers, "Origin": "https://attacker.example"})[0], 403)
        for invalid in ({**data, "confirmed": False}, {**data, "password": "not-accepted"},
                        {**data, "email": "unowned@example.invalid"}, {**data, "provider_id": "not-a-provider"}):
            self.assertEqual(self.request("/api/accounts", "POST", json.dumps(invalid), headers=headers)[0], 400)
        status, _, body = self.request("/api/accounts", "POST", payload, headers=headers)
        self.assertEqual(status, 201)
        ident = json.loads(body)["id"]
        rows = json.loads(self.request("/api/accounts")[2])["accounts"]
        created = next(a for a in rows if a["id"] == ident)
        self.assertEqual(created["label"], data["label"])
        self.assertEqual(created["provider_id"], "github")
        self.assertTrue(created["checklist"]["reviewed"])
        self.assertFalse(created["checklist"]["saved_in_bitwarden"])

    def test_origin_host_and_cors_protection(self):
        self.assertEqual(self.request("/api/accounts",headers={"Origin":"https://attacker.example"})[0],403)
        self.assertEqual(self.request("/api/accounts",headers={"Host":"attacker.example"})[0],403)
        self.assertEqual(self.request("/api/import",method="OPTIONS")[0],403)
        status, headers, _ = self.request("/api/accounts")
        self.assertNotIn("Access-Control-Allow-Origin",headers)

    def test_page_secure_headers_and_local_assets(self):
        status, headers, data = self.request("/",authorized=False)
        self.assertEqual(status,200)
        self.assertEqual(headers["Cache-Control"],"no-store")
        self.assertEqual(headers["X-Frame-Options"],"DENY")
        self.assertIn("connect-src 'self'",headers["Content-Security-Policy"])
        text = data.decode()
        self.assertNotIn("__LOCAL_TOKEN__",text)
        self.assertNotRegex(text,r'<(?:script|link|img)[^>]+(?:src|href)="https?://')
        for path in ["/app.js","/style.css"]:
            self.assertEqual(self.request(path,authorized=False)[0],200)

    def test_no_filesystem_traversal(self):
        for path in ["/../data/accounts.sqlite3","/data/accounts.sqlite3","/%2e%2e/imap.json"]:
            self.assertEqual(self.request(path)[0],404)

    def test_eml_import_and_checklist_mutation(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "")
        status, _, result = self.request("/api/import","POST",raw,headers={"Content-Type":"message/rfc822"})
        self.assertEqual(status,200)
        counts = json.loads(result)
        self.assertGreaterEqual(counts["evidence"]+counts["duplicates"]+counts["unchanged"],1)
        body = json.dumps({"checklist":{"reviewed":True}})
        self.assertEqual(self.request("/api/accounts/github","PATCH",body,headers={"Content-Type":"application/json"})[0],200)

    def test_export_and_invalid_requests(self):
        raw = synthetic_mail("notify@discord.com", "Your account has been created", "")
        self.request("/api/import","POST",raw,headers={"Content-Type":"message/rfc822"})
        status, _, body = self.request("/api/bitwarden","POST",json.dumps({"ids":["discord"]}),headers={"Content-Type":"application/json"})
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)["items"][0]["login"]["password"],"")
        for payload in ["[]","{invalid}",json.dumps({"password":"not-accepted"})]:
            self.assertEqual(self.request("/api/accounts/discord","PATCH",payload,headers={"Content-Type":"application/json"})[0],400)

    def test_bitwarden_preview_is_read_only_and_strictly_shaped(self):
        raw = synthetic_mail("notify@discord.com", "Your account has been created", "")
        self.request("/api/import", "POST", raw, headers={"Content-Type": "message/rfc822"})
        body = json.dumps({"ids": ["discord"], "language": "en", "target": "cli"})
        status, _, data = self.request("/api/bitwarden/preview", "POST", body, headers={"Content-Type": "application/json"})
        self.assertEqual(status, 200)
        preview = json.loads(data)
        self.assertEqual(preview["items"][0]["account_id"], "discord")
        self.assertIn("ARGUS-Transfer-ID", preview["items"][0]["fields"])
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM instance_bitwarden_handoffs").fetchone()[0], 0)
        for payload in [{"ids": ["discord"], "language": "en"}, {"ids": ["discord"], "language": "en", "target": "vault"},
                        {"ids": ["discord"], "language": "en", "target": "file", "confirmed": True}]:
            self.assertEqual(self.request("/api/bitwarden/preview", "POST", json.dumps(payload),
                                          headers={"Content-Type": "application/json"})[0], 400)

    def test_direct_bitwarden_cli_handoff_requires_explicit_selection(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "")
        self.request("/api/import", "POST", raw, headers={"Content-Type":"message/rfc822"})
        with patch("argus_security.bitwarden.add_to_unlocked_cli", return_value={"items":1,"providers":["github"]}) as handoff:
            status, _, body = self.request("/api/bitwarden/cli", "POST", json.dumps({"ids":["github"],"language":"en","confirmed":True}), headers={"Content-Type":"application/json"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["items"], 1)
        handoff.assert_called_once_with(self.store, ["github"], "en")
        self.assertEqual(self.request("/api/bitwarden/cli", "POST", json.dumps({"ids":["github"]}), headers={"Content-Type":"application/json"})[0], 400)
        with patch("argus_security.bitwarden.add_to_unlocked_cli") as unconfirmed:
            for confirmed in (None, False, "true", 1):
                payload = {"ids":["github"],"language":"en"}
                if confirmed is not None:
                    payload["confirmed"] = confirmed
                self.assertEqual(self.request("/api/bitwarden/cli", "POST", json.dumps(payload), headers={"Content-Type":"application/json"})[0], 400)
            unconfirmed.assert_not_called()

    def test_bitwarden_audit_requires_confirmation_and_returns_only_summary(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "")
        self.request("/api/import", "POST", raw, headers={"Content-Type":"message/rfc822"})
        headers = {"Content-Type": "application/json"}
        self.assertEqual(self.request("/api/bitwarden/audit", "POST",
                                      json.dumps({"ids":["github"], "language":"en", "confirmed":False}),
                                      headers=headers)[0], 400)
        with patch("argus_security.bitwarden.audit_unlocked_cli",
                   return_value={"accounts":[{"account_id":"github", "match":"found", "count":1}]}) as audit:
            status, _, body = self.request("/api/bitwarden/audit", "POST",
                                           json.dumps({"ids":["github"], "language":"en", "confirmed":True}),
                                           headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"accounts":[{"account_id":"github", "match":"found", "count":1}]})
        audit.assert_called_once_with(self.store, ["github"], "en")

    def test_guided_bitwarden_handoff_requires_current_account_and_confirmation(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "")
        self.request("/api/import", "POST", raw, headers={"Content-Type":"message/rfc822"})
        headers = {"Content-Type":"application/json"}
        status, _, body = self.request("/api/workflow", "POST", json.dumps({"action":"start"}), headers=headers)
        self.assertEqual(status, 200)
        current = json.loads(body)["current"]
        for payload in ({"account_id":current,"language":"en","confirmed":False},
                        {"account_id":"not-current","language":"en","confirmed":True},
                        {"account_id":current,"language":"en","confirmed":True,"password":"rejected"}):
            self.assertEqual(self.request("/api/secure-next/bitwarden", "POST", json.dumps(payload), headers=headers)[0], 400)
        with patch("argus_security.bitwarden.add_to_unlocked_cli", return_value={"items":1,"status":"ok"}) as handoff:
            status, _, body = self.request("/api/secure-next/bitwarden", "POST", json.dumps({"account_id":current,"language":"en","confirmed":True}), headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["items"], 1)
        handoff.assert_called_once_with(self.store, [current], "en")

    def test_post_size_limit_and_chunked_rejected(self):
        self.assertEqual(self.request("/api/import","POST",b"x",headers={"Content-Type":"message/rfc822","Content-Length":"3000000"})[0],400)
        self.assertEqual(self.request("/api/import","POST",b"x",headers={"Content-Type":"message/rfc822","Transfer-Encoding":"chunked"})[0],400)

    def test_worklist_api_and_new_routes_keep_authentication_guards(self):
        raw = synthetic_mail("notify@discord.com", "Your account has been created", "")
        self.request("/api/import", "POST", raw, headers={"Content-Type":"message/rfc822"})
        headers = {"Content-Type":"application/json"}
        status, _, _ = self.request("/api/workflow", "POST", json.dumps({"action":"add", "ids":["discord"]}), headers=headers)
        self.assertEqual(status, 200)
        status, _, _ = self.request("/api/workflow", "POST", json.dumps({"action":"snooze", "id":"discord", "days":1}), headers=headers)
        self.assertEqual(status, 200)
        status, _, body = self.request("/api/workflow", "POST", json.dumps({"action":"prioritize"}), headers=headers)
        self.assertEqual(status, 200)
        priority_result = json.loads(body)
        self.assertTrue(priority_result["ok"])
        self.assertNotIn("discord", priority_result["added"])
        snapshot = json.loads(self.request("/api/accounts")[2])
        self.assertIn("discord", [item["id"] for item in snapshot["workflow"]["items"]])
        for route in ("/api/workflow", "/api/bitwarden/resolve", "/api/bitwarden/cli", "/api/bitwarden/audit", "/api/secure-next/bitwarden"):
            self.assertEqual(self.request(route, "POST", "{}", authorized=False, headers=headers)[0], 401)
            self.assertEqual(self.request(route, "POST", "{}", headers={**headers, "Origin":"https://attacker.example"})[0], 403)
        self.assertEqual(self.request("/api/workflow", "POST", json.dumps({"action":"pause", "password":"rejected"}), headers=headers)[0], 400)
        self.assertEqual(self.request("/api/workflow", "POST", json.dumps({"action":"snooze", "id":"discord", "days":1, "password":"rejected"}), headers=headers)[0], 400)
        self.assertEqual(self.request("/api/bitwarden/resolve", "POST", json.dumps({"id":"missing", "created":True, "confirmed":False}), headers=headers)[0], 400)
