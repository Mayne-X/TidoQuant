"""Lightweight HTTP API server for the dashboard.

Runs on port 4900. Returns JSON from SQLite database.
Supports both swing and scalper strategy data.
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
        self.wfile.write(json.dumps(data, default=str).encode())

    def do_GET(self):
        path = self.path
        if path in ("/api/summary", "/summary"):
            self._json(dashboard_summary())
        elif path in ("/api/detail", "/detail"):
            self._json(dashboard_detail())
        elif path in ("/api/equity", "/equity"):
            self._json(equity_history(500))
        elif path in ("/api/trades/open", "/trades/open"):
            self._json(get_open_trades())
        elif path in ("/api/trades/closed", "/trades/closed"):
            self._json(get_closed_trades(200))
        elif path in ("/api/trades/by_symbol", "/trades/by_symbol"):
            self._json(trades_by_symbol())
        elif path in ("/api/pnl/daily", "/pnl/daily"):
            self._json(daily_pnl(90))
        elif path in ("/api/cycles", "/cycles"):
            self._json(cycle_logs(100))
        elif path in ("/api/pipeline", "/pipeline"):
            self._json(pipeline_detail(100))
        elif path in ("/api/health", "/health"):
            self._json({"status": "ok", "agent_pipeline": "active", "mode": "dual-strategy"})
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
