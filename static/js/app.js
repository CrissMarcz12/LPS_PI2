import { completeGame, getProfiles, getSession, leaveGame, nextRound, restartGame, retryRound, saveProgress, selectProfile, sendLandmarks } from "./game.js";
import { LocalHandCamera } from "./recognition.js";
import { cameraReady, render, showState } from "./ui.js?v=10";

const THEMES = [["violet", "💜", "Violeta"], ["sky", "💙", "Azul"], ["mint", "💚", "Verde"], ["coral", "🧡", "Coral"]];
const AVATARS = [["robo", "UTECHIE-ROBO", "/static/assets/avatars/robot-base.png"], ["llamabot", "UTECHIE-LLAMA", "/static/assets/avatars/robot-llama.png"], ["navibot", "UTECHIE-NAVIDAD", "/static/assets/avatars/robot-navidad.png"], ["perubot", "UTECHIE-PERÚ", "/static/assets/avatars/robot-peru.png"]];
const ID_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
let camera, autoRetryTimer, autoNextTimer, gameActive = false, savingResult = false;
let profiles = [], selectedProfile = null, selectedAvatar = null, playerCode = "", characterIndex = -1, screenMode = "profiles", soundEnabled = true, lastSavedScore = -1;
const BLE_SERVICE_UUID = "5d8f6d58-7190-4c4d-9f9e-910daebaa001";
const BLE_CHANNEL_UUID = "5d8f6d58-7190-4c4d-9f9e-910daebaa002";
let bluetoothDevice = null, bluetoothChannel = null, bluetoothWrite = Promise.resolve(), lastHardwareFeedback = "", hardwareErrorActive = false, lastErrorSoundRound = -1;
const lastButtonPressedAt = [0, 0, 0, 0];
const BUTTON_DEBOUNCE_MS = 220;
let podiumOpen = false;
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[char]));
const avatarMarkup = (avatar, name) => String(avatar || "").startsWith("/static/assets/avatars/")
  ? `<img src="${escapeHtml(avatar)}" alt="${escapeHtml(name)}">`
  : escapeHtml(avatar || "★");

