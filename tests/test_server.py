import http.client
from contextlib import closing
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

from account_finder.registry import Registry
from account_finder.scan import synthetic_mail
from account_finder.server import DashboardServer
from account_finder.store import Store


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
        self.assertEqual(snapshot["product"]["id"], "free")
        self.assertEqual(snapshot["product"]["billing"], "not_configured")
        self.assertEqual(snapshot["product"]["commercial_status"], "pro_in_development")
        self.assertFalse(snapshot["product"]["telemetry"])
        self.assertTrue(snapshot["product"]["free_features"])
        self.assertTrue(snapshot["product"]["pro_preview"])
        self.assertEqual(snapshot["background_scan"], {"enabled": False, "authorized": False,
                                                        "interval_seconds": 86400, "limit": 500,
                                                        "next_run_at": None, "last_started_at": None,
                                                        "last_finished_at": None, "last_result": None,
                                                        "last_error": None, "running": False})

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
        self.assertGreaterEqual(json.loads(result)["evidence"]+json.loads(result)["duplicates"],1)
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

    def test_direct_bitwarden_cli_handoff_requires_explicit_selection(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "")
        self.request("/api/import", "POST", raw, headers={"Content-Type":"message/rfc822"})
        with patch("account_finder.bitwarden.add_to_unlocked_cli", return_value={"items":1,"providers":["github"]}) as handoff:
            status, _, body = self.request("/api/bitwarden/cli", "POST", json.dumps({"ids":["github"],"language":"en"}), headers={"Content-Type":"application/json"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["items"], 1)
        handoff.assert_called_once_with(self.store, ["github"], "en")
        self.assertEqual(self.request("/api/bitwarden/cli", "POST", json.dumps({"ids":["github"]}), headers={"Content-Type":"application/json"})[0], 400)

    def test_post_size_limit_and_chunked_rejected(self):
        self.assertEqual(self.request("/api/import","POST",b"x",headers={"Content-Type":"message/rfc822","Content-Length":"3000000"})[0],400)
        self.assertEqual(self.request("/api/import","POST",b"x",headers={"Content-Type":"message/rfc822","Transfer-Encoding":"chunked"})[0],400)

    def test_worklist_api_and_new_routes_keep_authentication_guards(self):
        raw = synthetic_mail("notify@discord.com", "Your account has been created", "")
        self.request("/api/import", "POST", raw, headers={"Content-Type":"message/rfc822"})
        headers = {"Content-Type":"application/json"}
        status, _, _ = self.request("/api/workflow", "POST", json.dumps({"action":"add", "ids":["discord"]}), headers=headers)
        self.assertEqual(status, 200)
        snapshot = json.loads(self.request("/api/accounts")[2])
        self.assertIn("discord", [item["id"] for item in snapshot["workflow"]["items"]])
        for route in ("/api/workflow", "/api/bitwarden/resolve", "/api/bitwarden/cli"):
            self.assertEqual(self.request(route, "POST", "{}", authorized=False, headers=headers)[0], 401)
            self.assertEqual(self.request(route, "POST", "{}", headers={**headers, "Origin":"https://attacker.example"})[0], 403)
        self.assertEqual(self.request("/api/workflow", "POST", json.dumps({"action":"pause", "password":"rejected"}), headers=headers)[0], 400)
        self.assertEqual(self.request("/api/bitwarden/resolve", "POST", json.dumps({"id":"missing", "created":True, "confirmed":False}), headers=headers)[0], 400)
