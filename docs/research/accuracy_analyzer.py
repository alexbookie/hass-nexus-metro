"""Analyze prediction accuracy: predictions.jsonl vs ground-truth arrivals in events.jsonl.

Ground truth: 'Arrived' events from the KML feed (per train/station/platform,
1-minute granularity). Each live prediction (train X arrives at S/P in E min,
made at time T) is matched to the first actual arrival of X at S/P at or after
T; error = actual - predicted arrival time in minutes (positive = late vs
prediction). For the same departures, the scheduled time gives a
timetable-only baseline.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import statistics

OUT_DIR = Path(__file__).parent
MATCH_HORIZON_MIN = 30.0  # ignore arrivals more than this past the prediction

LEAD_BUCKETS = [(0, 2), (2, 5), (5, 10), (10, 20), (20, 60)]


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_arrivals(events: list[dict]) -> dict[tuple[str, str, int], list[float]]:
    """Unique 'Arrived' times (UK minutes) per (train, station, platform), sorted."""
    seen: set[tuple] = set()
    arrivals: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for e in events:
        if e["event"] != "Arrived":
            continue
        key = (e["train_id"], e["station"], e["platform"], e["event_time_mins"])
        if key in seen:
            continue
        seen.add(key)
        arrivals[(e["train_id"], e["station"], e["platform"])].append(float(e["event_time_mins"]))
    for times in arrivals.values():
        times.sort()
    return arrivals


def match_predictions(
    predictions: list[dict],
    arrivals: dict[tuple[str, str, int], list[float]],
) -> list[dict]:
    """Attach actual arrival times to live-matched predictions."""
    matched = []
    for p in predictions:
        if not p["train_id"] or p["live_estimate_mins"] is None:
            continue
        key = (p["train_id"], p["station"], p["platform"])
        times = arrivals.get(key)
        if not times:
            continue
        made_at = p["now_mins"]
        predicted = made_at + p["live_estimate_mins"]
        actual = next((t for t in times if t >= made_at - 0.5), None)
        if actual is None or actual - made_at > MATCH_HORIZON_MIN:
            continue
        row = {
            **p,
            "predicted_arrival": predicted,
            "actual_arrival": actual,
            "error": actual - predicted,
            "lead": actual - made_at,
        }
        if p["scheduled_mins"] is not None:
            row["scheduled_error"] = actual - (made_at + p["scheduled_mins"])
        matched.append(row)
    return matched


def describe(errors: list[float]) -> str:
    if not errors:
        return "n=0"
    abs_err = sorted(abs(e) for e in errors)
    mae = sum(abs_err) / len(abs_err)
    bias = sum(errors) / len(errors)
    p90 = abs_err[min(len(abs_err) - 1, int(0.9 * len(abs_err)))]
    within1 = sum(1 for a in abs_err if a <= 1.0) / len(abs_err)
    within2 = sum(1 for a in abs_err if a <= 2.0) / len(abs_err)
    return (
        f"n={len(errors)} MAE={mae:.2f}m bias={bias:+.2f}m median={statistics.median(errors):+.2f}m "
        f"p90|e|={p90:.2f}m within1min={within1:.0%} within2min={within2:.0%}"
    )


def main() -> None:
    predictions = load_jsonl(OUT_DIR / "predictions.jsonl")
    events = load_jsonl(OUT_DIR / "events.jsonl")
    arrivals = build_arrivals(events)
    matched = match_predictions(predictions, arrivals)

    live_rows = [p for p in predictions if p["live_estimate_mins"] is not None]
    print(f"predictions rows: {len(predictions)} (live-matched: {len(live_rows)})")
    print(f"unique arrival ground truths: {sum(len(v) for v in arrivals.values())}")
    print(f"predictions matched to an actual arrival: {len(matched)}")
    if not matched:
        return

    print("\n== Live estimate accuracy (all matched predictions) ==")
    print(describe([m["error"] for m in matched]))

    both = [m for m in matched if "scheduled_error" in m]
    print("\n== Live vs timetable baseline (same departures) ==")
    print(f"live:      {describe([m['error'] for m in both])}")
    print(f"timetable: {describe([m['scheduled_error'] for m in both])}")

    print("\n== By lead time (minutes until actual arrival) ==")
    for lo, hi in LEAD_BUCKETS:
        bucket = [m["error"] for m in matched if lo <= m["lead"] < hi]
        print(f"  {lo:>2}-{hi:<2}m: {describe(bucket)}")

    print("\n== By station/platform ==")
    by_sp: dict[str, list[float]] = defaultdict(list)
    for m in matched:
        by_sp[f"{m['station']} P{m['platform']}"].append(m["error"])
    for sp in sorted(by_sp):
        print(f"  {sp}: {describe(by_sp[sp])}")

    print("\n== By reported status ==")
    by_status: dict[str, list[float]] = defaultdict(list)
    for m in matched:
        by_status[m["status"].split(" (")[0]].append(m["error"])
    for status in sorted(by_status):
        print(f"  {status}: {describe(by_status[status])}")


if __name__ == "__main__":
    main()
