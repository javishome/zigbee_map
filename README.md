# Zigbee Map

A Home Assistant custom integration that draws the Zigbee mesh reported by
[zigbee2mqtt](https://www.zigbee2mqtt.io/). It asks zigbee2mqtt for a Graphviz
network map over MQTT and renders it in a sidebar panel, entirely inside the
browser — no cloud service and no extra Python dependencies.

Several zigbee2mqtt instances can be watched at once, each on its own base
topic, and switched between from the panel.

## Features

- **Zigbee Map** panel in the Home Assistant sidebar.
- Watches one or many zigbee2mqtt instances (`zigbee2mqtt`, `zigbee2mqtt2`, …)
  with a network picker in the toolbar. Instances that are not running are
  reported as such instead of breaking the panel.
- Device counts per type: coordinator, mains-powered routers, battery end
  devices — and a filter to show or hide each type.
- Text filter over friendly name, IEEE address and model, which highlights
  matches and their neighbours.
- Click a device for its address, model and per-neighbour link quality.
- Six Graphviz layout engines (`circo`, `dot`, `fdp`, `neato`, `osage`,
  `twopi`), pan, zoom and fit-to-view.
- Light and dark theme, following the browser and switchable by hand.
- A `zigbee2mqtt_networkmap.update` service, optionally scoped to one network.

## Requirements

- Home Assistant 2024.11 or newer with the
  [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) set up.
- One or more zigbee2mqtt instances on the same MQTT broker.
- A writable `<config>/www` folder — the panel assets are copied to
  `<config>/www/community/zigbee2mqtt_networkmap/` on startup.

## Installation

### HACS (recommended)

1. In HACS, add this repository as a custom repository of type **Integration**.
2. Install **Zigbee Map**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and pick
   **Zigbee map**.

### Manual

1. Copy `custom_components/zigbee2mqtt_networkmap` into your
   `<config>/custom_components/` folder.
2. Restart Home Assistant.
3. Add the integration from **Settings → Devices & services**.

## Configuration

The setup dialog asks for the **base topics** to watch — one entry per
zigbee2mqtt instance. Each must match that instance's `mqtt.base_topic`:

| Instance | Base topic |
| --- | --- |
| First zigbee2mqtt add-on | `zigbee2mqtt` |
| Second add-on | `zigbee2mqtt2` |
| Third add-on | `zigbee2mqtt3` |

Topics can be added or removed later through the integration's **Configure**
button; the integration reloads itself when the options are saved.

A topic may be listed before its add-on exists. Nothing is required to answer:
such a network shows as **not seen** in the panel and everything else keeps
working.

Only one instance of the *integration* is supported, because the panel assets
are written to a single shared folder. Watch several zigbee2mqtt instances by
listing several base topics, not by adding the integration twice.

## Usage

Open **Zigbee Map** in the sidebar.

- **Network** picks the zigbee2mqtt instance to display, with its state next to
  the name: `online`, `offline`, or `not seen` (nothing heard from it yet).
- **Update** asks the selected instance for a fresh map. The double-arrow button
  next to it asks every configured instance.
- zigbee2mqtt walks the whole mesh, so a scan takes anywhere from a few seconds
  to a couple of minutes; the panel polls every three seconds and gives up after
  two minutes with a message naming the instance that stayed silent.
- **Device types** in the bottom-left corner shows how many coordinators,
  routers and end devices the map holds; click a row to hide that type.
- **Filter devices** highlights matching devices and dims the rest.

Keyboard shortcuts: `/` focus the filter, `1`/`2`/`3` toggle the device types,
`n` next network, `r` update the current network, `Shift+R` update all, `+`/`-`
zoom, `f` fit to view, `Esc` clear the filter and selection.

### Service

```yaml
# Refresh every configured instance
action: zigbee2mqtt_networkmap.update
```

```yaml
# Refresh one instance
action: zigbee2mqtt_networkmap.update
data:
  network: zigbee2mqtt2
```

`network` also accepts a list. An unknown base topic raises an error naming the
configured ones.

### State objects

| Entity | Meaning |
| --- | --- |
| `zigbee2mqtt_networkmap.<topic>_last_update` | Timestamp of that network's last map, one per base topic |
| `zigbee2mqtt_networkmap.map_last_update` | Timestamp of whichever network updated last, with a `network` attribute |

The per-network entity id uses the slugified base topic, for example
`zigbee2mqtt_networkmap.zigbee2mqtt2_last_update`.

## How it works

1. On setup, the integration copies its `www/` folder to
   `<config>/www/community/zigbee2mqtt_networkmap/` and writes a `settings.js`
   holding two freshly generated webhook IDs and the list of watched topics.
2. For every base topic it subscribes to
   `<topic>/bridge/response/networkmap` (the maps) and `<topic>/bridge/state`
   (whether that instance is online — old `online`/`offline` payloads and newer
   `{"state": "online"}` are both understood).
3. The panel is a small custom element that embeds `map.html` in an iframe.
4. **Update** calls the trigger webhook with the wanted network, which publishes
   `graphviz` to `<topic>/bridge/request/networkmap`.
5. Answers are stored in memory and mirrored to `source.js` as
   `networks_data`, keyed by base topic.
6. The panel polls the check webhook until the maps arrive, renders them with
   [viz.js](https://github.com/mdaines/viz.js) (a WebAssembly build of Graphviz)
   and makes them pan/zoomable with
   [panzoom](https://github.com/anvaka/panzoom).

Because the webhook IDs are regenerated on every restart, `settings.js` is
cache-busted on load.

## Repository layout

```
custom_components/zigbee2mqtt_networkmap/
├── __init__.py        # setup, MQTT plumbing, webhooks, service, panel
├── config_flow.py     # UI config + options flow
├── const.py           # shared constants
├── manifest.json
├── services.yaml
├── strings.json
├── translations/      # en, vi
└── www/               # assets copied into <config>/www/community/
    ├── map.html
    ├── zigbee2mqtt-map-panel.js
    ├── panzoom/
    └── viz.js/
```

## Troubleshooting

**The panel says the webhook IDs are missing.** `settings.js` could not be
written. Check that `<config>/www/community/zigbee2mqtt_networkmap/` exists and
is writable, then restart Home Assistant.

**A network shows as "not seen".** Nothing has been received on
`<topic>/bridge/state`. Either that zigbee2mqtt instance is not running, or its
`mqtt.base_topic` differs from what is configured here.

**No answer after two minutes.** The base topic matches nothing on the broker.
Subscribing to `<topic>/bridge/response/networkmap` with an MQTT client shows
whether zigbee2mqtt answers at all.

**Layouts overlap.** `neato` and `fdp` get `overlap=false` and curved splines
injected; if a map is still crowded, try `circo` or `dot`.

## Credits

Based on the original
[zigbee2mqtt_networkmap](https://github.com/rgruebel/ha_zigbee2mqtt_networkmap)
idea, packaged and maintained by [javishome](https://github.com/javishome).
