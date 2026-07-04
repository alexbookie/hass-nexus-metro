"""Tests for the train matching and ETA estimation logic."""

from __future__ import annotations

import pytest

from custom_components.nexus_metro.matching import (
    _is_at_terminus,
    build_combined_departures,
    estimate_train_eta,
    find_matching_train,
)
from custom_components.nexus_metro.models import LiveTrain, TrainEvent, TravelineDeparture


def _train(
    *,
    train_id: str = "100",
    event: TrainEvent = TrainEvent.DEPARTED,
    station: str = "RGC",
    platform: int = 1,
    event_mins: float = 900.0,
    destination: str = "South Hylton",
) -> LiveTrain:
    return LiveTrain(
        train_id=train_id,
        lat=54.98,
        lon=-1.62,
        event=event,
        event_station_code=station,
        event_platform=platform,
        event_time_mins=event_mins,
        destination=destination,
    )


def _dep(
    *,
    service: str = "G",
    destination: str = "South Hylton",
    due: str = "5 mins",
    scheduled_mins: float | None = 5.0,
) -> TravelineDeparture:
    return TravelineDeparture(
        service=service,
        destination=destination,
        due=due,
        scheduled_mins=scheduled_mins,
    )


class TestIsAtTerminus:
    def test_ready_at_airport_is_terminus(self):
        train = _train(event=TrainEvent.READY, station="APT", destination="South Hylton")
        assert _is_at_terminus(train) is True

    def test_arrived_at_airport_is_terminus(self):
        train = _train(event=TrainEvent.ARRIVED, station="APT", destination="South Hylton")
        assert _is_at_terminus(train) is True

    def test_departed_at_airport_is_not_terminus(self):
        train = _train(event=TrainEvent.DEPARTED, station="APT", destination="South Hylton")
        assert _is_at_terminus(train) is False

    def test_ready_mid_route_is_not_terminus(self):
        train = _train(event=TrainEvent.READY, station="JES", destination="South Hylton")
        assert _is_at_terminus(train) is False

    def test_unknown_destination_returns_false(self):
        train = _train(event=TrainEvent.READY, station="APT", destination="Narnia")
        assert _is_at_terminus(train) is False


class TestEstimateTrainEta:
    def test_basic_eta(self):
        # Train departed Regent Centre heading to South Hylton.
        # Target: Jesmond (RGC -> SGF -> ILF -> WJS -> JES)
        # Segment times: RGC->SGF=4, SGF->ILF=1, ILF->WJS=2, WJS->JES=2 = 9 mins
        # Departed adjustment: -0.5 * first_seg(4) = -2 => 7 mins
        train = _train(station="RGC", event=TrainEvent.DEPARTED, event_mins=900.0)
        eta = estimate_train_eta(train, "JES", now_mins=900.0)

        assert eta is not None
        assert eta == pytest.approx(7.0, abs=0.1)

    def test_approaching_reduces_eta(self):
        train = _train(station="RGC", event=TrainEvent.APPROACHING, event_mins=900.0)
        eta = estimate_train_eta(train, "JES", now_mins=900.0)

        # Approaching: -0.9 * first_seg(4) = -3.6 => ~5.4
        assert eta is not None
        assert eta < 7.0  # Less than departed ETA

    def test_elapsed_time_reduces_eta(self):
        train = _train(station="RGC", event=TrainEvent.DEPARTED, event_mins=900.0)
        # 2 minutes have passed since the event
        eta = estimate_train_eta(train, "JES", now_mins=902.0)

        assert eta is not None
        assert eta == pytest.approx(5.0, abs=0.1)

    def test_target_behind_train_returns_none(self):
        # Train at JES heading to South Hylton, target is RGC (behind)
        train = _train(station="JES", destination="South Hylton")
        assert estimate_train_eta(train, "RGC", now_mins=900.0) is None

    def test_unknown_destination_returns_none(self):
        train = _train(destination="Narnia")
        assert estimate_train_eta(train, "JES", now_mins=900.0) is None

    def test_station_not_on_route_returns_none(self):
        # Train heading to South Hylton, target is SJM (St James, Yellow only)
        train = _train(destination="South Hylton")
        assert estimate_train_eta(train, "SJM", now_mins=900.0) is None

    def test_midnight_rollover(self):
        # Event at 23:59 (1439 mins), now is 00:01 (1 min)
        train = _train(station="RGC", event=TrainEvent.DEPARTED, event_mins=1439.0)
        eta = estimate_train_eta(train, "JES", now_mins=1.0)

        assert eta is not None
        assert eta >= 0


class TestFindMatchingTrain:
    def test_matches_same_destination(self):
        dep = _dep(destination="South Hylton", scheduled_mins=5.0)
        trains = [_train(destination="South Hylton", station="WJS")]

        eta, train = find_matching_train(dep, "JES", 1, trains, now_mins=900.0)

        assert train is not None
        assert eta is not None

    def test_no_match_different_destination(self):
        dep = _dep(destination="Airport", scheduled_mins=5.0)
        trains = [_train(destination="South Hylton")]

        _eta, train = find_matching_train(dep, "JES", 1, trains, now_mins=900.0)

        assert train is None
        assert _eta is None

    def test_no_match_for_absolute_time(self):
        dep = _dep(scheduled_mins=None, due="22:41")
        trains = [_train(destination="South Hylton")]

        _eta, train = find_matching_train(dep, "JES", 1, trains, now_mins=900.0)

        assert train is None

    def test_direction_filter_inbound_platform_1(self):
        dep = _dep(destination="South Hylton", scheduled_mins=5.0)
        # Train heading to Airport (outbound) on platform 1 — should not match
        trains = [_train(destination="Airport", station="WJS")]

        _eta, train = find_matching_train(dep, "JES", 1, trains, now_mins=900.0)
        assert train is None


class TestBuildCombinedDepartures:
    def test_combines_matched_and_unmatched(self):
        deps = [
            _dep(destination="South Hylton", scheduled_mins=5.0),
            _dep(destination="South Shields", scheduled_mins=12.0),
        ]
        trains = [_train(destination="South Hylton", station="WJS", event_mins=900.0)]

        combined = build_combined_departures("JES", 1, deps, trains, now_mins=900.0)

        assert len(combined) == 2
        # First should be matched
        assert combined[0].destination == "South Hylton"
        assert combined[0].train_id == "100"
        assert combined[0].status != "Scheduled"
        # Second should be unmatched
        assert combined[1].destination == "South Shields"
        assert combined[1].status == "Scheduled"

    def test_no_double_matching(self):
        deps = [
            _dep(destination="South Hylton", scheduled_mins=5.0),
            _dep(destination="South Hylton", scheduled_mins=15.0),
        ]
        # Only one train available
        trains = [_train(destination="South Hylton", station="WJS", event_mins=900.0)]

        combined = build_combined_departures("JES", 1, deps, trains, now_mins=900.0)

        matched_trains = [d.train_id for d in combined if d.train_id]
        assert len(matched_trains) == 1

    def test_empty_departures(self):
        combined = build_combined_departures("JES", 1, [], [], now_mins=900.0)
        assert combined == []

    def test_terminus_train_shows_on_time(self):
        deps = [_dep(destination="South Hylton", scheduled_mins=10.0)]
        # Train READY at Airport (terminus) — ETA will be high but should be "On time"
        trains = [
            _train(
                destination="South Hylton",
                station="APT",
                event=TrainEvent.READY,
                event_mins=900.0,
            )
        ]

        combined = build_combined_departures("JES", 1, deps, trains, now_mins=900.0)

        assert len(combined) == 1
        assert combined[0].status == "On time"
