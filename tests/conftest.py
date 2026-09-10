"""Fixtures for the Heatit WiFi unit tests.

The device API is mocked at the ``HeatitWiFiAPI`` boundary, so these tests
exercise the coordinator, the entity platforms and the write paths without
touching the network. They need ``pytest-homeassistant-custom-component``.
"""
from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.heatit_wifi.const import DOMAIN

DEVICE_ID = "8E6EDC28A7D0"
DEVICE_NAME = "Lab thermostat"

# A WiFi6 (API v7) status payload in Internal sensor mode.
WIFI6_STATUS: dict[str, Any] = {
    "id": DEVICE_ID,
    "firmware": "2.20",
    "internalTemperature": 21.5,
    "floorTemperature": 23.0,
    "externalTemperature": 100.0,
    "currentPower": 500,
    "totalConsumption": 12.5,
    "network": {
        "mac": "8e:6e:dc:28:a7:d0",
        "ipAddress": "192.168.1.50",
        "wifiSignalStrength": "-60dBm",
    },
    "parameters": {
        "operatingMode": 1,
        "sensorMode": 1,
        "sensorValue": 0,
        "regulationMode": False,
        "heatingSetpoint": 22.0,
        "coolingSetpoint": 24.0,
        "ecoSetpoint": 18.0,
        "temperatureControlHysteresis": 0.5,
        "activeDisplayBrightness": 7,
        "standbyDisplayBrightness": 3,
        "internalCalibration": 0.0,
        "floorCalibration": -0.5,
        "externalCalibration": 0.0,
        "powerRegulatorActiveTime": 20,
        "floorMinimumTemperatureLimit": 5.0,
        "floorMaximumTemperatureLimit": 27.0,
        "internalMinimumTemperatureLimit": 5.0,
        "internalMaximumTemperatureLimit": 40.0,
        "externalMinimumTemperatureLimit": 5.0,
        "externalMaximumTemperatureLimit": 40.0,
        "sizeOfLoad": 15,
        "actionAfterError": 60,
        "temperatureDisplay": True,
        "disableButtons": 0,
        "OWD": {
            "openWindowDetection": True,
            "activeTime": 0,
        },
    },
}


def _wifi7_status() -> dict[str, Any]:
    """A WiFi7 (firmware 0.1.13) in Internal sensor mode.

    Compared with the WiFi6 it adds the model field, renames the calibration
    parameters, reports the RSSI at the top level, uses a 0-100 brightness
    scale, numbers sensorValue differently and has externalSensorFallback.
    """
    status = copy.deepcopy(WIFI6_STATUS)
    status["model"] = "Heatit WiFi7"
    status["firmware"] = "0.1.13"
    status["wifiSignalStrength"] = "-45dBm"
    status["network"] = {"mac": "8e:6e:dc:28:a7:d0", "ipAddress": "192.168.1.51"}
    params = status["parameters"]
    for old, new in (
        ("internalCalibration", "internalSensorCalibration"),
        ("floorCalibration", "floorSensorCalibration"),
        ("externalCalibration", "externalSensorCalibration"),
    ):
        params[new] = params.pop(old)
    params["sensorValue"] = 1  # 10 kOhm in the WiFi7 numbering
    params["externalSensorFallback"] = 2
    params["activeDisplayBrightness"] = 70
    params["standbyDisplayBrightness"] = 30
    params["OWD"] = {"openWindowDetection": True, "activeTime": 900}
    return status


WIFI7_STATUS: dict[str, Any] = _wifi7_status()

# The same WiFi7 switched to Relay mode (RELA): the thermostat-only
# parameters disappear from the status and the relay ones show up.
WIFI7_RELAY_STATUS: dict[str, Any] = {
    "id": DEVICE_ID,
    "model": "Heatit WiFi7",
    "firmware": "0.1.13",
    "state": "closed",
    "currentPower": 0,
    "totalConsumption": 3.0,
    "wifiSignalStrength": "-70dBm",
    "network": {"mac": "8e:6e:dc:28:a7:d0", "ipAddress": "192.168.1.51"},
    "parameters": {
        "sensorMode": 7,
        "onOff": True,
        "alwaysOn": False,
        "invertedOutput": False,
        "automaticTurnOn": 0,
        "automaticTurnOff": 3600,
        "turnOffDelayTime": 5,
        "deviceRestoreState": 0,
        "sizeOfLoad": 0,
        "disableButtons": 1,
    },
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components from this repository."""


@pytest.fixture
def entity_registry_enabled_by_default() -> None:
    """Enable every entity, including the ones disabled by default."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        return_value=True,
    ):
        yield


@pytest.fixture
def status() -> dict[str, Any]:
    """Status payload the mocked device returns; parametrize to override."""
    return copy.deepcopy(WIFI6_STATUS)


@pytest.fixture
def mock_api(status: dict[str, Any]):
    """Mock the device API so no HTTP requests are made."""
    with (
        patch(
            "custom_components.heatit_wifi.HeatitWiFiAPI.get_device_id",
            new=AsyncMock(return_value=status["id"]),
        ),
        patch(
            "custom_components.heatit_wifi.HeatitWiFiAPI.get_status",
            new=AsyncMock(return_value=status),
        ) as get_status,
        patch(
            "custom_components.heatit_wifi.HeatitWiFiAPI.set_parameter",
            new=AsyncMock(return_value={"status": "Success"}),
        ) as set_parameter,
        patch(
            "custom_components.heatit_wifi.HeatitWiFiAPI.reset_device",
            new=AsyncMock(return_value={"status": "success"}),
        ) as reset_device,
    ):
        yield {
            "get_status": get_status,
            "set_parameter": set_parameter,
            "reset_device": reset_device,
        }


async def setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add and set up a config entry for the mocked device."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data={CONF_HOST: "http://192.168.1.50", CONF_NAME: DEVICE_NAME},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def config_entry(
    hass: HomeAssistant,
    mock_api: dict[str, AsyncMock],
    entity_registry_enabled_by_default: None,
) -> MockConfigEntry:
    """Set up the integration with every entity enabled."""
    return await setup_entry(hass)
