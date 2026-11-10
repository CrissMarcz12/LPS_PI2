import { completeGame, getProfiles, getSession, leaveGame, nextRound, restartGame, retryRound, saveProgress, selectProfile, sendLandmarks } from "./game.js";
import { LocalHandCamera } from "./recognition.js";
import { cameraReady, render, showState } from "./ui.js?v=9";

const THEMES = [["violet", "💜", "Violeta"], ["sky", "💙", "Azul"], ["mint", "💚", "Verde"], ["coral", "🧡", "Coral"]];
const AVATARS = [["robo", "UTECHIE-ROBO", "/static/assets/avatars/robot-base.png"], ["llamabot", "UTECHIE-LLAMA", "/static/assets/avatars/robot-llama.png"], ["navibot", "UTECHIE-NAVIDAD", "/static/assets/avatars/robot-navidad.png"], ["perubot", "UTECHIE-PERÚ", "/static/assets/avatars/robot-peru.png"]];
const ID_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
let camera, autoRetryTimer, autoNextTimer, gameActive = false, savingResult = false;
let profiles = [], selectedProfile = null, selectedAvatar = null, playerCode = "", characterIndex = -1, screenMode = "profiles", soundEnabled = true, lastSavedScore = -1;

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
  if (state.score !== lastSavedScore) { lastSavedScore = state.score; safely(() => saveProgress(state)); }
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
  grid.innerHTML = AVATARS.map(([id, name, avatar], index) => `<button type="button" class="profile-choice theme-${THEMES[index][0]}" data-avatar="${id}"><small>BOTÓN ${index + 1}</small>${avatar.startsWith("/") ? `<img class="profile-avatar-image" src="${avatar}" alt="${name}">` : `<span class="profile-avatar">${avatar}</span>`}<strong>${name}</strong><em>Crea o recupera tu ID</em></button>`).join("");
  grid.querySelectorAll("[data-avatar]").forEach(button => button.addEventListener("click", () => chooseProfile(button.dataset.avatar)));
}
async function showProfileSelection() {
  clearTimers(); camera?.stop(); gameActive = false; savingResult = false; screenMode = "profiles";
  const data = await safely(getProfiles);
  if (data) { profiles = data.profiles; selectedProfile = profiles.find(profile => profile.id === data.selectedProfileId) || null; }
  paintProfiles(); showState("start-state");
}
function chooseProfile(avatarId) {
  selectedAvatar = AVATARS.find(avatar => avatar[0] === avatarId) || null;
  if (!selectedAvatar) return;
  playerCode = ""; characterIndex = -1; screenMode = "id-entry";
  showAvatar("#id-avatar", selectedAvatar[2], selectedAvatar[1]);
  document.querySelector("#id-name").textContent = selectedAvatar[1];
  paintCode(); showState("id-state");
}
function showAvatar(selector, avatar, name) {
  const element = document.querySelector(selector);
  element.innerHTML = avatar.startsWith("/") ? `<img src="${avatar}" alt="${name}">` : avatar;
}
function paintCode() {
  const active = characterIndex >= 0 ? ID_CHARACTERS[characterIndex] : "•";
  const text = `${playerCode}${playerCode.length < 4 ? active : ""}`.padEnd(4, "•");
  document.querySelector("#player-code").textContent = text.split("").join(" ");
}
function cycleCharacter() {
  if (playerCode.length >= 4) return;
  characterIndex = (characterIndex + 1) % ID_CHARACTERS.length;
  paintCode();
}
function confirmCharacter() {
  if (playerCode.length >= 4) return;
  if (characterIndex < 0) characterIndex = 0;
  playerCode += ID_CHARACTERS[characterIndex];
  characterIndex = -1; paintCode();
  if (playerCode.length === 4) showCustomizer();
}
function eraseCharacter() {
  if (playerCode) playerCode = playerCode.slice(0, -1);
  characterIndex = -1; paintCode();
}
function showCustomizer() {
  screenMode = "customize";
  showAvatar("#custom-avatar", selectedAvatar[2], selectedAvatar[1]);
  document.querySelector("#custom-name").textContent = `${selectedAvatar[1]}-${playerCode}`;
  const themes = document.querySelector("#theme-grid");
  themes.innerHTML = THEMES.map(([id, emoji, label], index) => `<button type="button" class="theme-choice theme-${id}" data-theme="${id}"><small>BOTÓN ${index + 1}</small><span>${emoji}</span><strong>${label}</strong></button>`).join("");
  themes.querySelectorAll("[data-theme]").forEach(button => button.addEventListener("click", () => chooseTheme(button.dataset.theme)));
  showState("customize-state");
}
async function chooseTheme(theme) {
  if (!selectedAvatar || playerCode.length !== 4) return;
  const response = await safely(() => selectProfile(selectedAvatar[0], playerCode, theme));
  if (!response?.success) return;
  selectedProfile = response.profile; profiles = response.profiles;
  await enterFullscreen(); await startActivity();
}
async function startActivity() {
  if (!selectedProfile) return showProfileSelection();
  clearTimers(); camera?.stop();
  lastSavedScore = -1;
  const state = await safely(restartGame);
  if (!state) return;
  gameActive = true; screenMode = "game";
  if (state.target) await safely(startRecognition); else apply(state);
}
async function stopActivity() { clearTimers(); camera?.stop(); gameActive = false; const saved = await safely(leaveGame); if (saved?.profiles) profiles = saved.profiles; showProfileSelection(); }
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
  if (screenMode === "profiles") return chooseProfile(AVATARS[button - 1]?.[0]);
  if (screenMode === "id-entry") {
    if (button === 1) return cycleCharacter();
    if (button === 2) return confirmCharacter();
    if (button === 3) return eraseCharacter();
    if (button === 4) { playerCode = ""; characterIndex = -1; return paintCode(); }
  }
  if (screenMode === "customize") return chooseTheme(THEMES[button - 1]?.[0]);
  if (!gameActive) return;
  if (button === 1) stopActivity();
  if (button === 2) advanceRound();
  if (button === 3) { soundEnabled = !soundEnabled; document.body.dataset.sound = soundEnabled ? "on" : "off"; }
  if (button === 4) startActivity();
} };
document.addEventListener("rimaymaki-button", event => window.RimayMakiControls.press(event.detail));
document.querySelector("#id-state").addEventListener("click", event => { if (event.target === document.querySelector("#id-state")) cycleCharacter(); });
document.addEventListener("keydown", event => {
  if (screenMode !== "id-entry") return;
  if (event.key === "Enter") { event.preventDefault(); confirmCharacter(); return; }
  if (event.key === "Backspace") { event.preventDefault(); eraseCharacter(); return; }
  event.preventDefault(); cycleCharacter();
});

const fullscreen = document.querySelector("#fullscreen");
async function enterFullscreen() { const surface = document.documentElement; try { if (surface.requestFullscreen) await surface.requestFullscreen(); else surface.webkitRequestFullscreen?.(); } catch (error) { console.warn("No se pudo activar pantalla completa", error); } }
async function toggleFullscreen() { if (document.fullscreenElement) await document.exitFullscreen(); else await enterFullscreen(); }
fullscreen.addEventListener("click", toggleFullscreen);
document.querySelector("#exit-game").addEventListener("click", stopActivity);
document.querySelectorAll(".start-fullscreen").forEach(button => button.addEventListener("click", toggleFullscreen));
document.querySelector("#play-again").addEventListener("click", showProfileSelection);
document.addEventListener("fullscreenchange", () => { const active = Boolean(document.fullscreenElement); document.body.classList.toggle("immersive", active); fullscreen.textContent = active ? "×" : "⛶"; fullscreen.setAttribute("aria-label", active ? "Salir de pantalla completa" : "Activar pantalla completa"); });
showProfileSelection();
