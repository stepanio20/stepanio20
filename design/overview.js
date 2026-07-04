/* Плиточный обзор вариантов: наверху страницы комнаты — сетка плиток с
   заголовком, палитрой, ценой и коротким описанием. Тап по плитке →
   разворачивает и прокручивает к подробному варианту. Работает офлайн. */
(function () {
  var variants = Array.prototype.slice.call(document.querySelectorAll('article.variant'));
  if (!variants.length) return;
  var navWrap = document.querySelector('.wrap .variant-nav');
  if (!navWrap) return;

  var photos = (window.PHOTOS && window.PHOTOS.variants) || {};
  var prefix = /recibidor/.test(location.pathname) ? 'recibidor'
    : /salon/.test(location.pathname) ? 'salon' : '';

  var sec = document.createElement('section');
  sec.className = 'ov';
  sec.innerHTML = '<div class="ov-head"><span class="ov-kicker">Варианты — нажмите плитку</span>' +
    '<p class="ov-sub">Сначала обзор всех решений, потом откройте любой — там визуализации, ' +
    'палитра и ссылки на каждый предмет.</p></div>';
  var grid = document.createElement('div');
  grid.className = 'ov-grid';
  sec.appendChild(grid);

  variants.forEach(function (art) {
    var vid = art.id;
    var num = (art.querySelector('.v-num') || {}).textContent || '';
    var title = (art.querySelector('.v-head h2') || {}).textContent || '';
    var descEl = art.querySelector('.v-desc');
    var desc = descEl ? descEl.textContent.replace(/\s+/g, ' ').trim() : '';
    if (desc.length > 110) desc = desc.slice(0, 108).replace(/[\s,.;—-]+\S*$/, '') + '…';
    var price = (art.querySelector('.v-total b') || {}).textContent || '';
    var pal = art.querySelectorAll('.palette i');

    var card = document.createElement('a');
    card.className = 'ov-card';
    card.href = '#' + vid;

    // мини-превью: пробуем первое реальное фото, иначе — палитра-градиент
    var thumb = document.createElement('div');
    thumb.className = 'ov-thumb';
    var cols = [];
    pal.forEach(function (i) { cols.push(i.style.background || '#e8e1d6'); });
    thumb.style.background = cols.length
      ? 'linear-gradient(135deg,' + cols.join(',') + ')'
      : '#e8e1d6';
    var renders = (window.PHOTOS && window.PHOTOS.renders) || {};
    var thumbSrc = renders[prefix + '-' + vid]
      ? '../img/' + renders[prefix + '-' + vid]
      : (photos[prefix + '-' + vid] || [])[0];
    if (thumbSrc) {
      var im = new Image();
      im.className = 'ov-thumb-img';
      im.alt = title;
      im.loading = 'lazy';
      im.addEventListener('load', function () { thumb.appendChild(im); });
      im.src = thumbSrc;
    }

    var pals = '<div class="ov-pal">' + cols.map(function (c) {
      return '<i style="background:' + c + '"></i>';
    }).join('') + '</div>';

    card.innerHTML = '';
    card.appendChild(thumb);
    var body = document.createElement('div');
    body.className = 'ov-body';
    body.innerHTML =
      '<span class="ov-num">' + num + '</span>' +
      '<h3>' + title + '</h3>' +
      pals +
      '<p>' + desc + '</p>' +
      '<div class="ov-foot"><span class="ov-price">' + price + '</span>' +
      '<span class="ov-go">Смотреть →</span></div>';
    card.appendChild(body);

    // плавная прокрутка + подсветка целевого варианта
    card.addEventListener('click', function (e) {
      var target = document.getElementById(vid);
      if (!target) return;
      e.preventDefault();
      target.classList.add('flash');
      setTimeout(function () { target.classList.remove('flash'); }, 1400);
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState(null, '', '#' + vid);
    });

    grid.appendChild(card);
  });

  navWrap.parentNode.insertBefore(sec, navWrap);
})();
