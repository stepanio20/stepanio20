# DiamondScanBot — the Dubai diamond radar

A Telegram bot that turns the informal WhatsApp/Telegram "have / looking-for" chatter
of Dubai diamond dealers into a structured, matchable feed — then pings buyers and
sellers the moment a stone meets a request. Built on the [market study](../research/diamond-b2b/)
and mirroring the proven **Dubai Deals** scheme (intake → verify/enrich → publish deal
cards to a channel), adapted from real estate to diamonds.

**Live bot:** [t.me/DiamondScanBot](https://t.me/DiamondScanBot) · focus market: **Dubai** · natural diamonds only (see the [Gold analysis](../research/diamond-b2b/gold-vs-diamond.md) for why we skip gold for now).

---

## What it does

1. **Feed the radar (opt-in only).** Dealers *forward* messages from their groups, *paste* a
   stone/request, or *upload* a CSV stock file (RapNet-style headers).
2. **Structure it.** `parser.py` extracts a canonical record — shape · carat · color/fancy ·
   clarity · cut · lab · cert · fluorescence · $/ct · Rap% — and classifies **have vs want**.
3. **Match & alert.** `matcher.py` scores each demand against live listings (fuzzy on the 4Cs
   with tolerances + a price ceiling); both sides get pinged on a match.
4. **Connect behind a subscription.** Subscribers reveal the counterparty and close the deal
   their way (memo or wire). We never touch goods or money — a pure introduction service.
5. **Publish deal cards.** Verified stones can be posted to a channel as a FOMO infographic
   (`dealcard.py`) — the visual "new deals on the market" feed, with buyer/seller contact.

## Why this shape (from the research)

- **Deals close in chat**, but structured platforms (RapNet, Nivoda, VDB) only see uploaded
  feeds — the messenger layer is unoccupied. That gap is the product.
- **Telegram-first, opt-in ingestion.** No covert WhatsApp scraping: it's a ToS/ban/legal
  non-starter (reverse clients live 2–8 weeks; group content is non-public → ToS + CFAA
  exposure; GDPR/UAE PDPL/India DPDP/Israel Amendment 13). The only defensible paths are
  (a) forwards, (b) the dealer's own CSV, (c) **BYO-session** read-only reading of groups a
  consenting subscriber *already* belongs to (`ingest.TelethonIngestor`).

## Architecture

| Module | Responsibility |
|---|---|
| `config.py` | Env-based settings (loads gitignored `.env`), subscription tiers |
| `parser.py` | Free-text → `ParsedStone` (regex core, optional LLM hook). **11/11 tests** vs real group messages |
| `matcher.py` | Demand↔listing scoring (0–1) with 4C tolerances + price ceiling |
| `db.py` | SQLite persistence (users, subscriptions, listings, demands, matches, groups, events) |
| `ingest.py` | forward / CSV import / BYO-session Telegram reader |
| `enrich.py` | GIA Report Results API cert verification + cross-check vs text (anti-cert-swap) |
| `dealcard.py` | Channel caption (FOMO) + PNG **deal-card** and buyer↔seller **match-card** infographics (Pillow) |
| `payments.py` | **veym** gateway subscriptions (MamoPay-backed, AED) + `/mamopay-webhook` |
| `bot.py` | aiogram 3 handlers, menus, callbacks, payment webhook, admin `/status` `/publish` |
| `branding/` | Avatar, promo banner/square, sample deal card (generator: `make_branding.py`) |

## Run it

```bash
cd diamond-bot
cp env.example .env           # put your TELEGRAM_BOT_TOKEN in .env (gitignored)
pip install -r requirements.txt
python bot.py                 # long-polling
python -m pytest -q           # or: python tests/test_parser.py
```

Docker: `docker build -t diamondscan . && docker run --env-file .env diamondscan`

**Deploy 24/7:** see [`DEPLOY.md`](./DEPLOY.md) (Railway — one process runs both long-polling
and the payment webhook, binding `$PORT`).

> **Note (this repo's sandbox only):** outbound HTTPS is proxied with a self-signed CA. `bot.py`
> auto-detects `HTTPS_PROXY` + the proxy CA and routes through them **only when present**, so it
> runs here *and* unchanged on a normal host. Verified live: `getMe`, `set_my_commands`, polling,
> and the `/health` + `/mamopay-webhook` server.

## Monetization

Subscriptions via the **veym** gateway (MamoPay-backed, **AED**) — the same gateway as the Dubai
Unit Bot. Charge is created on MamoPay (hosted checkout → pay link); veym relays the result to
`/mamopay-webhook`, which activates the plan.

Priced by stock size (sellers pay to list more; buyers search free) — the LuxeDiam model:

| Tier | Stock cap | AED / 30d | ≈ USD |
|---|---|---|---|
| **Free** | up to 500 stones | — | — |
| **Grow** | up to 1,000 stones | AED 99 | ~$25/mo |
| **Pro** | unlimited | AED 199 | ~$50/mo |

Every plan includes auto-matching and instant alerts. Uploads/forwards/CSV are capped to the
tier's stock limit (over-cap rows are skipped with an upgrade prompt). Adjust prices in `config.py`.

## Deal mechanics the service accounts for (and what it deliberately skips)

Baked into the product design from the market study:

- **Memo / consignment** — goods go out on memo 30–90 days, title stays with the consignor;
  the bot facilitates *introductions and deal confirmations*, it does not force a checkout.
- **Payment** — wire vs invoice, 60–120+ day credit is normal; the bot stays payment-agnostic.
- **Brokerage 1–2%** — monetize like a broker (subscription/intro), not a retail markup.
- **"Mazal u'bracha"** — deals close verbally and bilaterally; we record confirmations, not orders.

**Trust & fraud (the core asset):**
- **Vetting** at RapNet level — ID + business licence + trade references + **OFAC/sanctions
  screen** → the ✅ *Verified dealer* badge (`db.set_vetting`, surfaced on cards).
- **Cert verification** — GIA Report Results API + text↔cert cross-check to blunt cert-swap /
  fake-inscription fraud (`enrich.cross_check`).
- **Scam filter** — obvious advance-fee/impersonation patterns are dropped at ingest
  (`parser` flags), logged as `scam_filtered` events.
- **Sanctions metadata** — origin / G7·KP / ≥0.5ct self-cert fields carried on the stone record.
- **Shared KYC** — designed to plug into MyKYCBank (GJEPC; used by BDB, AWDC, DMCC/DDE).

**Handed to partners / out of scope:** logistics (Malca-Amit/Brink's/Ferrari — quote per
shipment, fully insured), escrow (0.5–5%), and financing. As a pure introduction service that
never touches goods or funds, it largely sits outside the US dealer AML definition (31 CFR 1027);
handling payments would pull it in.

## Operator setup checklist (do these in Telegram)

- [ ] **Avatar:** set `branding/avatar.png` via **@BotFather → /setuserpic** (can't be set via API).
- [ ] **Group reading:** to let the bot read all messages in groups where an admin adds it,
      **@BotFather → /setprivacy → Disable** (bot currently has privacy ON).
- [ ] **Channel:** create the deals channel, add the bot as admin, put its id in `TELEGRAM_CHANNEL_ID`.
- [ ] **Admins:** put your Telegram user id in `ADMIN_USER_IDS` for `/status` and `/publish`.
- [ ] **Rotate the token** (it was shared in chat): @BotFather → /revoke, then update `.env`.

## Seeded target groups (Dubai-relevant, open Telegram)

`@demandsnatural` (demand) · `@diamondsexport` (supply) · `@certifieddiamonds` (supply) ·
`@diamonds_jewels_antwerp` (supply). Used as a free labeled seed corpus; the have/want split is
already enforced by group rules.
