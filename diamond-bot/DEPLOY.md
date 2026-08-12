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

## 5. Production checklist (do NOT skip — data-loss & security)

**Persistence (critical).** SQLite lives on the container's ephemeral disk → every redeploy
wipes all users, subscriptions, listings, demands and matches. Fix before real users:
1. Railway → service → **Volumes → New Volume**, mount path `/data`.
2. Set `DATABASE_PATH=/data/diamond_bot.db` (the app auto-creates the dir).
3. Seed the volume once (the 38k inventory is not in git):
   `python seed_inventory.py "<stock file>" --source market --replace` run inside the
   deployed container (Railway shell), or copy an existing `diamond_bot.db` onto the volume.
   *(For scale, swap SQLite for managed Postgres by reimplementing `db.py`'s function surface.)*

**Single replica.** A Telegram long-poller cannot be load-balanced — keep **Replicas = 1**.
A second replica = a second `getUpdates` = HTTP 409 and dropped updates.

**Secrets — rotate everything shared in chat (treat as burned):**
- `TELEGRAM_BOT_TOKEN` → @BotFather `/revoke`.
- `VEYM_API_KEY`, `VEYM_WEBHOOK_SECRET`, `MAMO_API_KEY` → rotate in veym/MamoPay, then
  re-register the webhook (step 3) with the new secret.
- Set all only as Railway service variables — never in chat or git.
- Keep `FREE_REVEAL=false` in production (it opens the reveal gate for everyone).

**Webhook hardening.** Front `/mamopay-webhook` with Railway/Cloudflare per-IP rate limiting
(the in-app throttle covers Telegram handlers, not the webhook).

## Notes
- Only one process may long-poll a bot token at a time. Stop any other instance
  (e.g. a local test run) before/after deploying, or Telegram returns 409 Conflict.
- To read group messages, @BotFather → `/setprivacy` → **Disable**, then add the bot
  to the group (bot-based) — or use `login.py` (user-session) for groups you already belong to.
- Admin `/stats` shows the acquisition→revenue funnel (set `ADMIN_USER_IDS`).
