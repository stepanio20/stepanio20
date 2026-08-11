"""Certificate verification against grading-industry registries (NGC/PCGS/PMG).

Industry-standard chain of trust for a user-published coin:
1. The user supplies the slab's certification number.
2. Format is validated against the service's numbering scheme.
3. PCGS — verified automatically via the official PCGS Public API
   (https://api.pcgs.com, free token → PCGS_API_TOKEN env). The API's answer
   (coin name + grade) is stored as cert_note and shown on the listing.
4. NGC / PMG — no public API exists; the listing links straight to the
   grader's public cert-lookup page (the source of truth) and an admin
   confirms with one tap after eyeballing it. Status: linked → verified.
5. One certificate number can back at most one active listing (anti-fraud,
   enforced in db.cert_in_use).

Statuses: none · pending (auto-check queued/failed) · linked (lookup URL
attached, awaiting moderation) · verified · mismatch · rejected.
"""
from __future__ import annotations

import logging
import os
import re

import httpx

log = logging.getLogger(__name__)

# slab numbering schemes (kept permissive on purpose — schemes drift over time)
_PATTERNS = {
    "PCGS": re.compile(r"^\d{7,9}$"),
    "NGC": re.compile(r"^\d{6,8}-\d{3}$"),
    "PMG": re.compile(r"^\d{6,8}-\d{3}$"),
}

LOOKUP_URLS = {
    "PCGS": "https://www.pcgs.com/cert/{num}",
    "NGC": "https://www.ngccoin.com/certlookup/{num}/",
    "PMG": "https://www.pmgnotes.com/certlookup/{num}/",
}


def parse_cert_input(text: str) -> tuple[str, str] | None:
    """'NGC 1234567-001' / 'pcgs 45689164' → (service, number) or None."""
    m = re.match(r"^\s*(ngc|pcgs|pmg)[\s:#-]*([\d-]+)\s*$", text.strip(), re.IGNORECASE)
    if not m:
        return None
    service = m.group(1).upper()
    number = m.group(2).strip("-")
    if not _PATTERNS[service].match(number):
        return None
    return service, number


def lookup_url(service: str, number: str) -> str:
    return LOOKUP_URLS[service].format(num=number)


async def verify_pcgs(number: str, timeout: float = 20.0) -> tuple[str, str]:
    """Return (status, note) via the official PCGS Public API.

    With PCGS_API_TOKEN set this is fully automatic; anonymous calls share a
    tiny per-IP quota and usually land in 'pending' (admin confirms later).
    """
    headers = {"User-Agent": "KatzCoinsRadar/1.0 (cert verification)"}
    token = os.getenv("PCGS_API_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"bearer {token}"
    url = f"https://api.pcgs.com/publicapi/coindetail/GetCoinFactsByCertNo/{number}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
        if r.status_code == 429:
            return "pending", "PCGS API quota; queued for manual confirmation"
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict) or not data.get("PCGSNo"):
            return "mismatch", "PCGS API: certificate not found"
        name = data.get("Name") or ""
        grade = data.get("Grade") or ""
        year = data.get("Year") or ""
        note = " ".join(str(x) for x in [year, name, grade] if x).strip()
        return "verified", note or "confirmed by PCGS API"
    except Exception as e:  # network/API hiccup — never block publishing
        log.warning("PCGS verify failed for %s: %s", number, e)
        return "pending", "auto-check unavailable; queued for manual confirmation"


async def verify(service: str, number: str) -> tuple[str, str]:
    """Dispatch: PCGS → API; NGC/PMG → linked (public registry + moderation)."""
    if service == "PCGS":
        return await verify_pcgs(number)
    return "linked", ""
