"""Constants for the Nexus Metro integration."""

from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

DOMAIN = "nexus_metro"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_STATION_CODE = "station_code"
CONF_STATION_NAME = "station_name"
CONF_PLATFORMS = "platforms"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 90
MIN_SCAN_INTERVAL = 60
MAX_SCAN_INTERVAL = 300
