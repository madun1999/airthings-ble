"""Sensor entities for Corentium Home 2."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CorentiumCoordinator

_RADON_UNIT = "Bq/m³"


@dataclass(frozen=True, kw_only=True)
class CorentiumSensorDescription(SensorEntityDescription):
    """Corentium sensor metadata."""


SENSORS = (
    CorentiumSensorDescription(
        key="radon_24h",
        translation_key="radon_24h",
        name="Radon 24 hour average",
        native_unit_of_measurement=_RADON_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CorentiumSensorDescription(
        key="radon_7d",
        translation_key="radon_7d",
        name="Radon 7 day average",
        native_unit_of_measurement=_RADON_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CorentiumSensorDescription(
        key="radon_30d",
        translation_key="radon_30d",
        name="Radon 30 day average",
        native_unit_of_measurement=_RADON_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CorentiumSensorDescription(
        key="radon_1y",
        translation_key="radon_1y",
        name="Radon 1 year average",
        native_unit_of_measurement=_RADON_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CorentiumSensorDescription(
        key="temperature",
        translation_key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    CorentiumSensorDescription(
        key="humidity",
        translation_key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    CorentiumSensorDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        name="Battery voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
    ),
    CorentiumSensorDescription(
        key="battery",
        translation_key="battery",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CorentiumSensorDescription(
        key="oldest_value_timestamp",
        translation_key="oldest_value_timestamp",
        name="Oldest value timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a config entry."""
    coordinator: CorentiumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CorentiumSensor(coordinator, description)
        for description in SENSORS
        if description.key in coordinator.data
    )


class CorentiumSensor(CoordinatorEntity[CorentiumCoordinator], SensorEntity):
    """One value from the device's latest-reading map."""

    entity_description: CorentiumSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CorentiumCoordinator,
        description: CorentiumSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        device = coordinator.device
        assert device is not None
        identifier = coordinator.address.replace(":", "").lower()
        self._attr_unique_id = f"{identifier}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            name=device.name or device.friendly_name(),
            manufacturer=device.manufacturer or "Airthings",
            model=device.model.product_name,
            serial_number=device.identifier or None,
            hw_version=device.hw_version or None,
            sw_version=device.sw_version or None,
        )

    @property
    def native_value(self):
        """Return the latest reading."""
        return self.coordinator.data.get(self.entity_description.key)
