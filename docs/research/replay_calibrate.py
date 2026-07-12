"""Replay collected snapshots through a dwell-corrected ETA model and re-score.

The collector logs every train's state at every KML poll (events.jsonl), so each
prediction row can be re-derived offline with a modified ETA model. This sweeps
a per-intermediate-stop dwell allowance and reports which value minimises MAE /
bias against the same ground-truth arrivals used by accuracy_analyzer.py.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys
import types

_ha = types.ModuleType("homeassistant")
_ha_const = types.ModuleType("homeassistant.const")


class _Platform:
    SENSOR = "sensor"


_ha_const.Platform = _Platform
_ha.const = _ha_const
sys.modules.setdefault("homeassistant", _ha)
sys.modules.setdefault("homeassistant.const", _ha_const)

_REPO = Path(__file__).resolve().parents[2]
_pkg = types.ModuleType("nexus_metro")
_pkg.__path__ = [str(_REPO / "custom_components" / "nexus_metro")]
sys.modules.setdefault("nexus_metro", _pkg)

from nexus_metro.metro_data import FALLBACK_SEGMENT_TIME, get_segment_time, route_for_train, travel_time  # noqa: E402

OUT_DIR = Path(__file__).parent
MATCH_HORIZON_MIN = 30.0


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_arrivals(events: list[dict]) -> dict[tuple[str, str, int], list[float]]:
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
    for v in arrivals.values():
        v.sort()
    return arrivals


def build_snapshots(events: list[dict]) -> tuple[list[str], dict[str, dict[str, dict]]]:
    """Sorted poll timestamps + ts -> train_id -> event row at that poll."""
    snaps: dict[str, dict[str, dict]] = defaultdict(dict)
    for e in events:
        snaps[e["ts"]][e["train_id"]] = e
    return sorted(snaps), snaps


def latest_snapshot_at(ts_sorted: list[str], ts: str) -> str | None:
    """Latest poll timestamp <= ts (ISO strings compare chronologically)."""
    import bisect

    i = bisect.bisect_right(ts_sorted, ts)
    return ts_sorted[i - 1] if i else None


def eta_with_dwell(train: dict, target_station: str, now_mins: float, dwell: float) -> float | None:
    """estimate_train_eta from matching.py, plus `dwell` min per intermediate stop."""
    route = route_for_train(train["destination"], train["station"])
    if route is None:
        return None
    if train["station"] not in route or target_station not in route:
        return None
    train_idx = route.index(train["station"])
    target_idx = route.index(target_station)
    if target_idx <= train_idx:
        return None

    remaining = travel_time(route, train_idx, target_idx)
    intermediate_stops = max(0, target_idx - train_idx - 1)
    remaining += dwell * intermediate_stops

    if train_idx + 1 < len(route):
        first_seg = get_segment_time(route[train_idx], route[train_idx + 1])
    else:
        first_seg = FALLBACK_SEGMENT_TIME

    if train["event"] == "Departed":
        remaining -= first_seg * 0.5
    elif train["event"] == "Approaching":
        remaining -= first_seg * 0.9

    elapsed = now_mins - train["event_time_mins"]
    if elapsed < -60:
        elapsed += 24 * 60

    return max(0, remaining - elapsed)


def score(errors: list[float]) -> str:
    abs_err = sorted(abs(e) for e in errors)
    mae = sum(abs_err) / len(abs_err)
    bias = sum(errors) / len(errors)
    within1 = sum(1 for a in abs_err if a <= 1.0) / len(abs_err)
    within2 = sum(1 for a in abs_err if a <= 2.0) / len(abs_err)
    return f"n={len(errors)} MAE={mae:.2f}m bias={bias:+.2f}m within1min={within1:.0%} within2min={within2:.0%}"


def main() -> None:
    predictions = load_jsonl(OUT_DIR / "predictions.jsonl")
    events = load_jsonl(OUT_DIR / "events.jsonl")
    arrivals = build_arrivals(events)
    ts_sorted, snapshots = build_snapshots(events)

    # Pre-pair predictions with train snapshot + actual arrival
    paired = []
    for p in predictions:
        if not p["train_id"] or p["live_estimate_mins"] is None:
            continue
        snap_ts = latest_snapshot_at(ts_sorted, p["ts"])
        snap = snapshots.get(snap_ts, {}).get(p["train_id"]) if snap_ts else None
        if snap is None:
            continue
        times = arrivals.get((p["train_id"], p["station"], p["platform"]))
        if not times:
            continue
        actual = next((t for t in times if t >= p["now_mins"] - 0.5), None)
        if actual is None or actual - p["now_mins"] > MATCH_HORIZON_MIN:
            continue
        paired.append((p, snap, actual))

    print(f"replayable predictions: {len(paired)}")
    if not paired:
        return

    for dwell in [0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]:
        errors = []
        for p, snap, actual in paired:
            eta = eta_with_dwell(snap, p["station"], p["now_mins"], dwell)
            if eta is None:
                continue
            errors.append(actual - (p["now_mins"] + eta))
        print(f"dwell={dwell:.2f}: {score(errors)}")


if __name__ == "__main__":
    main()
