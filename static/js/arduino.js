/** Puente Web Serial para el ESP32 conectado por USB a la tableta. */
const encoder = new TextEncoder();

export class ArduinoBridge {
  constructor({ onButton, onStatus } = {}) {
    this.onButton = onButton ?? (() => {});
    this.onStatus = onStatus ?? (() => {});
    this.port = null;
    this.writer = null;
    this.connected = false;
    this.buffer = "";
  }

  get supported() { return "serial" in navigator; }

  async restore() {
    if (!this.supported) return this.onStatus("unsupported");
    const ports = await navigator.serial.getPorts();
    if (ports[0]) await this.attach(ports[0]);
    else this.onStatus("disconnected");
  }

  async requestConnection() {
    if (!this.supported) throw new Error("Conecta el ESP32 desde Chrome o Edge en una tableta o computadora Windows.");
    const port = await navigator.serial.requestPort();
    await this.attach(port);
  }

  async attach(port) {
    this.onStatus("connecting");
    try {
      this.port = port;
      if (!port.readable && !port.writable) await port.open({ baudRate: 115200 });
      this.writer = port.writable.getWriter();
      this.connected = true;
      this.onStatus("connected");
      this.readLoop();
    } catch (error) {
      this.connected = false;
      this.onStatus("error");
      throw error;
    }
  }

  async readLoop() {
    const reader = this.port?.readable?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    try {
      while (this.port?.readable) {
        const { value, done } = await reader.read();
        if (done) break;
        this.buffer += decoder.decode(value, { stream: true });
        const lines = this.buffer.split(/\r?\n/);
        this.buffer = lines.pop() ?? "";
        lines.map(line => line.trim()).filter(Boolean).forEach(line => this.handleLine(line));
      }
    } catch (error) {
      console.warn("Se perdió la conexión con el ESP32.", error);
    } finally {
      reader.releaseLock();
      this.connected = false;
      this.onStatus("disconnected");
    }
  }

  handleLine(line) {
    if (/^BTN[1-4]$/.test(line)) this.onButton(line);
  }

  async send(text) {
    if (!this.connected || !this.writer) return;
    try { await this.writer.write(encoder.encode(`${text}\n`)); }
    catch (error) { console.warn("No se pudo enviar el resultado al ESP32.", error); }
  }

  feedback(result) {
    if (result === "correct") return this.send("BIEN");
    if (result === "incorrect") return this.send("MAL");
  }

  setBuzzerVolume(level) {
    const percent = Math.round(Math.max(0, Math.min(1, Number(level) || 0)) * 100);
    return this.send(`VOL${percent}`);
  }
}
