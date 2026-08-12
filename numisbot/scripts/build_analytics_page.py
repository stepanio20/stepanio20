"""Build the Katz archive analytics page from analyze_archive.py JSON."""
import json
import sys
import html as H

SP = "/tmp/claude-0/-home-user-stepanio20/1e8967c3-8e48-56fc-8f23-aec92ed4939f/scratchpad"
d = json.load(open(f"{SP}/report/analytics.json"))
fonts = open(f"{SP}/fonts/fonts_inline.css").read()

# validated categorical slots (dataviz skill reference palette)
CAT_L = {"Coins": "#2a78d6", "Gold": "#eb6834", "Paper Money": "#1baf7a"}
CAT_D = {"Coins": "#3987e5", "Gold": "#d95926", "Paper Money": "#199e70"}
KIND_ORDER = ["Coins", "Gold", "Paper Money"]


def fmt(n):
    return f"{n:,.0f}".replace(",", " ")


def esc(s):
    return H.escape(str(s), quote=True)


def hbar_rows(rows, name_key, val_key, sub_key=None, unit="€"):
    """Horizontal magnitude bars, one hue, direct value labels."""
    mx = max(r[val_key] for r in rows) or 1
    out = []
    for r in rows:
        w = 100 * r[val_key] / mx
        sub = f" · медиана €{fmt(r[sub_key])}" if sub_key else ""
        out.append(f"""
    <div class="hb" data-tip="{esc(r[name_key])}: {unit}{fmt(r[val_key])} ({r['sold']} лотов{esc(sub)})">
      <div class="hb-name">{esc(r[name_key])}</div>
      <div class="hb-track"><div class="hb-fill" style="width:{w:.1f}%"></div></div>
      <div class="hb-val">{unit}{fmt(r[val_key])}</div>
    </div>""")
    return "".join(out)


def vbars(items, label_key, val_key, tip_fmt):
    """Vertical magnitude bars (histogram), one hue."""
    mx = max(i[val_key] for i in items) or 1
    cells = []
    for i in items:
        hpct = 100 * i[val_key] / mx
        cells.append(f"""
      <div class="vb" data-tip="{esc(tip_fmt.format(**i))}">
        <div class="vb-val">{fmt(i[val_key])}</div>
        <div class="vb-track"><div class="vb-fill" style="height:{hpct:.1f}%"></div></div>
        <div class="vb-lab">{esc(i[label_key])}</div>
      </div>""")
    return "".join(cells)


kinds = d["by_kind"]
kind_bars = []
for k in KIND_ORDER:
    if k not in kinds:
        continue
    v = kinds[k]
    kind_bars.append(f"""
    <div class="kind" data-tip="{k}: продано {v['sold']} из {v['lots']} ({v['sell_through_pct']}%), молот €{fmt(v['hammer_eur'])}, медиана €{fmt(v['median_eur'])}">
      <div class="kind-head"><span class="dot dot-{k.split()[0].lower()}"></span><b>{k}</b></div>
      <div class="kind-st"><div class="kind-fill kf-{k.split()[0].lower()}" style="width:{v['sell_through_pct']}%"></div></div>
      <div class="kind-meta"><span class="num">{v['sell_through_pct']}%</span> sell-through · {v['sold']}/{v['lots']} лотов<br>
      молот <b>€{fmt(v['hammer_eur'])}</b> · медиана <b>€{fmt(v['median_eur'])}</b></div>
    </div>""")

top_lots_rows = "".join(
    f"""<tr><td>{i+1}</td><td><a href="{esc(l['url'])}">{esc(l['title'][:80])}</a></td>
    <td>{esc(l['country'])}</td><td class="num">€{fmt(l['realized_eur'])}</td></tr>"""
    for i, l in enumerate(d["top_lots"])
)

metals = list(d["metal_hammer_eur"].items())[:5]
metal_rows = hbar_rows(
    [{"name": k, "hammer_eur": v, "sold": ""} for k, v in metals],
    "name", "hammer_eur",
)

