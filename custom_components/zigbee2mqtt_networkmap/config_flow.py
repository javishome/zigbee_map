"""Config and options flow for the Zigbee2MQTT Networkmap integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import CONF_TOPICS, DEFAULT_TOPIC, DOMAIN


def clean_topics(raw) -> list[str]:
    """Normalise the submitted topics: trimmed, slash-free, deduplicated."""
    if isinstance(raw, str):
        raw = raw.split(",")

    topics: list[str] = []
    for value in raw or []:
        topic = str(value).strip().strip("/")
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def topics_schema(default: list[str]) -> vol.Schema:
    """One repeatable text field holding every base topic to watch."""
    return vol.Schema(
        {
            vol.Required(CONF_TOPICS, default=default): TextSelector(
                TextSelectorConfig(multiple=True)
            )
        }
    )


class ZigbeeMapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup of the integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Ask which zigbee2mqtt base topics to watch."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            topics = clean_topics(user_input.get(CONF_TOPICS))
            if not topics:
                return self.async_show_form(
                    step_id="user",
                    data_schema=topics_schema([DEFAULT_TOPIC]),
                    errors={CONF_TOPICS: "invalid_topics"},
                )
            return self.async_create_entry(
                title="Zigbee map", data={CONF_TOPICS: topics}
            )

        return self.async_show_form(
            step_id="user", data_schema=topics_schema([DEFAULT_TOPIC])
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow so the topics can be changed later."""
        return ZigbeeMapOptionsFlow()


class ZigbeeMapOptionsFlow(OptionsFlow):
    """Allow the watched base topics to be changed after setup."""

    async def async_step_init(self, user_input=None):
        """Show and store the topic list."""
        # Imported lazily so this module stays importable on its own.
        from . import configured_topics

        current = configured_topics(self.config_entry)

        if user_input is not None:
            topics = clean_topics(user_input.get(CONF_TOPICS))
            if not topics:
                return self.async_show_form(
                    step_id="init",
                    data_schema=topics_schema(current),
                    errors={CONF_TOPICS: "invalid_topics"},
                )
            return self.async_create_entry(title="", data={CONF_TOPICS: topics})

        return self.async_show_form(
            step_id="init", data_schema=topics_schema(current)
        )
