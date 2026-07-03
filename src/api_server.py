"""Lightweight HTTP API server for the dashboard.

Runs on port 4900 (bound to 0.0.0.0 inside Docker).
Returns JSON from the SQLite database.
"""
from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

from .database import dashboard_summary, equity_history, get_closed_trades, get_open_trades


class APIHandler(BaseHTTPRequestHandler):

    def _json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == "/api/summary":
            self._json(dashboard_summary())
        elif self.path == "/api/equity":
            self._json(equity_history(200))
        elif self.path == "/api/trades/open":
            self._json(get_open_trades())
        elif self.path == "/api/trades/closed":
            self._json(get_closed_trades(100))
        elif self.path == "/api/health":
            self._json({"status": "ok"})
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        pass


def run_api_server(port: int = 4900):
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    import threading
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t
