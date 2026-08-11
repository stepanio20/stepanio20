# Deploy DiamondScanBot 24/7 (Railway)

The bot runs one process that does **both** Telegram long-polling and an HTTP
server for the `veym` payment webhook (binds `$PORT`). Railway is the natural
host (veym itself runs there).

## 1. Create the service
1. Railway → **New Project → Deploy from GitHub repo** → pick this repo.
2. Service → **Settings → Root Directory** = `diamond-bot`
   (so the `Dockerfile` / `railway.json` here are used).
3. Railway builds the Dockerfile (installs deps + DejaVu fonts for the cards).

## 2. Set variables (Service → Variables)
Required:
- `TELEGRAM_BOT_TOKEN` — from @BotFather (rotate the one shared in chat: `/revoke`).

Payments (veym / MamoPay, AED):
- `VEYM_API_KEY` — the veym `apikey` (rotate the shared one).
- `VEYM_BASE_URL` = `https://veym.up.railway.app/v1`
- `VEYM_WEBHOOK_SECRET` — the `authorization` value veym will send to `/mamopay-webhook`.
- `MAMO_API_KEY` — the MamoPay merchant key that **creates** the hosted charge
  (the one the Dubai Unit Bot uses). Without it, plan buttons show a graceful
  "activation pending" message instead of a pay link.
- `PUBLIC_BASE_URL` — set to the Railway domain after step 3 (e.g. `https://diamondscan.up.railway.app`).

Ops:
- `ADMIN_USER_IDS` — your Telegram numeric id (for `/status`, `/publish`, and to bypass the paywall).
- `FREE_REVEAL` = `false` in production (`true` only for demos — it opens the paywall for everyone).
- `CONTACT_PHONE`, `TELEGRAM_CHANNEL_ID` (optional deal-card channel), `GIA_API_KEY` (optional).

Optional ingestion (BYO-session — see `login.py`):
- `TG_API_ID`, `TG_API_HASH`, `TG_SESSION`.

`PORT` is injected by Railway automatically — don't set it.

## 3. Domain + webhook
1. Service → **Settings → Networking → Generate Domain**. Copy it into `PUBLIC_BASE_URL`.
2. Register the webhook with veym so payment events reach the bot:
   ```
   curl -X POST https://veym.up.railway.app/v1/webhooks \
     -H "apikey: $VEYM_API_KEY" -H "Content-Type: application/json" \
     -d '{"url":"https://<your-domain>/mamopay-webhook","authorization":"<VEYM_WEBHOOK_SECRET>"}'
   ```
   (Confirm the exact field names against how the Dubai Unit Bot registered its webhook —
   the existing entries are visible at `GET /v1/webhooks`.)

## 4. Verify
- Health: `https://<your-domain>/health` → `DiamondScan up`.
- Logs show: `Starting @DiamondScanBot ...` and `Webhook server on :<port>`.
- DM the bot `/start` → it replies.

## Notes
- Only one process may long-poll a bot token at a time. Stop any other instance
  (e.g. a local test run) before/after deploying, or Telegram returns 409 Conflict.
- To read group messages, @BotFather → `/setprivacy` → **Disable**, then add the bot
  to the group (bot-based) — or use `login.py` (user-session) for groups you already belong to.