function setBluetoothStatus(message, connected = false) {
  const status = document.querySelector("#bluetooth-status");
  const gameStatus = document.querySelector("#bluetooth-game-status");
  const button = document.querySelector("#bluetooth-connect");
  if (status) { status.textContent = message; status.classList.toggle("connected", connected); }
  if (gameStatus) { gameStatus.textContent = connected ? "⌁ ESP32 conectado" : "⌁ ESP32 sin conectar"; gameStatus.classList.toggle("connected", connected); }
  if (button) { button.textContent = connected ? "✓ ESP32 CONECTADO" : "⌁ CONECTAR ESP32"; button.classList.toggle("connected", connected); }
}
function bluetoothConnected() { return Boolean(bluetoothDevice?.gatt?.connected && bluetoothChannel); }
function sendToEsp32(command) {
  if (!bluetoothConnected()) return Promise.resolve(false);
  const payload = new TextEncoder().encode(command);
  bluetoothWrite = bluetoothWrite.catch(() => undefined).then(() => bluetoothChannel.writeValue(payload)).then(() => true).catch(error => {
    console.warn("No se pudo enviar al ESP32", error);
    setBluetoothStatus("Control Bluetooth desconectado");
    return false;
  });
  return bluetoothWrite;
}
function paintSound(enabled) {
  soundEnabled = enabled;
  document.body.dataset.sound = enabled ? "on" : "off";
}
function toggleSound() {
  paintSound(!soundEnabled);
  return sendToEsp32(soundEnabled ? "SILENCIO_OFF" : "SILENCIO_ON");
}
function stopHardwareFeedback() {
  if (hardwareErrorActive) sendToEsp32("DETENER_ERROR");
  hardwareErrorActive = false;
}
function handleBluetoothMessage(event) {
  const message = new TextDecoder().decode(event.target.value).trim().toUpperCase();
  console.log("ESP32:", message);
  const pressed = message.match(/^BTN([1-4])$/);
  if (pressed) {
    const button = Number(pressed[1]);
    const now = performance.now();
    if (now - lastButtonPressedAt[button - 1] < BUTTON_DEBOUNCE_MS) return;
    lastButtonPressedAt[button - 1] = now;
    window.RimayMakiControls.press(button);
    return;
  }
  if (message === "SONIDO_ACTIVADO") paintSound(true);
  if (message === "SONIDO_APAGADO") paintSound(false);
}
function handleBluetoothDisconnect() {
  bluetoothChannel = null;
  setBluetoothStatus("Control Bluetooth desconectado");
}
async function connectBluetooth() {
  if (!navigator.bluetooth) {
    setBluetoothStatus("Usa Chrome en Android, Windows o Mac para conectar el ESP32.");
    return;
  }
  if (bluetoothConnected()) return;
  try {
    setBluetoothStatus("Busca RIMAYMAKI-ESP32…");
    bluetoothDevice = await navigator.bluetooth.requestDevice({ filters: [{ services: [BLE_SERVICE_UUID] }] });
    bluetoothDevice.addEventListener("gattserverdisconnected", handleBluetoothDisconnect);
    const server = await bluetoothDevice.gatt.connect();
    const service = await server.getPrimaryService(BLE_SERVICE_UUID);
    bluetoothChannel = await service.getCharacteristic(BLE_CHANNEL_UUID);
    await bluetoothChannel.startNotifications();
    bluetoothChannel.addEventListener("characteristicvaluechanged", handleBluetoothMessage);
    setBluetoothStatus("Control ESP32 conectado", true);
    paintSound(soundEnabled);
    sendToEsp32(soundEnabled ? "SILENCIO_OFF" : "SILENCIO_ON");
    sendToEsp32("PING");
  } catch (error) {
    console.warn("Bluetooth no conectado", error);
    setBluetoothStatus(error?.name === "NotFoundError" ? "No se eligió un ESP32." : "No se pudo conectar al ESP32.");
  }
}
function syncHardwareFeedback(state) {
  if (!bluetoothConnected() || !state?.result) return;
  const key = `${state.result}:${state.currentRound}:${state.correctAnswers}:${state.wrongAnswers}:${state.score}`;
  if (state.result !== "incorrect" && hardwareErrorActive) stopHardwareFeedback();
  if (key === lastHardwareFeedback) return;
  if (state.result === "correct") { lastHardwareFeedback = key; sendToEsp32("BIEN"); }
  if (state.result === "incorrect") {
    // Una postura equivocada puede seguir frente a la cámara varios frames.
    // Solo avisamos una vez por letra para que el buzzer no sea insistente.
    if (lastErrorSoundRound !== state.currentRound) {
      lastErrorSoundRound = state.currentRound;
      hardwareErrorActive = true;
      sendToEsp32("MAL");
    }
    lastHardwareFeedback = key;
  }
}

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
  syncHardwareFeedback(state);
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
  // Al cambiar de letra la cámara ya está funcionando: conservarla evita que
  // Chrome vuelva a pedir permisos o se quede sin stream en una tablet.
  if (camera?.running) {
    cameraReady(true, "Cámara activa · detectando mano");
    return;
  }
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
  paintProfiles();
  document.querySelector("#profile-grid").classList.remove("hidden");
  document.querySelector("#start-heading").textContent = "Elige tu aventurero";
  document.querySelector("#start-copy").textContent = "Usa los botones 1, 2, 3 o 4 para elegirlo.";
  document.querySelector("#begin-player-flow").classList.add("hidden");
  showState("start-state");
}
async function showWelcome() {
  clearTimers(); camera?.stop(); stopHardwareFeedback(); gameActive = false; savingResult = false; screenMode = "welcome";
  selectedProfile = null; selectedAvatar = null; playerCode = ""; characterIndex = -1;
  podiumOpen = false; document.querySelector("#podium-overlay").classList.add("hidden");
  document.querySelector("#profile-grid").classList.add("hidden");
  document.querySelector("#start-heading").textContent = "Presiona botón 1 para comenzar";
  document.querySelector("#start-copy").textContent = "Conecta el control y presiona el botón 1 para elegir tu aventurero.";
  document.querySelector("#begin-player-flow").classList.remove("hidden");
  showState("start-state");
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
  // Evita que una pulsación repetida cambie de color o inicie dos veces.
  screenMode = "starting";
  const response = await safely(() => selectProfile(selectedAvatar[0], playerCode, theme));
  if (!response?.success) { showCustomizer(); return; }
  selectedProfile = response.profile; profiles = response.profiles;
  await launchGame();
}
async function launchGame() {
  if (!selectedProfile) return showWelcome();
  await enterFullscreen();
  await startActivity();
}
async function startActivity() {
  if (!selectedProfile) return showWelcome();
  clearTimers(); camera?.stop(); stopHardwareFeedback();
  lastSavedScore = -1;
  savingResult = false; lastErrorSoundRound = -1;
  lastHardwareFeedback = "";
  hardwareErrorActive = false;
  const state = await safely(restartGame);
  if (!state) return;
  gameActive = true; screenMode = "game";
  if (state.target) await safely(startRecognition); else apply(state);
}
async function stopActivity() { clearTimers(); camera?.stop(); stopHardwareFeedback(); gameActive = false; const saved = await safely(leaveGame); if (saved?.profiles) profiles = saved.profiles; showWelcome(); }
async function finishActivity(state) {
  if (savingResult) return;
  savingResult = true; gameActive = false; clearTimers(); camera?.stop(); stopHardwareFeedback();
  const saved = await safely(completeGame);
  if (saved?.profiles) profiles = saved.profiles;
  podiumOpen = false; screenMode = "results"; render(state, saved);
}
async function endActivity() {
  if (!gameActive || savingResult) return;
  savingResult = true;
  const state = await safely(getSession);
  clearTimers(); camera?.stop(); stopHardwareFeedback(); gameActive = false;
  const saved = await safely(leaveGame);
  if (saved?.profiles) profiles = saved.profiles;
  podiumOpen = false; screenMode = "results";
  if (state) render({...state, result: "completed"}, saved);
}
async function showPodium() {
  const data = await safely(getProfiles);
  if (!data) return;
  const players = data.profiles || [];
  const cards = document.querySelector("#podium-cards");
  const list = document.querySelector("#podium-list");
  cards.innerHTML = players.slice(0, 3).map(player => `<article class="podium-card place-${player.position}"><span>${player.position === 1 ? "🥇" : player.position === 2 ? "🥈" : "🥉"}</span><div>${avatarMarkup(player.avatar, player.name)}</div><strong>${escapeHtml(player.name)}</strong><b>${player.totalScore} ⭐</b></article>`).join("");
  list.innerHTML = players.map(player => `<li><span>#${player.position} ${avatarMarkup(player.avatar, player.name)} ${escapeHtml(player.name)}</span><b>${player.totalScore} ⭐</b><em>✓ ${player.averageAccuracy}%</em></li>`).join("");
  podiumOpen = true;
  document.querySelector("#podium-overlay").classList.remove("hidden");
}
async function advanceRound() {
  if (!gameActive) return;
  stopHardwareFeedback();
  const state = await safely(nextRound);
  if (!state) return;
  if (state.result === "completed") { apply(state); return; }
  apply(state);
}

