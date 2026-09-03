"""Async client voor de DOT-NL (DAFNE) charge point API.

Deze module is de I/O-boundary: één functie haalt de GeoJSON-feed op en
vertaalt die naar typelijke domeinobjecten. homeassistant-imports zijn hier
niet nodig, zodat de parser unit-testbaar blijft zonder HA-runtime.
"""

from __future__ import annotations

import json

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from .const import API_URL, HTTP_TOO_MANY_REQUESTS, REQUEST_TIMEOUT_SECONDS
from .models import (
    BoundingBox,
    ChargePoint,
    Connector,
    DotnlConnectionError,
    DotnlPayloadError,
    DotnlRateLimitError,
    FeatureCollectionJson,
    _AvailabilityJson,
    _FeatureJson,
)


def build_request_url(bbox: BoundingBox) -> str:
    """Bouw de request-URL met de boundingbox als query-parameter."""
    return f"{API_URL}?bbox={bbox}"


def _parse_connector(raw: _AvailabilityJson) -> Connector:
    return Connector(
        available=raw.get("available", 0),
        total=raw.get("total", 0),
        connector_type=raw.get("connector_type", "UNKNOWN"),
        connector_format=raw.get("connector_format"),
        power_type=raw.get("power_type"),
        power_max=raw.get("power_max"),
    )


def _parse_charge_point(feature: _FeatureJson) -> ChargePoint:
    properties = feature.get("properties", {})
    coordinates = feature["geometry"]["coordinates"]

    connectors = tuple(
        _parse_connector(raw) for raw in properties.get("availabilities", [])
    )

    return ChargePoint(
        cp_id=feature["id"],
        address=properties.get("address"),
        operator=properties.get("operator_name"),
        owner=properties.get("owner_name"),
        is_open=properties.get("open"),
        latitude=coordinates[1],
        longitude=coordinates[0],
        last_updated=properties.get("last_updated"),
        connectors=connectors,
    )


def parse_features(payload: FeatureCollectionJson) -> list[ChargePoint]:
    """Vertaal een GeoJSON FeatureCollection naar een lijst laadpalen.

    Raises:
        DotnlPayloadError: de payload mist verwachte sleutels of heeft
            een onverwachte vorm.

    """
    try:
        features = payload["features"]
    except (KeyError, TypeError) as err:
        raise DotnlPayloadError from err

    try:
        return [_parse_charge_point(feature) for feature in features]
    except (KeyError, TypeError, ValueError, IndexError) as err:
        raise DotnlPayloadError from err


async def async_fetch_charge_points(
    session: ClientSession, bbox: BoundingBox
) -> list[ChargePoint]:
    """Haal alle laadpalen binnen de boundingbox op bij de DOT-NL API.

    Raises:
        DotnlRateLimitError: HTTP 429 - te veel requests.
        DotnlConnectionError: netwerkfout of onverwachte HTTP-status.
        DotnlPayloadError: het antwoord is geen geldige FeatureCollection.

    """
    url = build_request_url(bbox)
    timeout = ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    try:
        async with session.get(url, timeout=timeout, raise_for_status=True) as response:
            payload: FeatureCollectionJson = await response.json(content_type=None)
    except ClientResponseError as err:
        if err.status == HTTP_TOO_MANY_REQUESTS:
            raise DotnlRateLimitError from err
        raise DotnlConnectionError(err.status) from err
    except (TimeoutError, ClientError, json.JSONDecodeError) as err:
        raise DotnlConnectionError(0) from err

    return parse_features(payload)
