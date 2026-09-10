"""Config flow for Corentium Home 2."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME, CONF_SCAN_INTERVAL

from .const import DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN


class CorentiumConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure a Corentium Home 2."""

    VERSION = 1

    def __init__(self) -> None:
        self._address: str | None = None
        self._name = DEFAULT_NAME

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        self._address = discovery_info.address
        self._name = discovery_info.name or DEFAULT_NAME
        await self.async_set_unique_id(self._address)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_ADDRESS: self._address,
                    CONF_NAME: self._name,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                },
            )
        return self.async_show_form(step_id="confirm")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a device by Bluetooth address."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={**user_input, CONF_ADDRESS: address},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=60)),
                }
            ),
        )

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Import legacy YAML configuration."""
        address = import_data[CONF_ADDRESS].upper()
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured(updates={CONF_ADDRESS: address})
        name = import_data.get(CONF_NAME, DEFAULT_NAME)
        return self.async_create_entry(
            title=name,
            data={
                CONF_ADDRESS: address,
                CONF_NAME: name,
                CONF_SCAN_INTERVAL: import_data.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            },
        )
