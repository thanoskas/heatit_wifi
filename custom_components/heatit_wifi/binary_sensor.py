"""Binary sensor platform for the Heatit WiFi thermostat."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitWiFiConfigEntry
from .entity import HeatitWiFiEntity


@dataclass(frozen=True, kw_only=True)
class HeatitWiFiBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a Heatit WiFi binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


def _owd_field(name: str) -> Callable[[dict[str, Any]], bool | None]:
    def _value(data: dict[str, Any]) -> bool | None:
        owd = (data.get("parameters") or {}).get("OWD") or {}
        value = owd.get(name)
        return None if value is None else bool(value)

    return _value


BINARY_SENSOR_DESCRIPTIONS: tuple[HeatitWiFiBinarySensorEntityDescription, ...] = (
    HeatitWiFiBinarySensorEntityDescription(
        key="open_window_detected",
        translation_key="open_window_detected",
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=_owd_field("activeNow"),
    ),
    HeatitWiFiBinarySensorEntityDescription(
        key="open_window_detection_enabled",
        translation_key="open_window_detection_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_owd_field("openWindowDetection"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitWiFiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi binary sensors from a config entry."""
    data = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        HeatitWiFiBinarySensor(data.coordinator, name, data.device_id, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class HeatitWiFiBinarySensor(HeatitWiFiEntity, BinarySensorEntity):
    """A Heatit WiFi binary sensor backed by a BinarySensorEntityDescription."""

    entity_description: HeatitWiFiBinarySensorEntityDescription

    def __init__(
        self,
        coordinator,
        device_name: str,
        device_id: str,
        description: HeatitWiFiBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, device_name, device_id)
        self.entity_description = description
        self._attr_unique_id = f"heatit_wifi_{device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        return self.entity_description.value_fn(data)
