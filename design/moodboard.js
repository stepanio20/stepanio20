/* Секция «Референсы / концепт-борд»: коллаж мудборд-тайлов + палитра материалов
   + кураторские ссылки. Вставляется на страницу комнаты перед навигацией по вариантам. */
(function () {
  var path = location.pathname;
  var prefix = /recibidor/.test(path) ? 'recibidor' : /salon/.test(path) ? 'salon' : null;
  if (!prefix) return;
  var IMG = '../img/';

  var DATA = {
    salon: {
      intro: 'Настроение проекта: тёплый japandi с лофт-характером и коллекционерским ' +
        'ретро-акцентом 70-х. Светлый дуб и орех, олива, хром, бумажный свет, ноль красного. ' +
        'Ниже — концепт-борд, палитра материалов и подборки живых референсов.',
      tiles: ['mood-salon-1', 'mood-salon-2', 'mood-salon-3', 'mood-salon-4', 'mood-salon-5'],
      refs: [
        { l: 'Japandi гостиная · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=japandi%20living%20room%20light%20oak' },
        { l: 'Ретро 70-х · орех + олива · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=70s%20living%20room%20walnut%20olive%20green' },
        { l: 'Camaleonda styling · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=camaleonda%20sofa%20interior' },
        { l: 'Гоночная арт-стена (F1) · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=motorsport%20poster%20gallery%20wall%20interior' },
        { l: 'F1 gallery-wall в чёрных рамах · Poster Store', u: 'https://posterstore.com/g/p/gallery-wall-inspiration/race-car-gallery-wall-with-photographs-and-illustrations-of-formula-1-cars-with-black-wood-frames-for-the-living-room/' },
        { l: 'Camaleonda: 11 интерьеров · Elle Decoration', u: 'https://www.elledecoration.co.uk/inspiration/living-dining/a65087974/camaleonda-seating-ideas/' },
        { l: 'Выпуклое зеркало-сфера · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=convex%20bubble%20mirror%20interior%20akari%20lamp' },
        { l: 'Japandi · Unsplash', u: 'https://unsplash.com/s/photos/japandi-interior' }
      ]
    },
    recibidor: {
      intro: 'Настроение проекта: вход как маленький бутик — витрина с подсветкой под сумки, ' +
        'закрытое хранение обуви, зеркало в рост, тёплый дуб и натуральные фактуры. ' +
        'Ниже — концепт-борд, палитра материалов и подборки живых референсов.',
      tiles: ['mood-recibidor-1', 'mood-recibidor-2', 'mood-recibidor-3', 'mood-recibidor-4', 'mood-recibidor-5'],
      refs: [
        { l: 'Бутик-прихожая · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=luxury%20entryway%20display%20cabinet%20handbags' },
        { l: 'Витрина для сумок с LED · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=glass%20display%20cabinet%20bags%20led%20light' },
        { l: 'Хранение обуви japandi · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=japandi%20entryway%20shoe%20storage' },
        { l: 'Зеркало в рост + консоль · Pinterest', u: 'https://www.pinterest.com/search/pins/?q=full%20length%20mirror%20console%20entryway' },
        { l: 'Recibidor moderno · Unsplash', u: 'https://unsplash.com/s/photos/modern-entryway' }
      ]
    }
  };

  var PALETTE = [
    { n: 'Дуб', c: 'linear-gradient(135deg,#d8c19a,#c8a87c)' },
    { n: 'Орех', c: 'linear-gradient(135deg,#6d5138,#4a3624)' },
    { n: 'Олива', c: 'linear-gradient(135deg,#8a8c62,#63654a)' },
    { n: 'Крем', c: '#f7f3ec' },
    { n: 'Графит', c: 'linear-gradient(135deg,#3d3a36,#2a2724)' },
    { n: 'Хром', c: 'linear-gradient(135deg,#e3e1dc,#9a968f)' },
    { n: 'Амбра', c: 'linear-gradient(135deg,#cf9f5c,#8a5a20)' },
    { n: 'Песок', c: '#e8dcc6' }
  ];
  var MATERIALS = ['Дуб · шпон', 'Орех', 'Оливковый бархат', 'Лён', 'Букле', 'Джут', 'Шлифованный хром', 'Стекло'];

  var d = DATA[prefix];
  var wrap = document.querySelector('.wrap .variant-nav');
  if (!wrap) return;
  var host = wrap.parentNode;

  var sec = document.createElement('section');
  sec.className = 'moodboard';
  sec.innerHTML =
    '<div class="mb-head"><span class="mb-kicker">Референсы · концепт-борд</span>' +
    '<p class="mb-intro">' + d.intro + '</p></div>';

  // коллаж
  var collage = document.createElement('div');
  collage.className = 'mb-collage';
  d.tiles.forEach(function (id, i) {
    var fig = document.createElement('figure');
    fig.className = 'mb-tile mb-tile-' + (i % 5);
    var img = new Image();
    img.alt = 'Референс';
    img.loading = 'lazy';
    img.src = IMG + id + '.svg';
    img.addEventListener('error', function () { fig.style.display = 'none'; });
    img.addEventListener('click', function () { openLb(img.src); });
    fig.appendChild(img);
    collage.appendChild(fig);
  });
  sec.appendChild(collage);

  // палитра
  var pal = document.createElement('div');
  pal.className = 'mb-block';
  pal.innerHTML = '<h4>Палитра и материалы</h4>';
  var sw = document.createElement('div'); sw.className = 'mb-palette';
  PALETTE.forEach(function (p) {
    var s = document.createElement('div'); s.className = 'mb-swatch';
    s.innerHTML = '<i style="background:' + p.c + '"></i><span>' + p.n + '</span>';
    sw.appendChild(s);
  });
  pal.appendChild(sw);
  var mat = document.createElement('div'); mat.className = 'mb-materials';
  MATERIALS.forEach(function (m) {
    var c = document.createElement('span'); c.className = 'mb-chip'; c.textContent = m;
    mat.appendChild(c);
  });
  pal.appendChild(mat);
  sec.appendChild(pal);

  // ссылки-референсы
  var refs = document.createElement('div');
  refs.className = 'mb-block';
  refs.innerHTML = '<h4>Живые подборки референсов</h4>';
  var rl = document.createElement('div'); rl.className = 'mb-refs';
  d.refs.forEach(function (r) {
    var a = document.createElement('a');
    a.className = 'mb-ref'; a.href = r.u; a.target = '_blank'; a.rel = 'noopener';
    a.textContent = r.l + ' ↗';
    rl.appendChild(a);
  });
  refs.appendChild(rl);
  sec.appendChild(refs);

  host.insertBefore(sec, wrap);

  // лайтбокс (переиспользуем, если создан gallery.js)
  function openLb(src) {
    var lb = document.querySelector('.lightbox');
    if (!lb) {
      lb = document.createElement('div');
      lb.className = 'lightbox';
      lb.innerHTML = '<img alt="">';
      lb.addEventListener('click', function () { lb.classList.remove('on'); });
      document.body.appendChild(lb);
    }
    lb.querySelector('img').src = src;
    lb.classList.add('on');
  }
})();
