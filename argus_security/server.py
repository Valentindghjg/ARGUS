# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Loopback-only dashboard with memory-only bearer token and strict origins."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit, unquote

from .errors import UserFacingError
from .guidance import hint_for
from .analysis import MAX_MESSAGE_BYTES
from .background import BackgroundScanService, KeyringCredentialStore
from .scan import ScanSession, scan_messages
from .store import Store

WEB = Path(__file__).with_name("web")
ACCOUNT_ACTION = re.compile(r"/api/accounts/([^/]+)/(decision|steps|sign-in-with)")


class ImportBusy(Exception):
    pass


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, store: Store, port=8765):
        self.store = store
        self.token = secrets.token_urlsafe(32)
        self.import_lock = threading.RLock()
        self.import_job = None
        self.background_service = BackgroundScanService(store, KeyringCredentialStore())
        self.background_stop = threading.Event()
        self.background_thread = None
        super().__init__(("127.0.0.1", port), Handler)
        self.origins = {f"http://127.0.0.1:{self.server_port}", f"http://localhost:{self.server_port}"}
        self.hosts = {f"127.0.0.1:{self.server_port}", f"localhost:{self.server_port}"}

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}/"

    def active_import(self):
        if self.import_job and self.import_job.stats["running"]:
            if time.monotonic() - self.import_job.last_activity > 600:
                self.import_job.finish("partial")
            else:
                return self.import_job
        return None

    def import_session(self, job_id):
        self.active_import()
        if not self.import_job or job_id != self.import_job.stats["id"]:
            raise ValueError("Unknown import session")
        return self.import_job

    def background_snapshot(self):
        try:
            return self.background_service.snapshot()
        except ValueError:
            # A damaged local schedule must not stop the dashboard or reveal
            # untrusted stored values. It will require a fresh terminal setup.
            return {"enabled": False, "authorized": False, "last_error": "Background IMAP schedule needs local setup"}

    def start_background_scans(self):
        """Start the opt-in in-process scheduler only for an enabled profile."""
        if self.background_thread or not self.background_snapshot().get("enabled"):
            return
        self.background_thread = threading.Thread(target=self._background_loop,
                                                  name="argus-imap-scheduler", daemon=True)
        self.background_thread.start()

    def _background_loop(self):
        while not self.background_stop.is_set():
            self._background_pass()
            status = self.background_snapshot()
            due = status.get("next_run_at")
            seconds = 60
            if isinstance(due, (int, float)):
                seconds = max(1, min(60, due - time.time()))
            self.background_stop.wait(seconds)

    def _background_pass(self):
        # Never start an automatic mailbox run during a browser EML import.
        # The next pass will see the same persistent IMAP checkpoint.
        with self.import_lock:
            busy = self.active_import() is not None
        if busy:
            return
        try:
            self.background_service.run_due(allow_network=True)
        except Exception:
            # A locked database or damaged schedule must not end the scheduler
            # thread silently; run_due already records safe scan failures, and
            # the next pass retries without exposing exception text.
            pass

    def server_close(self):
        self.background_stop.set()
        with self.import_lock:
            if self.import_job and self.import_job.stats["running"]:
                self.import_job.finish("partial")
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    server_version = "ARGUS"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format, *args):
        # URLs, headers, bodies and credentials never enter access/error logs.
        pass

    def _send(self, status, data, kind="application/json; charset=utf-8", attachment=None):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        elif isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'; object-src 'none'")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _error(self, status, message):
        # The hint is looked up by the constant message; it never echoes input.
        body = {"error": message}
        hint = hint_for(message)
        if hint:
            body["hint"] = hint
        self._send(status, body)

    def _gate(self, api=False):
        if self.client_address[0] != "127.0.0.1" or self.headers.get("Host") not in self.server.hosts:
            self._error(403, "Only local requests with a valid Host are allowed")
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in self.server.origins:
            self._error(403, "Foreign Origin rejected")
            return False
        if api:
            token = self.headers.get("Authorization", "")
            try:
                valid = hmac.compare_digest(token.encode("ascii"), ("Bearer " + self.server.token).encode("ascii"))
            except UnicodeError:
                valid = False
            if not valid:
                self._error(401, "Reload the dashboard; the local session token is missing")
                return False
        return True

    def _read(self, limit):
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("Chunked requests are not supported")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid content length") from None
        if not 0 < length <= limit:
            raise ValueError("File / request is empty or too large")
        data = self.rfile.read(length)
        if len(data) != length:
            raise ValueError("Incomplete request")
        return data

    def _json(self):
        if self.headers.get_content_type() != "application/json":
            raise ValueError("JSON is required")
        data = json.loads(self._read(64 * 1024))
        if not isinstance(data, dict):
            raise ValueError("A JSON object is required")
        return data

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self._gate(path.startswith("/api/")):
            return
        if path == "/":
            page = (WEB / "index.html").read_text(encoding="utf-8")
            from . import __version__
            page = page.replace("__LOCAL_TOKEN__", self.server.token).replace("__APP_VERSION__", __version__)
            self._send(200, page, "text/html; charset=utf-8")
        elif path == "/i18n.js":
            from .i18n import catalog
            self._send(200, "window.AF_TRANSLATIONS=" + json.dumps(catalog(), ensure_ascii=False) + ";", "text/javascript; charset=utf-8")
        elif path in {"/app.js", "/style.css"}:
            kind = "text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8"
            self._send(200, (WEB / path[1:]).read_bytes(), kind)
        elif path == "/api/changes":
            self._send(200, {"changes": self.server.store.recent_changes()})
        elif path == "/api/session/report":
            from urllib.parse import parse_qs
            language = parse_qs(urlsplit(self.path).query).get("language", ["en"])[0]
            try:
                self._send(200, {"text": self.server.store.session_report_text(language)})
            except UserFacingError as exc:
                self._error(400, str(exc))
            except ValueError:
                self._error(400, "Unsupported language; choose en or de")
        elif path == "/api/accounts":
            with self.server.import_lock:
                job = self.server.active_import()
                snapshot = self.server.store.snapshot()
                snapshot["active_import"] = dict(job.stats) if job else None
                background = self.server.background_snapshot()
                if hint_for(background.get("last_error")):
                    background["last_error_hint"] = hint_for(background["last_error"])
                snapshot["background_scan"] = background
            self._send(200, snapshot)
        else:
            self._error(404, "Not found")

    def do_PATCH(self):
        if not self._gate(api=True):
            return
        path = urlsplit(self.path).path
        if not path.startswith("/api/accounts/"):
            self._error(404, "Not found")
            return
        try:
            self.server.store.update_account(unquote(path[len("/api/accounts/"):]), self._json())
            self._send(200, {"ok": True})
        except UserFacingError as exc:
            self._error(400, str(exc))
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            self._error(400, "Invalid update; check required steps before marking the account done")
        except sqlite3.Error:
            self._error(503, "The local database is temporarily unavailable")

    def do_POST(self):
        if not self._gate(api=True):
            return
        path = urlsplit(self.path).path
        try:
            action = ACCOUNT_ACTION.fullmatch(path)
            if path == "/api/accounts":
                account_id = self.server.store.create_account(self._json())
                self._send(201, {"id": account_id})
            elif action and action.group(2) == "decision":
                data = self._json()
                if set(data) - {"decision", "reason"} or "decision" not in data:
                    raise UserFacingError("Choose confirmed, rejected or undecided")
                self._send(200, self.server.store.decide(unquote(action.group(1)), data["decision"], data.get("reason")))
            elif action and action.group(2) == "sign-in-with":
                data = self._json()
                if set(data) != {"account_id"}:
                    raise UserFacingError("Choose an account you confirmed yourself")
                self._send(200, self.server.store.link_sign_in(unquote(action.group(1)), data["account_id"]))
            elif action:
                from .store import UNCHANGED
                data = self._json()
                if "step" not in data or set(data) - {"step", "state", "review_after"} or len(data) < 2:
                    raise UserFacingError("Choose a valid security step")
                self._send(200, self.server.store.set_step(unquote(action.group(1)), data["step"],
                                                           state=data.get("state", UNCHANGED),
                                                           review_after=data.get("review_after", UNCHANGED)))
            elif path == "/api/digest/seen":
                data = self._json()
                if set(data) != {"revision"}:
                    raise UserFacingError("These changes are no longer current; reload the page")
                self._send(200, self.server.store.acknowledge_changes(data["revision"]))
            elif path == "/api/digest/seen/undo":
                if self._json() != {}:
                    raise UserFacingError("There is no review mark to undo")
                self._send(200, self.server.store.undo_acknowledge_changes())
            elif path == "/api/catalog":
                self._send(200, self.server.store.add_provider(self._json()))
            elif path == "/api/catalog/remove":
                data = self._json()
                if set(data) != {"id"}:
                    raise UserFacingError("Only providers you added yourself can be removed")
                self._send(200, self.server.store.remove_provider(data["id"]))
            elif path in {"/api/exclusions", "/api/exclusions/remove"}:
                data = self._json()
                if path.endswith("remove"):
                    if set(data) != {"domain"}:
                        raise UserFacingError("This sender domain is not hidden")
                    self._send(200, self.server.store.remove_exclusion(data["domain"]))
                else:
                    if set(data) != {"domain", "reason"}:
                        raise UserFacingError("Choose why this sender domain should be hidden")
                    self._send(200, self.server.store.exclude_domain(data["domain"], data["reason"]))
            elif path == "/api/profile/mailboxes":
                data = self._json()
                if set(data) != {"address", "account_id"}:
                    raise UserFacingError("Choose an account you confirmed yourself")
                self._send(200, self.server.store.set_mailbox(data["address"], data["account_id"]))
            elif path in {"/api/profile/relations", "/api/profile/relations/remove"}:
                data = self._json()
                if path.endswith("remove"):
                    if set(data) != {"address", "other"}:
                        raise UserFacingError("These addresses have no saved relation")
                    self._send(200, self.server.store.remove_relation(data["address"], data["other"]))
                else:
                    if set(data) != {"address", "other", "kind"}:
                        raise UserFacingError("Choose how the two addresses are related")
                    self._send(200, self.server.store.relate_addresses(data["address"], data["other"], data["kind"]))
            elif path == "/api/undo":
                data = self._json()
                if set(data) != {"batch"} or (data["batch"] is not None and not isinstance(data["batch"], str)):
                    raise UserFacingError("There is no local change to undo")
                self._send(200, self.server.store.undo(data["batch"]))
            elif path == "/api/import":
                if self.headers.get_content_type() not in {"message/rfc822", "application/octet-stream"}:
                    raise ValueError("EML is required")
                raw = self._read(MAX_MESSAGE_BYTES)
                job_id = self.headers.get("X-Import-ID")
                with self.server.import_lock:
                    if job_id:
                        job = self.server.import_session(job_id)
                        job.process(raw)
                        result = job.publish()
                    else:
                        if self.server.active_import():
                            raise ImportBusy()
                        result = scan_messages(self.server.store, [raw], "eml")
                self._send(200, result)
            elif path == "/api/import/start":
                data = self._json()
                expected = data.get("expected")
                if set(data) != {"expected"} or type(expected) is not int or not 1 <= expected <= 10_000:
                    raise UserFacingError("Between 1 and 10000 files are required")
                with self.server.import_lock:
                    if self.server.active_import():
                        raise ImportBusy()
                    job = ScanSession(self.server.store, "eml", expected=expected)
                    self.server.import_job = job
                    result = dict(job.stats)
                self._send(200, result)
            elif path in {"/api/import/skip", "/api/import/finish"}:
                data = self._json()
                allowed = {"id", "count"} if path.endswith("skip") else {"id", "result"}
                if set(data) - allowed:
                    raise ValueError("Invalid import data")
                with self.server.import_lock:
                    job = self.server.import_session(data.get("id"))
                    result = job.skip(data.get("count", 1)) if path.endswith("skip") else job.finish(data.get("result"))
                self._send(200, result)
            elif path == "/api/profile/emails":
                data = self._json()
                if set(data) != {"emails"}:
                    raise UserFacingError("Specify only your own addresses")
                with self.server.import_lock:
                    if self.server.active_import():
                        raise ImportBusy()
                    added = self.server.store.add_emails(data["emails"])
                self._send(200, {"added": added, "rescan_recommended": bool(added)})
            elif path == "/api/bitwarden":
                from .bitwarden import make_export
                data = self._json()
                result = make_export(self.server.store, data.get("ids"), data.get("language", "en"))
                self._send(200, result, attachment="argus-bitwarden.json")
            elif path == "/api/bitwarden/preview":
                from .bitwarden import preview_export
                data = self._json()
                if set(data) != {"ids", "language", "target"}:
                    raise UserFacingError("An explicit selection is required")
                self._send(200, preview_export(self.server.store, data["ids"], data["language"], data["target"]))
            elif path == "/api/bitwarden/cli":
                from .bitwarden import add_to_unlocked_cli
                data = self._json()
                if set(data) != {"ids", "language", "confirmed"} or data["confirmed"] is not True:
                    raise UserFacingError("Confirm the Bitwarden transfer")
                result = add_to_unlocked_cli(self.server.store, data["ids"], data["language"])
                self._send(200, result)
            elif path == "/api/bitwarden/audit":
                from .bitwarden import audit_unlocked_cli
                data = self._json()
                if set(data) != {"ids", "language", "confirmed"} or data["confirmed"] is not True:
                    raise UserFacingError("Confirm the local Bitwarden check")
                self._send(200, audit_unlocked_cli(self.server.store, data["ids"], data["language"]))
            elif path == "/api/secure-next/bitwarden":
                from .bitwarden import add_to_unlocked_cli
                data = self._json()
                if set(data) != {"account_id", "language", "confirmed"} or data["confirmed"] is not True:
                    raise UserFacingError("Confirm the guided Bitwarden preparation")
                snapshot = self.server.store.snapshot(data["language"])
                current = snapshot["workflow"]["current"]
                if not isinstance(data["account_id"], str) or data["account_id"] != current:
                    raise UserFacingError("Choose the current guided account")
                result = add_to_unlocked_cli(self.server.store, [current], data["language"])
                self._send(200, result)
            elif path == "/api/bitwarden/resolve":
                from .handoffs import resolve
                self._send(200, resolve(self.server.store, self._json()))
            elif path == "/api/review-rule":
                data = self._json()
                if set(data) != {"months", "scope"}:
                    raise UserFacingError("Choose 6, 12 or 24 months and which accounts the rule covers")
                self._send(200, self.server.store.set_review_rule(data["months"], data["scope"]))
            elif path == "/api/review-rule/apply":
                data = self._json()
                if set(data) != {"ids"}:
                    raise UserFacingError("Choose accounts with a suggested review date")
                self._send(200, self.server.store.apply_review_proposals(data["ids"]))
            elif path == "/api/session":
                data = self._json()
                if data.get("action") == "start" and set(data) == {"action", "size"}:
                    self._send(200, self.server.store.start_session(data["size"]))
                elif data == {"action": "end"}:
                    self._send(200, self.server.store.end_session())
                else:
                    raise UserFacingError("Choose a session with one or three tasks")
            elif path == "/api/workflow":
                from .workflow import change_worklist
                self._send(200, change_worklist(self.server.store, self._json()))
            else:
                self._error(404, "Not found")
        except ImportBusy:
            self._error(409, "An EML import is already running. Finish or cancel it first.")
        except UserFacingError as exc:
            # Fixed, translatable texts only (Bitwarden, worklist, mailbox and
            # account rules). Every other error stays generic.
            self._error(400, str(exc))
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            self._error(400, "Request failed; check format, selection and size limits")
        except sqlite3.Error:
            self._error(503, "The local database is temporarily unavailable")

    def do_OPTIONS(self):
        self._error(403, "Cross-origin access is not authorized")


def startup_notice(background, language="en"):
    """Tell the truth about mailbox activity before the dashboard starts serving."""
    from .i18n import translate
    if background.get("enabled") and not background.get("target_confirmed"):
        return translate("Press Ctrl+C to stop the server. Scheduled IMAP scans wait for approval of the current IMAP settings and will not connect; run background-imap enable to approve them.", language)
    if background.get("enabled"):
        return translate("Press Ctrl+C to stop the server. Scheduled read-only IMAP scans are enabled and may connect to your mailbox while it runs; use background-imap disable to stop them.", language)
    return translate("Press Ctrl+C to stop the server. No mailbox connection is active.", language)


def serve(store: Store, port=8765, open_browser=False, language="en"):
    from .i18n import translate
    with DashboardServer(store, port) as server:
        server.start_background_scans()
        print(translate("Local dashboard: ", language) + server.url, flush=True)
        print(startup_notice(server.background_snapshot(), language), flush=True)
        if open_browser:
            import webbrowser
            webbrowser.open(server.url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
