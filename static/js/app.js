import { completeGame, getProfiles, getSession, nextRound, restartGame, retryRound, selectProfile, sendLandmarks } from "./game.js";
import { LocalHandCamera } from "./recognition.js";
import { cameraReady, render, showState } from "./ui.js?v=8";

const THEMES = [["violet", "💜", "Violeta"], ["sky", "💙", "Azul"], ["mint", "💚", "Verde"], ["coral", "🧡", "Coral"]];
let camera, autoRetryTimer, autoNextTimer, gameActive = false, savingResult = false;
let profiles = [], selectedProfile = null, screenMode = "profiles", soundEnabled = true;

function clearTimers() {
  if (autoRetryTimer) { clearTimeout(autoRetryTimer); autoRetryTimer = null; }
  if (autoNextTimer) { clearTimeout(autoNextTimer); autoNextTimer = null; }
}
async function safely(action) {
  try { return await action(); }
  catch (error) { console.error(error); cameraReady(false, "No pudimos conectar con el juego."); return null; }
}
function apply(state) {
  if (!state || typeof state !== "object") throw new Error("Respuesta inválida del servicio.");
  if (!gameActive) return;
  if (state.result === "completed") { finishActivity(state); return; }
  render(state); camera?.setCorrectionHint?.(state.result === "incorrect" ? state.errorHint : "");
  if (state.result === "incorrect" && !autoRetryTimer) {
    autoRetryTimer = setTimeout(async () => { autoRetryTimer = null; const next = await safely(retryRound); if (next) apply(next); }, 650);
  } else if (state.result !== "incorrect" && autoRetryTimer) clearTimers();
  if (state.result === "correct" && !autoNextTimer) {
    autoNextTimer = setTimeout(async () => { autoNextTimer = null; await advanceRound(); }, 1450);
  } else if (state.result !== "correct" && autoNextTimer) { clearTimeout(autoNextTimer); autoNextTimer = null; }
}
async function startRecognition() {
  const state = await getSession(); apply(state); if (!state.target) return;
  camera?.stop();
  camera = new LocalHandCamera(document.querySelector("#camera"), document.querySelector("#landmarks"), apply, () => cameraReady(false, "No pudimos usar la cámara. Permite el acceso e inténtalo otra vez."), sendLandmarks, state.recognitionIntervalMs || 100);
  const active = await camera.start();
  cameraReady(active, active ? "Cámara activa · detectando mano" : "Cámara no disponible");
}
function paintProfiles() {
  const grid = document.querySelector("#profile-grid");
  grid.innerHTML = profiles.map((profile, index) => `<button type="button" class="profile-choice theme-${profile.theme}" data-profile="${profile.id}"><small>BOTÓN ${index + 1}</small><span class="profile-avatar">${profile.avatar}</span><strong>${profile.name}</strong><em>⭐ ${profile.totalScore} · 🔥 ${profile.maxStreak}</em></button>`).join("");
  grid.querySelectorAll("[data-profile]").forEach(button => button.addEventListener("click", () => chooseProfile(button.dataset.profile)));
}
async function showProfileSelection() {
  clearTimers(); camera?.stop(); gameActive = false; savingResult = false; screenMode = "profiles";
  const data = await safely(getProfiles);
  if (data) { profiles = data.profiles; selectedProfile = profiles.find(profile => profile.id === data.selectedProfileId) || null; }
  paintProfiles(); showState("start-state");
}
function chooseProfile(profileId) {
  selectedProfile = profiles.find(profile => profile.id === profileId) || null;
  if (!selectedProfile) return;
  screenMode = "customize";
  document.querySelector("#custom-avatar").textContent = selectedProfile.avatar;
  document.querySelector("#custom-name").textContent = selectedProfile.name;
  const themes = document.querySelector("#theme-grid");
  themes.innerHTML = THEMES.map(([id, emoji, label], index) => `<button type="button" class="theme-choice theme-${id}" data-theme="${id}"><small>BOTÓN ${index + 1}</small><span>${emoji}</span><strong>${label}</strong></button>`).join("");
  themes.querySelectorAll("[data-theme]").forEach(button => button.addEventListener("click", () => chooseTheme(button.dataset.theme)));
  showState("customize-state");
}
async function chooseTheme(theme) {
  if (!selectedProfile) return;
  const response = await safely(() => selectProfile(selectedProfile.id, theme));
  if (!response?.success) return;
  selectedProfile = response.profile; profiles = response.profiles;
  await enterFullscreen(); await startActivity();
}
async function startActivity() {
  if (!selectedProfile) return showProfileSelection();
  clearTimers(); camera?.stop();
  const state = await safely(restartGame);
  if (!state) return;
  gameActive = true; screenMode = "game";
  if (state.target) await safely(startRecognition); else apply(state);
}
function stopActivity() { clearTimers(); camera?.stop(); gameActive = false; showProfileSelection(); }
async function finishActivity(state) {
  if (savingResult) return;
  savingResult = true; gameActive = false; clearTimers(); camera?.stop();
  const saved = await safely(completeGame);
  if (saved?.profiles) profiles = saved.profiles;
  screenMode = "results"; render(state, saved);
}
async function advanceRound() {
  if (!gameActive) return;
  camera?.stop(); const state = await safely(nextRound);
  if (!state) return;
  if (state.result === "completed") { apply(state); return; }
  await safely(startRecognition);
}

// El puente físico (Bluetooth o Serial) solo debe llamar press(1..4).
window.RimayMakiControls = { press(buttonNumber) {
  const button = Number(buttonNumber);
  if (screenMode === "profiles") return chooseProfile(profiles[button - 1]?.id);
  if (screenMode === "customize") return chooseTheme(THEMES[button - 1]?.[0]);
  if (!gameActive) return;
  if (button === 1) stopActivity();
  if (button === 2) advanceRound();
  if (button === 3) { soundEnabled = !soundEnabled; document.body.dataset.sound = soundEnabled ? "on" : "off"; }
  if (button === 4) startActivity();
} };
document.addEventListener("rimaymaki-button", event => window.RimayMakiControls.press(event.detail));

const fullscreen = document.querySelector("#fullscreen");
async function enterFullscreen() { const surface = document.documentElement; try { if (surface.requestFullscreen) await surface.requestFullscreen(); else surface.webkitRequestFullscreen?.(); } catch (error) { console.warn("No se pudo activar pantalla completa", error); } }
async function toggleFullscreen() { if (document.fullscreenElement) await document.exitFullscreen(); else await enterFullscreen(); }
fullscreen.addEventListener("click", toggleFullscreen);
document.querySelectorAll(".start-fullscreen").forEach(button => button.addEventListener("click", toggleFullscreen));
document.querySelector("#play-again").addEventListener("click", showProfileSelection);
document.addEventListener("fullscreenchange", () => { const active = Boolean(document.fullscreenElement); document.body.classList.toggle("immersive", active); fullscreen.textContent = active ? "×" : "⛶"; fullscreen.setAttribute("aria-label", active ? "Salir de pantalla completa" : "Activar pantalla completa"); });
showProfileSelection();
