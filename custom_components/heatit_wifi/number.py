"""Number platform for the Heatit WiFi thermostat."""
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
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFiConfigEntry
from .api import HeatitWiFiAPI
from .entity import HeatitWiFiEntity


@dataclass(frozen=True, kw_only=True)
class HeatitWiFiNumberEntityDescription(NumberEntityDescription):
    """Describe a Heatit WiFi number backed by a device parameter."""

    parameter: str
    value_fn: Callable[[dict[str, Any]], float | None]
    # The WiFi7 renamed some parameters (e.g. internalCalibration ->
    # internalSensorCalibration); when set, reads accept either name and
    # writes use whichever the device actually reports.
    alt_parameter: str | None = None
    # Converts the HA value into the API payload. Defaults to an int for
    # integer steps and a one-decimal float otherwise.
    payload_fn: Callable[[float], Any] | None = None
    # Parameters that only exist on the WiFi7 (e.g. Relay mode timers).
    wifi7_only: bool = False


def _parameter_field(name: str) -> Callable[[dict[str, Any]], float | None]:
    return lambda data: (data.get("parameters") or {}).get(name)


def _size_of_load(data: dict[str, Any]) -> float | None:
    # The API stores the load in 100 W increments (0 = use metering).
    value = (data.get("parameters") or {}).get("sizeOfLoad")
    return None if value is None else value * 100


def _power_regulator_active_time(data: dict[str, Any]) -> float | None:
    # The API stores the PWER duty cycle in 10 % steps (1 = 10 %, 3 min of
    # the 30 min cycle; default 2 = 20 %).
    value = (data.get("parameters") or {}).get("powerRegulatorActiveTime")
    return None if value is None else value * 10


def _action_after_error_payload(value: float) -> int:
    # Valid values are 0 (stay off) or 10-65535 seconds; round the
    # unusable 1-9 s range down to "off".
    return 0 if value < 10 else int(value)


def _temperature_limit(
    key: str, parameter: str, *, enabled: bool = False
) -> HeatitWiFiNumberEntityDescription:
    return HeatitWiFiNumberEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=enabled,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5.0,
        native_max_value=40.0,
        native_step=0.5,
        mode=NumberMode.BOX,
        parameter=parameter,
        value_fn=_parameter_field(parameter),
    )


def _duration(
    key: str, parameter: str, max_value: int
) -> HeatitWiFiNumberEntityDescription:
    # WiFi7 Relay mode timers, in seconds (0 = disabled).
    return HeatitWiFiNumberEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=0,
        native_max_value=max_value,
        native_step=1,
        mode=NumberMode.BOX,
        parameter=parameter,
        value_fn=_parameter_field(parameter),
        wifi7_only=True,
    )


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
) -> HeatitWiFiNumberEntityDescription:
    return HeatitWiFiNumberEntityDescription(
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


def _brightness(key: str, parameter: str) -> HeatitWiFiNumberEntityDescription:
    # WiFi6 uses a 1-10 scale (x10%); WiFi7 firmware reports 0-100 in
    # steps of 10. The entity switches scale based on the reported model.
    return HeatitWiFiNumberEntityDescription(
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


NUMBER_DESCRIPTIONS: tuple[HeatitWiFiNumberEntityDescription, ...] = (
    HeatitWiFiNumberEntityDescription(
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
    HeatitWiFiNumberEntityDescription(
        key="power_regulator_active_time",
        translation_key="power_regulator_active_time",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=10,
        native_max_value=100,
        native_step=10,
        mode=NumberMode.SLIDER,
        parameter="powerRegulatorActiveTime",
        value_fn=_power_regulator_active_time,
        payload_fn=lambda value: int(round(value / 10)),
    ),
    # Floor limits protect e.g. wooden floors, so they are on by default;
    # the internal/external limits are opt-in.
    _temperature_limit("floor_min_temperature", "floorMinimumTemperatureLimit", enabled=True),
    _temperature_limit("floor_max_temperature", "floorMaximumTemperatureLimit", enabled=True),
    _temperature_limit("internal_min_temperature", "internalMinimumTemperatureLimit"),
    _temperature_limit("internal_max_temperature", "internalMaximumTemperatureLimit"),
    _temperature_limit("external_min_temperature", "externalMinimumTemperatureLimit"),
    _temperature_limit("external_max_temperature", "externalMaximumTemperatureLimit"),
    HeatitWiFiNumberEntityDescription(
        key="size_of_load",
        translation_key="size_of_load",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=9900,
        native_step=100,
        mode=NumberMode.BOX,
        parameter="sizeOfLoad",
        value_fn=_size_of_load,
        payload_fn=lambda value: int(round(value / 100)),
    ),
    HeatitWiFiNumberEntityDescription(
        key="action_after_error",
        translation_key="action_after_error",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
        parameter="actionAfterError",
        value_fn=_parameter_field("actionAfterError"),
        payload_fn=_action_after_error_payload,
    ),
    _duration("automatic_turn_off", "automaticTurnOff", 86400),
    _duration("automatic_turn_on", "automaticTurnOn", 86400),
    _duration("turn_off_delay", "turnOffDelayTime", 60),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi numbers from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    # WiFi7-only parameters are skipped on a WiFi6 (which reports no
    # model field and can't be in Relay mode).
    status = data.coordinator.data or {}
    is_wifi7 = bool(status.get("model")) or (
        (status.get("parameters") or {}).get("sensorMode") == 7
    )
    async_add_entities(
        HeatitWiFiNumber(
            data.coordinator, data.api, name, data.device_id, description
        )
        for description in NUMBER_DESCRIPTIONS
        if is_wifi7 or not description.wifi7_only
    )


class HeatitWiFiNumber(HeatitWiFiEntity, NumberEntity):
    """A Heatit WiFi number that adjusts a numeric device parameter."""

    entity_description: HeatitWiFiNumberEntityDescription

    def __init__(
        self,
        coordinator,
        api: HeatitWiFiAPI,
        device_name: str,
        device_id: str,
        description: HeatitWiFiNumberEntityDescription,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, device_name, device_id)
        self.entity_description = description
        self._api = api
        self._attr_unique_id = f"heatit_wifi_{device_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Unavailable when the device doesn't report the parameter.

        A WiFi7 in Relay mode drops the thermostat-only parameters
        (hysteresis, calibrations, ...) from /api/status.
        """
        if not super().available:
            return False
        return self.native_value is not None

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return self.entity_description.value_fn(data)

    def _percent_scale(self) -> bool:
        """True when this is a brightness on the WiFi7's 0-100 scale.

        Decided by the model, not the value: a WiFi7 dimmed to 10 or less
        would otherwise drop to the WiFi6's 1-10 slider and could no longer
        be raised above 10 from Home Assistant.
        """
        if self.entity_description.key not in BRIGHTNESS_KEYS:
            return False
        if (self.coordinator.data or {}).get("model"):
            return True
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
        payload: Any
        if (payload_fn := self.entity_description.payload_fn) is not None:
            payload = payload_fn(value)
        else:
            # Integer-step parameters (brightness, timers) are integers
            # in the API; the rest take one decimal.
            step = self.native_step
            payload = int(value) if step and step >= 1 else round(value, 1)
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
