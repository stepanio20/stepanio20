"""Valuation by realized-price comparables from the local archive.

Keyword-match approach (no vision): pull candidates by the first significant
word, then require the rest of the words in the title, relaxing from the tail
until enough comparables are found. Returns quartile range + median — the
honest "what similar items actually fetched at Katz" number.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

_STOP = {
    "монета", "монеты", "монету", "банкнота", "медаль", "орден", "coin", "coins",
    "banknote", "medal", "order", "the", "and", "for", "with", "года", "год",
    "серебро", "золото", "медь", "silver", "gold", "copper",  # metals match too broadly
    "состояние", "сохран", "оригинал", "редкая", "редкий", "rare",
}


# Katz catalog is English-only; map/transliterate Cyrillic numismatic terms
_RU_TERMS = {
    "россия": "russia", "российская": "russia", "империя": "empire",
    "рубль": "rouble", "рубля": "rouble", "рублей": "roubles",
    "копейка": "kopek", "копейки": "kopeks", "копеек": "kopeks",
    "полтина": "poltina", "полуполтинник": "polupoltinnik",
    "червонец": "chervonets", "гривенник": "grivennik", "деньга": "denga",
    "талер": "taler", "злотый": "zlotych", "злотых": "zlotych",
    "австрия": "austria", "германия": "germany", "польша": "poland",
    "франция": "france", "англия": "britain", "сша": "usa", "китай": "china",
    "золото": "gold", "серебро": "silver", "николай": "nicholas",
    "александр": "alexander", "екатерина": "catherine", "пётр": "peter",
    "петр": "peter", "павел": "paul", "елизавета": "elizabeth",
}
_TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})


def _to_catalog(word: str) -> str:
    if word in _RU_TERMS:
        return _RU_TERMS[word]
    if re.search(r"[а-яё]", word):
        return word.translate(_TRANSLIT)
    return word


def keywords(text: str, limit: int = 6) -> list[str]:
    words = re.findall(r"[^\W_]+", text.lower(), re.UNICODE)
    out = []
    for w in words:
        if len(w) >= 3 and w not in _STOP and not w.isdigit() or (w.isdigit() and len(w) == 4):
            w = _to_catalog(w)
            if w and w not in out:
                out.append(w)
    return out[:limit]


@dataclass
class Valuation:
    n: int
    median: float
    p25: float
    p75: float
    lo: float
    hi: float
    used_words: list[str]
    comparables: list = field(default_factory=list)  # top rows for display


async def valuate(db, text: str, min_matches: int = 3) -> Valuation | None:
    """None when we genuinely have no comparables."""
    words = keywords(text)
    if not words:
        return None

    # anchor on the RAREST word: its pool is the most specific comparables set
    had_alpha = any(not w.isdigit() for w in words)
    pools: list[tuple[str, list]] = []
    for w in words:
        if w.isdigit():
            continue  # a year is a filter, never an anchor
        rows_w = await db.price_history(w, limit=200)
        if rows_w:
            pools.append((w, rows_w))
    if not pools and not had_alpha:  # the user typed only a year
        w = words[0]
        rows_w = await db.price_history(w, limit=200)
        if rows_w:
            pools.append((w, rows_w))
    if not pools:
        return None
    anchor, pool = min(pools, key=lambda p: len(p[1]))
    words = [anchor] + [x for x in words if x != anchor]

    # AND-refine, relaxing from the tail
    active = words[:]
    rows = pool
    while len(active) > 1:
        filtered = [r for r in pool
                    if all(w in (r["title"] or "").lower() for w in active[1:])]
        if len(filtered) >= min_matches:
            rows = filtered
            break
        active = active[:-1]
    else:
        rows = pool
    if len(rows) < 1:
        return None

    prices = sorted(r["realized"] for r in rows)
    q = statistics.quantiles(prices, n=4) if len(prices) >= 4 else None
    return Valuation(
        n=len(rows),
        median=statistics.median(prices),
        p25=q[0] if q else prices[0],
        p75=q[2] if q else prices[-1],
        lo=prices[0], hi=prices[-1],
        used_words=active,
        comparables=sorted(rows, key=lambda r: -r["realized"])[:3],
    )
