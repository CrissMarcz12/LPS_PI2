import { getSession, nextRound, retryRound } from "./game.js";
import { BrowserCamera } from "./recognition.js";
import { cameraReady, render } from "./ui.js";

let camera;
function apply(state) {
  if (!state || typeof state !== "object") throw new Error("Respuesta inválida del servicio.");
  render(state); camera?.drawLandmarks(state.showLandmarks && Array.isArray(state.landmarks) ? state.landmarks : []);
  // La cámara sigue visible debajo de la celebración; solo se detiene al terminar la sesión.
  if (state.result === "completed") camera?.stop();
}
async function startRecognition() {
  const state = await getSession(); apply(state); if (!state.target) return;
  camera?.stop();
  camera = new BrowserCamera(document.querySelector("#camera"), document.querySelector("#capture"), document.querySelector("#landmarks"), apply, () => cameraReady(false, "No pudimos usar la cámara. Permite el acceso e inténtalo otra vez."), undefined, state.recognitionIntervalMs || 100);
  const active = await camera.start(); cameraReady(active, active ? "Cámara activa · detectando mano" : "Cámara no disponible");
}
async function safely(action) { try { return await action(); } catch (error) { console.error(error); cameraReady(false, "No pudimos conectar con el reconocimiento."); return null; } }
document.querySelector("#next").addEventListener("click", async () => { camera?.stop(); const state = await safely(nextRound); if (state?.result !== "completed") await safely(startRecognition); else if (state) apply(state); });
document.querySelector("#retry").addEventListener("click", async () => { const state = await safely(retryRound); if (state) { apply(state); await safely(startRecognition); } });
const fullscreen = document.querySelector("#fullscreen");
fullscreen.addEventListener("click", async () => { const stage = document.querySelector("#camera-stage"); try { if (document.fullscreenElement) await document.exitFullscreen(); else if (stage.requestFullscreen) await stage.requestFullscreen(); else stage.webkitRequestFullscreen?.(); } catch (error) { console.warn("No se pudo activar pantalla completa", error); } });
document.addEventListener("fullscreenchange", () => { const active = Boolean(document.fullscreenElement); document.body.classList.toggle("immersive", active); fullscreen.textContent = active ? "×" : "⛶"; fullscreen.setAttribute("aria-label", active ? "Salir de pantalla completa" : "Activar pantalla completa"); });
safely(startRecognition);
