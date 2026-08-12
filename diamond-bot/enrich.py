"""
Certificate enrichment via the GIA Report Results API (the diamond analogue of the
Dubai bot's Dubai-Unit-API owner/unit lookup).

Pricing (Aug 2026): free on your own submissions; pay-as-you-go $0.20/lookup;
subscriptions $1k/mo (10k lookups) … $15k/mo (500k). Docs:
  https://www.gia.edu/report-results-api

This module is a thin, dependency-light client. With no GIA_API_KEY set it returns a
clearly-marked stub so the rest of the pipeline runs end-to-end in development.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

from config import settings

GIA_ENDPOINT = "https://api.gia.edu/report-results/graphql"  # per GIA developer docs

_QUERY = """
query($number: String!) {
  getReportByNumber(reportNumber: $number) {
    reportNumber reportType reportDate
    results {
      shape caratWeight colorGrade clarityGrade cutGrade
      polish symmetry fluorescence measurements
    }
  }
}
"""


def verify_cert(cert_number: str, lab: str = "GIA") -> Optional[dict]:
    """
    Return normalized grading data for a report number, or a stub when no key is set.
    Only GIA has a true metered public API; IGI/HRD need scraping/partnership (out of MVP scope).
    """
    if not cert_number:
        return None
    if lab.upper() != "GIA" or not settings.gia_api_key:
        return {
            "cert_number": cert_number, "lab": lab, "verified": False,
            "note": "stub — set GIA_API_KEY for live GIA verification; IGI/HRD need partnership",
        }
    try:
        body = json.dumps({"query": _QUERY, "variables": {"number": cert_number}}).encode()
        req = urllib.request.Request(
            GIA_ENDPOINT, data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.gia_api_key}"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            data = json.loads(resp.read().decode())
        node = (data.get("data") or {}).get("getReportByNumber")
        if not node:
            return {"cert_number": cert_number, "lab": "GIA", "verified": False, "note": "not found"}
        r = (node.get("results") or {})
        return {
            "cert_number": node.get("reportNumber"), "lab": "GIA", "verified": True,
            "report_type": node.get("reportType"), "report_date": node.get("reportDate"),
            "shape": r.get("shape"), "carat": r.get("caratWeight"),
            "color": r.get("colorGrade"), "clarity": r.get("clarityGrade"),
            "cut": r.get("cutGrade"), "polish": r.get("polish"),
            "symmetry": r.get("symmetry"), "fluorescence": r.get("fluorescence"),
            "measurements": r.get("measurements"),
        }
    except Exception as e:  # noqa: BLE001 — never let enrichment crash the bot
        return {"cert_number": cert_number, "lab": lab, "verified": False, "note": f"error: {e}"}


def cross_check(parsed: dict, cert: dict) -> list[str]:
    """Flag mismatches between the chat text and the certificate (anti-cert-swap fraud)."""
    issues = []
    if not cert or not cert.get("verified"):
        return issues
    def near(a, b, tol=0.02):
        try:
            return abs(float(a) - float(b)) <= tol
        except (TypeError, ValueError):
            return False
    if parsed.get("carat") and cert.get("carat") and not near(parsed["carat"], cert["carat"]):
        issues.append(f"carat {parsed['carat']} vs cert {cert['carat']}")
    for k in ("color", "clarity"):
        if parsed.get(k) and cert.get(k) and str(parsed[k]).upper() != str(cert[k]).upper():
            issues.append(f"{k} {parsed[k]} vs cert {cert[k]}")
    return issues
