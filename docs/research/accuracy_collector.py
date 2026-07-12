"""Accuracy data collector for Nexus Metro live arrival predictions.

Runs the integration's real pipeline (api.py + matching.py) against live
endpoints and logs, as JSONL:

- predictions.jsonl: every combined-departure prediction for the monitored
  platforms (train id, live estimate minutes, scheduled minutes, status)
- events.jsonl: every observed train event network-wide (Arrived / Departed /
  Approaching / Ready), which later provides ground-truth arrival times

Designed to run in short chunks that append to the same files:

    python accuracy_collector.py --minutes 8

Analysis dedups events, so chunks need no shared state.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import sys
import time
import types
from zoneinfo import ZoneInfo

import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_LOGGER = logging.getLogger("collector")

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

from nexus_metro.api import KmlClient, TravelineClient  # noqa: E402
from nexus_metro.matching import build_combined_departures  # noqa: E402
from nexus_metro.metro_data import get_atco_code  # noqa: E402

OUT_DIR = Path(__file__).parent
PREDICTIONS_PATH = OUT_DIR / "predictions.jsonl"
EVENTS_PATH = OUT_DIR / "events.jsonl"

# Station/platform pairs to predict for. WJS sees both lines; MSN covers the
# yellow coast stretch. (EBO is closed by engineering works on 2026-07-04.)
MONITORED: list[tuple[str, int]] = [("WJS", 1), ("WJS", 2), ("MSN", 1), ("MSN", 2)]

KML_INTERVAL_S = 30
PREDICTION_INTERVAL_S = 120
UK_TZ = ZoneInfo("Europe/London")


def _append(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def _uk_now_mins() -> float:
    uk_now = datetime.now(tz=UK_TZ)
    return uk_now.hour * 60 + uk_now.minute + uk_now.second / 60


async def _poll_kml(kml: KmlClient) -> list:
    trains = await kml.async_get_trains(int(time.time() * 1000))
    for t in trains:
        _append(
            EVENTS_PATH,
            {
                "ts": _now_iso(),
                "train_id": t.train_id,
                "event": t.event.value,
                "station": t.event_station_code,
                "platform": t.event_platform,
                "event_time_mins": t.event_time_mins,
                "destination": t.destination,
            },
        )
    return trains


async def _poll_predictions(traveline: TravelineClient, trains: list) -> int:
    count = 0
    now_mins = _uk_now_mins()
    for station_code, platform_number in MONITORED:
        atco = get_atco_code(station_code, platform_number)
        if atco is None:
            continue
        try:
            deps = await traveline.async_get_departures(atco)
        except Exception as err:  # noqa: BLE001 - keep collecting on any source error
            _LOGGER.warning("Traveline error for %s P%d: %s", station_code, platform_number, err)
            continue
        combined = build_combined_departures(
            station_code=station_code,
            platform_number=platform_number,
            traveline_departures=deps,
            trains=trains,
            now_mins=now_mins,
        )
        for dep in combined:
            _append(
                PREDICTIONS_PATH,
                {
                    "ts": _now_iso(),
                    "now_mins": round(now_mins, 2),
                    "station": station_code,
                    "platform": platform_number,
                    "destination": dep.destination,
                    "service": dep.service,
                    "scheduled_due": dep.scheduled_due,
                    "scheduled_mins": dep.scheduled_mins,
                    "live_estimate_mins": dep.live_estimate_mins,
                    "status": dep.status,
                    "train_id": dep.train_id,
                },
            )
            count += 1
    return count


async def run(minutes: float) -> None:
    deadline = time.monotonic() + minutes * 60
    next_prediction = 0.0
    total_events = 0
    total_preds = 0

    async with aiohttp.ClientSession() as session:
        traveline = TravelineClient(session)
        kml = KmlClient(session)

        while time.monotonic() < deadline:
            cycle_start = time.monotonic()
            try:
                trains = await _poll_kml(kml)
                total_events += len(trains)
                if cycle_start >= next_prediction:
                    next_prediction = cycle_start + PREDICTION_INTERVAL_S
                    total_preds += await _poll_predictions(traveline, trains)
            except Exception as err:  # noqa: BLE001 - transient failures must not kill the run
                _LOGGER.warning("Cycle error: %s", err)

            elapsed = time.monotonic() - cycle_start
            await asyncio.sleep(max(1.0, KML_INTERVAL_S - elapsed))

    _LOGGER.info("Chunk done: %d event rows, %d prediction rows", total_events, total_preds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=8.0)
    args = parser.parse_args()
    asyncio.run(run(args.minutes))
