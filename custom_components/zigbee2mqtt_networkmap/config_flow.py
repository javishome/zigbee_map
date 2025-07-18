from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .__init__ import DOMAIN

class ZigbeeMapConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_create_flow(handler, context, data):
            """Create flow."""
    async def async_finish_flow(flow, result):
            """Finish flow."""
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Zigbee map", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
            })
        )
