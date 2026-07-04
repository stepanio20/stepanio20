/* Галерея варианта: блок «ДО → ПОСЛЕ» (реальное фото квартиры → рендер с мебелью
   этого варианта), затем остальные ракурсы рендера. Ниже на странице — список
   мебели и описание. Показываются только реальные изображения; битые убираются. */
(function () {
  var path = location.pathname;
  var prefix = /recibidor/.test(path) ? 'recibidor' : /salon/.test(path) ? 'salon' : null;
  if (!prefix) return;
  var IMG = '../img/';
  var P = window.PHOTOS || {};
  var RENDERS = P.renders || {};
  var STOCK = P.variants || {};
  var BEFORE = (P.before || {})[prefix];

  function lb(src) {
    var el = document.querySelector('.lightbox');
    if (!el) {
      el = document.createElement('div'); el.className = 'lightbox';
      el.innerHTML = '<img alt="">';
      el.addEventListener('click', function () { el.classList.remove('on'); });
      document.body.appendChild(el);
    }
    el.querySelector('img').src = src; el.classList.add('on');
  }

  function fig(src, label, cls) {
    var f = document.createElement('figure');
    f.className = 'ga-fig ' + (cls || '');
    var im = new Image();
    im.className = 'ga-img'; im.alt = label || ''; im.loading = 'lazy';
    im.addEventListener('click', function () { lb(im.src); });
    im.addEventListener('error', function () { f.remove(); });
    im.src = src;
    f.appendChild(im);
    if (label) {
      var c = document.createElement('figcaption'); c.className = 'ga-cap'; c.textContent = label;
      f.appendChild(c);
    }
    return f;
  }

  document.querySelectorAll('article.variant').forEach(function (art) {
    var vid = art.id; if (!vid) return;
    var id = prefix + '-' + vid;
    var vis = art.querySelector('.v-visual');

    // список рендеров этого варианта (свой дом + мебель варианта)
    var rv = RENDERS[id];
    var renders = rv ? (typeof rv === 'string' ? [rv] : rv.slice()) : [];
    // добавим доп. ракурсы real2/real3, если это одиночная строка
    if (rv && typeof rv === 'string') {
      ['-real2', '-real3'].forEach(function (suf) {
        renders.push(id + suf + '.webp'); // проверятся onerror
      });
      // rv уже "id-real.webp"; убираем дубли
    }
    var renderUrls = renders.map(function (f) { return IMG + f; });

    if (!renderUrls.length && !BEFORE) return;

    var g = document.createElement('div');
    g.className = 'v-gallery';

    // блок ДО → ПОСЛЕ
    var ba = document.createElement('div');
    ba.className = 'ba';
    if (BEFORE) ba.appendChild(fig(IMG + BEFORE, 'До — ваша квартира сейчас', 'ba-before'));
    if (renderUrls.length) ba.appendChild(fig(renderUrls[0], 'После — с мебелью этого варианта', 'ba-after'));
    g.appendChild(ba);

    // остальные ракурсы
    var rest = renderUrls.slice(1);
    if (rest.length) {
      var grid = document.createElement('div'); grid.className = 'g-grid';
      rest.forEach(function (u, i) {
        var im = new Image();
        im.className = 'g-cell'; im.alt = 'Ракурс'; im.loading = 'lazy'; im.style.order = i;
        im.addEventListener('click', function () { lb(im.src); });
        im.addEventListener('error', function () { im.remove(); });
        im.src = u; grid.appendChild(im);
      });
      g.appendChild(grid);
    }

    var cap = document.createElement('div');
    cap.className = 'g-caption';
    cap.textContent = 'Слева — ваша квартира сейчас, справа и ниже — как будет с предложенной мебелью (рендеры Venice AI по вашим фото). Нажмите, чтобы увеличить.';
    g.appendChild(cap);

    if (vis) { vis.style.display = 'none'; vis.insertAdjacentElement('beforebegin', g); }
    else art.appendChild(g);
  });
})();
