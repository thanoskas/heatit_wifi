"""Tests for the config, options and reconfigure flows."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.heatit_wifi6.const import DOMAIN

from .conftest import DEVICE_ID, DEVICE_NAME

OTHER_DEVICE_ID = "AABBCCDDEEFF"


def _patch_device_id(value: str):
    """Control what the flow's connectivity probe returns."""
    return patch(
        "custom_components.heatit_wifi6.config_flow.HeatitWiFi6API.get_device_id",
        new=AsyncMock(return_value=value),
    )


@pytest.fixture
def mock_setup_entry():
    """Skip the real setup when a flow creates or reloads an entry."""
    with patch(
        "custom_components.heatit_wifi6.async_setup_entry", return_value=True
    ) as mock:
        yield mock


def _make_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Heatit WiFi6 ({DEVICE_NAME})",
        unique_id=DEVICE_ID,
        data={CONF_HOST: "http://192.168.1.50", CONF_NAME: DEVICE_NAME},
    )
    entry.add_to_hass(hass)
    return entry


async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with _patch_device_id(DEVICE_ID):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: DEVICE_NAME, CONF_HOST: "192.168.1.50/"},
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Heatit WiFi6 ({DEVICE_NAME})"
    # The host is normalized: scheme added, trailing slash stripped.
    assert result["data"][CONF_HOST] == "http://192.168.1.50"
    assert result["result"].unique_id == DEVICE_ID


async def test_user_flow_cannot_connect_then_recovers(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with _patch_device_id("unknown"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: DEVICE_NAME, CONF_HOST: "192.168.1.50"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    with _patch_device_id(DEVICE_ID):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: DEVICE_NAME, CONF_HOST: "192.168.1.50"},
        )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_aborts_when_already_configured(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    _make_entry(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with _patch_device_id(DEVICE_ID):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: DEVICE_NAME, CONF_HOST: "192.168.1.60"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_updates_host(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    entry = _make_entry(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with _patch_device_id(DEVICE_ID):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.99"}
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "http://192.168.1.99"
    # The name and unique_id survive the host change.
    assert entry.data[CONF_NAME] == DEVICE_NAME
    assert entry.unique_id == DEVICE_ID


async def test_reconfigure_cannot_connect_then_recovers(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    entry = _make_entry(hass)

    result = await entry.start_reconfigure_flow(hass)
    with _patch_device_id("unknown"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.99"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data[CONF_HOST] == "http://192.168.1.50"

    with _patch_device_id(DEVICE_ID):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.99"}
        )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "http://192.168.1.99"


async def test_reconfigure_rejects_different_device(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    entry = _make_entry(hass)

    result = await entry.start_reconfigure_flow(hass)
    with _patch_device_id(OTHER_DEVICE_ID):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.99"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "different_device"
    # The entry keeps pointing at the original thermostat.
    assert entry.data[CONF_HOST] == "http://192.168.1.50"
    assert entry.unique_id == DEVICE_ID


async def test_options_flow_sets_scan_interval(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    entry = _make_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: "http://192.168.1.50", CONF_SCAN_INTERVAL: 120},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 120
    assert entry.data[CONF_HOST] == "http://192.168.1.50"


async def test_options_flow_rejects_different_device(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    entry = _make_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with _patch_device_id(OTHER_DEVICE_ID):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_HOST: "http://192.168.1.99", CONF_SCAN_INTERVAL: 60},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "different_device"}
    assert entry.data[CONF_HOST] == "http://192.168.1.50"
