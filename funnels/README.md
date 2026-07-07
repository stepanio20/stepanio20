# Indaga — mobile sales funnels (5 A/B variants)

Quiz-style onboarding funnels (Noom / Cal-AI pattern), mobile-first, for **Instagram
traffic**. Target audience: **people who already have a 23andMe or MyHeritage DNA test.**

One shared engine (`shared/quiz.js` + `quiz.css`) drives all five; each variant is a
thin `index.html` that only defines copy, quiz questions, and accent color — so A/B
testing message *and* look is trivial.

| Link | Variant | Angle |
|---|---|---|
| `/1` | `v1-unlock` | "Unlock the DNA you already have" (the wedge) |
| `/2` | `v2-bioage` | "What's your biological age?" (longevity) |
| `/3` | `v3-symptoms` | "Your DNA explains your symptoms" (problem-first) |
| `/4` | `v4-multiomic` | "DNA + bloods, one honest picture" (trust) |
| `/5` | `v5-curiosity` | "12 fun things your DNA says" (viral) |

Flow each variant runs: **hero → 5 quiz questions → analyzing → personalized result teaser (blurred/locked) → email capture → offer/paywall + "upload your 23andMe file"**.

## Deploy to Vercel (2 minutes, gives you the 5 live links)

**This must be run by you** — the build environment can't reach Vercel's login.

**Option A — from GitHub (recommended, auto-redeploys on every push):**
1. vercel.com → **Add New → Project** → import `stepanio20/stepanio20`.
2. **Root Directory** → set to `funnels`.
3. Framework preset: **Other** (it's static). Deploy.
4. You get `https://<project>.vercel.app` — the 5 links are:
   - `https://<project>.vercel.app/1` … `/5`

**Option B — one command from your laptop:**
```bash
cd funnels
npx vercel deploy --prod      # first run: log in + link a project
```

Custom domain (recommended for Instagram): add e.g. `go.indaga.ai` in Vercel →
your links become `go.indaga.ai/1` … `/5`.

## Before driving traffic — 2 things to wire

1. **Analytics** (this is your investor data). In each variant's `<script>`, set:
   ```js
   window.ANALYTICS = { provider: 'posthog', key: 'phc_xxx' };  // or plausible / ga / custom
   ```
   Events fired automatically: `funnel_view · quiz_start · quiz_step · quiz_complete ·
   result_cta · lead · offer_view · checkout_start · upload_click`. That's the full
   funnel — conversion at every step, per variant.

2. **Checkout + upload** are demo stubs (they `alert()` and fire the event). Wire:
   - **Web:** Stripe Checkout on `checkout_start`.
   - **Real product:** the DNA-file upload → the indaga pipeline.

## Instagram setup
- Put `go.indaga.ai/1` … `/5` in 5 different ad creatives / link-in-bio slots.
- Because each variant tags every event with its `variant`, one analytics dashboard
  shows which angle converts best. Kill the losers, scale the winner.

## Files
```
funnels/
  index.html            # internal hub — preview all 5 (/1../5)
  vercel.json           # clean /1../5 rewrites + headers
  shared/quiz.css       # design system + quiz UI
  shared/quiz.js        # the funnel engine (data-driven)
  shared/analytics.js   # event layer (PostHog/Plausible/GA/custom)
  v1-unlock/ … v5-curiosity/   # the 5 variants (config only)
```

> Copy is written to convert, but every claim maps to something the real report can
> back up. Keep the "information, not medical advice" + "DNA never sold" lines — they're
> both trust drivers and regulatory cover.
