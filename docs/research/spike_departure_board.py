"""Proof-of-concept: validate the Traveline + KML pipeline end-to-end outside HA.

Drives the REAL integration modules (api.py, matching.py, metro_data.py) against
the live endpoints to prove the current architecture still works after the
Nexus API lockdown (July 2026), and probes the two disruption KML feeds we
recommend adding.

Run from the repo root with plain Python 3.13 (no devcontainer needed):

    python docs/research/spike_departure_board.py [STATION_CODE]

Requires: pip install aiohttp defusedxml
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from pathlib import Path
import sys
import time
import types
from zoneinfo import ZoneInfo

import aiohttp

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_LOGGER = logging.getLogger("spike")

# const.py imports `from homeassistant.const import Platform`; stub just that
# so the integration modules import outside an HA environment.
_ha = types.ModuleType("homeassistant")
_ha_const = types.ModuleType("homeassistant.const")


class _Platform:
    SENSOR = "sensor"


_ha_const.Platform = _Platform
_ha.const = _ha_const
sys.modules.setdefault("homeassistant", _ha)
sys.modules.setdefault("homeassistant.const", _ha_const)

# Register the package with a manual __path__ so submodules import WITHOUT
# executing __init__.py (which pulls in the full HA framework).
_pkg_dir = Path(__file__).resolve().parents[2] / "custom_components" / "nexus_metro"
_pkg = types.ModuleType("nexus_metro")
_pkg.__path__ = [str(_pkg_dir)]
sys.modules.setdefault("nexus_metro", _pkg)

from nexus_metro.api import KML_BASE, KmlClient, TravelineClient  # noqa: E402
from nexus_metro.matching import build_combined_departures  # noqa: E402
from nexus_metro.metro_data import STATION_NAMES, get_atco_code  # noqa: E402

ALERT_FEEDS = ("warning.kml", "alerts.kml")


def platform_numbers_for(station_code: str) -> list[int]:
    """Discover platforms for a station via which ATCO codes exist (max 4)."""
    return [p for p in range(1, 5) if get_atco_code(station_code, p) is not None]


async def probe_alert_feeds(session: aiohttp.ClientSession) -> None:
    """Fetch the disruption KML feeds and report their status."""
    for feed in ALERT_FEEDS:
        url = f"{KML_BASE}/{feed}?d={int(time.time() * 1000)}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            body = await resp.text()
            placemarks = body.count("<Placemark")
            _LOGGER.info(
                "%s: HTTP %s, %d bytes, %d active alert(s)",
                feed,
                resp.status,
                len(body),
                placemarks,
            )


async def build_board(station_code: str) -> None:
    """Fetch live + scheduled data and print a combined departure board."""
    station_name = STATION_NAMES.get(station_code, station_code)
    platform_numbers = platform_numbers_for(station_code)
    if not platform_numbers:
        raise SystemExit(f"Unknown station code: {station_code}")

    uk_now = datetime.now(tz=ZoneInfo("Europe/London"))
    now_mins = uk_now.hour * 60 + uk_now.minute + uk_now.second / 60

    async with aiohttp.ClientSession() as session:
        traveline = TravelineClient(session)
        kml = KmlClient(session)

        trains = await kml.async_get_trains(int(time.time() * 1000))
        _LOGGER.info("KML: %d live trains on the network", len(trains))

        await probe_alert_feeds(session)

        print(f"\n=== {station_name} ({station_code}) at {uk_now:%H:%M} ===")
        for platform_number in platform_numbers:
            atco_code = get_atco_code(station_code, platform_number)
            if atco_code is None:
                _LOGGER.warning("No ATCO code for platform %d", platform_number)
                continue

            departures = await traveline.async_get_departures(atco_code)
            combined = build_combined_departures(
                station_code=station_code,
                platform_number=platform_number,
                traveline_departures=departures,
                trains=trains,
                now_mins=now_mins,
            )

            print(f"\nPlatform {platform_number} ({atco_code}):")
            if not combined:
                print("  (no departures)")
            for dep in combined[:5]:
                live = f" live~{dep.live_estimate_mins:.0f}m" if dep.live_estimate_mins is not None else ""
                train = f" [train {dep.train_id}]" if dep.train_id else ""
                print(f"  {dep.service} {dep.destination:<20} due {dep.scheduled_due:<8} {dep.status}{live}{train}")


if __name__ == "__main__":
    asyncio.run(build_board(sys.argv[1] if len(sys.argv) > 1 else "WJS"))
