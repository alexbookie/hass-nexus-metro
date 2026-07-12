"""API clients for Traveline scheduled departures and KML live train positions."""

from __future__ import annotations

import logging
import re
from xml.etree import ElementTree as ET

import aiohttp
from defusedxml import ElementTree as DefusedET

from .metro_data import STATION_NAME_TO_CODE
from .models import LiveTrain, TrainEvent, TravelineDeparture

_LOGGER = logging.getLogger(__name__)

TRAVELINE_BASE = "https://www.traveline.info/stops"
KML_BASE = "https://app-metrortiapi-prod-001.azurewebsites.net/api/geo"

_KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}

# Regex for Traveline sr-only departure text
_TRAVELINE_PATTERN = re.compile(r"Service - (\w+)\. Destination - ([^.]+)\. Departure time - ([^.]+)\.")

# Traveline sometimes renders destinations as "South Shields Metro Station";
# the KML feed always uses the bare name, so strip the suffix for matching.
_METRO_STATION_SUFFIX = re.compile(r"\s+Metro Station$", re.IGNORECASE)

# Traveline destination names that differ from the KML feed's names.
_DESTINATION_ALIASES = {
    "Newcastle Airport": "Airport",
}

# Regex for KML "last seen" events
_EVENT_PATTERN = re.compile(r"(Arrived|Departed|Approaching)\s+(.+?)\s+platform\s+(\d+)\s+at\s+(\d+):(\d+)")
_READY_PATTERN = re.compile(r"Ready to start\s+(.+?)\s+platform\s+(\d+)\s+at\s+(\d+):(\d+)")


class NexusMetroApiError(Exception):
    """Base exception for Nexus Metro API errors."""


class NexusMetroConnectionError(NexusMetroApiError):
    """Raised when a data source is unreachable."""


class NexusMetroResponseError(NexusMetroApiError):
    """Raised when a data source returns an unexpected response."""


class TravelineClient:
    """Client for Traveline scheduled departure data."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialise with an aiohttp session."""
        self._session = session

    async def async_get_departures(self, atco_code: str) -> list[TravelineDeparture]:
        """Fetch scheduled departures for a platform ATCO code."""
        url = f"{TRAVELINE_BASE}/{atco_code}"
        headers = {"X-Requested-With": "XMLHttpRequest"}

        try:
            async with self._session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    raise NexusMetroResponseError(f"Traveline returned HTTP {resp.status} for {atco_code}")
                text = await resp.text()
        except aiohttp.ClientError as err:
            raise NexusMetroConnectionError(f"Failed to connect to Traveline: {err}") from err

        return _parse_traveline_html(text)


def _parse_traveline_html(html: str) -> list[TravelineDeparture]:
    """Parse Traveline HTML fragment into departures."""
    departures: list[TravelineDeparture] = []

    for match in _TRAVELINE_PATTERN.finditer(html):
        service, destination_raw, due_raw = match.groups()
        destination = _METRO_STATION_SUFFIX.sub("", destination_raw.strip())
        destination = _DESTINATION_ALIASES.get(destination, destination)
        due = due_raw.strip()

        scheduled_mins: float | None
        if "min" in due:
            mins_match = re.search(r"(\d+)", due)
            scheduled_mins = float(mins_match.group(1)) if mins_match else 0.0
        elif due.lower() == "due":
            scheduled_mins = 0.0
        else:
            scheduled_mins = None  # Absolute time like "22:41"

        departures.append(
            TravelineDeparture(
                service=service,
                destination=destination,
                due=due,
                scheduled_mins=scheduled_mins,
            )
        )

    return departures


class KmlClient:
    """Client for the live train positions KML feed."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialise with an aiohttp session."""
        self._session = session

    async def async_get_trains(self, timestamp_ms: int) -> list[LiveTrain]:
        """Fetch live train positions from the KML endpoint."""
        url = f"{KML_BASE}/trainstatuses.kml?d={timestamp_ms}"

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    raise NexusMetroResponseError(f"KML feed returned HTTP {resp.status}")
                text = await resp.text()
        except aiohttp.ClientError as err:
            raise NexusMetroConnectionError(f"Failed to connect to KML feed: {err}") from err

        return _parse_kml(text)


def _parse_kml(xml_text: str) -> list[LiveTrain]:
    """Parse KML XML into live train positions."""
    try:
        root = DefusedET.fromstring(xml_text)
    except ET.ParseError as err:
        _LOGGER.warning("Failed to parse KML XML: %s", err)
        return []

    trains: list[LiveTrain] = []

    for placemark in root.findall(".//kml:Placemark", _KML_NS):
        train = _parse_placemark(placemark)
        if train is not None:
            trains.append(train)

    return trains


def _parse_placemark(placemark: ET.Element) -> LiveTrain | None:
    """Parse a single KML Placemark into a LiveTrain."""
    train_id = placemark.get("id", "")

    coords_el = placemark.find(".//kml:coordinates", _KML_NS)
    if coords_el is None or coords_el.text is None:
        return None

    try:
        lon_s, lat_s, _ = coords_el.text.strip().split(",")
        lat = float(lat_s)
        lon = float(lon_s)
    except (ValueError, IndexError):
        return None

    data_el = placemark.find(".//kml:Data/kml:value", _KML_NS)
    if data_el is None or data_el.text is None:
        return None

    html = data_el.text

    last_match = re.search(r'data-title="Last seen">(.*?)</td>', html)
    dest_match = re.search(r'data-title="Destination">(.*?)</td>', html)
    if not last_match or not dest_match:
        return None

    last_seen = last_match.group(1)
    destination = dest_match.group(1)

    event: TrainEvent
    station_name: str
    platform: int
    event_h: int
    event_min: int

    event_match = _EVENT_PATTERN.match(last_seen)
    if event_match:
        event = TrainEvent(event_match.group(1))
        station_name = event_match.group(2)
        platform = int(event_match.group(3))
        event_h = int(event_match.group(4))
        event_min = int(event_match.group(5))
    else:
        ready_match = _READY_PATTERN.match(last_seen)
        if not ready_match:
            return None
        event = TrainEvent.READY
        station_name = ready_match.group(1)
        platform = int(ready_match.group(2))
        event_h = int(ready_match.group(3))
        event_min = int(ready_match.group(4))

    station_code = STATION_NAME_TO_CODE.get(station_name.lower().strip())
    if station_code is None:
        _LOGGER.debug("Unknown station in KML: %r", station_name)
        return None

    return LiveTrain(
        train_id=train_id,
        lat=lat,
        lon=lon,
        event=event,
        event_station_code=station_code,
        event_platform=platform,
        event_time_mins=event_h * 60 + event_min,
        destination=destination,
    )
