# Indaga iOS — drop-in components

Paste-ready SwiftUI for the changes requested for the app. Written to live in the
Indaga iOS app (`birinets/indaga-ios`); kept here because that's the repo Claude
can push to. **Ruslan: copy these files into the app and wire the 4 TODO hooks.**

## What's here

| File | Fixes |
|---|---|
| `AppTheme.swift` | **Contrast fix** — forces dark scheme, white text on black, no more black-on-black. Apply `.screen()` to every screen. |
| `MeView.swift` | **Version label** at the very bottom of the "Me" tab (auto-read from Info.plist). |
| `GenomeBuildView.swift` | **DNA processing UX** — real % progress (phase-based), ETA, "~2h, you can close the app" copy, auto-redirect to the report when ready, "Start onboarding again" button. |
| `PushNotifications.swift` | **"Your DNA is ready" push** (APNs) + deep-link routing to the report. |
| `OnboardingWebView.swift` | **Onboarding funnel** embedded (the 5 A/B variants) via WKWebView. |

## The one backend dependency (required for real %)

The app needs a status endpoint the build screen polls:

```
GET /genome/job/{id}/status  →
{ "state":"building", "phase":"Matching variants against ClinVar",
  "percent": 63.5, "eta_seconds": 2600, "report_url": null }
# when done → { "state":"ready", "percent":100, "report_url":"indaga://report/genome" }
```

`percent` is phase-weighted on the **backend** (see phase table in `GenomeBuildView.swift`).
Until that exists, the view falls back to a time-based estimate that eases to 95%
and only hits 100% when `state == ready` (never shows 100% early).

When the job finishes, the backend sends an APNs push with
`data.deep_link = "indaga://report/genome"` — that's what fires the notification
and routes the user to the report.

## 4 hooks to wire (marked `// TODO` in code)

1. `GenomeBuildVM.statusURL` → your API base URL.
2. `OnboardingWebView` → your deployed funnel URL (`stepanio20.github.io/stepanio20/1..5` once GitHub Pages is on).
3. `RootRouter.route(to:)` → your app's navigation (report screen, onboarding).
4. `PushNotifications` → register the device token with your backend.

## Contrast rule (the black-on-black bug)

Never leave `Text(...)` on a custom background without a color, and remove any
`.foregroundColor(.black)` / rely-on-`.primary` on dark screens. Default is now
`Color.ink` (white); secondary is `Color.ink2` (light grey) — **never black**.
