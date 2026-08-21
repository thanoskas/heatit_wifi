"""Shared entity base for the Heatit WiFi6 integration."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN


class HeatitWiFi6Entity(CoordinatorEntity[DataUpdateCoordinator[dict[str, Any]]]):
    """Base entity that ties Heatit entities to a single device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        device_name: str,
        device_id: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._device_name = device_name
        self._device_id = device_id

    @property
    def available(self) -> bool:
        """Return True if the coordinator was able to fetch data."""
        return self.coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry info derived from the latest status."""
        data = self.coordinator.data or {}
        network = data.get("network") or {}

        info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Heatit",
            model="WiFi6 Thermostat",
            sw_version=data.get("firmware"),
        )
        if mac := network.get("mac"):
            info["connections"] = {(CONNECTION_NETWORK_MAC, mac)}
        if ip_address := network.get("ipAddress"):
            info["configuration_url"] = f"http://{ip_address}"
        return info
