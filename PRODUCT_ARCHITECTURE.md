# PRODUCT_ARCHITECTURE.md — the "Concierge" layer

> **One line:** take the existing Knowledge Engine (DNA → bloods → wearable → report,
> see [`ARCHITECTURE.md`](./ARCHITECTURE.md)) and wrap it in a closed-loop personal
> health concierge that **plans your week** (food, training, recovery, therapies,
> screening) and **books/orders it for you** after a single weekly review-and-approve.

This is the productisation of the candidate already named in `ARCHITECTURE.md` §13:
*"Daily-advice agent that fuses genetics + wearable + blood + CGM + lifestyle over time —
the long-term goal"* and *"Tighter UX layer: web frontend."* This document is the design
for it. Status: **proposal / design doc** — no app code yet.

---

## 0. Relationship to `ARCHITECTURE.md`

| | `ARCHITECTURE.md` (exists) | `PRODUCT_ARCHITECTURE.md` (this doc) |
|---|---|---|
| Scope | **Knowledge Engine** — raw data → structured facts → PDF reports | **Concierge** — facts → weekly plan → orders/bookings/calendar |
| Mode | Batch pipeline, run from the CLI / interactively in Claude Code | Always-on service + app, with a weekly human-in-the-loop step |
| Output | ~25 PDFs + 14 domain JSON bundles + `healthlake/gold` facts | A confirmed weekly schedule pushed to Google Calendar + placed orders |
| Reuses | — | **All of it.** The pipeline *is* the brain. This layer is hands + calendar. |

The pipeline already produces the two things a concierge needs: (1) a **canonical
fact store** (`healthlake/gold`, the domain bundles) and (2) an **action plan**
(`ACTIONABLE_HEALTH_PROTOCOL.md`, `MEAL_PLAN.md`, `data_inventory.md`). The Concierge
turns those from documents into **scheduled, executed actions**.

---

## 1. What we're building (one paragraph)

A personal app where you connect your data once (Whoop, Apple Health, blood-test PDFs,
your 23andMe/Ancestry raw DNA file) and from then on, **every Monday it hands you a
ready-made week**: what to eat (with the food orderable in one tap), which recovery /
sauna / massage / therapy sessions to book, which lab tests are now due and where to
book them in Barcelona, and a supplement + training plan — all derived from your own
genetics + labs + wearable trends. You **review, edit, approve, and pay once**; it then
places the orders it can, hands off the ones it can't to the native app, and writes the
whole week into your Google Calendar.

### The two reference products, mapped to what we already have

| Reference | What it does well | Our equivalent | Status |
|---|---|---|---|
| **ITR / eatr.com** | Surfaces "all the pathological facts" — a dense, honest read of your biology | The Knowledge Engine's `v1_integrated` / domain reports — arguably *deeper* (adds DNA + PGS + PharmCAT, not just bloods) | **already strong** |
| **Ornament Health** | Tells you *which tests to take next* and *what data is missing* | The `data_inventory.md` phase (6g) — already answers "what data do you have and what does each unlock"; we extend it to "what to measure next and why" | **bones exist** |

So the analytical half is largely **built**. The new build is the **Concierge**:
funnel → recommendation → orchestration → action → calendar, plus the connectors.
Per your instinct, the missing-data nudge (Ornament-style) must be **informative, never
blocking** — the weekly plan ships with whatever data exists today and simply flags what
would sharpen it next.

---

## 2. The mental model — the weekly loop

```
   ┌────────────────────────────────────────────────────────────────────────┐
   │                          THE WEEKLY LOOP                                │
   └────────────────────────────────────────────────────────────────────────┘

   (one-time + ongoing)            (continuous)                (every Monday 07:00)
   ┌──────────────┐   ingest   ┌──────────────────┐  plan   ┌────────────────────┐
   │  CONNECT     │──────────▶ │  KNOWLEDGE ENGINE │───────▶ │  WEEKLY PLAN        │
   │  • Whoop     │            │  (the pipeline)   │         │  • meals            │
   │  • Apple HK  │            │  facts + report   │         │  • training/recovery│
   │  • bloods    │            │  + data gaps      │         │  • therapies        │
   │  • DNA file  │            └──────────────────┘         │  • tests due        │
   │  • prefs     │                     ▲                    │  • supplements      │
   └──────────────┘                     │ learn              └─────────┬──────────┘
                                        │                              │ review
                                        │                              ▼
   ┌──────────────┐   act    ┌──────────────────┐  approve  ┌────────────────────┐
   │  CALENDAR    │ ◀────────│  ACTION LAYER     │◀──────────│  YOU: edit + pay    │
   │  + orders    │          │  order / book /   │           │  (the only required │
   │  placed      │          │  hand-off         │           │   human step)       │
   └──────────────┘          └──────────────────┘           └────────────────────┘
```

