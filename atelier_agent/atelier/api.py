"""Minimal local JSON HTTP API over :class:`AtelierService`."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from atelier.service import AtelierService


class _Handler(BaseHTTPRequestHandler):
    service: AtelierService

    def _write(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        operation = urlparse(self.path).path.strip("/") or "health"
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
