import homeassistant.loader as loader
from homeassistant.components.mqtt import async_subscribe, async_publish
from homeassistant.components.webhook import (
    async_generate_id,
    async_register,
)
import os
from distutils.dir_util import copy_tree
from datetime import datetime
from aiohttp import web
import json

DOMAIN = 'zigbee2mqtt_networkmap'
DEPENDENCIES = ['mqtt']

CONF_TOPIC = 'topic'
DEFAULT_TOPIC = 'zigbee2mqtt'


async def async_setup(hass, config):
    fromDirectory = hass.config.path('custom_components', 'zigbee2mqtt_networkmap', 'www')
    toDirectory = hass.config.path('www', 'community', 'zigbee2mqtt_networkmap')

    # 👇 Chạy copy_tree trong thread executor
    await hass.async_add_executor_job(copy_tree, fromDirectory, toDirectory)

    # topic = config[DOMAIN].get(CONF_TOPIC, DEFAULT_TOPIC)
    topic = DEFAULT_TOPIC
    entity_id = 'zigbee2mqtt_networkmap.map_last_update'
    tmpVar = type('', (), {})()

    async def handle_webhook_trigger_update(hass, webhook_id, request):
        hass.async_create_task(update_service(None))
        return web.json_response({"success": "ok"})

    async def handle_webhook_check_update(hass, webhook_id, request):
        return web.json_response({
            "success": "ok",
            "update_received": bool(tmpVar.received_update),
            "update_received_data": tmpVar.update_data,
            "last_update": tmpVar.last_update
        })

    webhook_trigger_update_id = async_generate_id()
    async_register(
        hass,
        DOMAIN,
        'zigbee2mqtt_networkmap-webhook_trigger_update',
        webhook_trigger_update_id,
        handle_webhook_trigger_update,
    )

    webhook_check_update_id = async_generate_id()
    async_register(
        hass,
        DOMAIN,
        'zigbee2mqtt_networkmap-webhook_check_update',
        webhook_check_update_id,
        handle_webhook_check_update,
    )

    # 👇 Viết file settings.js trong thread executor
    def write_settings_js():
        path = hass.config.path('www', 'community', 'zigbee2mqtt_networkmap', 'settings.js')
        with open(path, "w") as f:
            f.write(f"var webhook_trigger_update_id = '{webhook_trigger_update_id}';\n")
            f.write(f"var webhook_check_update_id = '{webhook_check_update_id}';")

    await hass.async_add_executor_job(write_settings_js)

    async def message_received(msg):
        data_load = json.loads(msg.payload)
        value = data_load["data"]["value"]
        payload = str(value).replace('\n', ' ').replace('\r', '').replace("'", r"\'")
        last_update = datetime.now()

        # 👇 Viết file source.js trong thread executor
        def write_source_js():
            path = hass.config.path('www', 'community', 'zigbee2mqtt_networkmap', 'source.js')
            with open(path, "w") as f:
                f.write("var last_update = new Date('{}');\n".format(
                    last_update.strftime('%Y/%m/%d %H:%M:%S')))
                f.write("var graph = '{}';".format(payload))

        await hass.async_add_executor_job(write_source_js)

        hass.states.async_set(entity_id, last_update)
        tmpVar.received_update = True
        tmpVar.update_data = payload
        tmpVar.last_update = last_update.strftime('%Y/%m/%d %H:%M:%S')

    await async_subscribe(hass, topic + '/bridge/response/networkmap', message_received)

    hass.states.async_set(entity_id, None)
    tmpVar.received_update = False
    tmpVar.update_data = None
    tmpVar.last_update = None

    async def update_service(call):
        tmpVar.received_update = False
        tmpVar.update_data = None
        tmpVar.last_update = None
        hass.async_create_task(async_publish(hass, topic + '/bridge/request/networkmap', 'graphviz'))

    hass.services.async_register(DOMAIN, 'update', update_service)
    return True
async def async_setup_entry(hass, entry):
    """Set up zigbee2mqtt_networkmap from a config entry."""
    # Gọi hàm setup của bạn tại đây
    await async_setup(hass, {entry.domain: entry.data})
    return True
