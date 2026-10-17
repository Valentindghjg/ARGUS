# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A12 and priority 14: a narrow, opt-in folder watch that only runs with the dashboard."""
from contextlib import redirect_stderr, redirect_stdout
import http.client
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from argus_security import watch
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.registry import Registry
from argus_security.scan import synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN = "owner@example.invalid"


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class FolderWatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        self.folder = self.root / "exports"
        (self.folder / "sub").mkdir(parents=True)
        (self.folder / "a.eml").write_bytes(created("noreply@github.com"))
        (self.folder / "sub" / "b.eml").write_bytes(created("no-reply@dropbox.com"))
        (self.folder / "notes.txt").write_text("not an email")

    def run_now(self):
        """One pass that is certainly due: each call is a day later than the last."""
        self.clock = getattr(self, "clock", time.time()) + 24 * 60 * 60
        return watch.run_due(self.store, now=self.clock)

    def test_only_a_narrow_local_visible_folder_is_accepted(self):
        hidden = self.root / ".hidden"
        hidden.mkdir()
        refused = [Path(Path.home().anchor), Path.home(), hidden, self.root / "missing", self.folder / "a.eml",
                   self.profile, self.root, "\\\\server\\share", "//server/share"]
        link = self.root / "link"
        try:
            link.symlink_to(self.folder, target_is_directory=True)
            refused.append(link)
        except OSError:
            pass
        for path in refused:
            with self.subTest(path=path), self.assertRaises(UserFacingError):
                watch.validate_folder(path, self.profile)
        self.assertEqual(watch.validate_folder(self.folder, self.profile), self.folder.resolve())
        with self.assertRaises(UserFacingError):
            watch.enable(self.store, self.folder, interval_seconds=30)

    def test_new_eml_files_directly_in_the_folder_are_imported_while_enabled(self):
        self.assertEqual(watch.run_due(self.store), {"status": "disabled"})
        watch.enable(self.store, self.folder, interval_seconds=60)
        first = watch.run_due(self.store)
        self.assertEqual((first["status"], first["processed"], first["evidence"]), ("imported", 1, 1))
        self.assertEqual(watch.run_due(self.store)["status"], "not_due")
        self.assertEqual(self.run_now()["status"], "idle")
        (self.folder / "c.eml").write_bytes(created("noreply@spotify.com"))
        second = self.run_now()
        self.assertEqual((second["processed"], second["evidence"]), (1, 1))
        # A touched file with the same content is recognized as unchanged.
        os.utime(self.folder / "a.eml", (1, 1))
        self.assertEqual(self.run_now()["unchanged"], 1)
        jobs = self.store.control_overview()["jobs"]
        self.assertEqual({job["kind"] for job in jobs}, {"folder_watch"})
        self.assertEqual(self.store.snapshot()["summary"]["clues"], 2)

    def test_pause_limits_missing_folder_and_disable(self):
        watch.enable(self.store, self.folder)
        self.store.set_automation_paused(True)
        self.assertEqual(self.run_now(), {"status": "paused"})
        self.store.set_automation_paused(False)
        for name in ("d.eml", "e.eml"):
            (self.folder / name).write_bytes(created(f"noreply@{name[0]}-service.example"))
        with patch("argus_security.watch.MAX_FILES_PER_PASS", 2):
            self.assertEqual(self.run_now()["processed"], 2)
            self.assertEqual(self.run_now()["processed"], 1)
        (self.folder / "sub" / "b.eml").unlink()
        (self.folder / "sub").rmdir()
        for file in self.folder.iterdir():
            file.unlink()
        self.folder.rmdir()
        self.assertEqual(self.run_now(), {"status": "folder_missing"})
        self.assertEqual(watch.status(self.store)["last_result"], "folder_missing")
        watch.disable(self.store)
        self.assertEqual(watch.run_due(self.store), {"status": "disabled"})
        with self.assertRaises(UserFacingError):
            watch.disable(self.store)
        events = [(entry["event"], entry["kind"]) for entry in self.store.control_overview()["activity"]]
        self.assertIn(("approval_granted", "folder_watch"), events)
        self.assertIn(("approval_revoked", "folder_watch"), events)

    def test_cli_and_control_api(self):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            base = ["--language", "en", "--data-dir", str(self.profile), "watch-folder"]
            self.assertEqual(main([*base, "enable", str(self.folder), "--interval-minutes", "10"]), 0)
            self.assertEqual(main([*base, "enable"]), 2)
        self.assertEqual(json.loads(out.getvalue())["interval_seconds"], 600)
        self.assertIn("Subfolders are not read", err.getvalue())
        server = DashboardServer(self.store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def call(method, path, body=None):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            self.addCleanup(connection.close)
            connection.request(method, path, json.dumps(body) if body is not None else None,
                               {"Authorization": "Bearer " + server.token, "Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())

        control = call("GET", "/api/control")[1]
        self.assertTrue(control["watch"]["enabled"])
        self.assertEqual(control["waiting"][0]["kind"], "folder_watch")
        self.assertEqual(call("POST", "/api/watch/disable", {"path": "x"})[0], 400)
        self.assertEqual(call("POST", "/api/watch/disable", {})[0], 200)
        self.assertFalse(call("GET", "/api/control")[1]["watch"]["enabled"])


if __name__ == "__main__":
    unittest.main()
