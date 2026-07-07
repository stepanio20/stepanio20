# Connecting services to your Concierge

Step-by-step setup for every external service the Concierge can pull from or
push to. **Do this once.** Then `make_weekly_plan` and the PWA use the
connections automatically.

Quick map of what each one unlocks:

| Service | Required? | What it unlocks |
|---|---|---|
| Profile + bloods + DNA file | **yes** (any one) | The base personalised plan (this is most of the value) |
| **Whoop** OAuth | recommended | Recovery-aware training, sleep-aware scheduling, per-day deload flags |
| **Google Calendar** OAuth | recommended | Live event push on Approve (instead of dragging .ics) |
| Apple Health export | optional | Same class as Whoop; richer if you wear an Apple Watch |
| Oura / Garmin API | optional | Alternatives to Whoop |
| Uber Eats / Glovo | not yet | Order hand-off (deep link) for now; real API later (V2) |
| Mindbody (booking) | not yet | One-tap sauna / massage book + pay (V2) |
| Stripe | not yet | App subscription billing (only if you productise) |

---

## 0. Secrets store

All credentials live in **one** gitignored file at the repo root: `secrets.env`.
A template is at `secrets.env.example`. Copy it and fill in the bits you have:

```bash
cp secrets.env.example secrets.env
$EDITOR secrets.env
```

`secrets.env` is in `.gitignore`. Tokens never leave your machine.

---

## 1. Whoop — recovery, sleep, strain, HRV, VO2max

### From the PWA on your phone (no laptop needed)

Open the app. Step 2 of the funnel shows a **Whoop** tile — tap it to open the
Connect modal. Three options inside:

- **A · Simulate** — marks you connected without real data. Useful to demo the funnel.
- **B · Paste access token** — go to <https://developer.whoop.com/dashboard> on the same phone, open your app's settings, copy the **Test Token**, paste it here. Token is stored in your browser's localStorage (this device only) — never sent anywhere.
- **C · Upload Whoop snapshot JSON** — if you've already run the Python sync on a laptop (next section), AirDrop / iCloud Drive / email the resulting `whoop_latest.json` to your phone, then tap "Choose JSON file" in the modal. The app parses the summary locally and uses it for the plan.

The PWA can't currently call the Whoop API directly from the browser (CORS),
so option B is "credential saved, ready for backend use" — until a backend
lands, **option C is the path that actually feeds data into the plan**.

### From a laptop (full automated sync, ~5 minutes)

1. Open <https://developer.whoop.com/dashboard>. Sign in with your normal Whoop account.
2. Click **Create app**.
3. Fill the form:
   - **App name**: Concierge (or anything)
   - **Contact email**: yours
   - **Privacy policy URL**: any URL you control, or `https://example.com/privacy` for a personal-only app
   - **Redirect URIs**: paste exactly `http://localhost:8910/callback`
   - **Scopes**: tick `read:recovery read:sleep read:workout read:cycles read:profile read:body_measurement offline`
4. Save. The dashboard shows your **Client ID** and **Client Secret**. Paste both into `secrets.env`:
   ```
   WHOOP_CLIENT_ID=xxxxxxxx
   WHOOP_CLIENT_SECRET=xxxxxxxx
   ```
5. Authorise the app once (this opens a browser, you log in, the script catches the redirect on localhost and stores your refresh token):
   ```bash
   python3 -m concierge.connectors.whoop.authorize
   ```
6. Pull a snapshot any time:
   ```bash
   python3 -m concierge.connectors.whoop.sync --user me
   ```
   This writes `users/me/wearables/parsed/whoop_latest.json` and the next
   `make_weekly_plan` run picks it up.

**Optional — webhooks** (push instead of pull): only useful once the app lives on
a public HTTPS host. Skip until V2.

---

## 2. Google Calendar — live event push

**~5 minutes.**

1. Open <https://console.cloud.google.com/projectcreate>. Create a project named e.g. `concierge-me`.
2. Enable the API: <https://console.cloud.google.com/apis/library/calendar-json.googleapis.com> → **Enable**.
3. OAuth consent screen: <https://console.cloud.google.com/apis/credentials/consent>
   - User type: **External**
   - App name: Concierge · your email · save
   - On the Scopes screen, add `https://www.googleapis.com/auth/calendar.events`
   - Add yourself as a **test user**
4. Create credentials: <https://console.cloud.google.com/apis/credentials> → **Create credentials → OAuth client ID**
   - Application type: **Desktop**
   - Name: anything
