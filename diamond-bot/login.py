"""
One-time Telegram login to enable BYO-session group ingestion.

Run this LOCALLY on your own machine (never on a shared server) under the account
that is *already a member* of the diamond groups you want the radar to read:

    pip install telethon
    python login.py

It asks for:
  • API_ID and API_HASH  — create them once at https://my.telegram.org → "API development tools"
  • your phone number     — the account that belongs to the groups
  • the login code        — Telegram sends it to that account (and 2FA password if set)

It prints a TG_SESSION string. Paste TG_API_ID / TG_API_HASH / TG_SESSION into the
bot's environment (.env locally, or Railway variables). The reader is READ-ONLY: it
never sends messages. Only groups this account already belongs to are read — no covert
scraping, no central "scanner" account. You can revoke the session anytime in
Telegram → Settings → Devices.
"""
from __future__ import annotations

import getpass

try:
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
except Exception:
    raise SystemExit("Install Telethon first:  pip install telethon")


def main() -> None:
    api_id = int(input("API_ID: ").strip())
    api_hash = input("API_HASH: ").strip()
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        # Telethon handles the phone + code (+ 2FA) prompts interactively.
        session = client.session.save()
        me = client.get_me()
        print("\nLogged in as:", getattr(me, "username", None) or me.first_name)
        print("\nAdd these to your environment (.env or Railway variables):\n")
        print(f"TG_API_ID={api_id}")
        print(f"TG_API_HASH={api_hash}")
        print(f"TG_SESSION={session}")
        print("\nKeep TG_SESSION secret — it grants access to this account.")


if __name__ == "__main__":
    main()
