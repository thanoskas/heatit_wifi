"""Config flow for the Heatit WiFi6 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeatitWiFi6API
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
    }
)


def _normalize_host(host: str) -> str:
    if "://" not in host:
        host = f"http://{host}"
    return host.rstrip("/")


class HeatitWiFi6ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the user-driven config flow for Heatit WiFi6 thermostats."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> HeatitWiFi6OptionsFlow:
        """Create the options flow."""
        return HeatitWiFi6OptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = _normalize_host(user_input[CONF_HOST])
            user_input[CONF_HOST] = host

            session = async_get_clientsession(self.hass)
            api = HeatitWiFi6API(host, session)
            device_id = await api.get_device_id(retries=1, timeout=10)

            if device_id == "unknown":
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                _LOGGER.debug(
                    "Adding Heatit WiFi6 device id=%s name=%s host=%s",
                    device_id, user_input[CONF_NAME], host,
                )
                return self.async_create_entry(
                    title=f"Heatit WiFi6 ({user_input[CONF_NAME]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change the device's address without re-adding it."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = _normalize_host(user_input[CONF_HOST])

            session = async_get_clientsession(self.hass)
            api = HeatitWiFi6API(host, session)
            device_id = await api.get_device_id(retries=1, timeout=10)

            if device_id == "unknown":
                errors["base"] = "cannot_connect"
            else:
                # Guard against pointing the entry at a different
                # thermostat, which would orphan all its entities.
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_mismatch(reason="different_device")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_HOST: host}
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=entry.data[CONF_HOST]
                    ): cv.string,
                }
            ),
            errors=errors,
        )


class HeatitWiFi6OptionsFlow(OptionsFlow):
    """Change the polling interval or the device's address."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the options step."""
        errors: dict[str, str] = {}
        entry = self.config_entry

        if user_input is not None:
            host = _normalize_host(user_input[CONF_HOST])

            if host != entry.data[CONF_HOST]:
                session = async_get_clientsession(self.hass)
                api = HeatitWiFi6API(host, session)
                device_id = await api.get_device_id(retries=1, timeout=10)
                if device_id == "unknown":
                    errors["base"] = "cannot_connect"
                elif entry.unique_id and device_id != entry.unique_id:
                    # Guard against pointing the entry at a different
                    # thermostat, which would orphan all its entities.
                    errors["base"] = "different_device"
                else:
                    self.hass.config_entries.async_update_entry(
                        entry, data={**entry.data, CONF_HOST: host}
                    )

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=entry.data[CONF_HOST]
                ): cv.string,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
