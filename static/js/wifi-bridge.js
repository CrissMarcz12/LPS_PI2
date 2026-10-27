/** Puente HTTP para el ESP32 alimentado externamente y conectado por Wi-Fi. */
export class WifiBridge {
  constructor({ onButton, onStatus } = {}) {
    this.onButton = onButton ?? (() => {});
    this.onStatus = onStatus ?? (() => {});
    this.deviceId = new URLSearchParams(location.search).get("device") || localStorage.getItem("rimaymaki-device-id") || "RIMAY-001";
    localStorage.setItem("rimaymaki-device-id", this.deviceId);
    this.connected = false;
    this.status = "disconnected";
    this.timer = null;
    this.polling = false;
    this.transport = "wifi";
  }

  get supported() { return true; }

  setStatus(status) {
    if (this.status === status) return;
    this.status = status;
    this.onStatus(status);
  }

  async restore() {
    if (this.timer) return;
    this.setStatus("connecting");
    await this.pollEvents();
    this.timer = window.setInterval(() => this.pollEvents(), 250);
  }

  async requestConnection() { await this.restore(); }

  async pollEvents() {
    if (this.polling) return;
    this.polling = true;
    try {
      const response = await fetch(`/api/device/${encodeURIComponent(this.deviceId)}/events`, { cache: "no-store" });
      if (!response.ok) throw new Error("No se pudo consultar el ESP32 Wi-Fi.");
      const data = await response.json();
      this.connected = Boolean(data.online);
      this.setStatus(this.connected ? "connected" : "disconnected");
      (data.events || []).forEach(event => this.onButton(event));
    } catch (error) {
      this.connected = false;
      this.setStatus("error");
    } finally {
      this.polling = false;
    }
  }

  async send(command) {
    try {
      await fetch(`/api/device/${encodeURIComponent(this.deviceId)}/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
    } catch (error) {
      console.warn("No se pudo enviar una orden al ESP32 Wi-Fi.", error);
    }
  }

  feedback(result, withSound = true) {
    if (result === "correct") return this.send(withSound ? "BIEN" : "LED_BIEN");
    if (result === "incorrect") return this.send(withSound ? "MAL" : "LED_MAL");
  }

  setBuzzerEnabled(enabled) { return this.send(`SOUND${enabled ? 1 : 0}`); }
}