// El puente físico (Bluetooth o Serial) solo debe llamar press(1..4).
window.RimayMakiControls = { press(buttonNumber) {
  const button = Number(buttonNumber);
  if (screenMode === "welcome") {
    if (button === 1) return showProfileSelection();
    return;
  }
  if (screenMode === "profiles") return chooseProfile(AVATARS[button - 1]?.[0]);
  if (screenMode === "id-entry") {
    if (button === 1) return cycleCharacter();
    if (button === 2) return confirmCharacter();
    if (button === 3) return eraseCharacter();
    if (button === 4) { playerCode = ""; characterIndex = -1; return paintCode(); }
  }
  if (screenMode === "customize") return chooseTheme(THEMES[button - 1]?.[0]);
  if (screenMode === "results") {
    if (button === 1) return showWelcome();
    if (button === 4) return podiumOpen ? showWelcome() : showPodium();
    return;
  }
  if (!gameActive) return;
  if (button === 1) startActivity();
  if (button === 2) advanceRound();
  if (button === 3) toggleSound();
  if (button === 4) endActivity();
} };
document.addEventListener("rimaymaki-button", event => window.RimayMakiControls.press(event.detail));
document.querySelector("#bluetooth-connect").addEventListener("click", connectBluetooth);
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
document.querySelector("#begin-player-flow").addEventListener("click", showProfileSelection);
document.addEventListener("fullscreenchange", () => { const active = Boolean(document.fullscreenElement); document.body.classList.toggle("immersive", active); fullscreen.textContent = active ? "×" : "⛶"; fullscreen.setAttribute("aria-label", active ? "Salir de pantalla completa" : "Activar pantalla completa"); });
showWelcome();
