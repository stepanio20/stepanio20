# Fully-automated iOS → TestFlight

Goal: **`git push` → a TestFlight build appears, hands-off.** No Xcode, no manual
upload. Set up **once**, then it's automatic forever.

Two ways — pick one.

---

## Option A — Xcode Cloud (simplest, Apple-native) ⭐ recommended for least setup

No runners, no fastlane, Apple handles signing. ~10 min, all in the UI.

1. Open the app in **Xcode → Product → Xcode Cloud → Create Workflow**.
2. Connect the `birinets/indaga-ios` GitHub repo (grant the GitHub app).
3. Workflow:
   - **Start Condition:** Branch Changes → `main` (push).
   - **Actions:** Archive (iOS).
   - **Post-Actions:** **TestFlight (Internal Testing)** → pick your tester group.
4. Save. Done — every push to `main` builds + delivers to TestFlight automatically.

Signing: Xcode Cloud manages certificates/profiles for you (nothing to store).
Cost: free tier ~25 compute-hours/month (plenty for a small app).

**This is the most "fully automated" with the least to maintain.** Use this unless
you specifically need GitHub Actions.

---

## Option B — GitHub Actions + fastlane (more control, any CI)

Files in this folder — drop them into `indaga-ios`:

| File | → put at (in indaga-ios) |
|---|---|
| `ios-testflight.yml` | `.github/workflows/ios-testflight.yml` |
| `Fastfile` | `fastlane/Fastfile` |
| `Appfile` | `fastlane/Appfile` |
| `Matchfile` | `fastlane/Matchfile` |
| `Gemfile` | `Gemfile` (repo root) |

### One-time setup (~20 min)

**1. App Store Connect API key** (lets CI upload + sign without an Apple ID login):
- App Store Connect → Users and Access → **Integrations → App Store Connect API** → **+** → role **App Manager**.
- Download the `AuthKey_XXXX.p8` (once!). Note the **Key ID** and **Issuer ID**.

**2. Code signing via `fastlane match`** (stores certs/profiles in a private git repo):
- Create an empty **private** repo, e.g. `birinets/ios-certs`.
- Locally, once: `bundle exec fastlane match appstore` (creates + pushes the cert/profile). Choose a **match password**.

**3. Add GitHub secrets** (indaga-ios → Settings → Secrets and variables → Actions):

| Secret | What |
|---|---|
| `ASC_API_KEY_P8` | the `.p8` file, base64-encoded: `base64 -i AuthKey_XXXX.p8` |
| `ASC_KEY_ID` | the Key ID |
| `ASC_ISSUER_ID` | the Issuer ID |
| `MATCH_GIT_URL` | `https://github.com/birinets/ios-certs.git` |
| `MATCH_PASSWORD` | the match password from step 2 |
| `MATCH_GIT_BASIC_AUTHORIZATION` | `base64("<gh-username>:<PAT-with-repo-scope>")` — lets CI read the certs repo |

**4. Fill the TODOs** in `Fastfile` / `Appfile` (bundle id + scheme name).

Then every push to `main` runs the workflow → builds → signs → uploads to
TestFlight → testers get it. Watch it in the repo's **Actions** tab.

---

## Which to choose

- **Want minimal setup & maintenance** → Xcode Cloud (Option A).
- **Already live on GitHub Actions / want full control / free macOS minutes** → Option B.

Either way: the code changes we made (in `ios-spec/`) get pasted into `indaga-ios`
once; after that, the pipeline is fully automatic.

> Note: neither path can run from this sandbox (needs a Mac + the birinets repo) —
> this is the config to enable it on your side. Once set up, no human is in the loop.
