"""The Heatit WiFi6 integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HeatitWiFi6API
from .const import DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SENSOR,
]


@dataclass
class HeatitWiFi6Data:
    """Runtime data for a configured Heatit WiFi6 device."""

    coordinator: DataUpdateCoordinator[dict[str, Any]]
    api: HeatitWiFi6API
    device_id: str


HeatitWiFi6ConfigEntry: TypeAlias = ConfigEntry[HeatitWiFi6Data]


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatitWiFi6ConfigEntry
) -> bool:
    """Set up Heatit WiFi6 from a config entry."""
    host = entry.data[CONF_HOST]
    _LOGGER.debug("Setting up Heatit WiFi6 entry for host: %s", host)

    session = async_get_clientsession(hass)
    api = HeatitWiFi6API(host, session)

    device_id = await api.get_device_id(retries=1, timeout=10)
    if device_id == "unknown":
        raise ConfigEntryNotReady(
            f"Could not connect to Heatit device at {host}"
        )

    async def async_update_data() -> dict[str, Any]:
        try:
            data = await api.get_status()
        except Exception as err:  # noqa: BLE001 - surface as UpdateFailed
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        if not data:
            raise UpdateFailed("Failed to fetch data from Heatit WiFi6 thermostat")
        return data

    coordinator: DataUpdateCoordinator[dict[str, Any]] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=POLL_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = HeatitWiFi6Data(
        coordinator=coordinator,
        api=api,
        device_id=device_id,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: HeatitWiFi6ConfigEntry
) -> bool:
    """Unload a Heatit WiFi6 config entry."""
    _LOGGER.debug("Unloading Heatit WiFi6 entry for host: %s", entry.data[CONF_HOST])
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
