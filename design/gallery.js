/* Галерея визуализаций варианта: показывает ВСЕ найденные тайлы (hero, a..j)
   в адаптивной сетке. Не зависит от наличия «главной» картинки — каждый тайл
   независим. Если ни один не загрузился — остаётся градиент-заглушка. */
(function () {
  var path = location.pathname;
  var prefix = /recibidor/.test(path) ? 'recibidor' : /salon/.test(path) ? 'salon' : null;
  if (!prefix) return;
  var IMG = '../img/';
  var SUF = ['hero', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'];

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
    cap.textContent = 'Концепт-визуализации варианта (нажмите, чтобы увеличить).';
    g.appendChild(cap);

    SUF.forEach(function (suf, idx) {
      var img = new Image();
      img.className = 'g-cell';
      img.alt = 'Визуализация';
      img.loading = 'lazy';
      img.style.order = idx;
      img.addEventListener('load', function () {
        img.classList.add('on');
        if (vis) vis.style.display = 'none';
      });
      img.addEventListener('error', function () { img.remove(); });
      img.addEventListener('click', function () { openLb(img.src); });
      img.src = IMG + id + '-' + suf + '.svg';
      grid.appendChild(img);
    });

    if (vis) vis.insertAdjacentElement('beforebegin', g);
    else art.appendChild(g);
  });
})();
