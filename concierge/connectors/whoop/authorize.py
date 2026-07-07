"""One-time OAuth Authorization-Code dance for Whoop, using a local listener.

Usage (after editing secrets.env):
    source secrets.env
    python3 -m concierge.connectors.whoop.authorize

Opens the consent page in your browser. After you authorise, Whoop redirects to
http://localhost:8910/callback?code=... which this script catches, exchanges
for tokens, and saves to WHOOP_TOKEN_PATH (default secrets/whoop_token.json).
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

from . import client as wclient


def _need(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Missing env var {name}. Source secrets.env and fill it in (see CONNECTIONS.md §1).")
    return v


class _Handler(BaseHTTPRequestHandler):
    captured: dict[str, str] = {}

    def do_GET(self):  # noqa: N802
        q = urllib.parse.urlparse(self.path).query
        params = dict(urllib.parse.parse_qsl(q))
        _Handler.captured.update(params)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>Concierge: Whoop connected.</h2><p>You can close this tab.</p>")

    def log_message(self, fmt, *args):  # silence default access log
        pass


def main() -> int:
    client_id = _need("WHOOP_CLIENT_ID")
    client_secret = _need("WHOOP_CLIENT_SECRET")
    redirect_uri = os.environ.get("WHOOP_REDIRECT_URI", "http://localhost:8910/callback")
    token_path = Path(os.environ.get("WHOOP_TOKEN_PATH", "secrets/whoop_token.json"))

    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8910

    state = secrets.token_urlsafe(16)
    url = wclient.authorize_url(client_id, redirect_uri, state=state)
    print(f"Open this in your browser if it doesn't open automatically:\n  {url}\n")
    try:
        webbrowser.open(url)
    except webbrowser.Error:
        pass

    server = HTTPServer((host, port), _Handler)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    print(f"Listening on {redirect_uri} … waiting for Whoop to redirect back.")

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

    code = _Handler.captured["code"]
    tok = wclient.exchange_code(client_id, client_secret, code, redirect_uri)
    tok.save(token_path)
    print(f"Saved Whoop token to {token_path}. Scope: {tok.scope}")
    print("Next: python3 -m concierge.connectors.whoop.sync --user me")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
