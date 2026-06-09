import logging
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import CONF_HOST
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Stagger device connection on startup to avoid all devices connecting at the same time.
    entries = hass.config_entries.async_entries(DOMAIN)
    try:
        index = [e.entry_id for e in entries].index(entry.entry_id)
    except ValueError:
        index = 0  # fallback if not found; should never happen
    wait_seconds = index * 2 + 2  # Always wait at least 2 seconds for the first, 4s for the second, etc.
    if wait_seconds:
        _LOGGER.info("Waiting %s seconds before connecting Heatit device for host: %s", wait_seconds, str(entry.data[CONF_HOST]))
        await asyncio.sleep(wait_seconds)
    _LOGGER.info("Heatit async_setup_entry() called for host: %s", str(entry.data[CONF_HOST]))
    await hass.config_entries.async_forward_entry_setups(entry, ["climate"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Remove the Heatit device. async_unload_entry() called for host: %s", str(entry.data[CONF_HOST]))
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return await hass.config_entries.async_forward_entry_unload(entry, "climate")