5. Download the JSON. In `secrets.env`:
   ```
   GCAL_OAUTH_JSON=secrets/gcal_oauth.json
   ```
   Then save the downloaded JSON to that path (the `secrets/` folder is gitignored).
6. Authorise once:
   ```bash
   python3 -m concierge.connectors.gcal.authorize
   ```
7. After that, every `make_weekly_plan --push-calendar` writes confirmed events directly to your "Concierge" calendar (auto-created on first run). Until then, the .ics drag-and-drop still works.

---

## 3. 23andMe / Ancestry / MyHeritage — raw DNA file

**No API exists.** All vendors only allow you to download your own raw file
manually. **No live sync, by design of the vendors.**

- **23andMe**: <https://you.23andme.com/tools/data> → **Browse Raw Data → Download** → save the `.zip` into `users/me/dna/raw/`.
- **MyHeritage**: account → Settings → Manage DNA kits → Download.
- **Ancestry**: account → Your DNA results → Settings → Download Raw DNA Data.

Then run the pipeline once (it's already in this repo):
```bash
python3 pipeline/01_normalize.py --user me
python3 pipeline/02_opencravat.sh me
python3 pipeline/03_pharmcat.sh me
python3 pipeline/04_pl_screen.py --user me
```

These produce the genetic findings the Concierge engine reads.

---

## 4. Blood tests — upload PDFs

Drop any blood-test PDF, photo, or Excel into `users/me/bloods/`. The pipeline's
Phase 5 extractor (`pipeline/05_extract_bloods.py`) reads them into a single
analyte JSON the Concierge uses. Filenames can be anything — the date is parsed
out of the document.

The PDFs are gitignored and never leave your machine.

---

## 5. Apple Health export — sleep / HR / VO2max / ECG / CGM

iPhone → Health app → top-right profile → **Export All Health Data**. Unzip on
your laptop, place `export.xml` plus sibling folders into
`users/me/wearables/apple_export/`.

Then `pipeline/parse_apple_health.py` streams the multi-GB XML into structured
JSON. CGM (Dexcom / Libre) data is auto-extracted from the same export.

---

## 6. Oura / Garmin — wearable alternatives

If you use one of these instead of Whoop:

- **Oura**: dev portal at <https://cloud.ouraring.com/v2/docs>. OAuth2 like Whoop. Same scopes idea (sleep, readiness, HR). Follow the Whoop pattern — `concierge/connectors/oura/` is the placeholder.
- **Garmin Health API**: partner-gated. Skip unless you already have a partner agreement.

---

## 7. Restaurants / labs / wellness — booking & ordering

Not OAuth — these are **deep links** today (the plan card shows a button that
opens the right page in the native app). What was researched and pinned for
Barcelona is in `concierge/data/barcelona_venues.json`:

- **Labs**: SYNLAB, Echevarne, Cerba, plus public CatSalut (free for residents).
- **Wellness**: ILO STUDIOS, AIRE Ancient Baths, etc.
- **Healthy delivery**: Honest Greens, Flax & Kale, Poke House.

To swap or add venues, edit that JSON. No app rebuild needed.

Real auto-ordering / auto-booking lands when:

- **Uber Eats Consumer Delivery API** — partner-gated (NDA + Uber partner manager). V2.
- **Mindbody Affiliate API** — works *if* the studio runs on Mindbody/Fresha/Vagaro. V2.
- **Glovo** — no consumer API; hand-off only, ever.

---

## What I actually need from you to "turn on" each thing

| Service | What you hand me | Where it lands |
|---|---|---|
| Whoop | Client ID + Client Secret from `developer.whoop.com/dashboard` | `secrets.env` |
| Google Calendar | The OAuth client JSON from Google Cloud | `secrets/gcal_oauth.json` |
| 23andMe / Ancestry | The raw `.txt` or `.zip` you download from your account | `users/me/dna/raw/` |
| Bloods | Lab PDFs / photos | `users/me/bloods/` |
| Apple Health | `export.xml` from your iPhone | `users/me/wearables/apple_export/` |

The shortest path from "no data" to "useful plan": just **drop the blood PDF + DNA raw file + fill `profile.json`**. The wearable connector is a nice multiplier but not required.

---

## Privacy invariants

- `secrets.env` is gitignored. Tokens never enter git.
- `users/me/{bundles,reports,exports,bloods,dna/raw,wearables}/*` are all gitignored. Personal data stays on your machine.
- The PWA reads only local files. No backend; nothing leaves the device until you wire a real backend.
- See `PRODUCT_ARCHITECTURE.md` §12 (Privacy, GDPR, EU-MDR) for the regulatory line — relevant only if you decide to productise.
