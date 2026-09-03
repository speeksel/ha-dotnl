"""Domeintypes en typed errors voor de DOT-NL laadpalen-integratie.

De JSON-vormen (TypedDicts) zijn de parse-boundary: alles wat het domein
binnenkomt wordt hier vertaald naar bevroren dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from .const import MAX_AREA_SQUARE_DEGREES


class DotnlApiError(Exception):
    """Basisfout bij communiceren met de DOT-NL API."""


class DotnlConnectionError(DotnlApiError):
    """De DOT-NL API is onbereikbaar of gaf een onverwachte HTTP-status."""

    def __init__(self, status: int) -> None:
        msg = f"DOT-NL API niet bereikbaar (HTTP {status})"
        super().__init__(msg)
        self.status = status


class DotnlRateLimitError(DotnlApiError):
    """De DOT-NL API heeft het ratelimietaangevraagd (HTTP 429)."""


class DotnlPayloadError(DotnlApiError):
    """De DOT-NL API antwoordde met een payload die niet te parsen is."""


class BoundingBoxError(Exception):
    """Basisfout voor een ongeldige boundingbox."""


class BoundingBoxRangeError(BoundingBoxError):
    """min-coördinaat ligt niet links/onder de max-coördinaat."""

    def __init__(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> None:
        msg = (
            f"Ongeldige boundingbox: min ({min_lon}, {min_lat}) "
            f"moet kleiner zijn dan max ({max_lon}, {max_lat})"
        )
        super().__init__(msg)
        self.min_lon = min_lon
        self.min_lat = min_lat
        self.max_lon = max_lon
        self.max_lat = max_lat


class BoundingBoxAreaError(BoundingBoxError):
    """Het gebied overschrijdt de API-limiet van 1,0 vierkante graad."""

    def __init__(self, area: float) -> None:
        msg = (
            f"Boundingbox te groot: {area:.4f} vierkante graden "
            f"(max {MAX_AREA_SQUARE_DEGREES})"
        )
        super().__init__(msg)
        self.area = area


class _AvailabilityJson(TypedDict, total=False):
    available: int
    total: int
    connector_type: str
    connector_format: str
    power_type: str
    power_max: float


class _PropertiesJson(TypedDict, total=False):
    address: str
    last_updated: str
    open: bool
    cpo_id: str
    operator_name: str
    owner_name: str
    suboperator_name: str
    availabilities: list[_AvailabilityJson]


class _GeometryJson(TypedDict, total=False):
    coordinates: list[float]


class _FeatureJson(TypedDict, total=False):
    id: str
    geometry: _GeometryJson
    properties: _PropertiesJson


class FeatureCollectionJson(TypedDict, total=False):
    """Het GeoJSON-antwoord van de DOT-NL charge-point-data endpoint."""

    features: list[_FeatureJson]


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Geldige boundingbox in het formaat minLon,minLat,maxLon,maxLat."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def __post_init__(self) -> None:
        if self.min_lon >= self.max_lon or self.min_lat >= self.max_lat:
            raise BoundingBoxRangeError(self.min_lon, self.min_lat, self.max_lon, self.max_lat)
        if self.area_square_degrees > MAX_AREA_SQUARE_DEGREES:
            raise BoundingBoxAreaError(self.area_square_degrees)

    @property
    def area_square_degrees(self) -> float:
        """Oppervlakte in vierkante graden (API-limiet: 1,0)."""
        return (self.max_lon - self.min_lon) * (self.max_lat - self.min_lat)

    def __str__(self) -> str:
        return f"{self.min_lon},{self.min_lat},{self.max_lon},{self.max_lat}"


@dataclass(frozen=True, slots=True)
class Connector:
    """Beschikbaarheid van één aansluitingstype op een laadpaal."""

    available: int
    total: int
    connector_type: str
    connector_format: str | None
    power_type: str | None
    power_max: float | None


@dataclass(frozen=True, slots=True)
class ChargePoint:
    """Een laadpaal uit de DOT-NL dynamische dataset."""

    cp_id: str
    address: str | None
    operator: str | None
    owner: str | None
    is_open: bool | None
    latitude: float | None
    longitude: float | None
    last_updated: str | None
    connectors: tuple[Connector, ...]

    @property
    def available(self) -> int:
        """Totaal aantal vrije aansluitingen over alle connectortypes."""
        return sum(connector.available for connector in self.connectors)

    @property
    def total(self) -> int:
        """Totaal aantal aansluitingen over alle connectortypes."""
        return sum(connector.total for connector in self.connectors)
