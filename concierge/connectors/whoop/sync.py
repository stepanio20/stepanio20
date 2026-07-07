"""Pull a recent snapshot from Whoop and write it into the Health Graph.

After the one-time `python3 -m concierge.connectors.whoop.authorize`:

    python3 -m concierge.connectors.whoop.sync --user me [--days 14]

Writes:
  users/<user>/wearables/parsed/whoop_latest.json — raw snapshot
  users/<user>/bundles/health_graph.json          — `wearable` block updated

The next `make_weekly_plan` run picks up the new wearable facts automatically.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .client import WhoopClient

ROOT = Path(__file__).resolve().parents[3]


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _summarise(recovery: list[dict], sleep: list[dict], workouts: list[dict]) -> dict:
    def _f(items, key):
        vals = []
        for it in items:
            s = it.get("score") or {}
            v = s.get(key)
            if v is not None:
                vals.append(float(v))
        return vals

    recovery_scores = _f(recovery, "recovery_score")
    sleep_perf = _f(sleep, "sleep_performance_percentage")
    hrv_ms = _f(recovery, "hrv_rmssd_milli")
    resting_hr = _f(recovery, "resting_heart_rate")
    strain = []
    for w in workouts:
        s = (w.get("score") or {}).get("strain")
        if s is not None:
            strain.append(float(s))

    def _avg(vs):
        return round(statistics.mean(vs), 1) if vs else None

    low_days = sum(1 for v in recovery_scores if v < 34)
    return {
        "samples": {"recovery": len(recovery), "sleep": len(sleep), "workouts": len(workouts)},
        "recovery_avg": _avg(recovery_scores),
        "recovery_low_days": low_days,
        "sleep_perf_avg_pct": _avg(sleep_perf),
        "hrv_rmssd_avg_ms": _avg(hrv_ms),
        "resting_hr_avg": _avg(resting_hr),
        "strain_avg": _avg(strain),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pull a recent Whoop snapshot.")
    ap.add_argument("--user", default="me")
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args(argv)

    try:
        c = WhoopClient.from_env()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    start_iso, end_iso = _iso(start), _iso(end)

    print(f"Pulling Whoop {start_iso} → {end_iso} …")
    profile = c.profile()
    body = c.body_measurement()
    rec = c.recovery_collection(start_iso, end_iso, limit=25).get("records", [])
    slp = c.sleep_collection(start_iso, end_iso, limit=25).get("records", [])
    wk = c.workout_collection(start_iso, end_iso, limit=25).get("records", [])

    summary = _summarise(rec, slp, wk)
    snapshot = {
        "profile": profile, "body": body,
        "recovery": rec, "sleep": slp, "workouts": wk,
        "summary": summary,
    }

    parsed_dir = ROOT / "users" / args.user / "wearables" / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    snap_path = parsed_dir / "whoop_latest.json"
    snap_path.write_text(json.dumps(snapshot, indent=2))
    print(f"Wrote {snap_path.relative_to(ROOT)}  (recovery avg={summary['recovery_avg']}, "
          f"low-recovery days={summary['recovery_low_days']}/{args.days})")

    # Patch the user's health graph with a compact wearable block.
    bundle_path = ROOT / "users" / args.user / "bundles" / "health_graph.json"
    if bundle_path.exists():
        graph = json.loads(bundle_path.read_text())
    else:
        graph = {}
    graph["wearable"] = {
        "source": "whoop",
        "window_days": args.days,
        **summary,
    }
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(graph, indent=2))
    print(f"Patched {bundle_path.relative_to(ROOT)} (wearable block)")
    print("\nRe-run: python3 -m concierge.make_weekly_plan --user me")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
