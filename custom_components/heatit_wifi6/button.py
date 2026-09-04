"""Button platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .api import HeatitWiFi6API
from .entity import HeatitWiFi6Entity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HeatitWiFi6ButtonEntityDescription(ButtonEntityDescription):
    """Describe a Heatit WiFi6 button that triggers a device reset."""

    # Reset type for DELETE /api/reset/{type}.
    reset_type: str


BUTTON_DESCRIPTIONS: tuple[HeatitWiFi6ButtonEntityDescription, ...] = (
    HeatitWiFi6ButtonEntityDescription(
        key="reset_energy_meter",
        translation_key="reset_energy_meter",
        entity_category=EntityCategory.CONFIG,
        reset_type="kwh",
    ),
    HeatitWiFi6ButtonEntityDescription(
        key="reset_settings",
        translation_key="reset_settings",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        reset_type="settings",
    ),
    # Wipes everything INCLUDING the WiFi credentials, taking the device
    # offline until it is re-provisioned with the Heatit app. Disabled by
    # default so it can only be pressed after being enabled on purpose.
    HeatitWiFi6ButtonEntityDescription(
        key="factory_reset",
        translation_key="factory_reset",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        reset_type="factory",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFi6ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 buttons from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        HeatitWiFi6ResetButton(
            data.coordinator, data.api, name, data.device_id, description
        )
        for description in BUTTON_DESCRIPTIONS
    )


class HeatitWiFi6ResetButton(HeatitWiFi6Entity, ButtonEntity):
    """Button that sends one of the device's reset commands."""

    entity_description: HeatitWiFi6ButtonEntityDescription

    def __init__(
        self,
        coordinator,
        api: HeatitWiFi6API,
        device_name: str,
        device_id: str,
        description: HeatitWiFi6ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, device_name, device_id)
        self.entity_description = description
        self._api = api
        self._attr_unique_id = f"heatit_wifi6_{device_id}_{description.key}"

    async def async_press(self) -> None:
        """Send the reset command to the device."""
        reset_type = self.entity_description.reset_type
        if not await self._api.reset_device(reset_type):
            raise HomeAssistantError(
                f"Failed to run the '{reset_type}' reset on the Heatit thermostat"
            )
        await self.coordinator.async_request_refresh()
