class Zigbee2MqttMapPanel extends HTMLElement {
    connectedCallback() {
      this.innerHTML = `
        <iframe src="/local/community/zigbee2mqtt_networkmap/map.html" style="width:100%; height:100%; border:none;"></iframe>
      `;
    }
  }
  
  customElements.define("z2m-map", Zigbee2MqttMapPanel);