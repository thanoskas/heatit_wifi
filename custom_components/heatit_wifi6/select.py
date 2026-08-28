"""Select platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .api import HeatitWiFi6API
from .entity import HeatitWiFi6Entity

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
SENSOR_MODE_VALUES = {option: mode for mode, option in SENSOR_MODE_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFi6ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 selects from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        [
            HeatitWiFi6SensorModeSelect(
                data.coordinator, data.api, name, data.device_id
            ),
            HeatitWiFi6RegulationModeSelect(
                data.coordinator, data.api, name, data.device_id
            ),
        ]
    )


class HeatitWiFi6SensorModeSelect(HeatitWiFi6Entity, SelectEntity):
    """Select which sensor the thermostat regulates with."""

    _attr_translation_key = "sensor_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_options = list(SENSOR_MODE_VALUES)

    def __init__(
        self,
        coordinator,
        api: HeatitWiFi6API,
        device_name: str,
        device_id: str,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, device_name, device_id)
        self._api = api
        self._attr_unique_id = f"heatit_wifi6_{device_id}_sensor_mode"

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        mode = (data.get("parameters") or {}).get("sensorMode")
        return SENSOR_MODE_OPTIONS.get(mode)

    async def async_select_option(self, option: str) -> None:
        """Write the chosen sensor mode to the device."""
        mode = SENSOR_MODE_VALUES[option]
        if not await self._api.set_parameter("sensorMode", mode):
            raise HomeAssistantError(
                f"Failed to set sensorMode to {mode} on the Heatit thermostat"
            )
        if data := self.coordinator.data:
            data.setdefault("parameters", {})["sensorMode"] = mode
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class HeatitWiFi6RegulationModeSelect(HeatitWiFi6Entity, SelectEntity):
    """Choose between Hysteresis (HYST) and PWM regulation."""

    _attr_translation_key = "regulation_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_options = ["hysteresis", "pwm"]

    def __init__(
        self,
        coordinator,
        api: HeatitWiFi6API,
        device_name: str,
        device_id: str,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, device_name, device_id)
        self._api = api
        self._attr_unique_id = f"heatit_wifi6_{device_id}_regulation_mode"

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        value = (data.get("parameters") or {}).get("regulationMode")
        if value is None:
            return None
        return "pwm" if value else "hysteresis"

    async def async_select_option(self, option: str) -> None:
        """Write the chosen regulation mode to the device."""
        value = option == "pwm"
        if not await self._api.set_parameter("regulationMode", value):
            raise HomeAssistantError(
                f"Failed to set regulationMode to {value} on the Heatit thermostat"
            )
        if data := self.coordinator.data:
            data.setdefault("parameters", {})["regulationMode"] = value
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
