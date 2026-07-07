"""Minimal Whoop API v2 client. Stdlib only (urllib).

Docs: https://developer.whoop.com/api/

This deliberately implements only what the recommendation engine reads
(profile + recovery + sleep + workouts). The webhook receiver is a separate
concern (needs a public HTTPS server — not in scope for the personal MVP).

Token storage is a JSON file at WHOOP_TOKEN_PATH. The refresh-token rotates
on every refresh per Whoop's policy — the client persists the new one each time.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

API_BASE = "https://api.prod.whoop.com/developer"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
DEFAULT_SCOPES = [
    "read:recovery", "read:sleep", "read:workout", "read:cycles",
    "read:profile", "read:body_measurement", "offline",
]


@dataclass
class Token:
    access_token: str
    refresh_token: str
    expires_at: float        # epoch seconds
    scope: str = ""

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "Token":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + float(data.get("expires_in", 3600)) - 60,
            scope=data.get("scope", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"access_token": self.access_token, "refresh_token": self.refresh_token,
                "expires_at": self.expires_at, "scope": self.scope}

    @classmethod
    def load(cls, path: Path) -> "Token | None":
        if not path.exists():
            return None
        d = json.loads(path.read_text())
        return cls(**d)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _http(method: str, url: str, *, headers: dict[str, str] | None = None,
          body: bytes | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8")
    return json.loads(text) if text.strip() else {}


def authorize_url(client_id: str, redirect_uri: str, scopes: list[str] | None = None,
                  state: str = "concierge") -> str:
    q = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes or DEFAULT_SCOPES),
        "state": state,
    })
    return f"{AUTH_URL}?{q}"


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Token:
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    data = _http("POST", TOKEN_URL,
                 headers={"Content-Type": "application/x-www-form-urlencoded"},
                 body=body)
    return Token.from_response(data)


def refresh(client_id: str, client_secret: str, refresh_token: str) -> Token:
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": " ".join(DEFAULT_SCOPES),
    }).encode()
    data = _http("POST", TOKEN_URL,
                 headers={"Content-Type": "application/x-www-form-urlencoded"},
                 body=body)
    return Token.from_response(data)


class WhoopClient:
    def __init__(self, token: Token, client_id: str = "", client_secret: str = "",
                 token_path: Path | None = None):
        self.token = token
        self.client_id = client_id or os.environ.get("WHOOP_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("WHOOP_CLIENT_SECRET", "")
        self.token_path = token_path

    @classmethod
    def from_env(cls) -> "WhoopClient":
        path = Path(os.environ.get("WHOOP_TOKEN_PATH", "secrets/whoop_token.json"))
        tok = Token.load(path)
        if not tok:
            raise RuntimeError(f"No Whoop token at {path}. Run `python3 -m concierge.connectors.whoop.authorize` first.")
        return cls(token=tok, token_path=path)

    def _maybe_refresh(self) -> None:
        if self.token.expires_at > time.time():
            return
        if not (self.client_id and self.client_secret):
            raise RuntimeError("Token expired and WHOOP_CLIENT_ID/SECRET not set.")
        self.token = refresh(self.client_id, self.client_secret, self.token.refresh_token)
        if self.token_path:
            self.token.save(self.token_path)

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        self._maybe_refresh()
        url = f"{API_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return _http("GET", url, headers={"Authorization": f"Bearer {self.token.access_token}"})

    # --- read endpoints --------------------------------------------------- #
    def profile(self) -> dict[str, Any]:
        return self._get("/v2/user/profile/basic")

    def body_measurement(self) -> dict[str, Any]:
        return self._get("/v2/user/measurement/body")

    def recovery_collection(self, start_iso: str, end_iso: str, limit: int = 25) -> dict[str, Any]:
        return self._get("/v2/recovery", {"start": start_iso, "end": end_iso, "limit": str(limit)})

    def sleep_collection(self, start_iso: str, end_iso: str, limit: int = 25) -> dict[str, Any]:
        return self._get("/v2/activity/sleep",
                         {"start": start_iso, "end": end_iso, "limit": str(limit)})

    def workout_collection(self, start_iso: str, end_iso: str, limit: int = 25) -> dict[str, Any]:
        return self._get("/v2/activity/workout",
                         {"start": start_iso, "end": end_iso, "limit": str(limit)})

    def cycle_collection(self, start_iso: str, end_iso: str, limit: int = 25) -> dict[str, Any]:
        return self._get("/v2/cycle", {"start": start_iso, "end": end_iso, "limit": str(limit)})
