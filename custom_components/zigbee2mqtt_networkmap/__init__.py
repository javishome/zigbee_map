"""The Zigbee2MQTT Networkmap integration.

Requests a Graphviz network map from one or more zigbee2mqtt instances over MQTT
and serves them to a sidebar panel that renders the graphs client side with
viz.js. Configured instances are allowed to be absent: a base topic nobody
answers on simply stays unavailable instead of breaking the panel.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime

import voluptuous as vol
from aiohttp import web

from homeassistant.components.frontend import (
    async_register_built_in_panel,
    async_remove_panel,
)
from homeassistant.components.mqtt import async_publish, async_subscribe
from homeassistant.components.webhook import (
    async_generate_id,
    async_register as async_register_webhook,
    async_unregister as async_unregister_webhook,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.util import slugify

from .const import (
    CONF_NETWORK,
    CONF_TOPIC,
    CONF_TOPICS,
    DEFAULT_TOPIC,
    DOMAIN,
    ENTITY_ID,
    PANEL_ELEMENT_NAME,
    PANEL_URL_PATH,
    SERVICE_UPDATE,
    WEBHOOK_CHECK_NAME,
    WEBHOOK_TRIGGER_NAME,
    WWW_TARGET,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_SERVICE_SCHEMA = vol.Schema({vol.Optional(CONF_NETWORK): vol.Any(str, [str])})


def configured_topics(entry: ConfigEntry) -> list[str]:
    """Return the base topics for an entry, oldest storage shape included."""
    raw = entry.options.get(CONF_TOPICS, entry.data.get(CONF_TOPICS))
    if raw is None:
        # Entries written before multi-network support held a single topic, and
        # the very first release hardcoded the default.
        single = entry.options.get(CONF_TOPIC, entry.data.get(CONF_TOPIC))
        raw = [single] if single else [DEFAULT_TOPIC]
    if isinstance(raw, str):
        raw = [raw]

    topics: list[str] = []
    for value in raw:
        topic = str(value).strip().strip("/")
        if topic and topic not in topics:
            topics.append(topic)
    return topics or [DEFAULT_TOPIC]


class NetworkState:
    """The latest map, and reachability, of one zigbee2mqtt instance."""

    def __init__(self, topic: str, slug: str) -> None:
        self.topic = topic
        self.slug = slug
        self.graph: str | None = None
        self.last_update: str | None = None
        # None until zigbee2mqtt announces itself: the instance may not exist.
        self.online: bool | None = None
        # A scan is in flight. Survives the panel being closed, so reopening it
        # can pick the wait back up instead of asking for a second scan.
        self.pending = False
        self.requested_at: float | None = None

    @property
    def entity_id(self) -> str:
        """State object mirroring this network's last update."""
        return f"{DOMAIN}.{self.slug}_last_update"

    def mark_requested(self) -> None:
        """Forget the previous map and remember that a scan is running."""
        self.graph = None
        self.last_update = None
        self.pending = True
        # Monotonic: the panel needs an elapsed time, not a wall clock it would
        # have to compare against its own possibly-skewed clock.
        self.requested_at = time.monotonic()

    def mark_received(self, graph: str, timestamp: str) -> None:
        """Store an arrived map and close off the pending request."""
        self.graph = graph
        self.last_update = timestamp
        self.pending = False
        self.requested_at = None

    def pending_seconds(self) -> int | None:
        """How long the current scan has been running, if any."""
        if not self.pending or self.requested_at is None:
            return None
        return int(time.monotonic() - self.requested_at)

    def as_payload(self) -> dict:
        """Serialisable view used by the webhook and by source.js.

        A non-null graph means a map arrived since the last request, so the
        panel needs no separate "received" flag.
        """
        return {
            "topic": self.topic,
            "slug": self.slug,
            "online": self.online,
            "graph": self.graph,
            "last_update": self.last_update,
            "pending": self.pending,
            "pending_seconds": self.pending_seconds(),
        }


