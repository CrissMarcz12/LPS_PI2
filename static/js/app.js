import { getSession, nextRound, restartGame, retryRound, sendLandmarks } from "./game.js";
import { LocalHandCamera } from "./recognition.js";
import { cameraReady, render, showState } from "./ui.js?v=7";

let camera, autoRetryTimer, autoNextTimer, gameActive = false;
function apply(state) {
  if (!state || typeof state !== "object") throw new Error("Respuesta inválida del servicio.");
  if (!gameActive) return;
  if (state.result === "completed") { finishActivity(state); return; }
  render(state); camera?.setCorrectionHint?.(state.result === "incorrect" ? state.errorHint : "");
  // La cámara sigue visible debajo de la celebración; solo se detiene al terminar la sesión.
  if (state.result === "completed") camera?.stop();
  if (state.result === "incorrect" && !autoRetryTimer) {
    autoRetryTimer = setTimeout(async () => { autoRetryTimer = null; const next = await safely(retryRound); if (next) apply(next); }, 1250);
  } else if (state.result !== "incorrect" && autoRetryTimer) { clearTimeout(autoRetryTimer); autoRetryTimer = null; }
  if (state.result === "correct" && !autoNextTimer) {
    // Deja visible la animación de logro y continúa solo con la siguiente letra.
    autoNextTimer = setTimeout(async () => { autoNextTimer = null; await advanceRound(); }, 1450);
  } else if (state.result !== "correct" && autoNextTimer) { clearTimeout(autoNextTimer); autoNextTimer = null; }
}
async function startRecognition() {
  const state = await getSession(); apply(state); if (!state.target) return;
  camera?.stop();
  camera = new LocalHandCamera(document.querySelector("#camera"), document.querySelector("#landmarks"), apply, () => cameraReady(false, "No pudimos usar la cámara. Permite el acceso e inténtalo otra vez."), sendLandmarks, state.recognitionIntervalMs || 100);
  const active = await camera.start(); cameraReady(active, active ? "Cámara activa · detectando mano" : "Cámara no disponible");
}
async function safely(action) { try { return await action(); } catch (error) { console.error(error); cameraReady(false, "No pudimos conectar con el reconocimiento."); return null; } }
function showStartScreen(finished = false, state = null) {
  showState("start-state");
  document.querySelector("#start-title").textContent = finished ? "¡Gracias por jugar!" : "¡Hola, explorador!";
  document.querySelector("#start-copy").textContent = finished ? "Presiona START para comenzar una nueva aventura." : "Presiona el botón START para comenzar.";
  document.querySelector("#start-button").textContent = finished ? "JUGAR OTRA VEZ" : "START";
  document.querySelector("#start-summary").textContent = finished && state ? `${state.score} estrellas · racha máxima ${state.maxStreak}` : "Practica cada seña mirando la referencia.";
}
function stopActivity() {
  if (autoRetryTimer) { clearTimeout(autoRetryTimer); autoRetryTimer = null; }
  if (autoNextTimer) { clearTimeout(autoNextTimer); autoNextTimer = null; }
  camera?.stop();
  gameActive = false;
  showStartScreen(true);
}
function finishActivity(state) {
  camera?.stop();
  if (autoNextTimer) { clearTimeout(autoNextTimer); autoNextTimer = null; }
  gameActive = false;
  showStartScreen(true, state);
}
async function startActivity() {
  if (autoRetryTimer) { clearTimeout(autoRetryTimer); autoRetryTimer = null; }
  if (autoNextTimer) { clearTimeout(autoNextTimer); autoNextTimer = null; }
  camera?.stop();
  const state = await safely(restartGame);
  if (!state) return;
  gameActive = true;
  if (state.target) await safely(startRecognition);
  else apply(state);
}
async function restartActivity() { await startActivity(); }
async function advanceRound() {
  if (!gameActive) return;
  camera?.stop();
  const state = await safely(nextRound);
  if (!state) return;
  if (state.result === "completed") { apply(state); return; }
  await safely(startRecognition);
}
document.querySelector("#start-button").addEventListener("click", async () => { if (!document.fullscreenElement) await enterFullscreen(); await startActivity(); });
document.querySelector("#next").addEventListener("click", advanceRound);
const fullscreen = document.querySelector("#fullscreen");
async function enterFullscreen() { const surface = document.documentElement; try { if (surface.requestFullscreen) await surface.requestFullscreen(); else surface.webkitRequestFullscreen?.(); } catch (error) { console.warn("No se pudo activar pantalla completa", error); } }
async function toggleFullscreen() { if (document.fullscreenElement) await document.exitFullscreen(); else await enterFullscreen(); }
fullscreen.addEventListener("click", toggleFullscreen);
document.querySelector("#start-fullscreen").addEventListener("click", toggleFullscreen);
document.addEventListener("fullscreenchange", () => { const active = Boolean(document.fullscreenElement); document.body.classList.toggle("immersive", active); fullscreen.textContent = active ? "×" : "⛶"; fullscreen.setAttribute("aria-label", active ? "Salir de pantalla completa" : "Activar pantalla completa"); });
showStartScreen();
