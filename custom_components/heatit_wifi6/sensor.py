"""Sensor platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_NAME,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .entity import HeatitWiFi6Entity


@dataclass(frozen=True, kw_only=True)
class HeatitWiFi6SensorEntityDescription(SensorEntityDescription):
    """Describe a Heatit WiFi6 sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _param(name: str) -> Callable[[dict[str, Any]], Any]:
    return lambda data: (data.get("parameters") or {}).get(name)


def _current_temperature(data: dict[str, Any]) -> float | None:
    sensor_mode = (data.get("parameters") or {}).get("sensorMode")
    if sensor_mode == 0:
        return data.get("floorTemperature")
    if sensor_mode in (3, 4):
        return data.get("externalTemperature")
    return data.get("internalTemperature")


def _target_temperature(data: dict[str, Any]) -> float | None:
    params = data.get("parameters") or {}
    operating_mode = params.get("operatingMode")
    if operating_mode == 1:
        return params.get("heatingSetpoint")
    if operating_mode == 2:
        return params.get("coolingSetpoint")
    if operating_mode == 3:
        return params.get("ecoSetpoint")
    return None


def _wifi_signal(data: dict[str, Any]) -> str | None:
    return (data.get("network") or {}).get("wifiSignalStrength")


SENSOR_DESCRIPTIONS: tuple[HeatitWiFi6SensorEntityDescription, ...] = (
    HeatitWiFi6SensorEntityDescription(
        key="current_temperature",
        translation_key="current_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_current_temperature,
    ),
    HeatitWiFi6SensorEntityDescription(
        key="target_temperature",
        translation_key="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_target_temperature,
    ),
    HeatitWiFi6SensorEntityDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("currentPower"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="energy",
        translation_key="energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get("totalConsumption"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="internal_temperature",
        translation_key="internal_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("internalTemperature"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="external_temperature",
        translation_key="external_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("externalTemperature"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="floor_temperature",
        translation_key="floor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("floorTemperature"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="heating_setpoint",
        translation_key="heating_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_param("heatingSetpoint"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="cooling_setpoint",
        translation_key="cooling_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_param("coolingSetpoint"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="eco_setpoint",
        translation_key="eco_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_param("ecoSetpoint"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="wifi_signal_strength",
        translation_key="wifi_signal_strength",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_wifi_signal,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFi6ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 sensors from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        HeatitWiFi6Sensor(data.coordinator, name, data.device_id, description)
        for description in SENSOR_DESCRIPTIONS
    )


class HeatitWiFi6Sensor(HeatitWiFi6Entity, SensorEntity):
    """A Heatit WiFi6 sensor backed by a SensorEntityDescription."""

    entity_description: HeatitWiFi6SensorEntityDescription

    def __init__(
        self,
        coordinator,
        device_name: str,
        device_id: str,
        description: HeatitWiFi6SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_name, device_id)
        self.entity_description = description
        self._attr_unique_id = f"heatit_wifi6_{device_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if not data:
            return None
        return self.entity_description.value_fn(data)
