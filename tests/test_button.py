"""Tests for the Heatit WiFi6 button platform."""
from __future__ import annotations

import pytest

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import setup_entry


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )


async def test_reset_energy_meter(hass: HomeAssistant, config_entry, mock_api) -> None:
    await _press(hass, "button.lab_thermostat_reset_energy_meter")
    mock_api["reset_device"].assert_awaited_once_with("kwh")
    # The reset changes device state, so it is followed by a refresh.
    assert mock_api["get_status"].await_count == 2


async def test_reset_settings(hass: HomeAssistant, config_entry, mock_api) -> None:
    await _press(hass, "button.lab_thermostat_reset_settings_to_defaults")
    mock_api["reset_device"].assert_awaited_once_with("settings")


async def test_factory_reset(hass: HomeAssistant, config_entry, mock_api) -> None:
    await _press(hass, "button.lab_thermostat_factory_reset")
    mock_api["reset_device"].assert_awaited_once_with("factory")


async def test_factory_reset_disabled_by_default(
    hass: HomeAssistant, mock_api
) -> None:
    """It wipes the WiFi credentials, so it must be opt-in only."""
    await setup_entry(hass)

    registry = er.async_get(hass)
    entry = registry.async_get("button.lab_thermostat_factory_reset")
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    # Without an explicit enable it never becomes a pressable entity.
    assert hass.states.get("button.lab_thermostat_factory_reset") is None


async def test_reset_failure_raises(hass: HomeAssistant, config_entry, mock_api) -> None:
    mock_api["reset_device"].return_value = {}
    with pytest.raises(HomeAssistantError):
        await _press(hass, "button.lab_thermostat_reset_energy_meter")
