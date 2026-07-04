"""Tests for the Traveline and KML API clients."""

from __future__ import annotations

import pytest

from custom_components.nexus_metro.api import _parse_kml, _parse_traveline_html
from custom_components.nexus_metro.models import TrainEvent


class TestTravelineParsing:
    def test_parse_departures_with_minutes(self):
        html = (
            '<span class="sr-only">Service - G. Destination - South Hylton. '
            "Departure time - 3 mins.</span>"
            '<span class="sr-only">Service - Y. Destination - South Shields. '
            "Departure time - 8 mins.</span>"
        )
        deps = _parse_traveline_html(html)

        assert len(deps) == 2
        assert deps[0].service == "G"
        assert deps[0].destination == "South Hylton"
        assert deps[0].due == "3 mins"
        assert deps[0].scheduled_mins == 3.0
        assert deps[1].scheduled_mins == 8.0

    def test_parse_due_now(self):
        html = '<span class="sr-only">Service - G. Destination - Airport. Departure time - Due.</span>'
        deps = _parse_traveline_html(html)

        assert len(deps) == 1
        assert deps[0].due == "Due"
        assert deps[0].scheduled_mins == 0.0

    def test_parse_absolute_time(self):
        html = '<span class="sr-only">Service - Y. Destination - St James. Departure time - 22:41.</span>'
        deps = _parse_traveline_html(html)

        assert len(deps) == 1
        assert deps[0].due == "22:41"
        assert deps[0].scheduled_mins is None

    def test_parse_empty_html(self):
        assert _parse_traveline_html("") == []
        assert _parse_traveline_html("<div>No departures</div>") == []


class TestKmlParsing:
    SAMPLE_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<Placemark id="102">
  <Point><coordinates>-1.62,54.98,0</coordinates></Point>
  <ExtendedData>
    <Data name="details">
      <value><![CDATA[
        <table>
          <tr><td data-title="Last seen">Departed Regent Centre platform 1 at 15:03</td></tr>
          <tr><td data-title="Destination">South Hylton</td></tr>
        </table>
      ]]></value>
    </Data>
  </ExtendedData>
</Placemark>
<Placemark id="200">
  <Point><coordinates>-1.55,55.01,0</coordinates></Point>
  <ExtendedData>
    <Data name="details">
      <value><![CDATA[
        <table>
          <tr><td data-title="Last seen">Ready to start Airport platform 2 at 14:50</td></tr>
          <tr><td data-title="Destination">South Hylton</td></tr>
        </table>
      ]]></value>
    </Data>
  </ExtendedData>
</Placemark>
</Document>
</kml>"""

    def test_parse_departed_train(self):
        trains = _parse_kml(self.SAMPLE_KML)

        assert len(trains) == 2
        t = trains[0]
        assert t.train_id == "102"
        assert t.event == TrainEvent.DEPARTED
        assert t.event_station_code == "RGC"
        assert t.event_platform == 1
        assert t.event_time_mins == 15 * 60 + 3
        assert t.destination == "South Hylton"
        assert t.lat == pytest.approx(54.98)
        assert t.lon == pytest.approx(-1.62)

    def test_parse_ready_train(self):
        trains = _parse_kml(self.SAMPLE_KML)

        ready = trains[1]
        assert ready.train_id == "200"
        assert ready.event == TrainEvent.READY
        assert ready.event_station_code == "APT"
        assert ready.event_platform == 2

    def test_parse_approaching_train(self):
        kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<Placemark id="150">
  <Point><coordinates>-1.60,54.99,0</coordinates></Point>
  <ExtendedData>
    <Data name="details">
      <value><![CDATA[
        <table>
          <tr><td data-title="Last seen">Approaching Jesmond platform 1 at 10:15</td></tr>
          <tr><td data-title="Destination">South Shields</td></tr>
        </table>
      ]]></value>
    </Data>
  </ExtendedData>
</Placemark>
</Document>
</kml>"""
        trains = _parse_kml(kml)

        assert len(trains) == 1
        assert trains[0].event == TrainEvent.APPROACHING
        assert trains[0].event_station_code == "JES"

    def test_parse_empty_kml(self):
        kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document></Document>
</kml>"""
        assert _parse_kml(kml) == []

    def test_parse_invalid_xml(self):
        assert _parse_kml("not xml at all") == []

    def test_unknown_station_skipped(self):
        kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<Placemark id="999">
  <Point><coordinates>-1.60,54.99,0</coordinates></Point>
  <ExtendedData>
    <Data name="details">
      <value><![CDATA[
        <table>
          <tr><td data-title="Last seen">Departed Narnia platform 1 at 12:00</td></tr>
          <tr><td data-title="Destination">Airport</td></tr>
        </table>
      ]]></value>
    </Data>
  </ExtendedData>
</Placemark>
</Document>
</kml>"""
        assert _parse_kml(kml) == []
