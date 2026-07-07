/* Concierge weekly-plan viewer.
   Parses the Markdown produced by `python -m concierge.make_weekly_plan` and
   renders cards with approve / skip toggles + a sticky bottom bar.
   Zero deps; vanilla JS. State is in-memory only (no network, no auth). */

// Prefer a real plan.md if the user dropped one next to the app; otherwise sample.
// plan.md is gitignored — never committed.
const PLAN_CANDIDATES = ["plan.md", "sample_plan.md"];

const PRICES = {
  // per-card estimates; venue prices in MD aren't always present, so fall back here
  order: 14, sauna: 32, massage: 90, screening: 35, resistance: 0, zone2: 0, meal_cook: 0
};

const ICONS = {
  breakfast: "🥣", main: "🍽", snack: "🥜", resistance: "🏋️", "zone-2": "🚴",
  sauna: "🧖", massage: "💆", screening: "🩺", supplement: "💊", training: "🏋️",
  recovery: "🧖", behavioural: "🎯", default: "•"
};

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null) e.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return e;
}

function parsePlan(md) {
  // Sections we care about: header (week label), supplements, training, recovery,
  // behavioural, day-by-day, tests & screening. We extract each as a flat array
  // of "cards" with kind/title/meta/why/venue.
  const lines = md.split(/\r?\n/);
  let weekLabel = "";
  const m1 = md.match(/^# Weekly Plan — (.+)$/m);
  if (m1) weekLabel = m1[1];

  const sections = [];
  let cur = null;
  let curList = null;

  const newSection = (title, kind) => {
    cur = { title, kind, cards: [] };
    sections.push(cur);
  };

  const flushCardLine = (line) => {
    if (!cur) return false;
    // Bullet item with optional title and metadata
    const bul = line.match(/^- (.+)$/);
    if (!bul) return false;
    const text = bul[1].trim();
    const macroMatch = text.match(/^_([^_]+)_ — (.+?)(?:\s+·\s+(.*))?$/);
    let kind = cur.kind, slot = "", title = text, meta = "";
    if (cur.kind === "day" && macroMatch) {
      slot = macroMatch[1];
      title = macroMatch[2];
      meta = macroMatch[3] || "";
      kind = slot === "breakfast" || slot === "main" || slot === "snack" ? slot : cur.kind;
      // distinguish cook vs order
    } else {
      // session / generic
      if (/^🏋️/.test(text)) { kind = "training"; title = text.replace(/^🏋️\s+/, ""); }
    }
    const card = { kind, slot, title, meta, why: "", venue: null, day: cur.day };
    // why text after "— "
    const dashIdx = title.indexOf(" — ");
    if (dashIdx > 0) { card.why = title.slice(dashIdx + 3); card.title = title.slice(0, dashIdx); }
    cur.cards.push(card);
    curList = cur.cards;
    return true;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const dayH = line.match(/^### (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) (\S+)$/);
    if (dayH) { newSection(`${dayH[1]} ${dayH[2]}`, "day"); cur.day = dayH[2]; continue; }
    const h2 = line.match(/^## (.+)$/);
    if (h2) {
      const t = h2[1].toLowerCase();
      const kind = t.includes("targets") ? "targets"
        : t.includes("week") ? "week"
        : t.includes("tests") || t.includes("screening") ? "screening"
        : t.includes("approve") ? "approve"
        : t.includes("sharpen") ? "gaps"
        : "info";
      newSection(h2[1], kind);
      continue;
    }
    const h3 = line.match(/^### (.+)$/);
    if (h3 && cur && cur.kind === "targets") {
      const t = h3[1].toLowerCase();
      const k = t.includes("supplement") ? "supplement"
        : t.includes("training") ? "training"
        : t.includes("recovery") ? "recovery"
        : t.includes("behaviour") ? "behavioural" : cur.kind;
      newSection(h3[1], k);
      continue;
    }
    const macros = line.match(/^\*\*~(\d+) kcal · P (\d+) \/ C (\d+) \/ F (\d+) g\*\*/);
    if (macros && cur && cur.kind === "day") { cur.macros = macros[0].replace(/\*\*/g, ""); continue; }

    if (flushCardLine(line)) continue;

    // Continuation lines that begin with "  " carry venue or sub-suggestion
    if (curList && curList.length && /^\s+(📍|🔗)/.test(line)) {
      const m = line.match(/\[([^\]]+)\]\(([^)]+)\)\s*·\s*_?([^_·]+)_?(?:\s*·\s*~?€(\d+))?/);
      if (m) {
        const last = curList[curList.length - 1];
        last.venue = last.venue || [];
        last.venue.push({ name: m[1], url: m[2], area: m[3].trim(), price: m[4] ? +m[4] : null });
      }
    }
  }
  return { weekLabel, sections };
}

function priceFor(card) {
  if (card.kind === "training") return 0;
  if (card.kind === "recovery" || /sauna/i.test(card.title)) return PRICES.sauna;
  if (/massage/i.test(card.title)) return PRICES.massage;
  if (card.kind === "screening") return PRICES.screening;
  if (card.kind === "main" || card.kind === "snack" || card.kind === "breakfast") {
    if (/🛒 order/.test(card.meta) || /order/i.test(card.meta)) return PRICES.order;
    return 0;
  }
  if (card.kind === "supplement" || card.kind === "behavioural") return 0;
  return 0;
}

let state = {};   // cardId -> "pending" | "approved" | "skipped"

function cardId(card, i) {
  return `${card.day || "_"}::${card.kind}::${(card.title || "").slice(0, 40)}::${i}`;
}

function statsAndCost(allCards) {
  let a = 0, s = 0, cost = 0;
  for (const [id, st] of Object.entries(state)) {
    if (st === "approved") { a++; const c = allCards.find(x => x.__id === id); if (c) cost += priceFor(c); }
    else if (st === "skipped") s++;
  }
  return { a, s, cost: Math.round(cost) };
}

function renderCard(card) {
  const id = card.__id;
  const cs = state[id] || "pending";
  const icon = ICONS[card.kind] || ICONS[card.slot] || ICONS.default;
  const body = el("div", { class: "body" },
    el("div", { class: "title" }, card.title),
    card.meta ? el("div", { class: "meta" }, card.meta) : null,
    card.why ? el("div", { class: "why" }, card.why) : null,
    ...(card.venue || []).map(v => el("div", { class: "venue" },
      "📍 ", el("a", { href: v.url, target: "_blank", rel: "noreferrer" }, v.name),
      el("span", {}, ` · ${v.area}${v.price ? " · ~€" + v.price : ""}`)
    ))
  );
  const onClick = (act) => () => {
    state[id] = state[id] === act ? "pending" : act;
    refresh();
  };
  const actions = el("div", { class: "actions" },
    el("button", { "data-act": "approve", class: cs === "approved" ? "on" : "", onclick: onClick("approved") }, "✓"),
    el("button", { "data-act": "skip", class: cs === "skipped" ? "on" : "", onclick: onClick("skipped") }, "✕")
  );
  const card_el = el("div", { class: "card", "data-state": cs }, el("div", { class: "icon" }, icon), body, actions);
  return card_el;
}

function refresh() {
  const all = window.__allCards || [];
  const stats = statsAndCost(all);
  document.getElementById("approved-n").textContent = stats.a;
  document.getElementById("skipped-n").textContent = stats.s;
  document.getElementById("cost").textContent = stats.cost;
  document.getElementById("approve").disabled = stats.a === 0;
  // re-render approved/skipped state on existing nodes
  document.querySelectorAll(".card").forEach((node, i) => {
    const c = all[i]; if (!c) return;
    node.setAttribute("data-state", state[c.__id] || "pending");
    node.querySelectorAll("button").forEach(b => {
      const act = b.getAttribute("data-act");
      b.classList.toggle("on", state[c.__id] === (act === "approve" ? "approved" : "skipped"));
    });
  });
}

function render(parsed) {
  document.getElementById("week-label").textContent = parsed.weekLabel || "";
  const root = document.getElementById("root");
  root.innerHTML = "";
  const allCards = [];
  let cardIdx = 0;
  for (const sec of parsed.sections) {
    if (!sec.cards.length && sec.kind !== "day") continue;
    if (sec.kind !== "approve" && sec.kind !== "info") {
      root.appendChild(el("div", { class: "section" }, sec.title));
    }
    if (sec.kind === "day") {
      root.appendChild(el("h3", { class: "day-h" }, sec.title));
      if (sec.macros) root.appendChild(el("div", { class: "macros" }, sec.macros));
    }
    for (const c of sec.cards) {
      c.__id = cardId(c, cardIdx++);
      allCards.push(c);
      root.appendChild(renderCard(c));
    }
  }
  window.__allCards = allCards;
  refresh();
}

document.getElementById("approve").addEventListener("click", () => {
  const stats = statsAndCost(window.__allCards || []);
  alert(`Mock-approve ${stats.a} cards (~€${stats.cost}).\n\nIn a real deploy this triggers:\n• Whoop/Calendar push\n• booking-API calls (Mindbody etc.) where supported\n• deep-link hand-off (Uber Eats, walk-in labs)\n\nNo network calls happen from this preview.`);
});

async function loadPlan() {
  for (const url of PLAN_CANDIDATES) {
    try {
      const r = await fetch(url);
      if (r.ok) {
        const md = await r.text();
        render(parsePlan(md));
        if (url === "plan.md") {
          document.getElementById("week-label").textContent += " · your plan";
        }
        return;
      }
    } catch (e) { /* try next */ }
  }
  document.getElementById("root").innerHTML =
    `<p class="hint">Couldn't load <code>plan.md</code> or <code>sample_plan.md</code>. Running locally? <code>python3 -m http.server</code> in this folder, then open <code>http://localhost:8000</code>.</p>`;
}

// Funnel calls us once the user has paid / skipped onboarding.
window.__startDashboard = loadPlan;
