"""Data models for the Nexus Metro RTI API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MetroLine(StrEnum):
    """Metro line colour."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"


class TrainEvent(StrEnum):
    """Last known event for a train."""

    ARRIVED = "ARRIVED"
    DEPARTED = "DEPARTED"
    APPROACHING = "APPROACHING"
    READY_TO_START = "READY_TO_START"


class PlatformDirection(StrEnum):
    """Platform travel direction."""

    IN = "IN"
    OUT = "OUT"


@dataclass(frozen=True, kw_only=True)
class TrainDeparture:
    """A single upcoming train departure at a platform."""

    train_number: str
    destination: str
    due_in: int
    line: MetroLine | None
    last_event: TrainEvent
    last_event_location: str
    last_event_time: str
    scheduled_time: str | None
    predicted_time: str | None


@dataclass(frozen=True, kw_only=True)
class PlatformInfo:
    """Metadata for a station platform."""

    platform_number: int
    direction: PlatformDirection
    helper_text: str


@dataclass(frozen=True, kw_only=True)
class StationData:
    """Complete data for a station: metadata and departures per platform."""

    station_code: str
    station_name: str
    platforms: dict[int, PlatformInfo]
    departures: dict[int, list[TrainDeparture]]
