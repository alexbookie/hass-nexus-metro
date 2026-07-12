"""Tests for route and travel-time reference data."""

from __future__ import annotations

from custom_components.nexus_metro.metro_data import GREEN_AIRPORT_TO_SOUTH_HYLTON, route_for_train, travel_time


class TestSouthHyltonRoute:
    def test_sunderland_line_stations_present_in_order(self):
        """Fellgate, Brockley Whins, and East Boldon sit between Pelaw and Seaburn."""
        route = GREEN_AIRPORT_TO_SOUTH_HYLTON
        idx = route.index
        assert idx("PLW") < idx("FGT") < idx("BYW") < idx("EBO") < idx("SBN")

    def test_pelaw_to_seaburn_travel_time_covers_all_segments(self):
        route = GREEN_AIRPORT_TO_SOUTH_HYLTON
        minutes = travel_time(route, route.index("PLW"), route.index("SBN"))
        # PLW-FGT 3 + FGT-BYW 2 + BYW-EBO 3 + EBO-SBN 3
        assert minutes == 11


class TestRouteForTrain:
    def test_sunderland_route_ends_at_sunderland(self):
        route = route_for_train("Sunderland", "WJS")
        assert route is not None
        assert route[-1] == "SUN"

    def test_brockley_whins_route_ends_at_brockley_whins(self):
        route = route_for_train("Brockley Whins", "WJS")
        assert route is not None
        assert route[-1] == "BYW"
        assert "WJS" in route

    def test_pelaw_route_ends_at_pelaw(self):
        route = route_for_train("Pelaw", "WJS")
        assert route is not None
        assert route[-1] == "PLW"

    def test_regent_centre_route_runs_northbound_and_ends_at_regent_centre(self):
        route = route_for_train("Regent Centre", "WJS")
        assert route is not None
        assert route[-1] == "RGC"
        # Northbound: West Jesmond comes before South Gosforth before Regent Centre
        assert route.index("WJS") < route.index("SGF") < route.index("RGC")

    def test_monument_east_route_ends_at_monument_west_east(self):
        route = route_for_train("Monument East", "WSD")
        assert route is not None
        assert route[-1] == "MTW"
        # Toward town: Wallsend comes before Byker before Manors
        assert route.index("WSD") < route.index("BYK") < route.index("MAN")
