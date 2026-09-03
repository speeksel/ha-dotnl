"""Binary sensor per laadpaal: aan = minstens één aansluiting vrij."""

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

from . import DotnlCoordinator, get_coordinator
from .device import charge_point_device_info
from .models import ChargePoint

_DESCRIPTION = BinarySensorEntityDescription(
    key="available",
    translation_key="available",
    icon="mdi:ev-station",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Maak per laadpaal in het gebied een beschikbaarheidssensor aan."""
    coordinator = get_coordinator(hass, entry)
    async_add_entities(
        ChargePointAvailableSensor(coordinator, cp) for cp in coordinator.data or []
    )


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
