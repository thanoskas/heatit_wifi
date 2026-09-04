"""Tests for the Heatit WiFi6 sensor platform."""
from __future__ import annotations

import copy

import pytest

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .conftest import WIFI7_RELAY_STATUS, WIFI7_STATUS


async def test_wifi_signal_from_network_block(hass: HomeAssistant, config_entry) -> None:
    """WiFi6 nests the RSSI under network and appends the unit."""
    strength = hass.states.get("sensor.lab_thermostat_wifi_signal_strength")
    assert strength.state == "-60"
    assert strength.attributes["unit_of_measurement"] == "dBm"
    quality = hass.states.get("sensor.lab_thermostat_wifi_signal_quality")
    assert quality.state == "80"
    assert quality.attributes["unit_of_measurement"] == "%"


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_STATUS)])
async def test_wifi_signal_top_level(hass: HomeAssistant, config_entry) -> None:
    """WiFi7 firmware 0.1.13 sends wifiSignalStrength at the top level."""
    assert hass.states.get("sensor.lab_thermostat_wifi_signal_strength").state == "-45"
    assert hass.states.get("sensor.lab_thermostat_wifi_signal_quality").state == "100"


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_RELAY_STATUS)])
async def test_wifi_quality_linear_mapping(hass: HomeAssistant, config_entry) -> None:
    assert hass.states.get("sensor.lab_thermostat_wifi_signal_quality").state == "60"


async def test_owd_remaining_time(hass: HomeAssistant, config_entry) -> None:
    state = hass.states.get("sensor.lab_thermostat_open_window_remaining_time")
    assert state.state == "0"
    assert state.attributes["unit_of_measurement"] == "s"


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_STATUS)])
async def test_owd_remaining_time_counting(hass: HomeAssistant, config_entry) -> None:
    assert hass.states.get("sensor.lab_thermostat_open_window_remaining_time").state == "900"


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_RELAY_STATUS)])
async def test_owd_remaining_time_missing_in_relay_mode(
    hass: HomeAssistant, config_entry
) -> None:
    assert (
        hass.states.get("sensor.lab_thermostat_open_window_remaining_time").state
        == STATE_UNKNOWN
    )


async def test_disconnected_ntc_sensor(hass: HomeAssistant, config_entry) -> None:
    """The 100.0 C sentinel means no sensor is connected."""
    assert hass.states.get("sensor.lab_thermostat_external_temperature").state == STATE_UNKNOWN
    assert hass.states.get("sensor.lab_thermostat_floor_temperature").state == "23.0"


async def test_unavailable_when_device_unreachable(
    hass: HomeAssistant, config_entry, mock_api
) -> None:
    """All entities go unavailable when a poll fails."""
    mock_api["get_status"].return_value = {}
    coordinator = config_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert (
        hass.states.get("sensor.lab_thermostat_current_temperature").state
        == STATE_UNAVAILABLE
    )


async def test_ip_address(hass: HomeAssistant, config_entry) -> None:
    assert hass.states.get("sensor.lab_thermostat_ip_address").state == "192.168.1.50"
