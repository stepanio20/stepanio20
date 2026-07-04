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
    cap.textContent = 'Референс-фото в стиле варианта (нажмите, чтобы увеличить). Фото — Pexels.';
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

    var urls = PHOTOS[id] || [];
    if (urls.length) {
      urls.forEach(function (u, i) {
        var img = addImg(u, i);
        img.addEventListener('load', function () { state.photos++; });
        img.addEventListener('error', function () {
          img.remove();
          // если реальных фото не осталось — подтягиваем вектор как запас
          if (grid.querySelectorAll('img').length === 0) loadSvgFallback();
        });
        img.src = u;
        grid.appendChild(img);
      });
    } else {
      loadSvgFallback();
    }

    function loadSvgFallback() {
      if (state.svg) return; state.svg = 1;
      SVG_SUF.forEach(function (suf, i) {
        var img = addImg(IMG + id + '-' + suf + '.svg', 100 + i);
        img.addEventListener('error', function () { img.remove(); });
        img.src = IMG + id + '-' + suf + '.svg';
        grid.appendChild(img);
      });
    }

    if (vis) vis.insertAdjacentElement('beforebegin', g);
    else art.appendChild(g);
  });
})();
