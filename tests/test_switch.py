"""Tests for the Heatit WiFi6 switch platform."""
from __future__ import annotations

import copy

import pytest

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant

from .conftest import WIFI7_RELAY_STATUS, WIFI7_STATUS


async def _turn(hass: HomeAssistant, entity_id: str, on: bool) -> None:
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON if on else SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )


async def test_wifi6_has_no_relay_entities(hass: HomeAssistant, config_entry) -> None:
    assert hass.states.get("switch.lab_thermostat_relay") is None
    assert hass.states.get("switch.lab_thermostat_always_on") is None
    assert hass.states.get("switch.lab_thermostat_inverted_output") is None
    assert (
        hass.states.get("switch.lab_thermostat_display_measured_temperature").state
        == STATE_ON
    )


async def test_child_lock_sends_int(hass: HomeAssistant, config_entry, mock_api) -> None:
    """WiFi7 firmware rejects a boolean for disableButtons."""
    assert hass.states.get("switch.lab_thermostat_child_lock").state == STATE_OFF
    await _turn(hass, "switch.lab_thermostat_child_lock", True)
    mock_api["set_parameter"].assert_awaited_once_with("disableButtons", 1)
    assert hass.states.get("switch.lab_thermostat_child_lock").state == STATE_ON


async def test_open_window_detection_nested_state(
    hass: HomeAssistant, config_entry, mock_api
) -> None:
    """OWD is nested in the status but written as a flat parameter."""
    assert hass.states.get("switch.lab_thermostat_open_window_detection").state == STATE_ON
    await _turn(hass, "switch.lab_thermostat_open_window_detection", False)
    mock_api["set_parameter"].assert_awaited_once_with("openWindowDetection", False)
    assert hass.states.get("switch.lab_thermostat_open_window_detection").state == STATE_OFF


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_STATUS)])
async def test_wifi7_thermostat_mode_relay_extras_unavailable(
    hass: HomeAssistant, config_entry
) -> None:
    for entity_id in (
        "switch.lab_thermostat_relay",
        "switch.lab_thermostat_always_on",
        "switch.lab_thermostat_inverted_output",
    ):
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE, entity_id
    assert hass.states.get("switch.lab_thermostat_open_window_detection").state == STATE_ON


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_RELAY_STATUS)])
async def test_wifi7_relay_mode_switches(hass: HomeAssistant, config_entry, mock_api) -> None:
    # Thermostat-only settings vanish from the status in Relay mode.
    assert (
        hass.states.get("switch.lab_thermostat_display_measured_temperature").state
        == STATE_UNAVAILABLE
    )
    assert (
        hass.states.get("switch.lab_thermostat_open_window_detection").state
        == STATE_UNAVAILABLE
    )

    # Live relay state comes from the lowercase "state" field.
    assert hass.states.get("switch.lab_thermostat_relay").state == STATE_ON
    await _turn(hass, "switch.lab_thermostat_relay", False)
    mock_api["set_parameter"].assert_awaited_once_with("onOff", False)
    assert hass.states.get("switch.lab_thermostat_relay").state == STATE_OFF

    mock_api["set_parameter"].reset_mock()
    assert hass.states.get("switch.lab_thermostat_always_on").state == STATE_OFF
    await _turn(hass, "switch.lab_thermostat_always_on", True)
    mock_api["set_parameter"].assert_awaited_once_with("alwaysOn", True)
    assert hass.states.get("switch.lab_thermostat_always_on").state == STATE_ON

    mock_api["set_parameter"].reset_mock()
    await _turn(hass, "switch.lab_thermostat_inverted_output", True)
    mock_api["set_parameter"].assert_awaited_once_with("invertedOutput", True)
    assert hass.states.get("switch.lab_thermostat_inverted_output").state == STATE_ON
