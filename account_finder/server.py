"""Loopback-only dashboard with memory-only bearer token and strict origins."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit, unquote

from .analysis import MAX_MESSAGE_BYTES
from .scan import ScanSession, scan_messages
from .store import Store

WEB = Path(__file__).with_name("web")


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

    def server_close(self):
        with self.import_lock:
            if self.import_job and self.import_job.stats["running"]:
                self.import_job.finish("partial")
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    server_version = "AccountFinder"
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
        self._send(status, {"error": message})

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
            self._send(200, page.replace("__LOCAL_TOKEN__", self.server.token), "text/html; charset=utf-8")
        elif path == "/i18n.js":
            from .i18n import catalog
            self._send(200, "window.AF_TRANSLATIONS=" + json.dumps(catalog(), ensure_ascii=False) + ";", "text/javascript; charset=utf-8")
        elif path in {"/app.js", "/style.css"}:
            kind = "text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8"
            self._send(200, (WEB / path[1:]).read_bytes(), kind)
        elif path == "/api/accounts":
            with self.server.import_lock:
                job = self.server.active_import()
                snapshot = self.server.store.snapshot()
                snapshot["active_import"] = dict(job.stats) if job else None
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
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            self._error(400, "Invalid update; check required steps before marking the account done")
        except sqlite3.Error:
            self._error(503, "The local database is temporarily unavailable")

    def do_POST(self):
        if not self._gate(api=True):
            return
        path = urlsplit(self.path).path
        try:
            if path == "/api/import":
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
                    raise ValueError("Between 1 and 10000 files are required")
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
                    raise ValueError("Specify only your own addresses")
                with self.server.import_lock:
                    if self.server.active_import():
                        raise ImportBusy()
                    added = self.server.store.add_emails(data["emails"])
                self._send(200, {"added": added, "rescan_recommended": bool(added)})
            elif path == "/api/bitwarden":
                from .bitwarden import make_export
                data = self._json()
                result = make_export(self.server.store, data.get("ids"), data.get("language", "en"))
                self._send(200, result, attachment="account-finder-bitwarden.json")
            else:
                self._error(404, "Not found")
        except ImportBusy:
            self._error(409, "An EML import is already running. Finish or cancel it first.")
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            self._error(400, "Request failed; check format, selection and size limits")
        except sqlite3.Error:
            self._error(503, "The local database is temporarily unavailable")

    def do_OPTIONS(self):
        self._error(403, "Cross-origin access is not authorized")


def serve(store: Store, port=8765, open_browser=False, language="en"):
    from .i18n import translate
    with DashboardServer(store, port) as server:
        print(translate("Local dashboard: ", language) + server.url, flush=True)
        print(translate("Press Ctrl+C to stop the server. No mailbox connection is active.", language), flush=True)
        if open_browser:
            import webbrowser
            webbrowser.open(server.url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
