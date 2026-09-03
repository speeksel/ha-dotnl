"""Async client voor de NDW OCPI-locaties-bulkdataset (per-EVSE-statussen).

De dataset is een groot bestand (~18 MB gzip, ~80.000 locaties) met per
laadpaal de individuele EVSE's en hun OCPI-status. Deze module streamt het
bestand met ijson zodat het geheugengebruik laag blijft, en filtert onderweg
op de boundingbox van het geconfigureerde gebied.
"""

from __future__ import annotations

import gzip
import tempfile
from typing import TypedDict

import ijson
from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from .const import HTTP_TOO_MANY_REQUESTS, OCPI_LOCATIONS_URL, OCPI_REQUEST_TIMEOUT_SECONDS
from .models import (
    BoundingBox,
    DotnlConnectionError,
    DotnlRateLimitError,
    Evse,
    EvseLocation,
    EvseStatus,
)

_SPOOL_MAX_BYTES = 32 * 1024 * 1024


class _PartyJson(TypedDict, total=False):
    name: str


class _CoordinatesJson(TypedDict, total=False):
    latitude: str
    longitude: str


class _ConnectorJson(TypedDict, total=False):
    standard: str
    power_type: str
    max_amperage: int
    max_voltage: int


class _EvseJson(TypedDict, total=False):
    uid: str
    evse_id: str
    status: str
    physical_reference: str
    capabilities: list[str]
    connectors: list[_ConnectorJson]
    last_updated: str


class _LocationJson(TypedDict, total=False):
    id: str
    address: str
    operator: _PartyJson
    country_code: str
    party_id: str
    coordinates: _CoordinatesJson
    evses: list[_EvseJson]


def _parse_status(raw: str) -> EvseStatus:
    """Vertaal een OCPI-statusstring; onbekende waarden worden UNKNOWN."""
    try:
        return EvseStatus(raw)
    except ValueError:
        return EvseStatus.UNKNOWN


def _parse_evse(raw: _EvseJson) -> Evse | None:
    """Parse één EVSE; None als de EVSE geen uid heeft (overslaan)."""
    uid = raw.get("uid")
    if uid is None:
        return None

    connector = (raw.get("connectors") or [None])[0] or {}
    return Evse(
        uid=uid,
        evse_id=raw.get("evse_id"),
        status=_parse_status(raw.get("status", "UNKNOWN")),
        physical_reference=raw.get("physical_reference"),
        capabilities=tuple(raw.get("capabilities") or ()),
        connector_standard=connector.get("standard"),
        connector_power_type=connector.get("power_type"),
        max_amperage=connector.get("max_amperage"),
        max_voltage=connector.get("max_voltage"),
        last_updated=raw.get("last_updated"),
    )


def _device_id(item: _LocationJson) -> str:
    """Bouw het device-id dat matcht met de realtime feed (NL-ALL-NLLOC...).

    Zonder country/party valt het id terug op de kale locatie-id.
    """
    party = item.get("party_id")
    country = item.get("country_code")
    if party and country:
        return f"{country}-{party}-{item['id']}"
    return item["id"]


def parse_location(item: _LocationJson, bbox: BoundingBox) -> EvseLocation | None:
    """Parse één OCPI-locatie; None als hij buiten de bbox of EVSE-loos is."""
    coordinates = item.get("coordinates", {})
    try:
        latitude = float(coordinates["latitude"])
        longitude = float(coordinates["longitude"])
    except (KeyError, TypeError, ValueError):
        return None

    if not bbox.contains(latitude, longitude):
        return None

    evses = tuple(
        parsed
        for raw in item.get("evses", [])
        if (parsed := _parse_evse(raw)) is not None
    )
    if not evses:
        return None

    return EvseLocation(
        device_id=_device_id(item),
        address=item.get("address"),
        operator=item.get("operator", {}).get("name"),
        evses=evses,
    )


async def async_fetch_evse_locations(
    session: ClientSession, bbox: BoundingBox
) -> list[EvseLocation]:
    """Download en parse de OCPI-bulkdataset, gefilterd op de boundingbox.

    Raises:
        DotnlRateLimitError: HTTP 429.
        DotnlConnectionError: netwerkfout of onverwachte HTTP-status.

    """
    timeout = ClientTimeout(total=OCPI_REQUEST_TIMEOUT_SECONDS)
    try:
        async with session.get(
            OCPI_LOCATIONS_URL, timeout=timeout, raise_for_status=True
        ) as response:
            compressed = await response.read()
    except ClientResponseError as err:
        if err.status == HTTP_TOO_MANY_REQUESTS:
            raise DotnlRateLimitError from err
        raise DotnlConnectionError(err.status) from err
    except (TimeoutError, ClientError) as err:
        raise DotnlConnectionError(0) from err

    with tempfile.SpooledTemporaryFile(max_size=_SPOOL_MAX_BYTES) as buffer:
        buffer.write(gzip.decompress(compressed))
        buffer.seek(0)
        return [
            location
            for item in ijson.items(buffer, "item")
            if (location := parse_location(item, bbox)) is not None
        ]
