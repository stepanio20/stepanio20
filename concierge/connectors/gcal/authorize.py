"""One-time Google OAuth Authorization-Code dance for Calendar.

Usage (after editing secrets.env and saving the OAuth client JSON):
    source secrets.env
    python3 -m concierge.connectors.gcal.authorize

Opens the consent page. After consent, Google redirects to
http://localhost:8920/callback?code=... which we catch + exchange for tokens.
The token JSON is saved to GCAL_TOKEN_PATH.
"""
from __future__ import annotations

import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from . import client as gclient

_REDIRECT = "http://localhost:8920/callback"


def _need(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Missing env var {name}. Source secrets.env and fill it in (see CONNECTIONS.md §2).")
    return v


class _Handler(BaseHTTPRequestHandler):
    captured: dict[str, str] = {}

    def do_GET(self):  # noqa: N802
        q = urllib.parse.urlparse(self.path).query
        _Handler.captured.update(dict(urllib.parse.parse_qsl(q)))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>Concierge: Google Calendar connected.</h2><p>You can close this tab.</p>")

    def log_message(self, fmt, *args):
        pass


def main() -> int:
    oauth_json = Path(_need("GCAL_OAUTH_JSON"))
    if not oauth_json.exists():
        sys.exit(f"GCAL_OAUTH_JSON does not exist: {oauth_json}. Save the OAuth client JSON there (see CONNECTIONS.md §2).")
    cid, csec = gclient._read_client_json(oauth_json)
    token_path = Path(os.environ.get("GCAL_TOKEN_PATH", "secrets/gcal_token.json"))

    parsed = urllib.parse.urlparse(_REDIRECT)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8920

    state = secrets.token_urlsafe(16)
    url = gclient.authorize_url(cid, _REDIRECT, state=state)
    print(f"Open this in your browser if it doesn't open automatically:\n  {url}\n")
    try:
        webbrowser.open(url)
    except webbrowser.Error:
        pass

    server = HTTPServer((host, port), _Handler)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    print(f"Listening on {_REDIRECT} … waiting for Google to redirect back.")

    while "code" not in _Handler.captured and "error" not in _Handler.captured:
        try:
            th.join(timeout=0.5)
        except KeyboardInterrupt:
            server.shutdown()
            return 130

    server.shutdown()
    if "error" in _Handler.captured:
        print(f"OAuth error: {_Handler.captured}", file=sys.stderr)
        return 2
    if _Handler.captured.get("state") != state:
        print("OAuth state mismatch — possible CSRF, aborting.", file=sys.stderr)
        return 3

    tok = gclient.exchange_code(cid, csec, _Handler.captured["code"], _REDIRECT)
    tok.save(token_path)
    print(f"Saved Google Calendar token to {token_path}.")
    print("Next: make_weekly_plan picks up the connection automatically; --push-calendar flag (coming next) writes events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
