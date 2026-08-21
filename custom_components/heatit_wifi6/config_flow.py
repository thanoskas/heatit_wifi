"""Config flow for the Heatit WiFi6 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeatitWiFi6API
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
    }
)


class HeatitWiFi6ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the user-driven config flow for Heatit WiFi6 thermostats."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            if "://" not in host:
                host = f"http://{host}"
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
