"""Select platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .api import HeatitWiFi6API
from .entity import HeatitWiFi6Entity


@dataclass(frozen=True, kw_only=True)
class HeatitWiFi6SelectEntityDescription(SelectEntityDescription):
    """Describe a Heatit WiFi6 select backed by an enumerated parameter."""

    parameter: str
    # Maps the raw API value to an option key. Takes the status payload
    # because some enumerations are numbered differently on the WiFi7.
    options_fn: Callable[[dict[str, Any]], dict[int, str]]
    # The WiFi7 validates parameter types strictly.
    payload_fn: Callable[[int], Any] = int
    # Parameters that only exist on the WiFi7.
    wifi7_only: bool = False


def _static(options: dict[int, str]) -> Callable[[dict[str, Any]], dict[int, str]]:
    return lambda data: options


def _is_wifi7(data: dict[str, Any]) -> bool:
    # Only the WiFi7 firmware reports a model field in /api/status.
    return bool(data.get("model"))


# Maps the numeric sensorMode parameter to option keys. Mode 7 (Relay)
# exists only on the WiFi7 firmware; selecting it on a WiFi6 fails with
# an error from the device.
SENSOR_MODE_OPTIONS: dict[int, str] = {
    0: "floor",
    1: "internal",
    2: "internal_floor_limit",
    3: "external",
    4: "external_floor_limit",
    5: "power_regulator",
    7: "relay",
}

# regulationMode is a boolean: false = Hysteresis (HYST), true = PWM.
REGULATION_MODE_OPTIONS: dict[int, str] = {0: "hysteresis", 1: "pwm"}

# NTC resistance of the connected floor/external sensor. The WiFi6 and
# WiFi7 number these differently (the WiFi7 moved 6.8 kΩ to the front).
SENSOR_VALUE_OPTIONS_WIFI6: dict[int, str] = {
    0: "10k",
    1: "12k",
    2: "15k",
    3: "22k",
    4: "33k",
    5: "47k",
    6: "6k8",
    7: "100k",
}
SENSOR_VALUE_OPTIONS_WIFI7: dict[int, str] = {
    0: "6k8",
    1: "10k",
    2: "12k",
    3: "15k",
    4: "22k",
    5: "33k",
    6: "47k",
    7: "100k",
}

# WiFi7: which sensor to regulate with if the wireless external sensor
# stops reporting.
EXTERNAL_SENSOR_FALLBACK_OPTIONS: dict[int, str] = {
    0: "off",
    1: "floor",
    2: "internal",
    3: "internal_floor_limit",
    4: "external",
    5: "external_floor_limit",
    6: "power_regulator",
}

# WiFi7 Relay mode: relay state after a power loss.
DEVICE_RESTORE_STATE_OPTIONS: dict[int, str] = {
    0: "previous",
    1: "on",
    2: "off",
}


def _sensor_value_options(data: dict[str, Any]) -> dict[int, str]:
    return SENSOR_VALUE_OPTIONS_WIFI7 if _is_wifi7(data) else SENSOR_VALUE_OPTIONS_WIFI6


SELECT_DESCRIPTIONS: tuple[HeatitWiFi6SelectEntityDescription, ...] = (
    HeatitWiFi6SelectEntityDescription(
        key="sensor_mode",
        translation_key="sensor_mode",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        options=list(SENSOR_MODE_OPTIONS.values()),
        parameter="sensorMode",
        options_fn=_static(SENSOR_MODE_OPTIONS),
    ),
    HeatitWiFi6SelectEntityDescription(
        key="regulation_mode",
        translation_key="regulation_mode",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        options=list(REGULATION_MODE_OPTIONS.values()),
        parameter="regulationMode",
        options_fn=_static(REGULATION_MODE_OPTIONS),
        payload_fn=bool,
    ),
    HeatitWiFi6SelectEntityDescription(
        key="sensor_value",
        translation_key="sensor_value",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        options=list(SENSOR_VALUE_OPTIONS_WIFI7.values()),
        parameter="sensorValue",
        options_fn=_sensor_value_options,
    ),
    HeatitWiFi6SelectEntityDescription(
        key="external_sensor_fallback",
        translation_key="external_sensor_fallback",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        options=list(EXTERNAL_SENSOR_FALLBACK_OPTIONS.values()),
        parameter="externalSensorFallback",
        options_fn=_static(EXTERNAL_SENSOR_FALLBACK_OPTIONS),
        wifi7_only=True,
    ),
    HeatitWiFi6SelectEntityDescription(
        key="device_restore_state",
        translation_key="device_restore_state",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        options=list(DEVICE_RESTORE_STATE_OPTIONS.values()),
        parameter="deviceRestoreState",
        options_fn=_static(DEVICE_RESTORE_STATE_OPTIONS),
        wifi7_only=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFi6ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 selects from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    status = data.coordinator.data or {}
    is_wifi7 = _is_wifi7(status) or (
        (status.get("parameters") or {}).get("sensorMode") == 7
    )
    async_add_entities(
        HeatitWiFi6Select(data.coordinator, data.api, name, data.device_id, description)
        for description in SELECT_DESCRIPTIONS
        if is_wifi7 or not description.wifi7_only
    )


class HeatitWiFi6Select(HeatitWiFi6Entity, SelectEntity):
    """A Heatit WiFi6 select that sets an enumerated device parameter."""

    entity_description: HeatitWiFi6SelectEntityDescription

    def __init__(
        self,
        coordinator,
        api: HeatitWiFi6API,
        device_name: str,
        device_id: str,
        description: HeatitWiFi6SelectEntityDescription,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, device_name, device_id)
        self.entity_description = description
        self._api = api
        self._attr_unique_id = f"heatit_wifi6_{device_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Unavailable when the device doesn't report the parameter.

        A WiFi7 in Relay mode drops the thermostat-only parameters
        (e.g. regulationMode) from /api/status, and vice versa.
        """
        if not super().available:
            return False
        return self.current_option is not None

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        raw = (data.get("parameters") or {}).get(self.entity_description.parameter)
        if raw is None:
            return None
        # Booleans (regulationMode) hash like 0/1, so the lookup works.
        return self.entity_description.options_fn(data).get(raw)

    async def async_select_option(self, option: str) -> None:
        """Write the chosen option to the device."""
        description = self.entity_description
        data = self.coordinator.data or {}
        options = description.options_fn(data)
        value = next(key for key, name in options.items() if name == option)
        payload = description.payload_fn(value)
        if not await self._api.set_parameter(description.parameter, payload):
            raise HomeAssistantError(
                f"Failed to set {description.parameter} to {payload}"
                " on the Heatit thermostat"
            )
        # Update the shared cache and notify all entities (climate and
        # the relay switch depend on sensorMode); no immediate readback
        # since the firmware's status can lag the write.
        if data:
            data.setdefault("parameters", {})[description.parameter] = payload
            self.coordinator.async_set_updated_data(data)
        else:
            await self.coordinator.async_request_refresh()