The loop has exactly **one mandatory human step** — your weekly review-and-approve.
Everything before it is automated analysis; everything after it is automated execution.
This is not a limitation to engineer away — for anything that **spends money** or is
**medical**, the confirm step is the correct design (legally and for trust). You already
described it perfectly: *"конфермлю, чуть правлю, оплачиваю всю неделю."*

---

## 3. System architecture — two halves + the health graph

```
                         ┌─────────────────────────────────────────┐
   CONNECTORS            │             HEALTH GRAPH                 │
   ┌─────────┐ webhook   │   canonical, typed, time-stamped facts   │
   │ Whoop   │──────────▶│   (extends healthlake/gold + bundles)    │
   ├─────────┤           │                                          │
   │ Apple HK│──upload──▶│   • genomics (variants, PGS, PGx)        │
   ├─────────┤           │   • bloods (analyte time series)         │
   │ Bloods  │──OCR─────▶│   • wearable (sleep, HRV, recovery,      │
   ├─────────┤           │     strain, VO2max, glucose)             │
   │ DNA file│──pipeline▶│   • profile + lifestyle + preferences    │
   └─────────┘           │   • derived risk tiers + targets         │
                         └───────────────┬──────────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
   ┌────────────────────┐   ┌────────────────────────┐   ┌────────────────────┐
   │ KNOWLEDGE ENGINE   │   │ RECOMMENDATION ENGINE  │   │ DATA-GAP ENGINE    │
   │ (Phases 1–8)       │   │ facts → weekly targets │   │ (Ornament-style)   │
   │ report + facts     │   │ macros, training,      │   │ "measure X next,   │
   │                    │   │ recovery, supps,       │   │  here's why"       │
   │                    │   │ therapies, screening   │   │ NON-BLOCKING       │
   └────────────────────┘   └───────────┬────────────┘   └────────────────────┘
                                         ▼
                            ┌────────────────────────┐
                            │ ORCHESTRATION ENGINE   │
                            │ targets → concrete      │
                            │ week: meals, sessions,  │
                            │ bookings, calendar slots│
                            └───────────┬────────────┘
                                        ▼
                            ┌────────────────────────┐
                            │ ACTION LAYER           │
                            │ connectors that EXECUTE │
                            │ (order/book/calendar)   │
                            └────────────────────────┘
```

