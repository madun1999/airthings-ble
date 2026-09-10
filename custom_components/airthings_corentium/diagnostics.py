"""Diagnostics support for Airthings Corentium Home 2."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import CorentiumCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator: CorentiumCoordinator = hass.data[DOMAIN][entry.entry_id]
    device = coordinator.device
    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)

    return {
        "config_entry": {
            "title": entry.title,
            "source": entry.source,
            "scan_interval": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
            "address": _redact_address(entry.data[CONF_ADDRESS]),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_success": coordinator.last_success,
            "last_error": coordinator.last_error,
            "last_update_duration_seconds": coordinator.last_update_duration,
            "received_fields": coordinator.received_fields,
        },
        "device": {
            "model": device.model.product_name if device else None,
            "serial_number": "**REDACTED**" if device and device.identifier else None,
            "hardware_version": device.hw_version if device else None,
            "software_version": device.sw_version if device else None,
        },
        "device_registry_entries": [
            {
                "name": item.name,
                "model": item.model,
                "manufacturer": item.manufacturer,
                "disabled": item.disabled_by is not None,
            }
            for item in devices
        ],
    }


def _redact_address(address: str) -> str:
    """Keep enough of an address to distinguish devices without exposing it."""
    compact = address.replace(":", "").replace("-", "")
    return f"**:**:**:**:{compact[-4:-2]}:{compact[-2:]}" if len(compact) >= 4 else "**"
