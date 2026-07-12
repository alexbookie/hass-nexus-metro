"""Out-of-sample scoring for the afternoon run against the calibrated model.

Scores what the combined sensor would DISPLAY: the live estimate when present,
else the scheduled time (which is also what the distrust rule falls back to
for matched-but-implausibly-early rows, identifiable as train_id set with a
null live estimate).
"""

from __future__ import annotations

from collections import defaultdict

from accuracy_analyzer import LEAD_BUCKETS, MATCH_HORIZON_MIN, OUT_DIR, build_arrivals, describe, load_jsonl


def main() -> None:
    predictions = load_jsonl(OUT_DIR / "predictions.jsonl")
    events = load_jsonl(OUT_DIR / "events.jsonl")
    arrivals = build_arrivals(events)

    scored = []
    distrusted = 0
    for p in predictions:
        if not p["train_id"]:
            continue
        if p["live_estimate_mins"] is None:
            distrusted += 1
            shown = p["scheduled_mins"]
            kind = "fallback"
        else:
            shown = p["live_estimate_mins"]
            kind = "live"
        if shown is None:
            continue
        times = arrivals.get((p["train_id"], p["station"], p["platform"]))
        if not times:
            continue
        made_at = p["now_mins"]
        actual = next((t for t in times if t >= made_at - 0.5), None)
        if actual is None or actual - made_at > MATCH_HORIZON_MIN:
            continue
        scored.append(
            {
                **p,
                "kind": kind,
                "error": actual - (made_at + shown),
                "sched_error": (actual - (made_at + p["scheduled_mins"])) if p["scheduled_mins"] is not None else None,
                "lead": actual - made_at,
            }
        )

    print(f"matched rows scored: {len(scored)} (distrust fallbacks among matched rows: {distrusted})")
    if not scored:
        return

    print("\n== Displayed value accuracy (calibrated model, out-of-sample) ==")
    print(describe([s["error"] for s in scored]))

    with_sched = [s for s in scored if s["sched_error"] is not None]
    print("\n== vs timetable baseline (same rows) ==")
    print(f"displayed:  {describe([s['error'] for s in with_sched])}")
    print(f"timetable:  {describe([s['sched_error'] for s in with_sched])}")

    print("\n== By source of displayed value ==")
    for kind in ("live", "fallback"):
        rows = [s["error"] for s in scored if s["kind"] == kind]
        print(f"  {kind}: {describe(rows)}")

    print("\n== By station ==")
    by_st: dict[str, list[float]] = defaultdict(list)
    for s in scored:
        by_st[s["station"]].append(s["error"])
    for st in sorted(by_st):
        print(f"  {st}: {describe(by_st[st])}")

    print("\n== By lead time ==")
    for lo, hi in LEAD_BUCKETS:
        bucket = [s["error"] for s in scored if lo <= s["lead"] < hi]
        print(f"  {lo:>2}-{hi:<2}m: {describe(bucket)}")

    print("\n== By reported status ==")
    by_status: dict[str, list[float]] = defaultdict(list)
    for s in scored:
        by_status[s["status"].split(" (")[0]].append(s["error"])
    for status in sorted(by_status):
        print(f"  {status}: {describe(by_status[status])}")


if __name__ == "__main__":
    main()
