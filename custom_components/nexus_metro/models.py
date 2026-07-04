"""Data models for the Nexus Metro integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TrainEvent(StrEnum):
    """Last known event for a train."""

    ARRIVED = "Arrived"
    DEPARTED = "Departed"
    APPROACHING = "Approaching"
    READY = "READY"


@dataclass(frozen=True, kw_only=True)
class TravelineDeparture:
    """A scheduled departure from Traveline."""

    service: str
    destination: str
    due: str
    scheduled_mins: float | None  # None if due is an absolute time like "22:41"


@dataclass(frozen=True, kw_only=True)
class LiveTrain:
    """A live train position from the KML feed."""

    train_id: str
    lat: float
    lon: float
    event: TrainEvent
    event_station_code: str
    event_platform: int
    event_time_mins: float  # minutes since midnight
    destination: str


@dataclass(frozen=True, kw_only=True)
class CombinedDeparture:
    """A Traveline departure enriched with live train data."""

    service: str
    destination: str
    scheduled_due: str
    scheduled_mins: float | None
    live_estimate_mins: float | None
    status: str  # "On time", "Delayed (~Xm)", "Early (~Xm)", "Scheduled"
    train_id: str
    train_info: str


@dataclass(frozen=True, kw_only=True)
class PlatformData:
    """Combined departure data for a single platform."""

    platform_number: int
    traveline_departures: list[TravelineDeparture] = field(default_factory=list)
    live_trains: list[LiveTrain] = field(default_factory=list)
    combined_departures: list[CombinedDeparture] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class StationData:
    """Complete data for a station across all monitored platforms."""

    station_code: str
    station_name: str
    platforms: dict[int, PlatformData]
    all_live_trains: list[LiveTrain] = field(default_factory=list)
