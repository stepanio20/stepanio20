# Concierge — Weekly Plan PWA (M4 shell)

A zero-dependency, single-page web app that loads a weekly plan (Markdown
produced by the Concierge engine) and renders it as cards with approve / skip
toggles + a sticky bottom bar tallying approved actions and est. cost.

## What this is *not*

Not a real auto-booker yet. The Approve button in this shell **mocks** the
action layer — it doesn't call Whoop / Calendar / Uber / Mindbody / labs.
Wiring those connectors is M2 + M5 + M6 of [`../../PRODUCT_ARCHITECTURE.md`](../../PRODUCT_ARCHITECTURE.md).
The UI is the deliverable here: prove the 2–3 minute weekly experience feels right.

## Run locally (no install)

```bash
cd concierge/app
python3 -m http.server 8000
# open http://localhost:8000 — works on phone via your laptop's LAN IP
```

The page fetches `sample_plan.md` (committed, synthetic profile — no PHI).
For your real plan, generate it locally and drop it next to the HTML:

```bash
python3 -m concierge.make_weekly_plan --user me --out concierge/app/plan.md
# then edit main.js: change PLAN_URL = "plan.md"
```

`plan.md` is gitignored under `users/*/reports/*.md`, but the renamed copy in
`concierge/app/` is **not** automatically gitignored — be careful. Recommended:
serve your real plan from a private host, never commit it.

## Deploy

The app is fully static — three files (`index.html`, `style.css`, `main.js`) +
`sample_plan.md` + `manifest.webmanifest` + `icon.svg`. Deploy on whichever
static host you already have an account on:

### Vercel (one command on your machine)

```bash
cd concierge/app
npx vercel deploy --prod    # first time prompts you to login + link a project
```

`vercel.json` is configured. Subsequent deploys are one command.

### Netlify

```bash
cd concierge/app
npx netlify deploy --prod --dir .
```

### Surge.sh (simplest, anonymous)

```bash
cd concierge/app
npx surge . your-name.surge.sh
```

### Cloudflare Pages

Drag-and-drop the folder at <https://dash.cloudflare.com/?to=/:account/pages>.

## PWA install

`manifest.webmanifest` + the apple-touch-icon tag make the app installable
once it's served over HTTPS. On iOS: Safari → Share → Add to Home Screen.
No service worker yet (the app is small enough that offline-first isn't
needed for the MVP; can be added later if it earns its complexity).

## File map

| File | What |
|---|---|
| `index.html` | Skeleton + manifest link |
| `style.css` | Dark/light theme, mobile-first, sticky header + footer |
| `main.js` | Markdown → card model parser + render + state |
| `sample_plan.md` | Committed sample plan (synthetic profile) |
| `manifest.webmanifest` | PWA install metadata |
| `icon.svg` | App icon |
| `vercel.json` | Headers + clean URLs |

## Why static, not Next.js

For the MVP: every minute saved on toolchain is a minute spent on the actual
UX. Three files load on a phone in ~50 ms over LTE, install as a PWA, and
parse 6 KB of Markdown deterministically. Switch to Next.js / React only when
auth + per-user persistence + connector calls land — those genuinely need a
framework.
