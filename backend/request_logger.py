"""
request_logger.py — Phase 7: Structured per-request logging middleware.

Logs to both console (human-readable) and a rotating JSON file (machine-readable).
Every request records: timestamp, user_id, endpoint, method, status, execution_time_ms, error.

Usage (in app.py):
    from request_logger import register_logging_middleware
    register_logging_middleware(app)
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from flask import Flask, g, request

# ── Log file setup ────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_json_log_path = os.path.join(LOG_DIR, "requests.jsonl")

# Rotating handler: max 5 MB per file, keep 3 backups
_file_handler = RotatingFileHandler(
    _json_log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)

# Console handler — human-readable
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(
    logging.Formatter("[%(levelname)s] %(message)s")
)

logger = logging.getLogger("medicsense.request")
logger.setLevel(logging.DEBUG)
logger.addHandler(_file_handler)
logger.addHandler(_console_handler)
logger.propagate = False  # don't double-log to root


# ── Middleware ─────────────────────────────────────────────────────────────────

def register_logging_middleware(app: Flask) -> None:
    """Register before/after request hooks for structured request logging."""

    @app.before_request
    def _before() -> None:
        g.req_start = time.perf_counter()
        g.req_error = None
        # Extract user_id from JSON body or query string (best-effort)
        try:
            body = request.get_json(silent=True, force=True) or {}
            g.req_user_id = (
                body.get("user_id")
                or body.get("userId")
                or request.args.get("user_id")
                or request.args.get("userId")
                or "anonymous"
            )
        except Exception:
            g.req_user_id = "anonymous"

    @app.after_request
    def _after(response):
        try:
            elapsed_ms = round((time.perf_counter() - g.req_start) * 1000, 1)
            user_id = getattr(g, "req_user_id", "anonymous")
            error = getattr(g, "req_error", None)

            # Build structured log entry
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "endpoint": request.path,
                "user_id": user_id,
                "status": response.status_code,
                "time_ms": elapsed_ms,
            }
            if error:
                entry["error"] = str(error)

            # Write JSON line to rotating file
            _file_handler.stream.write(json.dumps(entry) + "\n")
            _file_handler.stream.flush()

            # Human-readable console line
            level = logging.WARNING if response.status_code >= 400 else logging.INFO
            status_icon = "✅" if response.status_code < 400 else ("⚠️" if response.status_code < 500 else "❌")
            err_suffix = f"  ERR={error}" if error else ""
            logger.log(
                level,
                f"{status_icon} {request.method:6s} {request.path:<30s} "
                f"[{response.status_code}] {elapsed_ms:>7.1f}ms  uid={user_id}{err_suffix}",
            )
        except Exception as log_exc:
            # Logging must never crash the app
            print(f"[LOGGER ERROR] {log_exc}")

        return response

    @app.errorhandler(Exception)
    def _handle_unhandled(exc):
        """Catch unhandled exceptions, log them, return 500."""
        g.req_error = repr(exc)
        logger.error(f"UNHANDLED {type(exc).__name__}: {exc}", exc_info=True)
        return {"success": False, "error": "An internal error occurred."}, 500
