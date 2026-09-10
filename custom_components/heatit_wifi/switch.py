"""Switch platform for the Heatit WiFi thermostat."""
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

from . import HeatitWiFiConfigEntry
from .api import HeatitWiFiAPI
from .entity import HeatitWiFiEntity


@dataclass(frozen=True, kw_only=True)
class HeatitWiFiSwitchEntityDescription(SwitchEntityDescription):
    """Describe a Heatit WiFi switch backed by a device parameter."""

    parameter: str
    value_fn: Callable[[dict[str, Any]], bool | None]
    # The WiFi7 firmware validates parameter types strictly (e.g.
    # disableButtons must be an integer, not a boolean).
    payload_fn: Callable[[bool], Any] = bool
    # Applies the freshly written value to the cached status payload so
    # the UI updates immediately instead of waiting for the next poll.
    set_local: Callable[[dict[str, Any], Any], None] | None = None
    # Parameters that only exist on the WiFi7 (Relay mode).
    wifi7_only: bool = False


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


def _set_owd_local(data: dict[str, Any], value: Any) -> None:
    owd = data.setdefault("parameters", {}).setdefault("OWD", {})
    owd["openWindowDetection"] = value


SWITCH_DESCRIPTIONS: tuple[HeatitWiFiSwitchEntityDescription, ...] = (
    HeatitWiFiSwitchEntityDescription(
        key="temperature_display",
        translation_key="temperature_display",
        entity_category=EntityCategory.CONFIG,
        device_class=SwitchDeviceClass.SWITCH,
        parameter="temperatureDisplay",
        value_fn=_parameter_field("temperatureDisplay"),
    ),
    HeatitWiFiSwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        entity_category=EntityCategory.CONFIG,
        device_class=SwitchDeviceClass.SWITCH,
        parameter="disableButtons",
        value_fn=_parameter_field("disableButtons"),
        payload_fn=int,
    ),
    HeatitWiFiSwitchEntityDescription(
        key="open_window_detection",
        translation_key="open_window_detection",
        entity_category=EntityCategory.CONFIG,
        device_class=SwitchDeviceClass.SWITCH,
        parameter="openWindowDetection",
        value_fn=_owd_enabled,
        set_local=_set_owd_local,
    ),
    # WiFi7 Relay mode extras.
    HeatitWiFiSwitchEntityDescription(
        key="always_on",
        translation_key="always_on",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        device_class=SwitchDeviceClass.SWITCH,
        parameter="alwaysOn",
        value_fn=_parameter_field("alwaysOn"),
        wifi7_only=True,
    ),
    HeatitWiFiSwitchEntityDescription(
        key="inverted_output",
        translation_key="inverted_output",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        device_class=SwitchDeviceClass.SWITCH,
        parameter="invertedOutput",
        value_fn=_parameter_field("invertedOutput"),
        wifi7_only=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi switches from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    # WiFi7-only entities are skipped on a WiFi6 (which reports no model
    # field in /api/status and can't be in Relay mode). On a WiFi7 they
    # stay unavailable until the device is put in Relay mode.
    status = data.coordinator.data or {}
    is_wifi7 = bool(status.get("model")) or (
        (status.get("parameters") or {}).get("sensorMode") == 7
    )
    entities: list[SwitchEntity] = [
        HeatitWiFiSwitch(
            data.coordinator, data.api, name, data.device_id, description
        )
        for description in SWITCH_DESCRIPTIONS
        if is_wifi7 or not description.wifi7_only
    ]
    if is_wifi7:
        entities.append(
            HeatitWiFiRelaySwitch(data.coordinator, data.api, name, data.device_id)
        )

    async_add_entities(entities)


class HeatitWiFiSwitch(HeatitWiFiEntity, SwitchEntity):
    """A Heatit WiFi switch that toggles a boolean device parameter."""

    entity_description: HeatitWiFiSwitchEntityDescription

    def __init__(
        self,
        coordinator,
        api: HeatitWiFiAPI,
        device_name: str,
        device_id: str,
        description: HeatitWiFiSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_name, device_id)
        self.entity_description = description
        self._api = api
        self._attr_unique_id = f"heatit_wifi_{device_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Unavailable when the device doesn't report the parameter.

        A WiFi7 in Relay mode drops the thermostat-only parameters
        (e.g. temperatureDisplay, OWD) from /api/status.
        """
        if not super().available:
            return False
        data = self.coordinator.data
        return bool(data) and self.entity_description.value_fn(data) is not None

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
        description = self.entity_description
        payload = description.payload_fn(value)
        if not await self._api.set_parameter(description.parameter, payload):
            raise HomeAssistantError(
                f"Failed to set {description.parameter} to {payload}"
                " on the Heatit thermostat"
            )
        # Push the new value into the shared cache and notify every
        # entity. Deliberately no immediate refresh: /api/status can
        # still report the old value right after a write, which would
        # revert the UI; the next scheduled poll confirms instead.
        if data := self.coordinator.data:
            if description.set_local is not None:
                description.set_local(data, payload)
            else:
                data.setdefault("parameters", {})[description.parameter] = payload
            self.coordinator.async_set_updated_data(data)
        else:
            await self.coordinator.async_request_refresh()


class HeatitWiFiRelaySwitch(HeatitWiFiEntity, SwitchEntity):
    """The relay output of a WiFi7 running in Relay mode (RELA)."""

    _attr_translation_key = "relay"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator,
        api: HeatitWiFiAPI,
        device_name: str,
        device_id: str,
    ) -> None:
        """Initialize the relay switch."""
        super().__init__(coordinator, device_name, device_id)
        self._api = api
        self._attr_unique_id = f"heatit_wifi_{device_id}_relay"

    @property
    def available(self) -> bool:
        """Only usable while the device is in Relay mode."""
        if not super().available:
            return False
        data = self.coordinator.data or {}
        return (data.get("parameters") or {}).get("sensorMode") == 7

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        # Prefer the live relay state; fall back to the onOff parameter.
        # The spec documents "Open"/"Closed" but real firmware (0.1.13)
        # sends lowercase, so compare case-insensitively.
        state = str(data.get("state", "")).lower()
        if state in ("open", "closed"):
            return state == "closed"
        value = (data.get("parameters") or {}).get("onOff")
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Close the relay."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Open the relay."""
        await self._async_set(False)

    async def _async_set(self, value: bool) -> None:
        if not await self._api.set_parameter("onOff", value):
            raise HomeAssistantError(
                f"Failed to set onOff to {value} on the Heatit relay"
            )
        if data := self.coordinator.data:
            data.setdefault("parameters", {})["onOff"] = value
            data["state"] = "closed" if value else "open"
            self.coordinator.async_set_updated_data(data)
        else:
            await self.coordinator.async_request_refresh()
