"""Train matching and ETA estimation logic.

Matches Traveline scheduled departures with live KML train positions
to produce combined departures with real-time status.
"""

from __future__ import annotations

import logging

from .const import (
    DWELL_TIME_MINS,
    EARLY_DISTRUST_THRESHOLD,
    MATCH_WINDOW,
    ON_TIME_THRESHOLD,
    STATUS_DELAYED,
    STATUS_ON_TIME,
    STATUS_SCHEDULED,
)
from .metro_data import (
    FALLBACK_SEGMENT_TIME,
    INBOUND_DESTINATIONS,
    OUTBOUND_DESTINATIONS,
    get_segment_time,
    route_for_train,
    travel_time,
)
from .models import CombinedDeparture, LiveTrain, TrainEvent, TravelineDeparture

_LOGGER = logging.getLogger(__name__)


def _is_at_terminus(train: LiveTrain) -> bool:
    """Check if a train is waiting at the start of its route.

    Trains with READY or Arrived events at the first station of their route
    are waiting to depart on schedule, not running early.
    """
    if train.event not in (TrainEvent.READY, TrainEvent.ARRIVED):
        return False

    route = route_for_train(train.destination, train.event_station_code)
    if route is None:
        return False

    if train.event_station_code not in route:
        return False

    idx = route.index(train.event_station_code)
    return idx <= 1


def estimate_train_eta(
    train: LiveTrain,
    target_station: str,
    now_mins: float,
) -> float | None:
    """Estimate minutes until a live train arrives at target_station."""
    route = route_for_train(train.destination, train.event_station_code)
    if route is None:
        return None

    if train.event_station_code not in route or target_station not in route:
        return None

    train_idx = route.index(train.event_station_code)
    target_idx = route.index(target_station)
    if target_idx <= train_idx:
        return None

    remaining = travel_time(route, train_idx, target_idx)

    # Segment times cover track time only; allow for dwell at each
    # intermediate platform stop.
    remaining += DWELL_TIME_MINS * max(0, target_idx - train_idx - 1)

    # Adjust for progress through the current segment
    if train_idx + 1 < len(route):
        first_seg = get_segment_time(route[train_idx], route[train_idx + 1])
    else:
        first_seg = FALLBACK_SEGMENT_TIME

    if train.event == TrainEvent.DEPARTED:
        remaining -= first_seg * 0.5
    elif train.event == TrainEvent.APPROACHING:
        remaining -= first_seg * 0.9

    # Account for elapsed time since the event
    elapsed = now_mins - train.event_time_mins
    if elapsed < -60:
        elapsed += 24 * 60  # midnight rollover

    eta = remaining - elapsed
    return max(0, eta)


def find_matching_train(
    departure: TravelineDeparture,
    target_station: str,
    target_platform: int,
    trains: list[LiveTrain],
    now_mins: float,
) -> tuple[float | None, LiveTrain | None]:
    """Find the best live train match for a scheduled departure.

    Returns (eta_minutes, train) or (None, None) if no match.
    """
    if departure.scheduled_mins is None:
        return None, None

    expected_eta = departure.scheduled_mins

    candidates: list[tuple[float, float, LiveTrain]] = []

    for train in trains:
        if train.destination != departure.destination:
            continue

        # Check direction matches the platform
        if target_platform in (1, 3) and train.destination not in INBOUND_DESTINATIONS:
            continue
        if target_platform in (2, 4) and train.destination not in OUTBOUND_DESTINATIONS:
            continue

        eta = estimate_train_eta(train, target_station, now_mins)
        if eta is None:
            continue

        diff = abs(eta - expected_eta)
        candidates.append((diff, eta, train))

    if not candidates:
        return None, None

    candidates.sort(key=lambda c: c[0])
    diff, eta, train = candidates[0]

    if diff > MATCH_WINDOW:
        return None, None

    return eta, train


def build_combined_departures(
    station_code: str,
    platform_number: int,
    traveline_departures: list[TravelineDeparture],
    trains: list[LiveTrain],
    now_mins: float,
) -> list[CombinedDeparture]:
    """Combine Traveline departures with live train data."""
    used_trains: set[str] = set()
    results: list[CombinedDeparture] = []

    for dep in traveline_departures:
        eta, train = find_matching_train(
            dep,
            station_code,
            platform_number,
            trains,
            now_mins,
        )

        # Don't double-match a train
        if train and train.train_id in used_trains:
            eta, train = None, None
        if train:
            used_trains.add(train.train_id)

        status: str
        train_id: str = ""
        train_info: str = ""

        if eta is not None and train is not None and dep.scheduled_mins is not None:
            diff = eta - dep.scheduled_mins
            at_terminus = _is_at_terminus(train)
            train_id = train.train_id
            train_info = f"{train.event.value} {train.event_station_code}"

            if at_terminus:
                status = STATUS_ON_TIME
            elif diff > ON_TIME_THRESHOLD:
                status = f"{STATUS_DELAYED} (~{eta:.0f}m)"
            elif diff < -EARLY_DISTRUST_THRESHOLD:
                # A live ETA this far ahead of schedule is almost always model
                # error, not real early running - trust the timetable instead.
                status = STATUS_ON_TIME
                eta = None
            else:
                status = STATUS_ON_TIME
        else:
            status = STATUS_SCHEDULED

        results.append(
            CombinedDeparture(
                service=dep.service,
                destination=dep.destination,
                scheduled_due=dep.due,
                scheduled_mins=dep.scheduled_mins,
                live_estimate_mins=eta,
                status=status,
                train_id=train_id,
                train_info=train_info,
            )
        )

    return results
