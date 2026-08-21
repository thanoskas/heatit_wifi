"""Climate platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .api import HeatitWiFi6API
from .entity import HeatitWiFi6Entity

_LOGGER = logging.getLogger(__name__)

OPERATING_MODE_OFF = 0
OPERATING_MODE_HEAT = 1
OPERATING_MODE_COOL = 2
OPERATING_MODE_ECO = 3

SETPOINT_BY_OPERATING_MODE = {
    OPERATING_MODE_HEAT: "heatingSetpoint",
    OPERATING_MODE_COOL: "coolingSetpoint",
    OPERATING_MODE_ECO: "ecoSetpoint",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFi6ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 climate entity from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        [
            HeatitWiFi6Thermostat(
                data.coordinator,
                data.api,
                name,
                data.device_id,
            )
        ]
    )
    _LOGGER.info(
        "Heatit WiFi6 climate entity for %s added to the list of entities", name
    )


class HeatitWiFi6Thermostat(HeatitWiFi6Entity, ClimateEntity):
    """Representation of a Heatit WiFi6 thermostat."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_preset_modes = [PRESET_NONE, PRESET_ECO]
    _attr_min_temp = 5
    _attr_max_temp = 40
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        coordinator,
        api: HeatitWiFi6API,
        device_name: str,
        device_id: str,
    ) -> None:
        """Initialize the thermostat entity."""
        super().__init__(coordinator, device_name, device_id)
        self._api = api
        self._attr_unique_id = f"heatit_wifi6_{device_id}"

    def _parameters(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return data.get("parameters") or {}

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature, picked according to active sensor mode."""
        data = self.coordinator.data
        if not data:
            return None
        sensor_mode = self._parameters().get("sensorMode")
        if sensor_mode == 0:
            return data.get("floorTemperature")
        if sensor_mode in (3, 4):
            return data.get("externalTemperature")
        return data.get("internalTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return setpoint corresponding to the active operating mode."""
        params = self._parameters()
        key = SETPOINT_BY_OPERATING_MODE.get(params.get("operatingMode"))
        if key is None:
            return None
        return params.get(key)

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current HVAC mode."""
        if not self.coordinator.data:
            return HVACMode.OFF
        return self._heatit_operatingmode_to_hvac_mode(
            self._parameters().get("operatingMode")
        )

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action."""
        data = self.coordinator.data
        if not data:
            return HVACAction.OFF
        return self._heatit_state_to_hvac_action(data.get("state"))

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode (eco or none)."""
        if self._parameters().get("operatingMode") == OPERATING_MODE_ECO:
            return PRESET_ECO
        return PRESET_NONE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        if self.hvac_mode == HVACMode.OFF:
            _LOGGER.warning(
                "Cannot set target temperature for %s while device is OFF",
                self._device_name,
            )
            return

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.error("No temperature provided to async_set_temperature")
            return

        operating_mode = self._parameters().get("operatingMode")
        param = SETPOINT_BY_OPERATING_MODE.get(operating_mode)
        if param is None:
            _LOGGER.error(
                "Cannot set temperature: unsupported operating mode %s",
                operating_mode,
            )
            return

        if await self._api.set_parameter(param, temperature):
            params = self.coordinator.data.setdefault("parameters", {})
            params[param] = temperature
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Switch between eco and normal heating modes."""
        if preset_mode == PRESET_ECO:
            await self._api.set_parameter("operatingMode", OPERATING_MODE_ECO)
        elif preset_mode in (PRESET_NONE, None):
            await self._api.set_parameter("operatingMode", OPERATING_MODE_HEAT)
        else:
            _LOGGER.warning("Unsupported preset_mode: %s", preset_mode)
            return
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the device's HVAC mode."""
        operating_mode = self._hvac_mode_to_heatit_operatingmode(hvac_mode)
        if operating_mode is None:
            _LOGGER.error("Unsupported HVACMode: %s", hvac_mode)
            return
        if await self._api.set_parameter("operatingMode", operating_mode):
            await self.coordinator.async_request_refresh()

    @staticmethod
    def _hvac_mode_to_heatit_operatingmode(mode: HVACMode) -> int | None:
        if mode == HVACMode.OFF:
            return OPERATING_MODE_OFF
        if mode == HVACMode.HEAT:
            return OPERATING_MODE_HEAT
        if mode == HVACMode.COOL:
            return OPERATING_MODE_COOL
        return None

    @staticmethod
    def _heatit_operatingmode_to_hvac_mode(operating_mode: int | None) -> HVACMode | None:
        # 0 = Off, 1 = Heat, 2 = Cool, 3 = Eco (Heat with Eco setpoint)
        if operating_mode == OPERATING_MODE_OFF:
            return HVACMode.OFF
        if operating_mode in (OPERATING_MODE_HEAT, OPERATING_MODE_ECO):
            return HVACMode.HEAT
        if operating_mode == OPERATING_MODE_COOL:
            return HVACMode.COOL
        _LOGGER.error("Unknown operating mode from Heatit: %s", operating_mode)
        return None

    def _heatit_state_to_hvac_action(self, state: str | None) -> HVACAction | None:
        if state == "Idle":
            return HVACAction.OFF if self.hvac_mode == HVACMode.OFF else HVACAction.IDLE
        if state == "Heating":
            return HVACAction.HEATING
        if state == "Cooling":
            return HVACAction.COOLING
        _LOGGER.error("Unknown state from Heatit: %s", state)
        return None
