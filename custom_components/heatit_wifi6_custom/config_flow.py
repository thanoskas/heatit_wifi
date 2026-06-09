import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HeatitWiFi6ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    
    VERSION = 1

    def __init__(self):
        self._host = None
        self._name = None

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            if "://" not in user_input[CONF_HOST]: 
                user_input[CONF_HOST] = "http://" + user_input[CONF_HOST]
            self._name = user_input[CONF_NAME]
            self._host = user_input[CONF_HOST]
            _LOGGER.info("add_device_done - name: %s, host: %s", str(self._name), str(self._host))
            
            return self.async_create_entry(
                title = f"Heatit WiFi6 ({self._name})",
                data = user_input
            )
        
        return self.async_show_form(
            step_id="user",
            data_schema = vol.Schema({
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_HOST): cv.string
            }),
            description_placeholders = {
               CONF_NAME: "description_name",
               CONF_HOST: "description_host"
            }
        )
