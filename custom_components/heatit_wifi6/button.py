"""Button platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .api import HeatitWiFi6API
from .entity import HeatitWiFi6Entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFi6ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 buttons from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        [
            HeatitWiFi6ResetEnergyButton(
                data.coordinator,
                data.api,
                name,
                data.device_id,
            )
        ]
    )


class HeatitWiFi6ResetEnergyButton(HeatitWiFi6Entity, ButtonEntity):
    """Button that resets the thermostat's energy (kWh) meter to zero."""

    _attr_translation_key = "reset_energy_meter"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator,
        api: HeatitWiFi6API,
        device_name: str,
        device_id: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, device_name, device_id)
        self._api = api
        self._attr_unique_id = f"heatit_wifi6_{device_id}_reset_energy_meter"

    async def async_press(self) -> None:
        """Reset the energy meter on the device."""
        if not await self._api.reset_device("kwh"):
            raise HomeAssistantError("Failed to reset the Heatit energy meter")
        await self.coordinator.async_request_refresh()
