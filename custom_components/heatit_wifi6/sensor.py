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
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .const import NTC_FAULT_TEMPERATURE
from .entity import HeatitWiFi6Entity


@dataclass(frozen=True, kw_only=True)
class HeatitWiFi6SensorEntityDescription(SensorEntityDescription):
    """Describe a Heatit WiFi6 sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _param(name: str) -> Callable[[dict[str, Any]], Any]:
    return lambda data: (data.get("parameters") or {}).get(name)


def _ntc_temperature(data: dict[str, Any], field: str) -> float | None:
    value = data.get(field)
    if value == NTC_FAULT_TEMPERATURE:
        return None
    return value


def _current_temperature(data: dict[str, Any]) -> float | None:
    sensor_mode = (data.get("parameters") or {}).get("sensorMode")
    if sensor_mode == 0:
        return _ntc_temperature(data, "floorTemperature")
    if sensor_mode in (3, 4):
        return _ntc_temperature(data, "externalTemperature")
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


def _owd_remaining_time(data: dict[str, Any]) -> int | None:
    # Seconds until Open Window Detection restores the normal setpoint
    # (0 when not triggered). Read-only on the device.
    owd = (data.get("parameters") or {}).get("OWD") or {}
    return owd.get("activeTime")


def _wifi_signal(data: dict[str, Any]) -> int | None:
    # The device reports the RSSI as a string like "-37dBm"; strip the
    # unit suffix so the sensor can be numeric (graphs, alerts).
    # The spec nests it under "network" but real WiFi7 firmware (0.1.13)
    # sends it at the top level of the status payload — accept both.
    raw = data.get("wifiSignalStrength")
    if raw is None:
        raw = (data.get("network") or {}).get("wifiSignalStrength")
    if raw is None:
        return None
    try:
        return int(str(raw).removesuffix("dBm").strip())
    except ValueError:
        return None


def _wifi_quality(data: dict[str, Any]) -> int | None:
    # Human-friendly quality: the common linear RSSI mapping where
    # -100 dBm -> 0 % and -50 dBm or better -> 100 %.
    rssi = _wifi_signal(data)
    if rssi is None:
        return None
    return max(0, min(100, 2 * (rssi + 100)))


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
        value_fn=lambda data: _ntc_temperature(data, "externalTemperature"),
    ),
    HeatitWiFi6SensorEntityDescription(
        key="floor_temperature",
        translation_key="floor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _ntc_temperature(data, "floorTemperature"),
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
        key="open_window_remaining_time",
        translation_key="open_window_remaining_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_owd_remaining_time,
    ),
    HeatitWiFi6SensorEntityDescription(
        key="wifi_signal_strength",
        translation_key="wifi_signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_wifi_signal,
    ),
    HeatitWiFi6SensorEntityDescription(
        key="wifi_signal_quality",
        translation_key="wifi_signal_quality",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:wifi",
        value_fn=_wifi_quality,
    ),
    HeatitWiFi6SensorEntityDescription(
        key="ip_address",
        translation_key="ip_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:ip-network",
        value_fn=lambda data: (data.get("network") or {}).get("ipAddress"),
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
