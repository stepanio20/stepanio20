/* Мини-рендерер поэтажных планов (SVG). Масштаб: 80 px = 1 м. */
(function () {
  var S = 80, PAD = 40, NS = 'http://www.w3.org/2000/svg';

  function el(name, attrs, parent) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function text(parent, x, y, str, cls, size) {
    var lines = str.split('\n');
    var t = el('text', { x: x, y: y, 'class': cls || '', 'font-size': size || 10.5,
      'text-anchor': 'middle', 'dominant-baseline': 'middle' }, parent);
    for (var i = 0; i < lines.length; i++) {
      el('tspan', { x: x, dy: i === 0 ? (-(lines.length - 1) * 5.5) : 11 }, t)
        .textContent = lines[i];
    }
    return t;
  }

  /* координаты точки на стороне: side top|bottom|left|right, m — метры от угла */
  function sidePt(spec, side, m) {
    var W = spec.w * S, H = spec.h * S;
    if (side === 'top') return { x: PAD + m * S, y: PAD };
    if (side === 'bottom') return { x: PAD + m * S, y: PAD + H };
    if (side === 'left') return { x: PAD, y: PAD + m * S };
    return { x: PAD + W, y: PAD + m * S };
  }

  window.drawPlan = function (id, spec) {
    var art = document.getElementById(id);
    if (!art) return;
    var host = document.createElement('div');
    host.className = 'v-plan';
    var vis = art.querySelector('.v-visual');
    if (vis) vis.insertAdjacentElement('afterend', host);
    else art.appendChild(host);
    var W = spec.w * S, H = spec.h * S;
    var svg = el('svg', {
      viewBox: '0 0 ' + (W + PAD * 2) + ' ' + (H + PAD * 2),
      'class': 'floorplan', role: 'img',
      'aria-label': 'План расстановки мебели'
    });

    /* пол */
    el('rect', { x: PAD, y: PAD, width: W, height: H, fill: '#f7f3ec' }, svg);

    /* зоны (ковры и т.п.) — под мебелью */
    (spec.items || []).forEach(function (it) {
      if (it.t !== 'zone') return;
      el('rect', { x: PAD + it.x * S, y: PAD + it.y * S, width: it.w * S, height: it.h * S,
        rx: 8, fill: 'none', stroke: '#b3a894', 'stroke-width': 1.6,
        'stroke-dasharray': '6 5' }, svg);
      text(svg, PAD + (it.x + it.w / 2) * S, PAD + (it.y + it.h / 2) * S + (it.dy || 0) * S,
        it.l, 'fp-zone', 10);
    });

    /* стены */
    el('rect', { x: PAD, y: PAD, width: W, height: H, fill: 'none',
      stroke: '#2a251f', 'stroke-width': 7 }, svg);

    /* особенности стен */
    (spec.walls || []).forEach(function (w) {
      var a = sidePt(spec, w.side, w.from), b = sidePt(spec, w.side, w.to);
      var horiz = (w.side === 'top' || w.side === 'bottom');
      var outward = (w.side === 'top' || w.side === 'left') ? -1 : 1;
      if (w.type === 'opening' || w.type === 'door') {
        el('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y,
          stroke: '#f7f3ec', 'stroke-width': 9 }, svg);
        el('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: '#a49b8d',
          'stroke-width': 1.6, 'stroke-dasharray': w.type === 'opening' ? '7 5' : 'none' }, svg);
        if (w.type === 'door') {
          var r = Math.abs((w.to - w.from)) * S;
          var sweep = horiz
            ? 'M ' + a.x + ' ' + a.y + ' A ' + r + ' ' + r + ' 0 0 ' + (outward === -1 ? 0 : 1) + ' ' + (a.x + r) + ' ' + (a.y - outward * r)
            : 'M ' + a.x + ' ' + a.y + ' A ' + r + ' ' + r + ' 0 0 ' + (outward === -1 ? 1 : 0) + ' ' + (a.x - outward * r) + ' ' + (a.y + r);
          el('path', { d: sweep, fill: 'none', stroke: '#a49b8d', 'stroke-width': 1.2 }, svg);
        }
      } else if (w.type === 'window') {
        el('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: '#f7f3ec', 'stroke-width': 7 }, svg);
        el('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: '#7fa8b8', 'stroke-width': 3 }, svg);
      } else if (w.type === 'mirror') {
        el('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: '#9fc4c9',
          'stroke-width': 3, 'stroke-dasharray': '2 3',
        }, svg);
      }
      if (w.l) {
        var mx = (a.x + b.x) / 2 + (horiz ? 0 : outward * 16);
        var my = (a.y + b.y) / 2 + (horiz ? outward * 15 : 0);
        var t = text(svg, mx, my, w.l, 'fp-wall', 9.5);
        if (!horiz) t.setAttribute('transform', 'rotate(' + (outward === -1 ? -90 : 90) + ' ' + mx + ' ' + my + ')');
      }
    });

    /* мебель */
    (spec.items || []).forEach(function (it) {
      if (it.t === 'zone') return;
      var isNew = it.t === 'new';
      var fill = isNew ? 'rgba(194,69,45,.13)' : '#e9e3d8';
      var stroke = isNew ? '#c2452d' : '#b3a894';
      if (it.shape === 'circle') {
        el('circle', { cx: PAD + it.x * S, cy: PAD + it.y * S, r: (it.w / 2) * S,
          fill: fill, stroke: stroke, 'stroke-width': isNew ? 2 : 1.4 }, svg);
        text(svg, PAD + it.x * S, PAD + it.y * S + (it.dy || 0) * S, it.l,
          isNew ? 'fp-new' : 'fp-keep', it.fs || 9.5);
      } else {
        el('rect', { x: PAD + it.x * S, y: PAD + it.y * S, width: it.w * S, height: it.h * S,
          rx: 6, fill: fill, stroke: stroke, 'stroke-width': isNew ? 2 : 1.4 }, svg);
        text(svg, PAD + (it.x + it.w / 2) * S, PAD + (it.y + it.h / 2) * S + (it.dy || 0) * S,
          it.l, isNew ? 'fp-new' : 'fp-keep', it.fs || 9.5);
      }
    });

    host.appendChild(svg);
    var lg = document.createElement('div');
    lg.className = 'plan-legend';
    lg.textContent = spec.legend ||
      'План расстановки · серое — остаётся · охра — купить · пунктир — ковёр/зона';
    host.appendChild(lg);
  };
})();