page = f"""<title>Katz Archive Analytics</title>
<style>
{fonts}
:root {{
  --bg:#FAF6F1; --bg-raise:#FFFFFF; --ink:#201915; --ink-soft:#5C5049;
  --line:#E4D8CE; --accent:#B8836B; --accent-strong:#96613F; --accent-soft:#F1E2D8;
  --bar:#2a78d6; --coins:#2a78d6; --gold:#eb6834; --paper:#1baf7a; --track:#EDE3D9;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#131110; --bg-raise:#1C1917; --ink:#EDE4DD; --ink-soft:#A99C92;
    --line:#35302C; --accent:#DCAC98; --accent-strong:#E7C1AF; --accent-soft:#2A211C;
    --bar:#3987e5; --coins:#3987e5; --gold:#d95926; --paper:#199e70; --track:#2A2622;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#131110; --bg-raise:#1C1917; --ink:#EDE4DD; --ink-soft:#A99C92;
  --line:#35302C; --accent:#DCAC98; --accent-strong:#E7C1AF; --accent-soft:#2A211C;
  --bar:#3987e5; --coins:#3987e5; --gold:#d95926; --paper:#199e70; --track:#2A2622;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font-family:'Raleway','Segoe UI',system-ui,sans-serif; font-size:15px; line-height:1.55; }}
.wrap {{ max-width:960px; margin:0 auto; padding:46px 26px 80px; }}
h1,h2 {{ font-family:'Oswald','Arial Narrow',sans-serif; font-weight:500; line-height:1.2; text-wrap:balance; }}
h1 {{ font-size:clamp(28px,5vw,42px); margin:6px 0 10px; }}
h2 {{ font-size:22px; margin:44px 0 6px; }}
.eyebrow {{ font-family:'Oswald',sans-serif; letter-spacing:.38em; text-transform:uppercase;
  font-size:11.5px; color:var(--accent-strong); }}
.sub {{ color:var(--ink-soft); max-width:640px; }}
.note {{ font-size:12.5px; color:var(--ink-soft); margin-top:6px; }}
.num {{ font-variant-numeric:tabular-nums; }}
a {{ color:var(--accent-strong); }}

.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:26px 0 8px; }}
.tile {{ border:1px solid var(--line); background:var(--bg-raise); border-radius:6px; padding:14px 16px 12px; }}
.tile b {{ display:block; font-family:'Oswald',sans-serif; font-weight:500; font-size:27px;
  color:var(--accent-strong); font-variant-numeric:tabular-nums; }}
.tile span {{ font-size:12.5px; color:var(--ink-soft); display:block; margin-top:3px; line-height:1.4; }}

.panel {{ border:1px solid var(--line); background:var(--bg-raise); border-radius:8px; padding:18px 20px; margin:14px 0; }}

.kinds {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; }}
.kind-head {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
.dot {{ width:11px; height:11px; border-radius:3px; display:inline-block; }}
.dot-coins {{ background:var(--coins); }} .dot-gold {{ background:var(--gold); }} .dot-paper {{ background:var(--paper); }}
.kind-st {{ height:14px; border-radius:4px; background:var(--track); overflow:hidden; }}
.kind-fill {{ height:100%; border-radius:4px 0 0 4px; }}
.kf-coins {{ background:var(--coins); }} .kf-gold {{ background:var(--gold); }} .kf-paper {{ background:var(--paper); }}
.kind-meta {{ font-size:12.5px; color:var(--ink-soft); margin-top:7px; }}
.kind-meta .num {{ font-size:16px; color:var(--ink); font-weight:700; }}

.vchart {{ display:flex; align-items:stretch; gap:6px; height:230px; margin-top:10px; }}
.vb {{ flex:1; display:flex; flex-direction:column; justify-content:flex-end; min-width:0; }}
.vb-val {{ font-size:11px; color:var(--ink-soft); text-align:center; margin-bottom:3px; font-variant-numeric:tabular-nums; }}
.vb-track {{ flex:0 0 auto; height:160px; display:flex; align-items:flex-end; }}
.vb-fill {{ width:100%; background:var(--bar); border-radius:4px 4px 0 0; min-height:2px; }}
.vb-lab {{ font-size:10.5px; color:var(--ink-soft); text-align:center; margin-top:6px;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.vb:hover .vb-fill {{ opacity:.82; }}

.hb {{ display:grid; grid-template-columns:minmax(120px,220px) 1fr 90px; gap:10px; align-items:center; padding:4px 0; }}
.hb-name {{ font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.hb-track {{ height:13px; background:var(--track); border-radius:4px; overflow:hidden; }}
.hb-fill {{ height:100%; background:var(--bar); border-radius:4px 0 0 4px; min-width:2px; }}
.hb-val {{ font-size:12.5px; text-align:right; font-variant-numeric:tabular-nums; color:var(--ink-soft); }}
.hb:hover .hb-fill {{ opacity:.82; }}

.tscroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:13.5px; min-width:560px; }}
th {{ text-align:left; font-family:'Oswald',sans-serif; font-weight:500; font-size:12px;
  letter-spacing:.07em; text-transform:uppercase; color:var(--accent-strong);
  padding:8px 10px; border-bottom:2px solid var(--accent); }}
td {{ padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
tr:last-child td {{ border-bottom:none; }}

#tip {{ position:fixed; pointer-events:none; background:var(--ink); color:var(--bg);
  font-size:12.5px; padding:6px 10px; border-radius:6px; max-width:340px; z-index:10;
  opacity:0; transition:opacity .08s; line-height:1.4; }}
</style>

<div class="wrap">
  <div class="eyebrow">Katz Coins Radar · Демо Dealer-аналитики</div>
  <h1>Что реально продаётся на Katz: цифры из архива</h1>
  <p class="sub">Живой срез по {d['auctions']} последним завершённым аукционам
  ({fmt(d['lots'])} лотов), выкачанный вежливым парсером бота из публичного API
  katzauction.com. Это та самая аналитика спроса, которую получает Dealer-тир — и
  аргумент в разговоре с самим домом.</p>

  <div class="tiles">
    <div class="tile"><b>{fmt(d['lots'])}</b><span>лотов в срезе ({d['auctions']} аукционов)</span></div>
    <div class="tile"><b>{d['sell_through_pct']}%</b><span>sell-through: {fmt(d['sold'])} лотов продано</span></div>
    <div class="tile"><b>€{fmt(d['hammer_total_eur'])}</b><span>суммарный молот (без 24% премии покупателя)</span></div>
    <div class="tile"><b>€{fmt(d['median_eur'])}</b><span>медианная цена продажи (средняя €{fmt(d['mean_eur'])})</span></div>
  </div>
  <p class="note">Молот-цены: без buyer's premium. GMV дома с премией ≈ на четверть выше.</p>

  <h2>Три конвейера дома</h2>
  <p class="sub">Sell-through и деньги по типам аукционов цикла Coins → Gold → Paper Money.</p>
  <div class="panel"><div class="kinds">{''.join(kind_bars)}</div></div>

  <h2>Где лежат деньги: распределение цен продажи</h2>
  <p class="sub">Число проданных лотов по ценовым корзинам, EUR (молот).</p>
  <div class="panel"><div class="vchart">{vbars(d['price_histogram'], 'bin', 'count', '€{bin}: {count} лотов')}</div></div>

  <h2>Топ-категорий по обороту</h2>
  <div class="panel">{hbar_rows(d['top_categories'], 'name', 'hammer_eur', 'median_eur')}</div>

  <h2>Топ-стран по обороту</h2>
  <div class="panel">{hbar_rows(d['top_countries'], 'name', 'hammer_eur', 'median_eur')}</div>

  <h2>Металл в проданных лотах (из заголовков)</h2>
  <div class="panel">{metal_rows}
  <p class="note">Металл извлечён регулярками из title/description — «Other/unspecified» означает, что металл в заголовке не указан (банкноты, награды, часть монет).</p></div>

  <h2>Самые дорогие проходы среза</h2>
  <div class="panel tscroll"><table>
    <tr><th>#</th><th>Лот</th><th>Страна</th><th>Молот</th></tr>
    {top_lots_rows}
  </table></div>

  <p class="note" style="margin-top:34px">Источник: публичный API katzauction.com, выкачано
  скриптом numisbot/scripts/backfill.py (1 запрос/сек). Агрегация — scripts/analyze_archive.py.
  Дата среза: 11.08.2026.</p>
</div>

<div id="tip"></div>
<script>
const tip = document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el => {{
  el.addEventListener('mousemove', e => {{
    tip.textContent = el.dataset.tip;
    tip.style.opacity = 1;
    const x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    const y = Math.min(e.clientY + 16, window.innerHeight - tip.offsetHeight - 8);
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }});
  el.addEventListener('mouseleave', () => tip.style.opacity = 0);
}});
</script>
"""
out = f"{SP}/report/katz_analytics.html"
open(out, "w").write(page)
print("written", out, len(page) // 1024, "KB")
