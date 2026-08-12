# Diamond B2B Market — Research & Product Proposal

Market research and a product proposal for a subscription service that parses
diamond dealers' Telegram/WhatsApp trading groups, structures "have/looking-for"
messages, and auto-matches buyers with sellers — instead of dealers scrolling
group history by hand.

## Files

| File | What it is |
|---|---|
| `diamond-market-report.pdf` | **The deliverable** — 18-page report (Russian): market structure, chat-trading mechanics, competitor & pricing landscape, API/open-data inventory, technical & legal feasibility, and a concrete build plan with monetization, roadmap, and risks. |
| `report.html` | Source of the PDF (styled, print-ready HTML). Regenerate the PDF with the command below. |

## Key conclusions (TL;DR)

- **The pain is real and unserved.** Deals close in WhatsApp/Telegram; no product
  today parses those dealer chats into a structured, matchable feed.
- **Fact-checks of the original chat claims:** "Amsterdam holds 90% of supply" →
  myth (that's De Beers, London→Botswana, ~26–30% today); "RapNet is Indian" →
  myth (US company); "sub ~$150" → that's RapNet Dealer membership, not the
  price list ($21–29/mo); "an app with 18k users sold" → not found in trade press
  (nearest is Get-Diamonds, sold to WFDB for a symbolic $5,000).
- **Build recommendation:** a Telegram-bot "radar" on a bring-your-own-session +
  opt-in-feed model, **Telegram-first**. Covert WhatsApp scraping is a
  ToS/ban/legal non-starter and must not be the MVP shortcut.
- **Monetization:** broker/seller side $100–250/mo (highest willingness to pay),
  buyer side $25–75/mo; optionally a Nivoda-style $0 + transaction fee.
- **Honest caveat:** a fast, high-value marketplace exit has no precedent here —
  treat this as a profitable niche SaaS (or a module under a future
  payments/logistics platform), not a venture rocket on its own.

## Regenerate the PDF

```bash
chromium --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=diamond-market-report.pdf \
  "file://$PWD/report.html"
```

## Method

13 parallel research agents (8 dimensions + a completeness critic + 4 gap-fill
agents), ~600 primary-source lookups, prioritizing 2024–2026 data. Numbers were
cross-checked across at least two outlets where possible. Source links are listed
at the end of the report.
