import {
    LitElement,
    html,
    css,
  } from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";
  
  class Zigbee2MqttMapPanel extends LitElement {
    render() {
      // Returns an iframe pointing to your map.html file
      return html`
        <iframe src="/local/community/zigbee2mqtt_networkmap/map.html"></iframe>
      `;
    }
  
    static get styles() {
      return css`
        :host {
          display: block;
          height: 100%;
        }
        iframe {
          width: 100%;
          height: 100%;
          border: none;
        }
      `;
    }
  }
  
  // Defines the new custom element
  customElements.define("z2m-map-panel", Zigbee2MqttMapPanel);