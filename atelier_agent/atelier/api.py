"""Minimal local JSON HTTP API over :class:`AtelierService`."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from atelier.service import AtelierService
from atelier.web import render_index


class _Handler(BaseHTTPRequestHandler):
    service: AtelierService

    def _write(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
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
    handler = type("AtelierHandler", (_Handler,), {"service": service or AtelierService()})
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
