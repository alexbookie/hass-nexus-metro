"""Constants for the Nexus Metro integration."""

from homeassistant.const import Platform

DOMAIN = "nexus_metro"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_STATION_CODE = "station_code"
CONF_STATION_NAME = "station_name"
CONF_PLATFORMS = "platforms"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 300

MAX_DEPARTURE_SLOTS = 4
NUM_DEPARTURE_SENSORS = 3

# Status values for combined departures
STATUS_ON_TIME = "On time"
STATUS_DELAYED = "Delayed"
STATUS_EARLY = "Early"
STATUS_SCHEDULED = "Scheduled"

# Matching thresholds (minutes)
ON_TIME_THRESHOLD = 3.0
MATCH_WINDOW = 15.0