The **Health Graph** is the contract between the two halves. It is the existing
`healthlake/gold` canonical-observation store (already in the roadmap as "the foundation
the daily-advice agent needs"), extended with: wearable streams, preferences, and the
derived *targets* the recommendation engine writes back. Everything downstream reads
only from the graph — so the report, the plan, and the data-gap nudges can never
disagree (the same traceability guarantee `verify_all.sh` already enforces).

---

## 4. The onboarding funnel (progressive, non-blocking)

The funnel doubles as the selling funnel and the data-ingestion flow. **Each step
produces value immediately** so the user is never stuck behind a missing input — this is
the Ornament principle applied to onboarding: show what's possible *now*, flag what would
unlock *more*.

| Step | Asks for | Time | Unlocks immediately | Drop-off guard |
|---|---|---|---|---|
| 1. Basics | age, sex, height, weight, city, goals | 2 min | BMI/composition framing, generic-but-personalised targets, a sample week | Instant "here's your first plan" — the hook |
| 2. Connect Whoop | OAuth (1 tap) | 30 s | sleep/recovery/strain-aware scheduling | optional, skippable |
| 3. Upload bloods | PDF / photo | 1 min | the *real* "pathological facts" report (ITR-grade) | OCR auto-extracts; no manual typing |
| 4. Upload DNA | 23andMe/Ancestry raw `.txt`/`.zip` | 1 min | PGx (drug response), PGS percentiles, P/LP screen | runs in background; week ships without it |
| 5. Preferences | diet, allergies, budget, neighbourhood, no-go foods, schedule | 3 min | orderable meals + bookable sessions near you | pre-filled smart defaults |
| 6. Connect Calendar + payment | Google OAuth + Stripe card | 1 min | the loop closes — plans become bookings | only needed before first *approve* |

**Non-blocking rule (the core UX principle):** the weekly plan renders with whatever is
present. Each plan card carries a small "confidence + what would sharpen this" footnote —
e.g. *"This sleep target uses your Whoop trend. Add a recent ferritin/vitamin-D panel to
personalise the supplement stack."* That single pattern is our Ornament-equivalent, and
it lives inline in the plan instead of gating it.

---

## 5. Data connectors — feasibility matrix (verified June 2026)

The honest core. Sources at the bottom (§15).

| Source | What we want | Official API? | Verdict |
|---|---|---|---|
| **Whoop** | sleep, recovery, HRV, strain, workouts, body | **Yes** — v2 REST, OAuth2 (`read:recovery/sleep/workout/cycles/profile/body_measurement`), real-time **webhooks** | ✅ **clean** — build first |
| **Apple Health** | sleep stages, HR/HRV, VO2max, steps, ECG, CGM | No cloud API; data via `export.xml` (pipeline already parses) or a **companion iOS app** using HealthKit | ✅ via export today; 🟡 companion app for live sync |
| **Oura / Garmin** | same class of recovery data | Oura API v2 (OAuth2) ✅; Garmin Health API gated (partnership) 🟡 | ✅/🟡 optional alternatives to Whoop |
| **Blood tests** | analyte values + ranges | No universal API | ✅ ingest by PDF/photo → OCR + LLM extraction (pipeline Phase 5 already does this) |
| **DNA (23andMe / Ancestry / MyHeritage)** | raw genotypes | **No** — 23andMe killed its 3rd-party API in 2018; others never had one | ✅ but **upload-only**: user downloads their raw file, we run the pipeline. No live sync, by design of the vendors. |
| **Google Calendar** | write the weekly schedule | **Yes** — full read/write REST, OAuth2 | ✅ **clean** |

### Actuation connectors (the "do it for me" half — harder, be honest)

| Action | Target | Reality | Verdict |
|---|---|---|---|
| **Order prepared food** | Uber Eats | Uber **Consumer Delivery API** can browse/cart/order on a user's behalf — but is **partner-gated** (NDA + API licensing agreement + Uber partner-manager approval) | 🟡 **possible, not self-serve.** MVP: deep-link a pre-built cart; user taps "order" in the Uber app |
| | Glovo | Only a **merchant/courier** Partner API (receive orders into a POS, request couriers). **No consumer-ordering API.** | ❌ no clean path; deep-link / hand-off only |
| **Order groceries** | Mercadona / Carrefour ES / Amazon Fresh | No public consumer-ordering APIs (Amazon has none for Fresh either) | ❌ → generate a **shopping list** (pipeline already does `SHOPPING_LIST.md`) + deep-link |
| **Book sauna/massage/therapy** | studios (e.g. ilo-studios) | Depends entirely on the studio's booking backend. **Mindbody** has an **Affiliate API** to *find, book, and pay* (guest checkout / repeat booking); Fresha, Vagaro, WellnessLiving have partner programs. Bespoke booking pages = no API. | 🟡 **feasible iff the studio runs on a supported platform**; else deep-link + hand-off |
| **Book lab tests** | Barcelona labs (Synlab, Cerba, Echevarne), CatSalut, at-home phlebotomy | Generally portal-based, no public API. At-home draw services sometimes integrable via partnership. | 🟡 generate the **test order + map of where to book** + deep-link; human books. Partner integration later. |
| **Pay** | Uber, labs, studios | We cannot auto-charge *their* systems. We charge **our** subscription via **Stripe**; third-party spend is paid by the user in-app at confirm | ✅ for our charges; 🟡 third-party = 1-tap-in-native-app |

### The design consequence

There is **no universe** where a third party silently spends your money across Uber +
labs + studios with zero confirmation — and you wouldn't want one. So the architecture
is deliberately **"prepare everything, then one approve."** For each action the layer
picks the best available rung:

```
   Rung 1  Full API booking/order + pay        (Whoop connect, Calendar write, Mindbody-Affiliate book, Uber if approved)
   Rung 2  Pre-built deep link / pre-filled cart → user taps confirm in native app   (Uber MVP, grocery, bespoke studios)
   Rung 3  Generated instruction + "Book" button that opens the right page            (CatSalut tests, walk-in labs)
```

The weekly plan tags every card with its rung, so you always know what will happen on
"Approve" vs what needs one more tap.

---

## 6. Knowledge Engine + the Data-Gap / Test-Recommendation module

**Reuse, don't rebuild.** The Concierge calls the existing pipeline:

- DNA upload → Phases 1–4 (normalize → annotate → PharmCAT → P/LP screen), optional
  TOPMed/Beagle imputation (`ARCHITECTURE.md` §4–5).
- Blood PDF → Phase 5 extraction into the analyte time series.
- Whoop/Apple → the wearable parser (generalised from `parse_apple_health.py` to also
  ingest Whoop JSON) → Phase 6h/6i insights.
- Phase 6 bundling → 14 domain JSONs → Phase 7 multi-agent synthesis → the report.

**New, small module — the Ornament-equivalent.** Extend `06g_data_inventory.py` from
*"what you have"* into *"what to measure next."* It already knows, per finding, which
data layer unlocks it. We add a **gap → test mapping**:

```
for each high-value conclusion the user CAN'T yet reach:
    find the cheapest data that would unlock it
    → emit { test, why_it_matters, what_it_unlocks, where_to_book (Barcelona), est_cost }
rank by (clinical value × inverse cost) ; show top N inline, non-blocking
```

Example output: *"You have no ApoB or Lp(a). One €30 add-on to your next lipid panel
would replace the LDL estimate with the metric that actually drives long-term risk, and
Lp(a) is a once-in-a-lifetime test. Book at Synlab (5 min from you)."* This is exactly
the ITR/Ornament value, generated from the user's own gaps.

---

## 7. The Recommendation Engine — facts → weekly targets

Pure function: reads the Health Graph, writes a `weekly_targets` object. No I/O, no LLM
required for the deterministic parts (keeps it cheap, testable, auditable). The LLM
(Phase 7 style, via the **Anthropic API** for the productised version — see `claude-api`
skill) is used only for the *narrative* and *meal/therapy selection*, never for the
safety-critical numbers.

| Target group | Driven by | Example |
|---|---|---|
| Energy + macros | profile, goal, BMR (Katch-McArdle from lean mass), wearable strain | "TDEE ≈ 2150 kcal maintenance; protein 1.8 g/kg = 120 g/day" |
| Micros / supplements | bloods (vit D, B12, ferritin, folate), PGx (MTHFR, etc.) | "D3 2000 IU/day until next panel; B12 via diet" |
| Training | recovery/HRV trend, VO2max, goal | "3× resistance, 1× Zone-2 45 min; deload if recovery < 34% two days" |
| Recovery / therapy | sleep debt, HRV, strain, stress | "2× sauna, 1× massage this week; lights-down 22:30 on low-recovery days" |
| Screening | age, family history, last-test dates, data gaps | "Lipid panel + ApoB due (14 mo since last); confirm home BP × 7 days" |

All targets carry provenance (`source: whoop|bloods|dna|profile`) so the plan can show
*why*, and the data-gap engine can say *what would refine it*.

---

## 8. The Orchestration Engine — targets → a concrete week

Turns abstract targets into dated, bookable items, subject to your real-world
constraints (calendar free/busy, budget, neighbourhood, preferences, opening hours).

```
INPUTS:  weekly_targets + preferences + Google Calendar free/busy + connector availability
SOLVE:   constraint-satisfaction over the week
         • meals that hit macro/micro targets, within diet/allergy/budget, orderable nearby
         • sessions placed on low-strain days, near home, within opening hours
         • test bookings batched (one fasting morning), before they go overdue
OUTPUT:  a Weekly Plan = ordered list of cards, each with {what, when, where, rung, cost, why}
```

This is a scheduling/optimisation problem, not an AI problem — start with a simple
greedy/heuristic solver (good enough), upgrade to a proper constraint solver later. The
LLM picks *which* meals/therapies feel good and writes the human-readable rationale; the
solver guarantees the numbers and the calendar fit.

---

## 9. The Action layer — actuation + human-in-the-loop confirm

On **Approve**, the layer walks the plan and executes each card at its highest available
rung (§5). Critical safety properties:

- **Idempotent + reversible where possible** — every booking/order gets a local record;
  re-running never double-books; cancellations are tracked.
- **Dry-run first** — "here's exactly what I'll order/book and the total €X" before any
  money moves. Nothing is charged or booked before explicit approve.
- **Per-card opt-out** — you can approve the week but skip the massage; partial approve is
  first-class.
- **Hand-off is honest** — Rung-2/3 cards open the native app with everything pre-filled;
  the plan marks them "needs your tap" so nothing silently fails.
- **Calendar last** — only confirmed actions are written to Google Calendar, so the
  calendar is the source of truth for "what's actually happening."

---

## 10. The "Monday morning" UX (the experience you described)

```
07:00  Push: "Your week is ready."
       → Open app. One screen: 7 days, each with meals / sessions / tests / supps.
       → Top banner: "This week: 2150 kcal/day · 2 sauna · 1 massage · lipid panel due · €148 total"

       You swipe through:
         • swap Tuesday lunch (1 tap, macros re-balance live)
         • move the massage to Thursday (calendar re-checks free/busy)
         • skip the grocery order (you'll cook)
         • keep the lab booking

       Bottom: "Approve & pay €121"  →  one tap.

07:01  • Stripe charges our €X subscription portion
       • Mindbody-backed sauna + massage booked & paid (Rung 1)
       • Uber cart pre-built → "tap to order" hand-off for the two delivery days (Rung 2)
       • Lab: order sheet generated + "Book at Synlab" deep link (Rung 3)
       • All confirmed items written to Google Calendar
       • Whoop keeps streaming → next Monday the plan adapts to how the week actually went
```

That is the whole product in one screen. Everything else is plumbing to make that screen
trustworthy.

---

## 11. Tech stack — personal MVP vs productised

| Layer | Personal MVP (just you, fastest) | Productised (sellable funnel) |
|---|---|---|
| Knowledge Engine | the existing Python pipeline, unchanged | same, containerised + queued |
| Orchestration/Recommendation | Python module in `concierge/` | same, as a service |
| LLM synthesis | Claude Code subagents (no API key, your subscription) | **Anthropic API** with prompt caching (`claude-api` skill) |
| Store | the repo + `healthlake/gold` JSON | Postgres + object storage (encrypted) |
| App | a single **Next.js** PWA (works on your phone, no App Store) | Next.js + a thin iOS companion for HealthKit |
| Auth/connectors | OAuth tokens in a local `.env` (gitignored) | proper secrets manager + per-user token vault |
| Payments | — (you pay third parties yourself at first) | Stripe (subscription) + per-action hand-off |
| Calendar | Google Calendar API | same |

**Recommended MVP:** keep the pipeline as-is, add a `concierge/` Python package
(recommendation + orchestration + connectors), and a small **Next.js PWA** for the
weekly-plan screen. Whoop + Google Calendar are the only two live connectors needed to
make the loop feel real; everything else can start at Rung 2/3 (deep links). This gets
you the Monday-morning experience for *yourself* without App Store review, partner
approvals, or handling other people's health data.

---

## 12. Privacy, security, GDPR & medical-device honesty

Non-negotiable, especially in the EU and **doubly** for genetic + health data.

- **Special-category data (GDPR Art. 9).** Genetic and health data are the most
  protected class. For personal/single-user use this is low-risk, but the moment it's a
  *product for other people* you need: explicit consent, a lawful basis, a DPIA, data
  minimisation, encryption at rest + in transit, EU data residency, and a deletion path.
- **The medical-device line.** ITR and Ornament survive by positioning as **wellness /
  information**, not diagnosis or treatment. The instant the app *recommends or books a
  medical test*, or phrases output as diagnosis, it risks falling under **EU MDR** as
  Software-as-a-Medical-Device. Keep recommendations framed as information + "discuss
  with your clinician," and keep the test-booking module as *"here's what's worth asking
  for"* rather than *"you have condition X."* The existing pipeline's discipline
  (no diagnostic language, heavy caveats, the adversarial-reviewer pass) is exactly the
  right instinct — carry it into the app copy.
- **Money + medical = always confirm.** Already the design (§9). This is also what keeps
  you out of "the app booked/charged something I didn't want" liability.
- **Local-first for the personal build.** Tokens in a gitignored `.env`; the Health Graph
  stays on your machine; only the Next.js PWA reads it locally. Nothing personal leaves
  your control until you choose to productise.

---

## 13. Build roadmap — what's feasible now

| Phase | Deliverable | Connectors | Effort | Feasible today? |
|---|---|---|---|---|
| **M0** | `concierge/` package + `concierge.json` config (this PR scaffolds it) | none | S | ✅ |
| **M1** | Recommendation engine: Health Graph → `weekly_targets` (deterministic) | reads existing bundles | M | ✅ |
| **M2** | Whoop connector (OAuth + webhook) → wearable facts into the graph | Whoop ✅ | M | ✅ |
| **M3** | Orchestration engine + a static weekly-plan **Markdown/PDF** (reuse Phase 8) | none | M | ✅ |
| **M4** | Next.js PWA weekly-plan screen (review/edit/approve) | — | M | ✅ |
| **M5** | Google Calendar write on approve | Calendar ✅ | S | ✅ |
| **M6** | Action layer Rung-2/3: deep links for Uber/grocery/labs/studios | deep links only | M | ✅ |
| **M7** | Data-gap → Barcelona test-recommendation module | extends 6g | S | ✅ |
| **V1** | Mindbody-Affiliate booking+pay for studios that support it | Mindbody 🟡 | M | 🟡 if studio qualifies |
| **V2** | Uber Consumer Delivery API (real auto-order) | Uber 🟡 | L | 🟡 needs partner approval |
| **V2** | Stripe subscription + multi-user + GDPR hardening (sellable funnel) | Stripe | L | 🟡 product decision |

**The honest MVP line:** M0–M7 are all buildable now, for you, with only **Whoop +
Google Calendar** as live APIs and everything else as one-tap hand-offs. That already
delivers the Monday-morning experience. Real auto-ordering (Uber) and selling it to
others (multi-user + GDPR + Stripe) are explicitly **V2** because they depend on partner
approvals and regulatory work, not on us.

---

## 14. Honest reality check — what *won't* work cleanly

- **"Fully automatic, zero taps" food ordering** is not available today without Uber
  partner approval, and Glovo offers no consumer API at all. The truthful MVP is
  "one-tap-confirm in the native app." Don't promise more.
- **Live DNA sync** doesn't exist — every consumer DNA vendor is upload-only. Fine: DNA
  is static, you upload once.
- **Generic lab-booking API for Barcelona** doesn't exist; it's portal-by-portal. We
  generate the order + the right link; the human books until a lab partnership exists.
- **Auto-paying third parties** from our backend is neither possible nor desirable. We
  charge our own subscription via Stripe; their spend is confirmed in their app.
- **Selling it** flips on the full GDPR Art. 9 + EU-MDR burden. Building it *for you*
  avoids essentially all of that. Strongly recommend: **personal MVP first, productise
  only once the loop proves valuable to you.**

---

## 15. Connector reference (verified June 2026)

- WHOOP for Developers — API v2, OAuth scopes, webhooks: <https://developer.whoop.com/api/> · <https://developer.whoop.com/docs/developing/webhooks/>
- Uber Consumer Delivery API (browse/cart/order on behalf of a consumer; partner-gated): <https://developer.uber.com/docs/consumer-delivery/introduction> · getting started + NDA/licensing: <https://developer.uber.com/docs/eats/guides/getting-started>
- Glovo Partner API (merchant/courier only — no consumer ordering): <https://api-docs.glovoapp.com/partners/index.html>
- Mindbody Affiliate API (find / book / pay wellness sessions): <https://developers.mindbodyonline.com/AffiliateDocumentation>
- 23andMe shut down 3rd-party API in 2018 (raw-file download still allowed): <https://www.mobihealthnews.com/content/23andme-shut-down-api-third-party-data-users-clinical-research-agreements-unaffected>
- Google Calendar API (read/write, OAuth2): <https://developers.google.com/calendar>
- Oura API v2: <https://cloud.ouraring.com/v2/docs>

*Connector availability changes; re-verify before building each one. Everything in §5/§13
marked 🟡 depends on an approval or a third party's backend choice and must be confirmed
at build time.*
