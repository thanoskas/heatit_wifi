"""The Heatit WiFi6 integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HeatitWiFi6API
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
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

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator: DataUpdateCoordinator[dict[str, Any]] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = HeatitWiFi6Data(
        coordinator=coordinator,
        api=api,
        device_id=device_id,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: HeatitWiFi6ConfigEntry
) -> None:
    """Reload the entry when options (or the host) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: HeatitWiFi6ConfigEntry
) -> bool:
    """Unload a Heatit WiFi6 config entry."""
    _LOGGER.debug("Unloading Heatit WiFi6 entry for host: %s", entry.data[CONF_HOST])
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
