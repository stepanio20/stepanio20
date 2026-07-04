/* Галерея варианта: сначала РЕАЛЬНЫЕ фото (Pexels) из window.PHOTOS.
   Если фото не подгрузилось — тихо убираем его. Если у варианта не осталось
   ни одного фото, откатываемся на векторные тайлы (hero,a..j), затем на градиент. */
(function () {
  var path = location.pathname;
  var prefix = /recibidor/.test(path) ? 'recibidor' : /salon/.test(path) ? 'salon' : null;
  if (!prefix) return;
  var IMG = '../img/';
  var SVG_SUF = ['hero', 'a', 'b', 'c', 'd', 'e', 'f', 'g'];
  var PHOTOS = (window.PHOTOS && window.PHOTOS.variants) || {};

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

  document.querySelectorAll('article.variant').forEach(function (art) {
    var vid = art.id;
    if (!vid) return;
    var id = prefix + '-' + vid;
    var vis = art.querySelector('.v-visual');

    var g = document.createElement('div');
    g.className = 'v-gallery';
    var grid = document.createElement('div');
    grid.className = 'g-grid';
    g.appendChild(grid);
    var cap = document.createElement('div');
    cap.className = 'g-caption';
    cap.textContent = 'Первое фото — фотореалистичный рендер именно этой квартиры (Venice AI, по вашим фото). Далее — референсы. Нажмите, чтобы увеличить.';
    g.appendChild(cap);

    var state = { photos: 0, svg: 0 };

    function addImg(src, order) {
      var img = new Image();
      img.className = 'g-cell';
      img.alt = 'Визуализация';
      img.loading = 'lazy';
      img.style.order = order;
      img.addEventListener('load', function () {
        img.classList.add('on');
        if (vis) vis.style.display = 'none';
      });
      img.addEventListener('click', function () { openLb(img.src); });
      img.dataset.src = src;
      return img;
    }

    var urls = (PHOTOS[id] || []).slice();
    // Первым — фотореалистичный img2img-рендер именно этой квартиры (Venice),
    // затем стоковые фото-референсы. Битые молча убираем.
    var renders = (window.PHOTOS && window.PHOTOS.renders) || {};
    var rv = renders[id];
    if (rv) {
      var list = (typeof rv === 'string') ? [rv] : rv.slice();
      // добавляем в начало: -real первым, затем -real2, -real3
      for (var k = list.length - 1; k >= 0; k--) urls.unshift(IMG + list[k]);
    }
    urls.forEach(function (u, i) {
      var img = addImg(u, i);
      img.addEventListener('load', function () { state.photos++; });
      img.addEventListener('error', function () { img.remove(); });
      img.src = u;
      grid.appendChild(img);
    });

    // галерею вставляем только если есть что показывать
    if (urls.length) {
      if (vis) vis.insertAdjacentElement('beforebegin', g);
      else art.appendChild(g);
    }
  });
})();
