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
from homeassistant.const import (
    CONF_NAME,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
)
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
    # The WiFi7 renamed some parameters (e.g. internalCalibration ->
    # internalSensorCalibration); when set, reads accept either name and
    # writes use whichever the device actually reports.
    alt_parameter: str | None = None


def _parameter_field(name: str) -> Callable[[dict[str, Any]], float | None]:
    return lambda data: (data.get("parameters") or {}).get(name)


def _dual_parameter_field(
    primary: str, alt: str
) -> Callable[[dict[str, Any]], float | None]:
    def _value(data: dict[str, Any]) -> float | None:
        params = data.get("parameters") or {}
        value = params.get(primary)
        return params.get(alt) if value is None else value

    return _value


def _calibration(
    key: str, parameter: str, alt_parameter: str
) -> HeatitWiFi6NumberEntityDescription:
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
        alt_parameter=alt_parameter,
        value_fn=_dual_parameter_field(parameter, alt_parameter),
    )


BRIGHTNESS_KEYS = {"active_display_brightness", "standby_display_brightness"}


def _brightness(key: str, parameter: str) -> HeatitWiFi6NumberEntityDescription:
    # WiFi6 uses a 1-10 scale (x10%); WiFi7 firmware reports 0-100 in
    # steps of 10. The entity switches scale based on the reported value.
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
    _calibration("internal_calibration", "internalCalibration", "internalSensorCalibration"),
    _calibration("floor_calibration", "floorCalibration", "floorSensorCalibration"),
    _calibration("external_calibration", "externalCalibration", "externalSensorCalibration"),
    HeatitWiFi6NumberEntityDescription(
        key="power_regulator_active_time",
        translation_key="power_regulator_active_time",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        parameter="powerRegulatorActiveTime",
        value_fn=_parameter_field("powerRegulatorActiveTime"),
    ),
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

    def _percent_scale(self) -> bool:
        """True when this is a brightness on the WiFi7's 0-100 scale."""
        if self.entity_description.key not in BRIGHTNESS_KEYS:
            return False
        value = self.native_value
        return value is not None and value > 10

    @property
    def native_min_value(self) -> float:
        return 0 if self._percent_scale() else super().native_min_value

    @property
    def native_max_value(self) -> float:
        return 100 if self._percent_scale() else super().native_max_value

    @property
    def native_step(self) -> float | None:
        return 10 if self._percent_scale() else super().native_step

    def _api_parameter(self) -> str:
        """Return the parameter name this device actually uses."""
        description = self.entity_description
        if description.alt_parameter:
            params = (self.coordinator.data or {}).get("parameters") or {}
            if description.parameter not in params and description.alt_parameter in params:
                return description.alt_parameter
        return description.parameter

    async def async_set_native_value(self, value: float) -> None:
        """Write the new value to the device."""
        parameter = self._api_parameter()
        # The brightness parameters are integers in the API.
        step = self.native_step
        payload: float | int = int(value) if step and step >= 1 else round(value, 1)
        if not await self._api.set_parameter(parameter, payload):
            raise HomeAssistantError(
                f"Failed to set {parameter} to {payload} on the Heatit thermostat"
            )
        # Update the shared cache and notify all entities; skip the
        # immediate readback since the firmware's status can lag the
        # write (the next scheduled poll confirms the value).
        if data := self.coordinator.data:
            data.setdefault("parameters", {})[parameter] = payload
            self.coordinator.async_set_updated_data(data)
        else:
            await self.coordinator.async_request_refresh()
