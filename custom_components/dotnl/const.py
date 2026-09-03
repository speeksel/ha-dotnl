"""Constanten voor de DOT-NL laadpalen-integratie."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "dotnl"

API_URL: Final = (
    "https://dotnl.ndw.nu/api/rest/geojson/dynamic-road-status/"
    "charge-point-data/v1/features"
)

OCPI_LOCATIONS_URL: Final = (
    "https://opendata.ndw.nu/charging_point_locations_ocpi.json.gz"
)

CONF_NAME: Final = "name"
CONF_MIN_LON: Final = "min_lon"
CONF_MIN_LAT: Final = "min_lat"
CONF_MAX_LON: Final = "max_lon"
CONF_MAX_LAT: Final = "max_lat"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_EVSE_DETAILS: Final = "evse_details"
CONF_OCPI_SCAN_INTERVAL: Final = "ocpi_scan_interval"

DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 3600

DEFAULT_EVSE_DETAILS: Final = True
DEFAULT_OCPI_SCAN_INTERVAL: Final = 3600
MIN_OCPI_SCAN_INTERVAL: Final = 600
MAX_OCPI_SCAN_INTERVAL: Final = 86400

MAX_AREA_SQUARE_DEGREES: Final = 1.0
REQUEST_TIMEOUT_SECONDS: Final = 15
OCPI_REQUEST_TIMEOUT_SECONDS: Final = 900
HTTP_TOO_MANY_REQUESTS: Final = 429
