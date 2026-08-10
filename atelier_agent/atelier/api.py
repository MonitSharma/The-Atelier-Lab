"""Minimal local JSON HTTP API over :class:`AtelierService`.

Binding to loopback is not by itself a security boundary. Any page the user
visits in a browser can issue requests to ``127.0.0.1``, and a hostname that
resolves to ``127.0.0.1`` (DNS rebinding) can read the responses. Since this API
writes files (``/upload``) and can start an agent that edits a repository
(``/repo_action``), three cheap browser-side invariants are enforced on every
request:

* **Host** must name loopback when bound to loopback — defeats DNS rebinding,
  which cannot forge it. Deliberate non-loopback exposure is allowed with a
  warning and same-host Origin checks, but the API has no authentication.
* **Origin**, when present, must be this same server — defeats classic CSRF.
* **Content-Type** on POST must be JSON — a cross-origin ``fetch`` cannot set
  that without a preflight, and we deliberately answer no CORS preflight.

The bundled UI at ``/ui`` is same-origin, so it satisfies all three unchanged.
"""

from __future__ import annotations

import ipaddress
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from atelier.service import AtelierService
from atelier.web import render_index

#: Names that denote this machine. Anything else in a Host header means the
#: request arrived via a domain that resolves here — i.e. a rebinding attempt.
_LOOPBACK_NAMES = ("127.0.0.1", "localhost", "[::1]", "::1")


class _Handler(BaseHTTPRequestHandler):
    service: AtelierService

    def _local_names(self) -> tuple[set[str], set[str]]:
        """Return the acceptable ``(hosts, origins)`` for the bound port."""
        port = self.server.server_address[1]
        hosts = {f"{name}:{port}" for name in _LOOPBACK_NAMES} | set(_LOOPBACK_NAMES)
        origins = {f"http://{name}:{port}" for name in _LOOPBACK_NAMES}
        origins |= {f"http://{name}" for name in _LOOPBACK_NAMES}
        return hosts, origins

    def _is_loopback_binding(self) -> bool:
        """Whether the server is bound only to a loopback interface."""
        bound_host = str(self.server.server_address[0]).strip().lower()
        if bound_host in {"localhost", "ip6-localhost"}:
            return True
        try:
            return ipaddress.ip_address(bound_host).is_loopback
        except ValueError:
            return False

    def _reject_untrusted_origin(self, *, require_json: bool) -> bool:
        """Write an error and return True when the request must not proceed."""
        hosts, origins = self._local_names()

        host = (self.headers.get("Host") or "").strip().lower()
        loopback_binding = self._is_loopback_binding()
        if loopback_binding and host and host not in hosts:
            self._write({"status": "error", "error_type": "untrusted_host",
                         "message": "This API only accepts loopback Host headers."}, 403)
            return True

        origin = (self.headers.get("Origin") or "").strip().lower()
        if loopback_binding:
            origin_allowed = origin in origins
        else:
            # A deliberately exposed server cannot know its public hostname
            # from the bind address (0.0.0.0 / ::). Still require a same-host
            # HTTP Origin, rather than accepting arbitrary cross-site callers.
            origin_parts = urlparse(origin) if origin else None
            origin_allowed = bool(
                origin_parts
                and origin_parts.scheme == "http"
                and host
                and origin_parts.netloc == host
            )
        if origin and not origin_allowed:
            self._write({"status": "error", "error_type": "cross_origin_denied",
                         "message": "Cross-origin requests are not accepted."}, 403)
            return True

        # Browsers always send this; a cross-site caller cannot suppress it.
        fetch_site = (self.headers.get("Sec-Fetch-Site") or "").strip().lower()
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            self._write({"status": "error", "error_type": "cross_origin_denied",
                         "message": "Cross-site requests are not accepted."}, 403)
            return True

        if require_json:
            content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if content_type != "application/json":
                self._write({"status": "error", "error_type": "unsupported_media_type",
                             "message": "POST requires Content-Type: application/json."}, 415)
                return True
        return False

    def _write(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _write_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        # The page is fully self-contained; forbid any external load, and stop
        # another site from framing it to drive the UI clickjacking-style.
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "connect-src 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Refuse CORS preflight outright — no cross-origin caller is welcome.

        Answering nothing here is what makes the JSON Content-Type requirement
        binding: a cross-origin ``fetch`` with a JSON body must preflight first,
        and a 405 with no ``Access-Control-Allow-*`` headers stops it there.
        """
        self.send_response(405)
        self.send_header("Allow", "GET, POST")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self._reject_untrusted_origin(require_json=False):
            return
        parsed = urlparse(self.path)
        path = parsed.path
        if path in {"", "/", "/ui"}:
            self._write_html(render_index())
            return
        operation = path.strip("/") or "health"
        if operation == "sources":
            operation = "library"
        if operation == "approvals":
            self._write(self.service.dispatch("approvals"))
            return
        if operation in {"source", "source_view"} and parse_qs(parsed.query).get("path"):
            payload = self.service.dispatch("source", {"path": parse_qs(parsed.query)["path"][0]})
            self._write(payload, 200 if payload.get("status", "ok") != "error" else 400)
            return
        if operation == "workflow" and parse_qs(parsed.query).get("run_id"):
            payload = self.service.dispatch("workflow_get", {"run_id": parse_qs(parsed.query)["run_id"][0]})
            self._write(payload, 200 if payload.get("status", "ok") != "error" else 404)
            return
        if operation.startswith("workflow/"):
            payload = self.service.dispatch("workflow_get", {"run_id": operation.split("/", 1)[1]})
            self._write(payload, 200 if payload.get("status", "ok") != "error" else 404)
            return
        payload = self.service.dispatch(operation.replace("/", "_"))
        self._write(payload, 200 if payload.get("status", "ok") != "error" else 404)

    def do_POST(self) -> None:  # noqa: N802
        if self._reject_untrusted_origin(require_json=True):
            return
        operation = urlparse(self.path).path.strip("/").replace("/", "_")
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("JSON body must be an object")
            payload = self.service.dispatch(operation, body)
            self._write(payload, 200 if payload.get("status", "ok") != "error" else 400)
        except (ValueError, json.JSONDecodeError) as exc:
            self._write({"status": "error", "error_type": "invalid_json", "message": str(exc)}, 400)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8787, service: AtelierService | None = None) -> None:
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = host in {"localhost", "ip6-localhost"}
    if not is_loopback:
        print(
            "WARNING: Atelier API is exposed beyond loopback without authentication.",
            file=sys.stderr,
        )
    handler = type("AtelierHandler", (_Handler,), {"service": service or AtelierService()})
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
