"""Device-registry-hulp: elke laadpaal wordt één device in Home Assistant."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .models import ChargePoint


def charge_point_device_info(cp: ChargePoint) -> DeviceInfo:
    """DeviceInfo voor een laadpaal; uniek per cp_id, herkenbaar per adres."""
    short_id = cp.cp_id.rsplit("-", 1)[-1]
    device_name = f"{cp.address} ({short_id})" if cp.address else short_id
    return DeviceInfo(
        identifiers={(DOMAIN, cp.cp_id)},
        name=device_name,
        manufacturer=cp.operator,
        model="Laadpaal",
    )
