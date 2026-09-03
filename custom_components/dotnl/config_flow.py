"""Config flow: gebied (boundingbox) + poll-interval instellen, met live test-fetch."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import async_fetch_charge_points
from .const import (
    CONF_MAX_LAT,
    CONF_MAX_LON,
    CONF_MIN_LAT,
    CONF_MIN_LON,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .models import BoundingBox, BoundingBoxAreaError, BoundingBoxRangeError, DotnlApiError

_LOGGER = logging.getLogger(__name__)

STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_MIN_LON): vol.Coerce(float),
        vol.Required(CONF_MIN_LAT): vol.Coerce(float),
        vol.Required(CONF_MAX_LON): vol.Coerce(float),
        vol.Required(CONF_MAX_LAT): vol.Coerce(float),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
        ),
    }
)


class DotnlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow voor een te monitoren gebied."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Eerste stap: gebied instellen en direct testen."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if error_key := await self._async_validate(user_input):
                errors["base"] = error_key
            else:
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=STEP_SCHEMA, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Hertype een bestaand gebied via 'Reconfigure'."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            if error_key := await self._async_validate(user_input):
                errors["base"] = error_key
            else:
                return self.async_update_reload_and_abort(entry, data=user_input)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._schema_with_defaults(entry),
            errors=errors,
        )

    async def _async_validate(self, user_input: dict[str, Any]) -> str | None:
        """Valideer de boundingbox en doe een live test-fetch.

        Geeft een foutcode voor de UI terug, of None wanneer alles geldig is.
        """
        try:
            bbox = BoundingBox(
                user_input[CONF_MIN_LON],
                user_input[CONF_MIN_LAT],
                user_input[CONF_MAX_LON],
                user_input[CONF_MAX_LAT],
            )
        except BoundingBoxRangeError:
            return "invalid_bbox"
        except BoundingBoxAreaError:
            return "bbox_too_large"

        session = async_get_clientsession(self.hass)
        try:
            points = await async_fetch_charge_points(session, bbox)
        except DotnlApiError:
            _LOGGER.warning("Test-fetch tijdens configuratie mislukt voor %s", bbox)
            return "cannot_connect"

        if not points:
            return "no_charge_points"
        return None

    def _schema_with_defaults(self, entry: config_entries.ConfigEntry) -> vol.Schema:
        """Reconfigure-formulier met de huidige waarden als standaard."""
        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=entry.data.get(CONF_NAME, "")): str,
                vol.Required(CONF_MIN_LON, default=entry.data[CONF_MIN_LON]): vol.Coerce(float),
                vol.Required(CONF_MIN_LAT, default=entry.data[CONF_MIN_LAT]): vol.Coerce(float),
                vol.Required(CONF_MAX_LON, default=entry.data[CONF_MAX_LON]): vol.Coerce(float),
                vol.Required(CONF_MAX_LAT, default=entry.data[CONF_MAX_LAT]): vol.Coerce(float),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )
