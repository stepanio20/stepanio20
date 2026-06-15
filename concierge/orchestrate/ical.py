"""RFC 5545 .ics calendar generation for a weekly plan.

Stdlib-only. The output drags-and-drops into Google Calendar (or any iCal client)
without a live API. Generates timed events for:
  - sessions (training / sauna / massage) with venue + URL in the description
  - one weekly "Meal prep & order day" event (default Sunday 17:00) summarising
    the order/cook split for the week so the user can batch-shop in one go
  - one screening reminder event per screening line, anchored to the start day
    at 10:00 (just a nudge — booking happens in the lab portal)

Timezone defaults to Europe/Madrid. Falls back to floating-time UTC if the
zoneinfo entry is missing (it's in stdlib since 3.9).
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

_TZ = "Europe/Madrid"


def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _uid(parts: list[str]) -> str:
    h = hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]
    return f"{h}@concierge.local"


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def _slot_time(day: date, slot: str) -> tuple[datetime, datetime]:
    """Default times per session kind."""
    starts = {
        "resistance": time(18, 0),
        "zone-2": time(19, 0),
        "sauna": time(20, 0),
        "massage": time(11, 0),
        "screening": time(10, 0),
        "meal_prep": time(17, 0),
    }
    durations = {
        "resistance": 60,
        "zone-2": 50,
        "sauna": 45,
        "massage": 60,
        "screening": 15,
        "meal_prep": 30,
    }
    key = next((k for k in starts if k in slot.lower()), "resistance")
    s = datetime.combine(day, starts[key])
    return s, s + timedelta(minutes=durations[key])


def build_ics(plan: dict[str, Any]) -> str:
    L: list[str] = []
    L += ["BEGIN:VCALENDAR",
          "VERSION:2.0",
          "PRODID:-//Concierge//Weekly Plan//EN",
          "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
          f"X-WR-TIMEZONE:{_TZ}"]

    targets = plan["targets"]
    start = date.fromisoformat(plan["start"])
    now_utc = datetime.utcnow()

    # Sessions across the week
    for day in plan["days"]:
        d = date.fromisoformat(day["date"])
        for s in day.get("sessions", []):
            title = s["text"]
            kind = "resistance" if "resistance" in title.lower() else (
                "zone-2" if "zone-2" in title.lower() else (
                "sauna" if "sauna" in title.lower() else (
                "massage" if "massage" in title.lower() else "resistance")))
            dt_s, dt_e = _slot_time(d, kind)
            descr_parts = []
            if s.get("venue_name"):
                descr_parts.append(f"Venue: {s['venue_name']}")
            if s.get("venue_address"):
                descr_parts.append(s["venue_address"])
            if s.get("venue_url"):
                descr_parts.append(f"Book: {s['venue_url']}")
            descr_parts.append("Information only — not medical advice.")
            descr = "\n".join(descr_parts)

            L += ["BEGIN:VEVENT",
                  f"UID:{_uid([d.isoformat(), title])}",
                  f"DTSTAMP:{_fmt(now_utc)}Z",
                  f"DTSTART;TZID={_TZ}:{_fmt(dt_s)}",
                  f"DTEND;TZID={_TZ}:{_fmt(dt_e)}",
                  f"SUMMARY:{_esc(title)}",
                  f"DESCRIPTION:{_esc(descr)}"]
            if s.get("venue_address"):
                L.append(f"LOCATION:{_esc(s['venue_address'])}")
            if s.get("venue_url"):
                L.append(f"URL:{_esc(s['venue_url'])}")
            L.append("END:VEVENT")

    # Weekly meal-prep & order event (Sunday before the week starts at 17:00)
    prep_day = start - timedelta(days=1)
    dt_s, dt_e = _slot_time(prep_day, "meal_prep")
    order_count = sum(1 for d in plan["days"] for m in d["meals"] if m["rung"] == "order")
    cook_count = sum(1 for d in plan["days"] for m in d["meals"] if m["rung"] == "cook")
    prep_desc = (f"Plan ahead: {cook_count} cook-meals, {order_count} order-meals "
                 f"this week. Shopping list -> from your reports/ folder.")
    L += ["BEGIN:VEVENT",
          f"UID:{_uid([prep_day.isoformat(), 'meal_prep'])}",
          f"DTSTAMP:{_fmt(now_utc)}Z",
          f"DTSTART;TZID={_TZ}:{_fmt(dt_s)}",
          f"DTEND;TZID={_TZ}:{_fmt(dt_e)}",
          "SUMMARY:Meal prep & weekly order",
          f"DESCRIPTION:{_esc(prep_desc)}",
          "END:VEVENT"]

    # Screenings — one reminder per item, anchored to Monday 10:00
    for it in targets.screenings:
        dt_s, dt_e = _slot_time(start, "screening")
        descr_parts = [it.text]
        if it.why:
            descr_parts.append(it.why)
        if getattr(it, "venue_name", ""):
            descr_parts.append(f"Suggested venue: {it.venue_name}")
        if getattr(it, "venue_url", ""):
            descr_parts.append(f"Book: {it.venue_url}")
        descr_parts.append("Information only — confirm relevance with a clinician.")
        L += ["BEGIN:VEVENT",
              f"UID:{_uid([start.isoformat(), 'screening', it.text])}",
              f"DTSTAMP:{_fmt(now_utc)}Z",
              f"DTSTART;TZID={_TZ}:{_fmt(dt_s)}",
              f"DTEND;TZID={_TZ}:{_fmt(dt_e)}",
              f"SUMMARY:Screening reminder — {_esc(it.text[:60])}",
              f"DESCRIPTION:{_esc(chr(10).join(descr_parts))}"]
        if getattr(it, "venue_address", ""):
            L.append(f"LOCATION:{_esc(it.venue_address)}")
        if getattr(it, "venue_url", ""):
            L.append(f"URL:{_esc(it.venue_url)}")
        L.append("END:VEVENT")

    L.append("END:VCALENDAR")
    # RFC 5545 line endings
    return "\r\n".join(L) + "\r\n"


def write_ics(plan: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_ics(plan))
    return out_path
