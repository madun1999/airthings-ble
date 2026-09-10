"""Home Assistant coordinator for Corentium Home 2."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from time import monotonic
from typing import Any

from airthings_ble import AirthingsBluetoothDeviceData, AirthingsDevice
from bleak.exc import BleakError

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

_SENSOR_KEYS = {
    "radon_1day_avg": "radon_24h",
    "radon_week_avg": "radon_7d",
    "radon_month_avg": "radon_30d",
    "radon_year_avg": "radon_1y",
    "temperature": "temperature",
    "humidity": "humidity",
    "battery_voltage": "battery_voltage",
    "battery": "battery",
}


class CorentiumCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll a Corentium through Home Assistant's Bluetooth manager."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.address = address
        self.parser = AirthingsBluetoothDeviceData(
            logger=_LOGGER,
            is_metric=True,
            max_attempts=3,
        )
        self.device: AirthingsDevice | None = None
        self.last_success: datetime | None = None
        self.last_error: str | None = None
        self.last_update_duration: float | None = None
        self.received_fields: tuple[str, ...] = ()

    async def _async_update_data(self) -> dict[str, Any]:
        started = monotonic()
        try:
            data = await self._async_fetch_data()
        except (BleakError, TimeoutError, ValueError) as err:
            self.last_error = f"{type(err).__name__}: {err}"
            raise UpdateFailed(f"Could not read {self.address}: {err}") from err
        finally:
            self.last_update_duration = monotonic() - started

        self.last_success = datetime.now(timezone.utc)
        self.last_error = None
        self.received_fields = tuple(sorted(data))
        return data

    async def _async_fetch_data(self) -> dict[str, Any]:
        """Fetch and normalize one reading from the Bluetooth device."""
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass,
            self.address,
            connectable=True,
        )
        if ble_device is None:
            raise BleakError(
                f"Bluetooth device {self.address} is not currently available"
            )

        device = await self.parser.update_device(ble_device)
        self.device = device
        data = {
            target: device.sensors[source]
            for source, target in _SENSOR_KEYS.items()
            if source in device.sensors
        }
        if (age := device.sensors.get("oldest_value_age")) is not None:
            data["oldest_value_timestamp"] = datetime.now(timezone.utc) - timedelta(
                seconds=float(age)
            )
        return data
