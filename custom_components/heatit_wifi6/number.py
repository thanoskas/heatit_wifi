"""Number platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import CONF_NAME, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .api import HeatitWiFi6API
from .entity import HeatitWiFi6Entity


@dataclass(frozen=True, kw_only=True)
class HeatitWiFi6NumberEntityDescription(NumberEntityDescription):
    """Describe a Heatit WiFi6 number backed by a device parameter."""

    parameter: str
    value_fn: Callable[[dict[str, Any]], float | None]


def _parameter_field(name: str) -> Callable[[dict[str, Any]], float | None]:
    return lambda data: (data.get("parameters") or {}).get(name)


def _calibration(key: str, parameter: str) -> HeatitWiFi6NumberEntityDescription:
    return HeatitWiFi6NumberEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-6.0,
        native_max_value=6.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        parameter=parameter,
        value_fn=_parameter_field(parameter),
    )


def _brightness(key: str, parameter: str) -> HeatitWiFi6NumberEntityDescription:
    # 1-10 maps to 10%-100% display brightness on the device.
    return HeatitWiFi6NumberEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_min_value=1,
        native_max_value=10,
        native_step=1,
        mode=NumberMode.SLIDER,
        parameter=parameter,
        value_fn=_parameter_field(parameter),
    )


NUMBER_DESCRIPTIONS: tuple[HeatitWiFi6NumberEntityDescription, ...] = (
    HeatitWiFi6NumberEntityDescription(
        key="hysteresis",
        translation_key="hysteresis",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0.3,
        native_max_value=3.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        parameter="temperatureControlHysteresis",
        value_fn=_parameter_field("temperatureControlHysteresis"),
    ),
    _brightness("active_display_brightness", "activeDisplayBrightness"),
    _brightness("standby_display_brightness", "standbyDisplayBrightness"),
    _calibration("internal_calibration", "internalCalibration"),
    _calibration("floor_calibration", "floorCalibration"),
    _calibration("external_calibration", "externalCalibration"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFi6ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 numbers from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        HeatitWiFi6Number(
            data.coordinator, data.api, name, data.device_id, description
        )
        for description in NUMBER_DESCRIPTIONS
    )


class HeatitWiFi6Number(HeatitWiFi6Entity, NumberEntity):
    """A Heatit WiFi6 number that adjusts a numeric device parameter."""

    entity_description: HeatitWiFi6NumberEntityDescription

    def __init__(
        self,
        coordinator,
        api: HeatitWiFi6API,
        device_name: str,
        device_id: str,
        description: HeatitWiFi6NumberEntityDescription,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, device_name, device_id)
        self.entity_description = description
        self._api = api
        self._attr_unique_id = f"heatit_wifi6_{device_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return self.entity_description.value_fn(data)

    async def async_set_native_value(self, value: float) -> None:
        """Write the new value to the device."""
        parameter = self.entity_description.parameter
        # The brightness parameters are integers in the API.
        payload: float | int = int(value) if self.entity_description.native_step == 1 else round(value, 1)
        if not await self._api.set_parameter(parameter, payload):
            raise HomeAssistantError(
                f"Failed to set {parameter} to {payload} on the Heatit thermostat"
            )
        await self.coordinator.async_request_refresh()
