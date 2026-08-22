class Zigbee2MqttMapPanel extends HTMLElement {
  connectedCallback() {
    if (this._rendered) {
      return;
    }
    this._rendered = true;

    // The panel host has no intrinsic height, so give it one before the
    // iframe tries to fill it.
    this.style.display = "block";
    this.style.height = "100%";
    this.style.width = "100%";

    const frame = document.createElement("iframe");
    // Home Assistant serves /local with a month-long cache header, so without a
    // busting parameter an updated map.html keeps being read from the browser
    // cache. viz.js and panzoom are left cacheable: they never change.
    frame.src = "/local/community/zigbee2mqtt_networkmap/map.html?v=" + Date.now();
    frame.setAttribute("title", "Zigbee network map");
    frame.style.cssText = "display:block;width:100%;height:100%;border:none;";
    this.appendChild(frame);
  }
}

customElements.define("z2m-map", Zigbee2MqttMapPanel);
