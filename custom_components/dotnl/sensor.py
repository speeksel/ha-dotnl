"""Sensoren per laadpaal: aantal vrije en totaal aantal aansluitingen."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DotnlCoordinator, get_coordinator
from .device import charge_point_device_info
from .models import ChargePoint

AVAILABLE_DESCRIPTION = SensorEntityDescription(
    key="available_connectors",
    translation_key="available_connectors",
    icon="mdi:ev-plug-type2",
    state_class="measurement",
)

TOTAL_DESCRIPTION = SensorEntityDescription(
    key="total_connectors",
    translation_key="total_connectors",
    icon="mdi:ev-station",
    state_class="measurement",
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Maak per laadpaal een vrije- en een totaal-aansluitingensensor aan."""
    coordinator = get_coordinator(hass, entry)
    async_add_entities(
        ChargePointCountSensor(coordinator, cp, description)
        for cp in coordinator.data or []
        for description in (AVAILABLE_DESCRIPTION, TOTAL_DESCRIPTION)
    )


class ChargePointCountSensor(CoordinatorEntity[DotnlCoordinator], SensorEntity):
    """Aantal aansluitingen (vrij of totaal) van één laadpaal."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DotnlCoordinator,
        cp: ChargePoint,
        description: SensorEntityDescription,
    ) -> None:
        """Houd de identiteit vast; de waarde komt uit de coordinator."""
        super().__init__(coordinator)
        self.entity_description = description
        self._cp_id = cp.cp_id
        self._attr_unique_id = f"{cp.cp_id}_{description.key}"
        self._attr_device_info = charge_point_device_info(cp)

    def _current(self) -> ChargePoint | None:
        """Zoek de actuele staat van deze laadpaal in de coordinator-data."""
        for cp in self.coordinator.data or []:
            if cp.cp_id == self._cp_id:
                return cp
        return None

    @property
    def native_value(self) -> int:
        """Het huidige aantal vrije of totale aansluitingen."""
        current = self._current()
        if current is None:
            return 0
        if self.entity_description is AVAILABLE_DESCRIPTION:
            return current.available
        return current.total
