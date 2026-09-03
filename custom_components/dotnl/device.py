"""Device-registry-hulp: elke laadpaal wordt één device in Home Assistant."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .models import ChargePoint


def device_info_from_parts(cp_id: str, address: str | None, operator: str | None) -> DeviceInfo:
    """DeviceInfo op basis van losse velden (deelbaar door beide datasets).

    De device-identifiers zijn gebaseerd op het laadpaal-id; realtime feed en
    OCPI-bulkdataset leveren daardoor entiteiten onder hetzelfde apparaat.
    """
    short_id = cp_id.rsplit("-", 1)[-1]
    device_name = f"{address} ({short_id})" if address else short_id
    return DeviceInfo(
        identifiers={(DOMAIN, cp_id)},
        name=device_name,
        manufacturer=operator,
        model="Laadpaal",
    )


def charge_point_device_info(cp: ChargePoint) -> DeviceInfo:
    """DeviceInfo voor een laadpaal uit de realtime feed."""
    return device_info_from_parts(cp.cp_id, cp.address, cp.operator)
