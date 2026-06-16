"""Minimal Google Calendar client — stdlib only.

Uses OAuth2 (installed-app flow). The user's OAuth client JSON (downloaded
from console.cloud.google.com) is at GCAL_OAUTH_JSON; the refresh token after
authorisation lands at GCAL_TOKEN_PATH.

API docs: https://developers.google.com/calendar/api/v3/reference
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

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://www.googleapis.com/calendar/v3"
SCOPES = ["https://www.googleapis.com/auth/calendar.events",
          "https://www.googleapis.com/auth/calendar"]


@dataclass
class Token:
    access_token: str
    refresh_token: str
    expires_at: float
    scope: str = ""

    @classmethod
    def from_response(cls, data: dict[str, Any], prev_refresh: str = "") -> "Token":
        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token") or prev_refresh,
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
        return cls(**json.loads(path.read_text()))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _read_client_json(path: Path) -> tuple[str, str]:
    d = json.loads(path.read_text())
    block = d.get("installed") or d.get("web") or d
    return block["client_id"], block["client_secret"]


def _http(method: str, url: str, *, headers=None, body=None) -> dict[str, Any]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8")
    return json.loads(text) if text.strip() else {}


def authorize_url(client_id: str, redirect_uri: str, scopes: list[str] = SCOPES,
                  state: str = "concierge") -> str:
    q = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
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
    }).encode()
    data = _http("POST", TOKEN_URL,
                 headers={"Content-Type": "application/x-www-form-urlencoded"},
                 body=body)
    return Token.from_response(data, prev_refresh=refresh_token)


class GCalClient:
    def __init__(self, token: Token, client_id: str, client_secret: str,
                 token_path: Path | None = None):
        self.token = token
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = token_path

    @classmethod
    def from_env(cls) -> "GCalClient":
        oauth_json = Path(os.environ.get("GCAL_OAUTH_JSON", "secrets/gcal_oauth.json"))
        token_path = Path(os.environ.get("GCAL_TOKEN_PATH", "secrets/gcal_token.json"))
        cid, csec = _read_client_json(oauth_json)
        tok = Token.load(token_path)
        if not tok:
            raise RuntimeError(f"No GCal token at {token_path}. Run `python3 -m concierge.connectors.gcal.authorize` first.")
        return cls(token=tok, client_id=cid, client_secret=csec, token_path=token_path)

    def _maybe_refresh(self) -> None:
        if self.token.expires_at > time.time():
            return
        self.token = refresh(self.client_id, self.client_secret, self.token.refresh_token)
        if self.token_path:
            self.token.save(self.token_path)

    def _req(self, method: str, path: str, body: dict | None = None,
             params: dict | None = None) -> dict[str, Any]:
        self._maybe_refresh()
        url = f"{API_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        h = {"Authorization": f"Bearer {self.token.access_token}"}
        b = None
        if body is not None:
            h["Content-Type"] = "application/json"
            b = json.dumps(body).encode()
        return _http(method, url, headers=h, body=b)

    # --- calendars + events ---------------------------------------------- #
    def list_calendars(self) -> list[dict]:
        return self._req("GET", "/users/me/calendarList").get("items", [])

    def find_or_create_calendar(self, name: str) -> str:
        """Return calendarId."""
        for c in self.list_calendars():
            if c.get("summary") == name:
                return c["id"]
        r = self._req("POST", "/calendars", body={"summary": name, "timeZone": "Europe/Madrid"})
        return r["id"]

    def insert_event(self, calendar_id: str, event: dict) -> dict:
        return self._req("POST", f"/calendars/{urllib.parse.quote(calendar_id)}/events", body=event)
