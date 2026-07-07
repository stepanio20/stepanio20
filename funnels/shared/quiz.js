/* Indaga quiz-funnel engine — data-driven. A variant defines window.FUNNEL and
 * includes this file; the engine renders hero → questions → analyzing → result
 * teaser → email capture → offer, firing analytics at every step.
 *
 * No dependencies. Answers persist in localStorage so refresh resumes.
 */
(function () {
  const F = window.FUNNEL;
  const T = window.track || function () {};
  const app = document.getElementById('app');
  const KEY = 'idg_answers_' + (F.variant || 'v');

  let answers = {};
  try { answers = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
  const save = () => localStorage.setItem(KEY, JSON.stringify(answers));

  // ---- helpers ---------------------------------------------------------- //
  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const k in (attrs || {})) {
      if (k === 'class') n.className = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k];
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    }
    for (const c of kids) if (c != null) n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    return n;
  }

  // flat sequence of screen ids
  const seq = ['hero', ...F.questions.map(q => 'q:' + q.id), 'analyzing', 'result', 'lead', 'offer'];
  let i = 0;

  function pct() { return Math.round((i) / (seq.length - 1) * 100); }

  function chrome(inner, showProgress) {
    app.innerHTML = '';
    const bar = el('div', { class: 'topbar' });
    if (i > 0 && i < seq.length) bar.appendChild(el('button', { class: 'back', 'aria-label': 'Back', onclick: prev }, '‹'));
    bar.appendChild(el('div', { class: 'brand', html: F.brand + '<span class="dot">.</span>' }));
    if (showProgress) {
      const p = el('div', { class: 'progress' }); const s = el('span'); p.appendChild(s);
      bar.appendChild(p); requestAnimationFrame(() => s.style.width = pct() + '%');
    }
    app.appendChild(bar);
    app.appendChild(inner);
  }

  function go(n) { i = Math.max(0, Math.min(seq.length - 1, n)); render(); window.scrollTo(0, 0); }
  function next() { go(i + 1); }
  function prev() { go(i - 1); }

  // ---- screens ---------------------------------------------------------- //
  function heroScreen() {
    const h = F.hero;
    const s = el('div', { class: 'screen' });
    if (h.eyebrow) s.appendChild(el('span', { class: 'eyebrow' }, h.eyebrow));
    s.appendChild(el('h1', { class: 'hero', html: h.headline }));
    if (h.sub) s.appendChild(el('p', { class: 'sub', html: h.sub }));
    if (h.stats) {
      const row = el('div', { class: 'stats' });
      h.stats.forEach(st => row.appendChild(el('div', { class: 'stat' }, el('b', {}, st.n), el('span', {}, st.l))));
      s.appendChild(row);
    }
    if (h.trust) {
      const t = el('div', { class: 'trust' });
      h.trust.forEach(x => t.appendChild(el('span', { html: x })));
      s.appendChild(t);
    }
    const cta = el('div', { class: 'sticky-cta' },
      el('button', { class: 'cta', onclick: () => { T('quiz_start'); next(); } }, h.cta || 'Start'));
    chrome(s, false);
    app.appendChild(cta);
  }

  function questionScreen(q) {
    const s = el('div', { class: 'screen' });
    s.appendChild(el('h2', { class: 'q', html: q.q }));
    if (q.hint) s.appendChild(el('p', { class: 'qhint' }, q.hint));
    const wrap = el('div', { class: 'options' });
    const cur = answers[q.id] || (q.type === 'multi' ? [] : null);

    q.options.forEach(o => {
      const selected = q.type === 'multi' ? cur.includes(o.value) : cur === o.value;
      const btn = el('button', { class: 'opt' + (selected ? ' sel' : '') },
        o.emoji ? el('span', { class: 'emoji' }, o.emoji) : null,
        el('span', {}, o.label),
        el('span', { class: 'check' }));
      btn.addEventListener('click', () => {
        if (q.type === 'multi') {
          const arr = answers[q.id] || [];
          answers[q.id] = arr.includes(o.value) ? arr.filter(v => v !== o.value) : [...arr, o.value];
          save(); render();
        } else {
          answers[q.id] = o.value; save();
          T('quiz_step', { step: q.id, value: o.value });
          setTimeout(next, 220);
        }
      });
      wrap.appendChild(btn);
    });
    s.appendChild(wrap);
    chrome(s, true);
    if (q.type === 'multi') {
      const ok = (answers[q.id] || []).length > 0;
      app.appendChild(el('div', { class: 'sticky-cta' },
        el('button', { class: 'cta', disabled: ok ? null : 'disabled',
          onclick: () => { T('quiz_step', { step: q.id, value: answers[q.id] }); next(); } }, 'Continue')));
    }
  }

  function analyzingScreen() {
    T('quiz_complete', { answers });
    const s = el('div', { class: 'screen analyzing' });
    s.appendChild(el('div', { class: 'spinner' }));
    s.appendChild(el('h2', { class: 'q', html: F.analyzing.title || 'Building your profile…' }));
    const lines = (F.analyzing.lines || []).map(t => el('div', { class: 'line' }, t));
    lines.forEach(l => s.appendChild(l));
    chrome(s, true);
    let k = 0;
    const tick = () => {
      if (k > 0) lines[k - 1].className = 'line done';
      if (k < lines.length) { lines[k].className = 'line on'; k++; setTimeout(tick, 620); }
      else setTimeout(next, 500);
    };
    setTimeout(tick, 350);
  }

  function resultScreen() {
    const r = F.result;
    const s = el('div', { class: 'screen' });
    if (r.eyebrow) s.appendChild(el('span', { class: 'eyebrow' }, r.eyebrow));
    s.appendChild(el('h1', { class: 'hero', html: typeof r.headline === 'function' ? r.headline(answers) : r.headline }));
    if (r.sub) s.appendChild(el('p', { class: 'sub', html: r.sub }));
    const cards = el('div', { class: 'result-cards' });
    (typeof r.cards === 'function' ? r.cards(answers) : r.cards).forEach(c => {
      const card = el('div', { class: 'rcard' + (c.locked ? ' locked' : '') },
        el('div', { class: 'ic' }, c.ic || '•'),
        el('div', {},
          el('h3', {}, c.title, c.tag ? el('span', { class: 'pill-tag', style: 'margin-left:8px' }, c.tag) : null),
          el('p', { html: c.teaser })),
        c.locked ? el('div', { class: 'lock' }, '🔒') : null);
      cards.appendChild(card);
    });
    s.appendChild(cards);
    chrome(s, true);
    app.appendChild(el('div', { class: 'sticky-cta' },
      el('button', { class: 'cta', onclick: () => { T('result_cta'); next(); } }, r.cta || 'See my full results')));
  }

  function leadScreen() {
    const l = F.lead;
    const s = el('div', { class: 'screen' });
    s.appendChild(el('h1', { class: 'hero', html: l.headline }));
    if (l.sub) s.appendChild(el('p', { class: 'sub', html: l.sub }));
    const input = el('input', { class: 'field', type: 'email', placeholder: l.placeholder || 'you@email.com',
      autocomplete: 'email', inputmode: 'email' });
    if (answers._email) input.value = answers._email;
    s.appendChild(input);
    chrome(s, true);
    const btn = el('button', { class: 'cta' }, l.cta || 'Get my results');
    btn.addEventListener('click', () => {
      const v = input.value.trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { input.style.borderColor = 'var(--bad)'; input.focus(); return; }
      answers._email = v; save();
      T('lead', { email_domain: v.split('@')[1] });
      next();
    });
    app.appendChild(el('div', { class: 'sticky-cta' }, btn,
      el('p', { class: 'fineprint', html: l.fine || 'We email your full report. No spam. Unsubscribe anytime.' })));
  }

  function offerScreen() {
    const o = F.offer;
    T('offer_view');
    const s = el('div', { class: 'screen' });
    if (o.eyebrow) s.appendChild(el('span', { class: 'eyebrow' }, o.eyebrow));
    s.appendChild(el('h1', { class: 'hero', html: o.headline }));
    if (o.sub) s.appendChild(el('p', { class: 'sub', html: o.sub }));
    const price = el('div', { class: 'price-row' });
    if (o.priceOld) price.appendChild(el('s', {}, o.priceOld));
    price.appendChild(el('b', {}, o.price)); price.appendChild(el('span', {}, o.per || '/mo'));
    s.appendChild(price);
    if (o.guarantee) s.appendChild(el('div', { class: 'guarantee' }, o.guarantee));
    if (o.perks) {
      const ul = el('ul', { class: 'perks' });
      o.perks.forEach(p => ul.appendChild(el('li', { html: p })));
      s.appendChild(ul);
    }
    // source badges — the targeting: they already have a DNA file
    if (o.sources) {
      const b = el('div', {});
      o.sources.forEach(x => b.appendChild(el('span', { class: 'badge-src', html: x })));
      s.appendChild(b);
    }
    chrome(s, true);
    const primary = el('button', { class: 'cta', onclick: () => { T('checkout_start', { plan: o.plan || 'plus' });
      alert('Checkout (demo). Wire Stripe on web / Apple IAP in app. Event fired: checkout_start.'); } }, o.cta || 'Unlock my report');
    const upload = el('button', { class: 'cta ghost', onclick: () => { T('upload_click');
      alert('Upload flow (demo): drop your 23andMe / MyHeritage .txt or .zip. Event fired: upload_click.'); } },
      o.uploadCta || 'I already have my 23andMe file ›');
    app.appendChild(el('div', { class: 'sticky-cta' }, primary, upload,
      el('p', { class: 'fineprint', html: o.fine || 'Cancel anytime · Information, not medical advice · Your DNA is never sold.' })));
  }

  // ---- router ----------------------------------------------------------- //
  function render() {
    const id = seq[i];
    if (id === 'hero') return heroScreen();
    if (id.startsWith('q:')) return questionScreen(F.questions.find(q => 'q:' + q.id === id));
    if (id === 'analyzing') return analyzingScreen();
    if (id === 'result') return resultScreen();
    if (id === 'lead') return leadScreen();
    if (id === 'offer') return offerScreen();
  }

  render();
})();
