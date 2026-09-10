"""Airthings Corentium Home 2 integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, issue_registry as ir

from .const import DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import CorentiumCoordinator

PLATFORMS = (Platform.SENSOR,)
_OFFICIAL_DOMAIN = "airthings_ble"


def _normalized_address(value: object) -> str:
    """Normalize Bluetooth addresses for comparisons and issue IDs."""
    return str(value).replace(":", "").replace("-", "").upper()


def _update_conflict_repair(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Warn when the official integration is configured for this device."""
    address = _normalized_address(entry.data[CONF_ADDRESS])
    issue_id = f"official_integration_conflict_{address.lower()}"
    conflict = any(
        address
        in {
            _normalized_address(other.data.get(CONF_ADDRESS, "")),
            _normalized_address(other.unique_id or ""),
        }
        for other in hass.config_entries.async_entries(_OFFICIAL_DOMAIN)
    )
    if conflict:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="official_integration_conflict",
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=60)),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Import legacy YAML configuration into a config entry."""
    if settings := config.get(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=dict(settings),
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Corentium config entry."""
    _update_conflict_repair(hass, entry)
    coordinator = CorentiumCoordinator(
        hass,
        entry.data[CONF_ADDRESS],
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Corentium config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
