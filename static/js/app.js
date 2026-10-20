import { getSession, nextRound, restartGame, retryRound, sendLandmarks } from "./game.js";
import { LocalHandCamera } from "./recognition.js";
import { cameraReady, cycleEffectsVolume, render } from "./ui.js";

let camera, autoRetryTimer;
function apply(state) {
  if (!state || typeof state !== "object") throw new Error("Respuesta inválida del servicio.");
  render(state); camera?.setCorrectionHint?.(state.result === "incorrect" ? state.errorHint : "");
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
// Arduino como teclado USB: P = inicio/apagado visual, N = siguiente,
// V = volumen de efectos y R = reiniciar actividad completa.
document.addEventListener("keydown", async event => {
  if (event.repeat) return;
  const key = event.key.toLowerCase();
  if (["p", "enter", " "].includes(key)) {
    event.preventDefault();
    await toggleFullscreen();
  } else if (["n", "arrowright"].includes(key) && !document.querySelector("#next").classList.contains("hidden")) {
    event.preventDefault();
    document.querySelector("#next").click();
  } else if (["v", "arrowup"].includes(key)) {
    event.preventDefault();
    cycleEffectsVolume();
  } else if (["r", "arrowleft"].includes(key)) {
    event.preventDefault();
    await restartActivity();
  }
});
safely(startRecognition);
