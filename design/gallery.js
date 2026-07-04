/* Галерея визуализаций: для каждого варианта вставляет hero + 3 детали.
   Если картинка ещё не сгенерирована (404) — тихо оставляет градиент-заглушку. */
(function () {
  var path = location.pathname;
  var prefix = /recibidor/.test(path) ? 'recibidor' : /salon/.test(path) ? 'salon' : null;
  if (!prefix) return;
  var IMG = '../img/';

  // лайтбокс (один на страницу)
  var lb = document.createElement('div');
  lb.className = 'lightbox';
  lb.innerHTML = '<img alt="">';
  lb.addEventListener('click', function () { lb.classList.remove('on'); });
  document.body.appendChild(lb);
  function zoom(src) { lb.firstChild.src = src; lb.classList.add('on'); }

  document.querySelectorAll('article.variant').forEach(function (art) {
    var vid = art.id; // v1..v6
    if (!vid) return;
    var id = prefix + '-' + vid;
    var vis = art.querySelector('.v-visual');
    if (!vis) return;

    var g = document.createElement('div');
    g.className = 'v-gallery';

    var hero = new Image();
    hero.className = 'g-hero';
    hero.alt = 'Визуализация: ' + art.querySelector('h2').textContent;
    hero.src = IMG + id + '-hero.svg';
    hero.style.cursor = 'zoom-in';
    hero.addEventListener('click', function () { zoom(hero.src); });

    var thumbs = document.createElement('div');
    thumbs.className = 'g-thumbs';
    ['a', 'b', 'c'].forEach(function (letter) {
      var t = new Image();
      t.alt = 'Деталь';
      t.src = IMG + id + '-' + letter + '.svg';
      t.addEventListener('click', function () { zoom(t.src); });
      t.addEventListener('error', function () { t.style.display = 'none'; });
      thumbs.appendChild(t);
    });

    var cap = document.createElement('div');
    cap.className = 'g-caption';
    cap.textContent = 'Иллюстрация-концепт (кликните, чтобы увеличить). Фотореалистичный рендер появится после подключения генерации.';

    g.appendChild(hero);
    g.appendChild(thumbs);
    g.appendChild(cap);

    // если hero загрузился — показываем галерею и прячем градиент-заглушку;
    // если нет — оставляем заглушку, галерею убираем.
    hero.addEventListener('load', function () { vis.style.display = 'none'; });
    hero.addEventListener('error', function () { g.remove(); });

    vis.insertAdjacentElement('beforebegin', g);
  });
})();
