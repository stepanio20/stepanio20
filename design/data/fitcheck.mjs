// Fit-check: проверяет каталог мебели против floorplan.json
// node fitcheck.mjs catalog.json
import { readFileSync } from 'fs';
const fp = JSON.parse(readFileSync(new URL('./floorplan.json', import.meta.url)));
const cat = JSON.parse(readFileSync(process.argv[2] || './catalog.json', 'utf8'));
const issues = [];
for (const c of cat.catalogs || []) {
  const room = fp[c.room]; if (!room) continue;
  const maxH = room.constraints?.max_furniture_h_cm ?? (room.ceiling_cm - 12);
  const maxD = room.constraints?.max_depth_along_corridor_cm;
  for (const t of c.tiers || []) for (const it of t.items || []) {
    const tag = `${c.room}/${c.style}/${t.tier}: ${it.name}`;
    // шторы/текстиль вешаются под потолок — длина полотна не «высота мебели»
    const soft = /штор|гардин|текстил|плед|ковер|ковёр/i.test(it.category || '');
    if (!soft && it.h_cm > maxH) issues.push(`ВЫСОТА ${tag} — ${it.h_cm} см > лимита ${maxH} (потолок ${room.ceiling_cm})`);
    if (soft && it.h_cm > room.ceiling_cm) issues.push(`ТЕКСТИЛЬ ${tag} — ${it.h_cm} см длиннее потолка ${room.ceiling_cm}`);
    if (c.room === 'recibidor' && maxD && it.d_cm > maxD && it.h_cm > 60)
      issues.push(`ГЛУБИНА ${tag} — ${it.d_cm} см > ${maxD} (узкий проход)`);
    if (c.room === 'recibidor' && it.w_cm > 350)
      issues.push(`ШИРИНА ${tag} — ${it.w_cm} см шире самой длинной стены (350)`);
    if (c.room === 'salon' && it.w_cm > 440 && it.h_cm > 5)
      issues.push(`ШИРИНА ${tag} — ${it.w_cm} см не встанет вдоль ТВ-стены (440)`);
  }
}
console.log(issues.length ? issues.join('\n') : 'FIT-CHECK: все предметы проходят по габаритам');
process.exit(issues.length ? 1 : 0);
