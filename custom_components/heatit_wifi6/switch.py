"""Switch platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFi6ConfigEntry
from .api import HeatitWiFi6API
from .entity import HeatitWiFi6Entity


@dataclass(frozen=True, kw_only=True)
class HeatitWiFi6SwitchEntityDescription(SwitchEntityDescription):
    """Describe a Heatit WiFi6 switch backed by a device parameter."""

    parameter: str
    value_fn: Callable[[dict[str, Any]], bool | None]


def _parameter_field(name: str) -> Callable[[dict[str, Any]], bool | None]:
    def _value(data: dict[str, Any]) -> bool | None:
        value = (data.get("parameters") or {}).get(name)
        return None if value is None else bool(value)

    return _value


def _owd_enabled(data: dict[str, Any]) -> bool | None:
    # In the status payload OWD settings are nested, unlike the flat
    # openWindowDetection key used when writing to /api/parameters.
    owd = (data.get("parameters") or {}).get("OWD") or {}
    value = owd.get("openWindowDetection")
    return None if value is None else bool(value)


SWITCH_DESCRIPTIONS: tuple[HeatitWiFi6SwitchEntityDescription, ...] = (
    HeatitWiFi6SwitchEntityDescription(
        key="temperature_display",
        translation_key="temperature_display",
        entity_category=EntityCategory.CONFIG,
        device_class=SwitchDeviceClass.SWITCH,
        parameter="temperatureDisplay",
        value_fn=_parameter_field("temperatureDisplay"),
    ),
    HeatitWiFi6SwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        entity_category=EntityCategory.CONFIG,
        device_class=SwitchDeviceClass.SWITCH,
        parameter="disableButtons",
        value_fn=_parameter_field("disableButtons"),
    ),
    HeatitWiFi6SwitchEntityDescription(
        key="open_window_detection",
        translation_key="open_window_detection",
        entity_category=EntityCategory.CONFIG,
        device_class=SwitchDeviceClass.SWITCH,
        parameter="openWindowDetection",
        value_fn=_owd_enabled,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFi6ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 switches from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        HeatitWiFi6Switch(
            data.coordinator, data.api, name, data.device_id, description
        )
        for description in SWITCH_DESCRIPTIONS
    )


class HeatitWiFi6Switch(HeatitWiFi6Entity, SwitchEntity):
    """A Heatit WiFi6 switch that toggles a boolean device parameter."""

    entity_description: HeatitWiFi6SwitchEntityDescription

    def __init__(
        self,
        coordinator,
        api: HeatitWiFi6API,
        device_name: str,
        device_id: str,
        description: HeatitWiFi6SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_name, device_id)
        self.entity_description = description
        self._api = api
        self._attr_unique_id = f"heatit_wifi6_{device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        return self.entity_description.value_fn(data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the parameter on the device."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the parameter on the device."""
        await self._async_set(False)

    async def _async_set(self, value: bool) -> None:
        parameter = self.entity_description.parameter
        if not await self._api.set_parameter(parameter, value):
            raise HomeAssistantError(
                f"Failed to set {parameter} to {value} on the Heatit thermostat"
            )
        await self.coordinator.async_request_refresh()
