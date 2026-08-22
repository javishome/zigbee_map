"""Constants for the Zigbee2MQTT Networkmap integration."""

DOMAIN = "zigbee2mqtt_networkmap"

# A single zigbee2mqtt base topic, as stored by releases before multi-network
# support. Still read so existing config entries keep working.
CONF_TOPIC = "topic"
# The current setting: one or more zigbee2mqtt base topics.
CONF_TOPICS = "topics"
CONF_NETWORK = "network"

DEFAULT_TOPIC = "zigbee2mqtt"

# Kept for backwards compatibility: mirrors whichever network updated last.
ENTITY_ID = f"{DOMAIN}.map_last_update"

PANEL_URL_PATH = "z2m-map"
PANEL_ELEMENT_NAME = "z2m-map"

WWW_TARGET = ("www", "community", DOMAIN)

SERVICE_UPDATE = "update"

WEBHOOK_TRIGGER_NAME = f"{DOMAIN}-webhook_trigger_update"
WEBHOOK_CHECK_NAME = f"{DOMAIN}-webhook_check_update"
