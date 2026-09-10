"""The Heatit WiFi integration."""
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

from .api import HeatitWiFiAPI
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
class HeatitWiFiData:
    """Runtime data for a configured Heatit WiFi device."""

    coordinator: DataUpdateCoordinator[dict[str, Any]]
    api: HeatitWiFiAPI
    device_id: str


HeatitWiFiConfigEntry: TypeAlias = ConfigEntry[HeatitWiFiData]


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatitWiFiConfigEntry
) -> bool:
    """Set up Heatit WiFi from a config entry."""
    host = entry.data[CONF_HOST]
    _LOGGER.debug("Setting up Heatit WiFi entry for host: %s", host)

    session = async_get_clientsession(hass)
    api = HeatitWiFiAPI(host, session)

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
            raise UpdateFailed("Failed to fetch data from Heatit WiFi thermostat")
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

    entry.runtime_data = HeatitWiFiData(
        coordinator=coordinator,
        api=api,
        device_id=device_id,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: HeatitWiFiConfigEntry
) -> None:
    """Reload the entry when options (or the host) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: HeatitWiFiConfigEntry
) -> bool:
    """Unload a Heatit WiFi config entry."""
    _LOGGER.debug("Unloading Heatit WiFi entry for host: %s", entry.data[CONF_HOST])
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