class NetworkmapCoordinator:
    """Owns every watched network plus the files served to the panel."""

    def __init__(self, hass: HomeAssistant, topics: list[str]) -> None:
        self.hass = hass
        self.networks: dict[str, NetworkState] = {}
        self.unsubscribers: list = []

        used: set[str] = set()
        for topic in topics:
            slug = slugify(topic) or "network"
            candidate = slug
            suffix = 2
            while candidate in used:
                candidate = f"{slug}_{suffix}"
                suffix += 1
            used.add(candidate)
            self.networks[topic] = NetworkState(topic, candidate)

    @property
    def www_dir(self) -> str:
        """Absolute path of the folder served to the browser."""
        return self.hass.config.path(*WWW_TARGET)

    def write_js(self, filename: str, contents: str) -> None:
        """Write a generated JS file into the served www folder.

        Runs in the executor. Raises OSError if the folder is not writable.
        """
        path = self.hass.config.path(*WWW_TARGET, filename)
        with open(path, "w", encoding="utf-8") as file:
            file.write(contents)

    def source_js(self) -> str:
        """Every network's map, as the panel expects to find it."""
        payload = {
            topic: network.as_payload() for topic, network in self.networks.items()
        }
        return f"var networks_data = {json.dumps(payload)};\n"

    def resolve(self, requested) -> list[NetworkState]:
        """Map a service or webhook argument to the networks it names."""
        if requested is None:
            return list(self.networks.values())
        names = [requested] if isinstance(requested, str) else list(requested)

        chosen: list[NetworkState] = []
        for name in names:
            topic = str(name).strip().strip("/")
            network = self.networks.get(topic)
            if network is None:
                known = ", ".join(self.networks) or "none"
                raise ServiceValidationError(
                    f"Unknown zigbee2mqtt network '{topic}'. Configured: {known}."
                )
            chosen.append(network)
        return chosen


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration from YAML.

    Configuration is done through the UI, so there is nothing to do here.
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zigbee2MQTT Networkmap from a config entry."""
    coordinator = NetworkmapCoordinator(hass, configured_topics(entry))
    asset_token = int(datetime.now().timestamp())

    source_dir = hass.config.path("custom_components", DOMAIN, "www")
    try:
        await hass.async_add_executor_job(
            lambda: shutil.copytree(
                source_dir, coordinator.www_dir, dirs_exist_ok=True
            )
        )
    except OSError as err:
        raise ConfigEntryNotReady(
            f"Unable to copy the panel assets to {coordinator.www_dir}: {err}"
        ) from err

    async def write_source() -> None:
        """Refresh source.js, logging rather than raising on failure."""
        try:
            await hass.async_add_executor_job(
                coordinator.write_js, "source.js", coordinator.source_js()
            )
        except OSError as err:
            _LOGGER.error(
                "Unable to write source.js into %s: %s", coordinator.www_dir, err
            )

    async def request_maps(networks: list[NetworkState]) -> None:
        """Ask the given networks for a fresh map."""
        for network in networks:
            network.mark_requested()
            hass.states.async_set(network.entity_id, None)
            await async_publish(
                hass, f"{network.topic}/bridge/request/networkmap", "graphviz"
            )
        await write_source()

    async def handle_webhook_trigger_update(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Ask one network, or every network, for a new map."""
        try:
            body = await request.json()
        except ValueError:
            body = {}
        try:
            networks = coordinator.resolve(
                body.get(CONF_NETWORK) if isinstance(body, dict) else None
            )
        except ServiceValidationError as err:
            return web.json_response({"success": False, "error": str(err)}, status=400)

        await request_maps(networks)
        return web.json_response(
            {"success": "ok", "requested": [network.topic for network in networks]}
        )

    async def handle_webhook_check_update(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Report the state of every watched network."""
        return web.json_response(
            {
                "success": "ok",
                "networks": {
                    topic: network.as_payload()
                    for topic, network in coordinator.networks.items()
                },
            }
        )

    trigger_id = async_generate_id()
    check_id = async_generate_id()

    async_register_webhook(
        hass, DOMAIN, WEBHOOK_TRIGGER_NAME, trigger_id, handle_webhook_trigger_update
    )
    async_register_webhook(
        hass, DOMAIN, WEBHOOK_CHECK_NAME, check_id, handle_webhook_check_update
    )

    settings_js = (
        f"var webhook_trigger_update_id = {json.dumps(trigger_id)};\n"
        f"var webhook_check_update_id = {json.dumps(check_id)};\n"
        f"var networks = {json.dumps(list(coordinator.networks))};\n"
    )
    try:
        await hass.async_add_executor_job(
            coordinator.write_js, "settings.js", settings_js
        )
    except OSError as err:
        async_unregister_webhook(hass, trigger_id)
        async_unregister_webhook(hass, check_id)
        raise ConfigEntryNotReady(
            f"Unable to write settings.js into {coordinator.www_dir}: {err}"
        ) from err

    def make_map_listener(network: NetworkState):
        """Build the networkmap handler for one instance."""

        async def message_received(msg) -> None:
            try:
                graph = json.loads(msg.payload)["data"]["value"]
            except (ValueError, KeyError, TypeError):
                _LOGGER.warning("Unexpected networkmap payload on %s", msg.topic)
                return

            timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            network.mark_received(graph, timestamp)
            await write_source()

            hass.states.async_set(network.entity_id, timestamp)
            hass.states.async_set(ENTITY_ID, timestamp, {"network": network.topic})

        return message_received

    def make_state_listener(network: NetworkState):
        """Build the bridge/state handler for one instance."""

        async def state_received(msg) -> None:
            payload = msg.payload
            if isinstance(payload, (bytes, bytearray)):
                payload = payload.decode("utf-8", "replace")
            payload = str(payload).strip()

            # zigbee2mqtt publishes a bare "online"/"offline" on older versions
            # and {"state": "online"} on newer ones.
            if payload.startswith("{"):
                try:
                    payload = str(json.loads(payload).get("state", "")).strip()
                except ValueError:
                    payload = ""

            lowered = payload.lower()
            if lowered in ("online", "offline"):
                network.online = lowered == "online"
                await write_source()

        return state_received

    for network in coordinator.networks.values():
        coordinator.unsubscribers.append(
            await async_subscribe(
                hass,
                f"{network.topic}/bridge/response/networkmap",
                make_map_listener(network),
            )
        )
        coordinator.unsubscribers.append(
            await async_subscribe(
                hass,
                f"{network.topic}/bridge/state",
                make_state_listener(network),
            )
        )
        hass.states.async_set(network.entity_id, None)

    hass.states.async_set(ENTITY_ID, None)
    await write_source()

    async def update_service(call: ServiceCall) -> None:
        """Service handler for zigbee2mqtt_networkmap.update."""
        await request_maps(coordinator.resolve(call.data.get(CONF_NETWORK)))

    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE, update_service, schema=UPDATE_SERVICE_SCHEMA
    )

    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="Zigbee Map",
        sidebar_icon="mdi:zigbee",
        frontend_url_path=PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": PANEL_ELEMENT_NAME,
                # /local is served with a month-long cache header, so the
                # panel script needs a token that changes when we reload.
                "module_url": (
                    f"/local/community/{DOMAIN}/zigbee2mqtt-map-panel.js"
                    f"?v={asset_token}"
                ),
                "full_width": True,
            }
        },
        require_admin=True,
    )

    coordinator.unsubscribers.append(
        lambda: async_unregister_webhook(hass, trigger_id)
    )
    coordinator.unsubscribers.append(lambda: async_unregister_webhook(hass, check_id))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and remove everything it registered."""
    coordinator: NetworkmapCoordinator | None = hass.data.get(DOMAIN, {}).pop(
        entry.entry_id, None
    )
    if coordinator is not None:
        for unsubscribe in coordinator.unsubscribers:
            unsubscribe()
        coordinator.unsubscribers.clear()
        for network in coordinator.networks.values():
            hass.states.async_remove(network.entity_id)

    hass.services.async_remove(DOMAIN, SERVICE_UPDATE)
    async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    hass.states.async_remove(ENTITY_ID)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
