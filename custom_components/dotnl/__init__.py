"""De DOT-NL laadpalen-integratie: polling-coordinator per geconfigureerd gebied."""

from __future__ import annotations

import logging
from datetime import timedelta
from functools import partial

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import async_fetch_charge_points
from .const import (
    CONF_MAX_LAT,
    CONF_MAX_LON,
    CONF_MIN_LAT,
    CONF_MIN_LON,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .models import BoundingBox, ChargePoint, DotnlApiError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

DotnlCoordinator = DataUpdateCoordinator[list[ChargePoint]]


async def _async_fetch(hass: HomeAssistant, bbox: BoundingBox) -> list[ChargePoint]:
    """Haal de laadpalen op en vertaal API-fouten naar UpdateFailed."""
    session = async_get_clientsession(hass)
    try:
        return await async_fetch_charge_points(session, bbox)
    except DotnlApiError as err:
        raise UpdateFailed(str(err)) from err
    except (TimeoutError, ClientError) as err:
        msg = "Fout bij het benaderen van de DOT-NL API"
        raise UpdateFailed(msg) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet een geconfigureerd gebied op met een eigen polling-coordinator."""
    bbox = BoundingBox(
        entry.data[CONF_MIN_LON],
        entry.data[CONF_MIN_LAT],
        entry.data[CONF_MAX_LON],
        entry.data[CONF_MAX_LAT],
    )
    interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.title}",
        update_method=partial(_async_fetch, hass, bbox),
        update_interval=timedelta(seconds=interval),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Verwijder een gebied en de bijbehorende entiteiten."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Herlaad het gebied als de configuratie via 'Reconfigure' is aangepast."""
    await hass.config_entries.async_reload(entry.entry_id)


def get_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> DotnlCoordinator:
    """Geef de coordinator van een entry terug (voor platform-setup)."""
    coordinator: DotnlCoordinator = hass.data[DOMAIN][entry.entry_id]
    return coordinator
