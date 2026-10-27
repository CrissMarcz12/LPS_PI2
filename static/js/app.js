import { getSession, nextRound, restartGame, retryRound, sendLandmarks } from "./game.js";
import { ArduinoBridge } from "./arduino.js";
import { LocalHandCamera } from "./recognition.js";
import { cameraReady, cycleEffectsVolume, render } from "./ui.js";

let camera, autoRetryTimer, lastArduinoFeedback;
let arduino;
function apply(state) {
  if (!state || typeof state !== "object") throw new Error("Respuesta inválida del servicio.");
  render(state); camera?.setCorrectionHint?.(state.result === "incorrect" ? state.errorHint : "");
  if (["correct", "incorrect"].includes(state.result) && state.result !== lastArduinoFeedback) {
    lastArduinoFeedback = state.result;
    arduino?.feedback(state.result);
  } else if (!["correct", "incorrect"].includes(state.result)) lastArduinoFeedback = null;
  // La cámara sigue visible debajo de la celebración; solo se detiene al terminar la sesión.
  if (state.result === "completed") camera?.stop();
  if (state.result === "incorrect" && !autoRetryTimer) {
    autoRetryTimer = setTimeout(async () => { autoRetryTimer = null; const next = await safely(retryRound); if (next) apply(next); }, 850);
  } else if (state.result !== "incorrect" && autoRetryTimer) { clearTimeout(autoRetryTimer); autoRetryTimer = null; }
}
async function startRecognition() {
  const state = await getSession(); apply(state); if (!state.target) return;
  camera?.stop();
  camera = new LocalHandCamera(document.querySelector("#camera"), document.querySelector("#landmarks"), apply, () => cameraReady(false, "No pudimos usar la cámara. Permite el acceso e inténtalo otra vez."), sendLandmarks, state.recognitionIntervalMs || 100);
  const active = await camera.start(); cameraReady(active, active ? "Cámara activa · detectando mano" : "Cámara no disponible");
}
async function safely(action) { try { return await action(); } catch (error) { console.error(error); cameraReady(false, "No pudimos conectar con el reconocimiento."); return null; } }
document.querySelector("#next").addEventListener("click", async () => { camera?.stop(); const state = await safely(nextRound); if (state?.result !== "completed") await safely(startRecognition); else if (state) apply(state); });
async function restartActivity() {
  camera?.stop();
  const state = await safely(restartGame);
  if (state?.target) await safely(startRecognition);
  else if (state) apply(state);
}
const fullscreen = document.querySelector("#fullscreen");
async function toggleFullscreen() { const stage = document.querySelector("#camera-stage"); try { if (document.fullscreenElement) await document.exitFullscreen(); else if (stage.requestFullscreen) await stage.requestFullscreen(); else stage.webkitRequestFullscreen?.(); } catch (error) { console.warn("No se pudo activar pantalla completa", error); } }
fullscreen.addEventListener("click", toggleFullscreen);
document.addEventListener("fullscreenchange", () => { const active = Boolean(document.fullscreenElement); document.body.classList.toggle("immersive", active); fullscreen.textContent = active ? "×" : "⛶"; fullscreen.setAttribute("aria-label", active ? "Salir de pantalla completa" : "Activar pantalla completa"); });
async function hardwareAction(action) {
  if (action === "start") {
    await toggleFullscreen();
  } else if (action === "next" && !document.querySelector("#next").classList.contains("hidden")) {
    document.querySelector("#next").click();
  } else if (action === "volume") {
    cycleEffectsVolume();
  } else if (action === "restart") {
    await restartActivity();
  }
}
const buttonAction = { BTN1: "start", BTN2: "next", BTN3: "volume", BTN4: "restart" };
function showArduinoStatus(status) {
  const button = document.querySelector("#arduino-connect");
  if (!button) return;
  const labels = { unsupported: "USB no compatible", disconnected: "CONECTAR ESP32", connecting: "CONECTANDO…", connected: "✓ ESP32", error: "REINTENTAR USB" };
  button.textContent = labels[status] || labels.disconnected;
  button.dataset.status = status;
  button.title = status === "connected" ? "ESP32 conectado" : "Conectar el ESP32 por USB";
}
arduino = new ArduinoBridge({ onButton: code => hardwareAction(buttonAction[code]), onStatus: showArduinoStatus });
document.querySelector("#arduino-connect").addEventListener("click", async () => {
  try { await arduino.requestConnection(); }
  catch (error) { console.warn("No se pudo conectar el ESP32.", error); showArduinoStatus("error"); }
});
// El ESP32 puede enviar BTN1…BTN4 directamente por Web Serial. Las teclas se
// conservan para probar la interfaz sin hardware.
document.addEventListener("keydown", async event => {
  if (event.repeat) return;
  const key = event.key.toLowerCase();
  const action = ["p", "enter", " "].includes(key) ? "start" : ["n", "arrowright"].includes(key) ? "next" : ["v", "arrowup"].includes(key) ? "volume" : ["r", "arrowleft"].includes(key) ? "restart" : null;
  if (action) {
    event.preventDefault();
    await hardwareAction(action);
  }
});
arduino.restore().catch(() => showArduinoStatus("disconnected"));
safely(startRecognition);
