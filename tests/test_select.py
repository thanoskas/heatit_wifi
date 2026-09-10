"""Tests for the Heatit WiFi select platform."""
from __future__ import annotations

import copy

import pytest

from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from .conftest import WIFI7_RELAY_STATUS, WIFI7_STATUS


async def _select(hass: HomeAssistant, entity_id: str, option: str) -> None:
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: option},
        blocking=True,
    )


async def test_sensor_value_wifi6_numbering(
    hass: HomeAssistant, config_entry, mock_api
) -> None:
    """On a WiFi6, sensorValue 0 is 10 kOhm and 6.8 kOhm is index 6."""
    state = hass.states.get("select.lab_thermostat_ntc_sensor_type")
    assert state.state == "10k"
    assert state.attributes["options"] == [
        "6k8", "10k", "12k", "15k", "22k", "33k", "47k", "100k",
    ]

    await _select(hass, "select.lab_thermostat_ntc_sensor_type", "6k8")
    mock_api["set_parameter"].assert_awaited_once_with("sensorValue", 6)
    assert hass.states.get("select.lab_thermostat_ntc_sensor_type").state == "6k8"


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_STATUS)])
async def test_sensor_value_wifi7_numbering(
    hass: HomeAssistant, config_entry, mock_api
) -> None:
    """On a WiFi7 the raw value 1 means 10 kOhm and 6.8 kOhm is index 0."""
    assert hass.states.get("select.lab_thermostat_ntc_sensor_type").state == "10k"

    await _select(hass, "select.lab_thermostat_ntc_sensor_type", "6k8")
    mock_api["set_parameter"].assert_awaited_once_with("sensorValue", 0)

    mock_api["set_parameter"].reset_mock()
    await _select(hass, "select.lab_thermostat_ntc_sensor_type", "100k")
    mock_api["set_parameter"].assert_awaited_once_with("sensorValue", 7)


async def test_regulation_mode_sends_bool(
    hass: HomeAssistant, config_entry, mock_api
) -> None:
    """regulationMode is a boolean on the wire."""
    assert hass.states.get("select.lab_thermostat_regulation_mode").state == "hysteresis"
    await _select(hass, "select.lab_thermostat_regulation_mode", "pwm")
    mock_api["set_parameter"].assert_awaited_once_with("regulationMode", True)
    assert hass.states.get("select.lab_thermostat_regulation_mode").state == "pwm"


async def test_wifi7_only_selects_skipped_on_wifi6(hass: HomeAssistant, config_entry) -> None:
    assert hass.states.get("select.lab_thermostat_external_sensor_fallback") is None
    assert hass.states.get("select.lab_thermostat_relay_state_after_power_loss") is None


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_STATUS)])
async def test_external_sensor_fallback(hass: HomeAssistant, config_entry, mock_api) -> None:
    state = hass.states.get("select.lab_thermostat_external_sensor_fallback")
    assert state.state == "internal"
    await _select(hass, "select.lab_thermostat_external_sensor_fallback", "off")
    mock_api["set_parameter"].assert_awaited_once_with("externalSensorFallback", 0)
    # Relay-only parameter is unavailable while in thermostat mode.
    assert (
        hass.states.get("select.lab_thermostat_relay_state_after_power_loss").state
        == STATE_UNAVAILABLE
    )


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_RELAY_STATUS)])
async def test_relay_mode_selects(hass: HomeAssistant, config_entry, mock_api) -> None:
    assert hass.states.get("select.lab_thermostat_sensor_mode").state == "relay"
    assert hass.states.get("select.lab_thermostat_regulation_mode").state == STATE_UNAVAILABLE
    assert hass.states.get("select.lab_thermostat_ntc_sensor_type").state == STATE_UNAVAILABLE

    restore = hass.states.get("select.lab_thermostat_relay_state_after_power_loss")
    assert restore.state == "previous"
    await _select(hass, "select.lab_thermostat_relay_state_after_power_loss", "on")
    mock_api["set_parameter"].assert_awaited_once_with("deviceRestoreState", 1)
    assert (
        hass.states.get("select.lab_thermostat_relay_state_after_power_loss").state == "on"
    )
