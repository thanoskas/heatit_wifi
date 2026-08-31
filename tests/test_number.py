"""Tests for the Heatit WiFi6 number platform."""
from __future__ import annotations

import copy

import pytest

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import WIFI7_RELAY_STATUS, WIFI7_STATUS, setup_entry


async def _set_value(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )


async def test_temperature_limits(hass: HomeAssistant, config_entry) -> None:
    """The six limits read from the device and use the spec's 5-40 range."""
    for suffix, expected in (
        ("floor_minimum_temperature", "5.0"),
        ("floor_maximum_temperature", "27.0"),
        ("internal_minimum_temperature", "5.0"),
        ("internal_maximum_temperature", "40.0"),
        ("external_minimum_temperature", "5.0"),
        ("external_maximum_temperature", "40.0"),
    ):
        state = hass.states.get(f"number.lab_thermostat_{suffix}")
        assert state is not None, suffix
        assert state.state == expected
        assert state.attributes["min"] == 5.0
        assert state.attributes["max"] == 40.0
        assert state.attributes["step"] == 0.5


async def test_floor_limits_enabled_by_default(hass: HomeAssistant, mock_api) -> None:
    """Floor protection is on out of the box; the other limits are opt-in."""
    await setup_entry(hass)
    registry = er.async_get(hass)
    floor = registry.async_get("number.lab_thermostat_floor_maximum_temperature")
    internal = registry.async_get("number.lab_thermostat_internal_maximum_temperature")
    assert floor is not None and floor.disabled_by is None
    assert internal is not None and internal.disabled_by is not None


async def test_set_temperature_limit(hass: HomeAssistant, config_entry, mock_api) -> None:
    """Half-degree limits are sent as floats and shown without a readback."""
    await _set_value(hass, "number.lab_thermostat_floor_maximum_temperature", 26.5)
    mock_api["set_parameter"].assert_awaited_once_with(
        "floorMaximumTemperatureLimit", 26.5
    )
    assert mock_api["get_status"].await_count == 1
    state = hass.states.get("number.lab_thermostat_floor_maximum_temperature")
    assert state.state == "26.5"


async def test_size_of_load_in_watts(hass: HomeAssistant, config_entry, mock_api) -> None:
    """sizeOfLoad is stored in 100 W steps but exposed in watts."""
    state = hass.states.get("number.lab_thermostat_size_of_load")
    assert state.state == "1500"
    assert state.attributes["unit_of_measurement"] == "W"

    await _set_value(hass, "number.lab_thermostat_size_of_load", 2000)
    mock_api["set_parameter"].assert_awaited_once_with("sizeOfLoad", 20)
    assert hass.states.get("number.lab_thermostat_size_of_load").state == "2000"

    mock_api["set_parameter"].reset_mock()
    await _set_value(hass, "number.lab_thermostat_size_of_load", 0)
    mock_api["set_parameter"].assert_awaited_once_with("sizeOfLoad", 0)


@pytest.mark.parametrize(
    ("value", "payload"),
    [(0, 0), (5, 0), (10, 10), (600.0, 600), (65535, 65535)],
)
async def test_action_after_error_payload(
    hass: HomeAssistant, config_entry, mock_api, value: float, payload: int
) -> None:
    """Values below the 10 s minimum collapse to 0 (stay off)."""
    assert hass.states.get("number.lab_thermostat_retry_delay_after_error").state == "60"
    await _set_value(hass, "number.lab_thermostat_retry_delay_after_error", value)
    mock_api["set_parameter"].assert_awaited_once_with("actionAfterError", payload)


async def test_failed_write_raises(hass: HomeAssistant, config_entry, mock_api) -> None:
    """A rejected POST surfaces as an error and keeps the old value."""
    mock_api["set_parameter"].return_value = {}
    with pytest.raises(HomeAssistantError):
        await _set_value(hass, "number.lab_thermostat_floor_maximum_temperature", 30)
    state = hass.states.get("number.lab_thermostat_floor_maximum_temperature")
    assert state.state == "27.0"


async def test_wifi7_only_numbers_skipped_on_wifi6(hass: HomeAssistant, config_entry) -> None:
    """Relay mode timers don't exist on a WiFi6, so no entity is created."""
    assert hass.states.get("number.lab_thermostat_automatic_turn_off") is None
    assert hass.states.get("number.lab_thermostat_automatic_turn_on") is None
    assert hass.states.get("number.lab_thermostat_turn_off_delay") is None


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_STATUS)])
async def test_wifi7_thermostat_mode(hass: HomeAssistant, config_entry, mock_api) -> None:
    """On a WiFi7 in thermostat mode the relay timers exist but are unavailable."""
    assert hass.states.get("number.lab_thermostat_automatic_turn_off").state == STATE_UNAVAILABLE
    assert hass.states.get("number.lab_thermostat_turn_off_delay").state == STATE_UNAVAILABLE
    # Renamed calibration parameter is read and written under the new name.
    assert hass.states.get("number.lab_thermostat_floor_sensor_calibration").state == "-0.5"
    await _set_value(hass, "number.lab_thermostat_floor_sensor_calibration", 1.2)
    mock_api["set_parameter"].assert_awaited_once_with("floorSensorCalibration", 1.2)


@pytest.mark.parametrize("status", [copy.deepcopy(WIFI7_RELAY_STATUS)])
async def test_wifi7_relay_mode(hass: HomeAssistant, config_entry, mock_api) -> None:
    """In Relay mode the timers work and the thermostat numbers go unavailable."""
    off = hass.states.get("number.lab_thermostat_automatic_turn_off")
    assert off.state == "3600"
    assert off.attributes["max"] == 86400
    delay = hass.states.get("number.lab_thermostat_turn_off_delay")
    assert delay.state == "5"
    assert delay.attributes["max"] == 60
    assert hass.states.get("number.lab_thermostat_hysteresis").state == STATE_UNAVAILABLE
    assert (
        hass.states.get("number.lab_thermostat_floor_maximum_temperature").state
        == STATE_UNAVAILABLE
    )

    await _set_value(hass, "number.lab_thermostat_automatic_turn_on", 120)
    mock_api["set_parameter"].assert_awaited_once_with("automaticTurnOn", 120)
    assert hass.states.get("number.lab_thermostat_automatic_turn_on").state == "120"
