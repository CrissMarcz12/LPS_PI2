import { getSession, nextRound, retryRound } from "./game.js";
import { BrowserCamera } from "./recognition.js";
import { cameraReady, render } from "./ui.js";

let camera;
function apply(state) {
  if (!state || typeof state !== "object") throw new Error("Respuesta inválida del servicio.");
  render(state); camera?.drawLandmarks(Array.isArray(state.landmarks) ? state.landmarks : []);
  if (["correct", "incorrect", "completed"].includes(state.result)) camera?.stop();
}
async function startRecognition() {
  const state = await getSession(); apply(state); if (!state.target) return;
  camera?.stop();
  camera = new BrowserCamera(document.querySelector("#camera"), document.querySelector("#capture"), document.querySelector("#landmarks"), apply, () => cameraReady(false, "No pudimos usar la cámara. Permite el acceso e inténtalo otra vez."));
  const active = await camera.start(); cameraReady(active, active ? "Cámara activa · detectando mano" : "Cámara no disponible");
}
async function safely(action) { try { return await action(); } catch (error) { console.error(error); cameraReady(false, "No pudimos conectar con el reconocimiento."); return null; } }
document.querySelector("#next").addEventListener("click", async () => { camera?.stop(); const state = await safely(nextRound); if (state?.result !== "completed") await safely(startRecognition); else if (state) apply(state); });
document.querySelector("#retry").addEventListener("click", async () => { const state = await safely(retryRound); if (state) { apply(state); await safely(startRecognition); } });
safely(startRecognition);
