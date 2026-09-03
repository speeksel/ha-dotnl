"""Binary sensors per laadpaal (beschikbaar) en per EVSE (aansluiting)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DotnlCoordinator, EvseCoordinator, get_coordinators
from .device import charge_point_device_info, device_info_from_parts
from .models import ChargePoint, Evse, EvseLocation

_DESCRIPTION = BinarySensorEntityDescription(
    key="available",
    translation_key="available",
    icon="mdi:ev-station",
)

_EVSE_DESCRIPTION = BinarySensorEntityDescription(
    key="evse_available",
    icon="mdi:ev-plug-type2",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Maak per laadpaal een beschikbaarheidssensor en per EVSE een sensor aan."""
    dynamic, ocpi = get_coordinators(hass, entry)

    entities: list[BinarySensorEntity] = [
        ChargePointAvailableSensor(dynamic, cp) for cp in dynamic.data or []
    ]
    if ocpi is not None:
        entities.extend(_evse_entities(ocpi))
    async_add_entities(entities)


def _evse_entities(ocpi: EvseCoordinator) -> list[BinarySensorEntity]:
    """Bouw per EVSE een sensor, genummerd per laadpaal (Aansluiting 1, 2, ...)."""
    entities: list[BinarySensorEntity] = []
    for location in ocpi.data or []:
        for ordinal, evse in enumerate(location.evses, start=1):
            entities.append(
                EvseAvailableSensor(ocpi, location, evse, ordinal)
            )
    return entities


class ChargePointAvailableSensor(
    CoordinatorEntity[DotnlCoordinator], BinarySensorEntity
):
    """Beschikbaarheid van één laadpaal (aan = vrij)."""

    entity_description: BinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator: DotnlCoordinator, cp: ChargePoint) -> None:
        """Houd de identiteit vast; dynamische waarden komen uit de coordinator."""
        super().__init__(coordinator)
        self.entity_description = _DESCRIPTION
        self._cp_id = cp.cp_id
        self._attr_unique_id = f"{cp.cp_id}_available"
        self._attr_device_info = charge_point_device_info(cp)

    def _current(self) -> ChargePoint | None:
        """Zoek de actuele staat van deze laadpaal in de coordinator-data."""
        for cp in self.coordinator.data or []:
            if cp.cp_id == self._cp_id:
                return cp
        return None

    @property
    def is_on(self) -> bool:
        """Waar als er minstens één aansluiting vrij is."""
        current = self._current()
        return current is not None and current.available > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Details van de laadpaal: operator, adres, locatie, connectors."""
        current = self._current()
        if current is None:
            return {"charge_point_id": self._cp_id}
        return {
            "charge_point_id": current.cp_id,
            "address": current.address,
            "operator": current.operator,
            "open": current.is_open,
            "latitude": current.latitude,
            "longitude": current.longitude,
            "last_updated": current.last_updated,
            "connectors": [
                {
                    "type": connector.connector_type,
                    "format": connector.connector_format,
                    "power_type": connector.power_type,
                    "power_max_kw": (
                        connector.power_max / 1000 if connector.power_max else None
                    ),
                    "available": connector.available,
                    "total": connector.total,
                }
                for connector in current.connectors
            ],
        }


class EvseAvailableSensor(CoordinatorEntity[EvseCoordinator], BinarySensorEntity):
    """Beschikbaarheid van één fysieke aansluiting (aan = beschikbaar)."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: EvseCoordinator,
        location: EvseLocation,
        evse: Evse,
        ordinal: int,
    ) -> None:
        """Identiteit vasthouden; de status komt uit de OCPI-coordinator."""
        super().__init__(coordinator)
        self.entity_description = _EVSE_DESCRIPTION
        self._device_id = location.device_id
        self._uid = evse.uid
        self._attr_unique_id = f"{location.device_id}_{evse.uid}"
        self._attr_name = f"{location.address or location.device_id} Aansluiting {ordinal}"
        self._attr_device_info = device_info_from_parts(
            location.device_id, location.address, location.operator
        )

    def _current(self) -> Evse | None:
        """Zoek de actuele status van deze EVSE in de coordinator-data."""
        for location in self.coordinator.data or []:
            if location.device_id != self._device_id:
                continue
            for evse in location.evses:
                if evse.uid == self._uid:
                    return evse
        return None

    @property
    def is_on(self) -> bool:
        """Waar als de OCPI-status van deze aansluiting AVAILABLE is."""
        current = self._current()
        return current is not None and current.is_available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Details van deze aansluiting: status, EVSE-id, connector, vermogen."""
        current = self._current()
        if current is None:
            return {"evse_uid": self._uid}
        return {
            "evse_uid": current.uid,
            "evse_id": current.evse_id,
            "status": current.status.value,
            "physical_reference": current.physical_reference,
            "capabilities": list(current.capabilities),
            "connector_standard": current.connector_standard,
            "connector_power_type": current.connector_power_type,
            "max_amperage": current.max_amperage,
            "max_voltage": current.max_voltage,
            "last_updated": current.last_updated,
        }
