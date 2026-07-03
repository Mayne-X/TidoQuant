"""Lightweight HTTP API server for the dashboard.

Runs on port 4900 (bound to 0.0.0.0 inside Docker).
Returns JSON from the SQLite database.
"""
from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

from .database import (
    cycle_logs,
    dashboard_detail,
    dashboard_summary,
    daily_pnl,
    equity_history,
    get_closed_trades,
    get_open_trades,
    pipeline_detail,
    trades_by_symbol,
)


class APIHandler(BaseHTTPRequestHandler):

    def _json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        path = self.path
        # Allow /api prefix or bare paths for compatibility
        if path == "/api/summary" or path == "/summary":
            self._json(dashboard_summary())
        elif path == "/api/detail" or path == "/detail":
            self._json(dashboard_detail())
        elif path == "/api/equity" or path == "/equity":
            self._json(equity_history(200))
        elif path == "/api/trades/open" or path == "/trades/open":
            self._json(get_open_trades())
        elif path == "/api/trades/closed" or path == "/trades/closed":
            self._json(get_closed_trades(100))
        elif path == "/api/trades/by_symbol" or path == "/trades/by_symbol":
            self._json(trades_by_symbol())
        elif path == "/api/pnl/daily" or path == "/pnl/daily":
            self._json(daily_pnl(30))
        elif path == "/api/cycles" or path == "/cycles":
            self._json(cycle_logs(20))
        elif path == "/api/pipeline" or path == "/pipeline":
            self._json(pipeline_detail(20))
        elif path == "/api/health" or path == "/health":
            self._json({"status": "ok", "agent_pipeline": "active"})
        else:
            self._json({"error": "not found", "path": path}, 404)

    def log_message(self, fmt, *args):
        pass


def run_api_server(port: int = 4900):
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    import threading
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t
