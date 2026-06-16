/* Onboarding funnel — simulated end-to-end. Every action is faked but the
 * shape matches PRODUCT_ARCHITECTURE.md §4 (progressive, non-blocking)
 * and the connectors/payment described in PRODUCT_ARCHITECTURE.md §5/§11.
 *
 * Steps:
 *   1 — Basics (age / sex / city / goals)
 *   2 — Connect services (Whoop / Apple Health / Google Calendar) — fake OAuth
 *   3 — Upload DNA file (any .txt/.zip — never read, never sent)
 *   4 — Upload blood-test PDFs (any files — never read, never sent)
 *   5 — Preferences (diet pattern / allergies / dislikes / weekly budget)
 *   6 — Start process — simulated 4-stage pipeline run with progress bar
 *   7 — Your results are ready — paywall (fake) → unlock dashboard
 *
 * Progress is persisted in localStorage so a refresh resumes mid-funnel.
 * "Start over" wipes it.
 *
 * Once complete, calls window.__startDashboard() which reveals main.js's UI.
 */
(function () {
  // Funnel STATE is in-memory only — every page reload restarts onboarding
  // from the landing page (per user request 2026-06-16).
  // CONNECTION CREDENTIALS the user pastes/uploads ARE persisted (separate
  // localStorage key) so they survive a reload — losing those would be hostile.
  const CRED_KEY = "concierge.credentials.v1";
  const $ = (id) => document.getElementById(id);
  const funnelEl = $("funnel");
  const innerEl = $("funnel-inner");

  function el(tag, attrs = {}, ...children) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") e.className = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (v !== false && v !== null && v !== undefined) e.setAttribute(k, v);
    }
    for (const c of children) {
      if (c == null) continue;
      e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return e;
  }

  const initial = { step: 0, paid: false, profile: {}, connections: {}, files: {}, prefs: {} };
  let state = JSON.parse(JSON.stringify(initial));   // fresh on every page load
  function save() { /* in-memory only — no-op on purpose */ }
  function reset() { state = JSON.parse(JSON.stringify(initial)); }

  // ---- Credentials (persisted across reloads) -------------------------- //
  function loadCreds() {
    try { return JSON.parse(localStorage.getItem(CRED_KEY) || "{}"); }
    catch { return {}; }
  }
  function saveCreds(c) { localStorage.setItem(CRED_KEY, JSON.stringify(c)); }
  function setCred(svc, payload) {
    const c = loadCreds();
    c[svc] = Object.assign({}, c[svc], payload, { updated_at: new Date().toISOString() });
    saveCreds(c);
  }
  function clearCred(svc) {
    const c = loadCreds();
    delete c[svc];
    saveCreds(c);
  }

  // ---- shared chrome (used by onboarding steps 1..7) ------------------- //
  function chrome(stepNo, title, body, opts = {}) {
    innerEl.innerHTML = "";
    const steps = 7;
    const pct = Math.round(stepNo / steps * 100);
    const back = stepNo > 1 && stepNo < 7
      ? el("button", { class: "btn-ghost", onclick: () => { state.step = stepNo - 1; save(); paint(); } }, "← Back")
      : null;
    const skip = opts.canSkip
      ? el("button", { class: "btn-ghost right", onclick: () => { state.step = stepNo + 1; save(); paint(); } }, "Skip →")
      : null;

    const wrap = el("div", { class: "funnel" },
      el("div", { class: "progress" }, el("span", { style: `width:${pct}%` })),
      el("div", { class: "step-meta" },
        el("div", {},
          el("div", { class: "step-no" }, `Step ${stepNo} of ${steps}`),
          el("h1", {}, title)
        ),
        el("div", { class: "step-nav" }, back, skip)
      ),
      body
    );
    innerEl.appendChild(wrap);
  }

  // ---- Step 0 — Sales landing page ------------------------------------ //
  function step0() {
    innerEl.innerHTML = "";
    const cta = (label, classes = "btn-primary btn-xl") => el("button", {
      class: classes,
      onclick: () => { state.step = 1; save(); paint(); },
    }, label);

    const benefits = [
      { icon: "🧬", t: "Your DNA, decoded",
        d: "23andMe / Ancestry / MyHeritage raw file → PharmCAT drug response, polygenic risk percentiles, ClinVar pathogenic screen. Open-source, reproducible." },
      { icon: "🩸", t: "Your bloods, understood",
        d: "Drop any lab PDF — we extract every analyte and turn it into personal supplement, training, and screening targets backed by ATP III / EFSA / IOM thresholds." },
      { icon: "⌚",  t: "Your wearable, applied",
        d: "Connect Whoop / Oura / Apple Health and the plan adapts to your recovery and sleep — drops a session on a low-HRV day, schedules sauna when it matters." },
      { icon: "📍", t: "Your city, mapped",
        d: "Live Barcelona venue catalogue — labs (Synlab, Echevarne, Cerba), wellness (ILO, AIRE), healthy delivery (Honest Greens, Flax & Kale). One-tap book and order." },
    ];

    const steps3 = [
      { n: "1", t: "Connect & upload", d: "Whoop, Apple Health, DNA file, blood PDFs. 5 minutes once." },
      { n: "2", t: "We compute", d: "Genetics + bloods + wearable + family history fuse into a single plan." },
      { n: "3", t: "You approve", d: "Open the app Monday, review the week, one tap. Calendar fills itself." },
    ];

    const testimonials = [
      { q: "Replaced three subscriptions for me — and the explanations are better than what my GP gives me in 10 minutes.", who: "Marc, 32, Eixample" },
      { q: "The shopping list lands Sunday night. Mercadona arrives Monday. I just cook.", who: "Júlia, 29, Gràcia" },
      { q: "Got my GP to add ApoB and Lp(a) to my next panel based on the app's missing-data flag.", who: "Antonio, 41, Born" },
    ];

    const faq = [
      ["Is this medical advice?", "No. Everything is information, framed against published thresholds (ATP III, EFSA, IOM). The plan tells you what to discuss with your clinician — and never claims a diagnosis."],
      ["Where does my data go?", "Locally on your device. The MVP is a single-user app; nothing is sent to any backend you haven't explicitly connected (Google Calendar, Whoop). See the privacy section in the docs."],
      ["What if I don't have a wearable / DNA file / blood panel?", "Skip any step. The plan ships with whatever you have today and inline-flags exactly what would sharpen next week."],
      ["Why Barcelona-specific?", "Because abstract advice is useless. The app maps every recommendation to a real lab, studio, or restaurant within walking distance."],
    ];

    const landing = el("div", { class: "landing" },
      el("nav", { class: "nav" },
        el("div", { class: "brand-lg" }, "Concierge", el("span", { class: "dot" }, "·"), el("small", {}, "Barcelona")),
        el("div", { class: "nav-actions" },
          el("a", { href: "#how" }, "How it works"),
          el("a", { href: "#pricing" }, "Pricing"),
          el("a", { href: "#faq" }, "FAQ"),
          cta("Start free", "btn-primary"))),

      // hero
      el("section", { class: "hero" },
        el("div", { class: "eyebrow" }, "Your health, on Mondays. Auto-piloted."),
        el("h1", { class: "h1" },
          "Open the app once a week. ",
          el("span", { class: "grad" }, "Your body has a plan."),
        ),
        el("p", { class: "sub" },
          "Concierge fuses your DNA, blood tests, wearable trends and family history into one ",
          el("strong", {}, "personal weekly plan"),
          " — what to eat, when to train, which sauna to book, which lab tests to add next. ",
          "All mapped to real places in Barcelona. Calendar fills itself. You approve in 2 minutes."),
        el("div", { class: "hero-cta" }, cta("Start your week"),
          el("span", { class: "muted" }, "·"),
          el("a", { href: "#how", class: "link" }, "See how it works")),
        el("div", { class: "hero-trust" },
          el("span", {}, "🔒 Local-first · no backend in MVP"),
          el("span", {}, "🇪🇸 EU privacy by default"),
          el("span", {}, "🩺 Information, not diagnosis"))),

      // dashboard preview card
      el("section", { class: "preview" },
        el("div", { class: "preview-card" },
          el("div", { class: "preview-head" },
            el("strong", {}, "Monday 24 June"),
            el("span", { class: "muted" }, "2 424 kcal · P 119 g")),
          el("ul", { class: "preview-rows" },
            el("li", {}, el("span", { class: "ic" }, "🏋️"), "Resistance session", el("span", { class: "tag" }, "self")),
            el("li", {}, el("span", { class: "ic" }, "🧖"), "Sauna · ILO Studios", el("span", { class: "tag book" }, "book")),
            el("li", {}, el("span", { class: "ic" }, "🍽"), "Salmon, sweet potato, broccoli", el("span", { class: "tag" }, "cook")),
            el("li", {}, el("span", { class: "ic" }, "🩺"), "Lipid panel due · Echevarne", el("span", { class: "tag book" }, "book")),
            el("li", {}, el("span", { class: "ic" }, "💊"), "Vitamin D3 2 000 IU", el("span", { class: "tag" }, "self"))),
          el("div", { class: "preview-foot" },
            el("strong", {}, "~€148 / week"),
            el("button", { class: "btn-ghost-sm" }, "Approve · 1 tap")))),

      // benefits
      el("section", { id: "benefits", class: "benefits" },
        el("h2", {}, "Why Concierge"),
        el("div", { class: "grid-4" },
          ...benefits.map(b => el("div", { class: "card-b" },
            el("div", { class: "ic-big" }, b.icon),
            el("h3", {}, b.t),
            el("p", {}, b.d))))),

      // how it works
      el("section", { id: "how", class: "how" },
        el("h2", {}, "How it works"),
        el("div", { class: "grid-3" },
          ...steps3.map(s => el("div", { class: "card-s" },
            el("div", { class: "step-n" }, s.n),
            el("h3", {}, s.t),
            el("p", {}, s.d)))),
        el("div", { class: "center" }, cta("Start onboarding"))),

      // testimonials
      el("section", { class: "social" },
        el("h2", {}, "What people say"),
        el("div", { class: "grid-3" },
          ...testimonials.map(t => el("blockquote", { class: "quote" },
            el("p", {}, "“", t.q, "”"),
            el("footer", {}, t.who))))),

      // pricing
      el("section", { id: "pricing", class: "pricing" },
        el("h2", {}, "Simple pricing"),
        el("div", { class: "price-card" },
          el("div", { class: "price-h" }, el("strong", {}, "€19"), el("span", {}, "/month")),
          el("ul", {},
            el("li", {}, "Unlimited weekly plans"),
            el("li", {}, "All connectors (Whoop, Apple, Oura, Calendar)"),
            el("li", {}, "Barcelona venue catalogue + one-tap booking links"),
            el("li", {}, "Auto-generated shopping list + .ics calendar export"),
            el("li", {}, "Cancel any time · 7-day money-back")),
          cta("Start free trial"))),

      // faq
      el("section", { id: "faq", class: "faq" },
        el("h2", {}, "Frequently asked"),
        ...faq.map(([q, a]) => el("details", {}, el("summary", {}, q), el("p", {}, a)))),

      // final CTA
      el("section", { class: "final" },
        el("h2", {}, "Stop guessing. Start Monday on autopilot."),
        cta("Get started"),
        el("p", { class: "muted" }, "Preview: payment and connections are simulated end-to-end. No card is charged.")),

      // footer
      el("footer", { class: "site-foot" },
        el("p", {}, "© Concierge — information only, not medical advice. Built on top of an open-source genomics pipeline."),
        el("p", { class: "muted" }, "PRODUCT_ARCHITECTURE.md · CONNECTIONS.md")),
    );
    innerEl.appendChild(landing);
    window.scrollTo(0, 0);
  }

  // ---- Step 1 — Basics -------------------------------------------------- //
  function step1() {
    const p = state.profile;
    const goals = new Set(p.goals || []);
    function tog(g) {
      goals.has(g) ? goals.delete(g) : goals.add(g);
      paint();
    }
    const goalChips = ["longevity", "recomposition", "lose_fat", "gain_muscle", "sleep", "stress",
                       "lower_blood_pressure", "quit_nicotine", "athletic_performance"]
      .map(g => el("button", {
        class: "chip" + (goals.has(g) ? " on" : ""),
        onclick: () => { tog(g); p.goals = [...goals]; save(); },
      }, g.replace(/_/g, " ")));

    const next = el("button", { class: "btn-primary",
      onclick: () => { state.profile = p; state.step = 2; save(); paint(); } }, "Next →");

    chrome(1, "Tell us about yourself", el("div", { class: "fields" },
      el("label", {}, "Age",
        el("input", { type: "number", min: 16, max: 110, value: p.age || "",
          oninput: (e) => { p.age = +e.target.value || null; save(); } })),
      el("label", {}, "Sex",
        el("select", { onchange: (e) => { p.sex = e.target.value; save(); } },
          el("option", { value: "" }, "—"),
          el("option", { value: "XY", selected: p.sex === "XY" }, "Male (XY)"),
          el("option", { value: "XX", selected: p.sex === "XX" }, "Female (XX)"))),
      el("label", {}, "City",
        el("input", { type: "text", value: p.city || "Barcelona",
          oninput: (e) => { p.city = e.target.value; save(); } })),
      el("label", {}, "Height (cm)",
        el("input", { type: "number", value: p.height || "",
          oninput: (e) => { p.height = +e.target.value || null; save(); } })),
      el("label", {}, "Weight (kg)",
        el("input", { type: "number", value: p.weight || "",
          oninput: (e) => { p.weight = +e.target.value || null; save(); } })),
      el("div", { class: "field-wide" },
        el("div", { class: "lbl" }, "Goals (pick a few)"),
        el("div", { class: "chips" }, ...goalChips)),
      el("div", { class: "actions" }, next)
    ));
  }

  // ---- Step 2 — Connect services --------------------------------------- //
  // Three real ways to connect on phone (no laptop required for paths a/c):
  //   a) "Simulate" — for the demo: mark connected without real data
  //   b) Paste access token — works if you generated one on the Whoop dev dashboard
  //   c) Upload snapshot JSON — for users who already ran sync.py on a laptop
  function openConnectModal(svc, label) {
    const creds = loadCreds()[svc] || {};
    const close = () => overlay.remove();
    const overlay = el("div", { class: "overlay" });
    const summaryFromJson = (json) => {
      const s = json.summary || {};
      const parts = [];
      if (s.recovery_avg != null) parts.push(`recovery avg ${s.recovery_avg}/100`);
      if (s.hrv_rmssd_avg_ms != null) parts.push(`HRV ${s.hrv_rmssd_avg_ms} ms`);
      if (s.strain_avg != null) parts.push(`strain avg ${s.strain_avg}`);
      if (s.samples) parts.push(`${s.samples.recovery || 0} recovery + ${s.samples.sleep || 0} sleep records`);
      return parts.join(" · ");
    };

    const tokenInput = el("input", { type: "text", placeholder: "Paste access token…",
                                     value: creds.access_token || "" });
    const snapshotFile = el("input", { type: "file", accept: ".json", onchange: async (e) => {
      const f = e.target.files[0]; if (!f) return;
      try {
        const text = await f.text();
        const json = JSON.parse(text);
        const summary = summaryFromJson(json);
        setCred(svc, { snapshot_filename: f.name, snapshot_loaded_at: new Date().toISOString(),
                       summary, samples: (json.summary || {}).samples || null });
        state.connections[svc] = { method: "snapshot", connected_at: new Date().toISOString(), summary };
        close(); paint();
      } catch (err) {
        alert("Couldn't parse this JSON: " + err.message);
      }
    } });

    const modal = el("div", { class: "consent connect-modal" },
      el("h2", {}, `Connect ${label}`),
      el("p", { class: "muted" }, "Three ways — pick whichever fits."),

      // Option A — simulate
      el("div", { class: "opt" },
        el("strong", {}, "A · Try the demo (simulated)"),
        el("p", { class: "muted" }, "Mark as connected without real data. Useful for poking around."),
        el("button", { class: "btn-ghost-sm", onclick: () => {
          state.connections[svc] = { method: "simulated", connected_at: new Date().toISOString() };
          close(); paint();
        } }, "Simulate connect")),

      // Option B — paste access token
      el("div", { class: "opt" },
        el("strong", {}, "B · Paste access token"),
        el("p", { class: "muted" }, "Generate one on the Whoop developer dashboard → your app → Test Token. Stored locally in your browser (not sent anywhere)."),
        tokenInput,
        el("button", { class: "btn-ghost-sm", onclick: () => {
          const v = tokenInput.value.trim();
          if (!v) return alert("Paste a token first.");
          setCred(svc, { access_token: v });
          state.connections[svc] = { method: "token", connected_at: new Date().toISOString() };
          close(); paint();
        } }, "Save token & connect")),

      // Option C — upload snapshot JSON
      el("div", { class: "opt" },
        el("strong", {}, "C · Upload Whoop snapshot JSON"),
        el("p", { class: "muted" },
          "If you've run ", el("code", {}, "python3 -m concierge.connectors.whoop.sync --user me"),
          " on a laptop, AirDrop / iCloud Drive the resulting ",
          el("code", {}, "whoop_latest.json"), " to your phone and drop it here. We summarise it for the plan."),
        el("button", { class: "btn-ghost-sm", onclick: () => snapshotFile.click() }, "Choose JSON file"),
        snapshotFile),

      // Footer
      el("div", { class: "modal-foot" },
        creds.access_token || creds.snapshot_filename
          ? el("button", { class: "btn-ghost-sm danger", onclick: () => {
              clearCred(svc);
              delete state.connections[svc];
              close(); paint();
            } }, "Disconnect")
          : null,
        el("button", { class: "btn-ghost-sm right", onclick: close }, "Close")),

      el("p", { class: "legal" },
        "Reality check: the browser-side preview only stores credentials locally. ",
        "Real Whoop API calls require either the Python sync (Option C) or a backend (V2). ",
        "See ", el("code", {}, "CONNECTIONS.md"), " for the full guide."));
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  }

  function step2() {
    const creds = loadCreds();
    const services = [
      { id: "whoop", label: "Whoop", desc: "Recovery, sleep, strain, HRV, VO2max", connectable: true },
      { id: "oura", label: "Oura", desc: "Sleep + readiness + HR (alternative to Whoop)", connectable: true },
      { id: "apple", label: "Apple Health", desc: "Same metrics + ECG + CGM if you wear an Apple Watch", connectable: false,
        note: "iOS-only export — paste your export.xml on a laptop per CONNECTIONS.md §5." },
      { id: "gcal", label: "Google Calendar", desc: "Push your weekly plan as events", connectable: true },
    ];
    const tiles = services.map(s => {
      const isOn = !!state.connections[s.id];
      const detail = creds[s.id]?.summary || (creds[s.id]?.access_token ? "token saved" : null);
      return el("button", {
        class: "tile" + (isOn ? " on" : ""),
        onclick: () => s.connectable ? openConnectModal(s.id, s.label) : alert(s.note || "Not connectable from the browser."),
      },
        el("div", { class: "tile-h" },
          el("strong", {}, s.label),
          el("span", { class: "pill" }, isOn ? "✓ Connected" : (s.connectable ? "Connect" : "Manual"))),
        el("p", { class: "muted" }, s.desc),
        detail ? el("p", { class: "muted small" }, "↳ " + detail) : null);
    });
    const next = el("button", { class: "btn-primary",
      onclick: () => { state.step = 3; save(); paint(); } },
      Object.keys(state.connections).length ? "Next →" : "Skip — connect later");
    chrome(2, "Connect your devices", el("div", {},
      el("p", { class: "lede" }, "Each is optional. Phone-friendly: tap a tile, then either simulate, paste an access token, or upload a snapshot JSON. The plan ships with whatever's connected and inline-flags what would sharpen next week."),
      el("div", { class: "tiles" }, ...tiles),
      el("div", { class: "actions" }, next)
    ), { canSkip: true });
  }

  // ---- Step 3 — DNA upload (fake) -------------------------------------- //
  function fileDrop(stateKey, accept, label) {
    const have = state.files[stateKey];
    const input = el("input", { type: "file", accept, multiple: stateKey === "bloods",
      onchange: (e) => {
        const fs = [...e.target.files];
        if (!fs.length) return;
        state.files[stateKey] = fs.map(f => ({ name: f.name, size: f.size, simulated: true }));
        save();
        paint();
      } });
    const trigger = el("button", { class: "drop", onclick: () => input.click() },
      have ? el("div", {},
        el("strong", {}, "✓ Loaded:"),
        el("ul", {}, ...(Array.isArray(have) ? have : [have]).map(f =>
          el("li", {}, `${f.name} (${(f.size / 1024).toFixed(1)} KB)`)))
      ) : el("div", {}, el("strong", {}, label), el("p", { class: "muted" }, "Drag-and-drop or click to choose. Files stay in your browser only — not uploaded in this preview.")));
    return el("div", { class: "field-wide" }, input, trigger);
  }

  function step3() {
    const next = el("button", { class: "btn-primary",
      onclick: () => { state.step = 4; save(); paint(); } },
      state.files.dna ? "Next →" : "Skip — upload later");
    chrome(3, "Upload your DNA file", el("div", {},
      el("p", { class: "lede" }, "23andMe / AncestryDNA / MyHeritage / FTDNA — drop the raw download (.txt or .zip). All vendors only let you download manually; there's no API, by design."),
      el("p", { class: "muted" }, "What it unlocks: PGx (drug response), polygenic risk percentiles, a high-penetrance ClinVar screen."),
      fileDrop("dna", ".txt,.zip,.csv,.tsv,.tar,.gz", "Drop raw DNA file"),
      el("div", { class: "actions" }, next)
    ), { canSkip: true });
  }

  // ---- Step 4 — Blood tests (fake) ------------------------------------- //
  function step4() {
    const next = el("button", { class: "btn-primary",
      onclick: () => { state.step = 5; save(); paint(); } },
      state.files.bloods ? "Next →" : "Skip — upload later");
    chrome(4, "Upload blood tests", el("div", {},
      el("p", { class: "lede" }, "Any recent lab PDFs or photos. The engine reads them into a single analyte timeline — this is what makes generic targets personal."),
      el("p", { class: "muted" }, "What it unlocks: supplement targeting (D3, B12, ferritin, ApoB), screening cadence, the Ornament-style data-gap module."),
      fileDrop("bloods", ".pdf,.jpg,.jpeg,.png,.xlsx,.csv", "Drop blood-test files"),
      el("div", { class: "actions" }, next)
    ), { canSkip: true });
  }

  // ---- Step 5 — Preferences -------------------------------------------- //
  function step5() {
    const p = state.prefs;
    const allergies = new Set(p.allergies || []);
    function togA(a) { allergies.has(a) ? allergies.delete(a) : allergies.add(a); p.allergies = [...allergies]; save(); paint(); }
    const allergyChips = ["lactose", "gluten", "nuts", "fish", "egg", "soy"]
      .map(a => el("button", { class: "chip" + (allergies.has(a) ? " on" : ""), onclick: () => togA(a) }, a));
    const next = el("button", { class: "btn-primary",
      onclick: () => { state.step = 6; save(); paint(); } }, "Start processing →");
    chrome(5, "Preferences", el("div", { class: "fields" },
      el("label", {}, "Diet pattern",
        el("select", { onchange: (e) => { p.pattern = e.target.value; save(); } },
          ...["omnivore","mediterranean","pescatarian","vegetarian","vegan","low_carb","high_protein"]
            .map(x => el("option", { value: x, selected: p.pattern === x }, x.replace(/_/g, " "))))),
      el("label", {}, "Meals/day",
        el("input", { type: "number", min: 1, max: 6, value: p.meals_per_day || 3,
          oninput: (e) => { p.meals_per_day = +e.target.value || 3; save(); } })),
      el("label", {}, "Training days/week",
        el("input", { type: "number", min: 0, max: 7, value: p.training_days || 3,
          oninput: (e) => { p.training_days = +e.target.value || 3; save(); } })),
      el("label", {}, "Weekly budget (€)",
        el("input", { type: "number", min: 0, value: p.budget || 200,
          oninput: (e) => { p.budget = +e.target.value || 0; save(); } })),
      el("div", { class: "field-wide" },
        el("div", { class: "lbl" }, "Allergies"),
        el("div", { class: "chips" }, ...allergyChips)),
      el("div", { class: "actions" }, next)
    ));
  }

  // ---- Step 6 — Processing -------------------------------------------- //
  function step6() {
    const stages = [
      "Normalising DNA + variant annotation (PharmCAT / OpenCRAVAT)…",
      "Extracting blood analytes + computing PGS percentiles…",
      "Joining wearable, profile, and family-history priors…",
      "Synthesising your personalised plan + Barcelona venues…",
    ];
    const list = el("ul", { class: "stages" });
    const bar = el("div", { class: "bar" }, el("span", { style: "width:0%" }));
    const wrap = el("div", {}, bar, list);
    chrome(6, "Running your pipeline", wrap);

    // Simulate the pipeline running — visible feedback.
    let i = 0;
    function tick() {
      if (i >= stages.length) {
        state.processed_at = new Date().toISOString();
        state.step = 7;
        save();
        setTimeout(paint, 250);
        return;
      }
      const li = el("li", {}, el("span", { class: "dot" }), stages[i]);
      list.appendChild(li);
      const targetPct = Math.round(((i + 1) / stages.length) * 100);
      animateBar(bar.firstChild, targetPct, 700, () => {
        li.classList.add("done");
        i++;
        tick();
      });
    }
    function animateBar(node, target, ms, done) {
      const start = parseInt(node.style.width || "0", 10);
      const t0 = performance.now();
      function frame(t) {
        const k = Math.min(1, (t - t0) / ms);
        node.style.width = Math.round(start + (target - start) * k) + "%";
        if (k < 1) requestAnimationFrame(frame);
        else done();
      }
      requestAnimationFrame(frame);
    }
    setTimeout(tick, 250);
  }

  // ---- Step 7 — Results ready (paywall, fake) -------------------------- //
  function step7() {
    if (state.paid) { unlockDashboard(); return; }
    const card = el("div", { class: "paywall" },
      el("div", { class: "tick" }, "✓"),
      el("h1", {}, "Your results are ready"),
      el("p", { class: "lede" }, "Unlock your weekly plan + .ics export + Barcelona venue catalog. Cancel any time."),
      el("ul", { class: "perks" },
        el("li", {}, "Personalised macros, supplement targets, training split"),
        el("li", {}, "Tests + clinics in Barcelona, with one-tap booking links"),
        el("li", {}, "Restaurants per meal · auto-generated shopping list"),
        el("li", {}, "Weekly export to Google Calendar"),
        el("li", { class: "muted" }, "Cancel any time. 7-day money-back.")),
      el("div", { class: "price" },
        el("strong", {}, "€19"),
        el("span", {}, "/month")),
      el("form", { id: "pay-form" },
        el("input", { type: "text", placeholder: "Cardholder name", required: true }),
        el("input", { type: "text", placeholder: "Card number — 4242 4242 4242 4242", required: true,
                      inputmode: "numeric", maxlength: 19 }),
        el("div", { class: "row" },
          el("input", { type: "text", placeholder: "MM/YY", required: true, maxlength: 5 }),
          el("input", { type: "text", placeholder: "CVC", required: true, maxlength: 4 })),
        el("button", { type: "submit", class: "btn-primary" }, "Pay €19 — simulated")
      ),
      el("p", { class: "legal" }, "This preview does NOT charge any card. No data is sent. Architecture sketch only. See PRODUCT_ARCHITECTURE.md §11/12."));
    chrome(7, "Done", card);
    $("pay-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const btn = e.target.querySelector("button");
      btn.disabled = true;
      btn.textContent = "Processing…";
      setTimeout(() => {
        state.paid = true;
        state.paid_at = new Date().toISOString();
        save();
        paint();
      }, 1000);
    });
  }

  // ---- Reveal dashboard ------------------------------------------------ //
  function unlockDashboard() {
    funnelEl.hidden = true;
    document.getElementById("root").hidden = false;
    document.getElementById("bar").hidden = false;
    const banner = el("div", { class: "welcome" },
      el("strong", {}, "Welcome to your dashboard."),
      el("span", {}, " Onboarding is simulated; this is your sample week."),
      el("button", { class: "link", onclick: () => { reset(); paint(); } }, "Start over"));
    document.getElementById("root").prepend(banner);
    if (typeof window.__startDashboard === "function") window.__startDashboard();
  }

  // ---- Router --------------------------------------------------------- //
  function paint() {
    const done = state.step >= 7 && state.paid;
    if (done) { unlockDashboard(); return; }
    funnelEl.hidden = false;
    document.getElementById("root").hidden = true;
    document.getElementById("bar").hidden = true;
    ({0: step0, 1: step1, 2: step2, 3: step3, 4: step4, 5: step5, 6: step6, 7: step7})[state.step]();
  }

  // Defer paint until DOM ready
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", paint);
  else paint();

  window.__funnelReset = reset;
})();
