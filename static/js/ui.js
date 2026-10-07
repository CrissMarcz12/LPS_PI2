const $ = id => document.getElementById(id);
let previousResult = "waiting";
function playTone(frequency, start, duration, type = "sine", gain = .05) {
  const context = window.rimayAudio ??= new AudioContext();
  const oscillator = context.createOscillator(), volume = context.createGain();
  oscillator.type = type; oscillator.frequency.setValueAtTime(frequency, start);
  volume.gain.setValueAtTime(.001, start); volume.gain.exponentialRampToValueAtTime(gain, start + .02); volume.gain.exponentialRampToValueAtTime(.001, start + duration);
  oscillator.connect(volume).connect(context.destination); oscillator.start(start); oscillator.stop(start + duration + .03);
}
function playFeedbackSound(result) {
  if (previousResult === result || !["correct", "incorrect"].includes(result)) return;
  try { const now = (window.rimayAudio ??= new AudioContext()).currentTime; result === "correct" ? [523,659,784].forEach((note,index) => playTone(note, now + index * .1, .16, "triangle", .055)) : playTone(180, now, .25, "sawtooth", .035); } catch (_) { /* El juego sigue funcionando si el navegador bloquea audio. */ }
}
export function showState(name) { ["empty-state","game-state","results-state"].forEach(id => $(id).classList.toggle("hidden", id !== name)); }
export function render(state) {
  if (!state.target) { showState("empty-state"); return; }
  if (state.result === "completed") { renderResults(state); return; }
  showState("game-state");
  $("target-letter").textContent = state.target; $("target-letter-tablet").textContent = state.target; $("detected-letter").textContent = state.prediction || "—";
  $("progress-label").textContent = `Actividad ${state.currentRound} / ${state.totalRounds}`;
  $("progress-bar").style.width = `${((state.currentRound - 1) / state.totalRounds) * 100}%`;
  $("header-xp").textContent = state.score; $("header-streak").textContent = state.currentStreak;
  $("game-score").textContent = state.score; $("game-streak").textContent = state.currentStreak;
  [["score",state.score],["streak",state.currentStreak],["correct",state.correctAnswers],["wrong",state.wrongAnswers]].forEach(([id,value]) => $(id).textContent = value);
  $("detected-confidence").textContent = state.handDetected ? (state.prediction ? "Reconociendo tu seña…" : "Analizando tu seña…") : "Esperando una mano";
  $("frames-status").textContent = state.handDetected ? `Mano detectada · ${state.framesCollected || 0}/5 predicciones` : "⚠ Mano no detectada";
  const debug = $("debug-status");
  const panel = $("debug-panel");
  if (state.debug) {
    debug.classList.remove("hidden"); debug.textContent = `${state.debug.endpoint} · ${state.debug.metrics.totalMs} ms`;
    panel.classList.remove("hidden"); const m = state.debug.metrics;
    panel.innerHTML = `<b>DEBUG RECONOCIMIENTO</b><span>MANO: ${state.debug.handDetected ? "detectada ✓" : "no detectada"}</span><span>FPS cámara: ${state.clientCameraFps || 0} · reconocimiento: ${state.debug.recognitionFps || 0}</span><span>Instantánea: ${state.debug.prediction || "—"} ${state.debug.confidence ?? ""}%</span><span>Estable: ${state.debug.stablePrediction || "—"} ${state.debug.stableConfidence ?? ""}%</span><span>Frames estables: ${state.debug.framesStable}/${state.debug.framesRequired}</span><span>JPEG: ${m.decodeMs} ms · MediaPipe: ${m.mediapipeMs} ms · Normalización: ${m.normalizationMs} ms</span><span>Clasificación: ${m.classificationMs} ms · Total: ${m.totalMs} ms</span><span>Modelo: cargado ✓</span>`;
  } else { debug.classList.add("hidden"); panel.classList.add("hidden"); }
  const image = $("reference-image"), placeholder = $("reference-placeholder");
  if (image.dataset.letter !== state.target) { image.dataset.letter = state.target; image.src = `/static/assets/signs/${encodeURIComponent(state.target)}.png`; image.classList.remove("missing"); placeholder.classList.add("hidden"); image.onerror = () => { image.classList.add("missing"); placeholder.classList.remove("hidden"); }; }
  const feedback = $("feedback"), title = $("feedback-title"), text = $("feedback-text"); feedback.className = `feedback ${state.result}`;
  const celebration = $("celebration"), next = $("next");
  const isCorrect = state.result === "correct";
  const stage = $("camera-stage");
  stage.classList.toggle("is-correct", isCorrect);
  stage.classList.toggle("is-incorrect", state.result === "incorrect");
  celebration.classList.toggle("hidden", !isCorrect);
  const tryAgain = $("try-again"), isIncorrect = state.result === "incorrect";
  $("error-wash").classList.toggle("active", isIncorrect);
  tryAgain.classList.toggle("hidden", !isIncorrect);
  if (isIncorrect) $("error-hint").textContent = state.errorHint || "Mira la foto e inténtalo otra vez.";
  if (isCorrect) {
    $("celebration-letter").textContent = state.target;
    $("celebration-points").textContent = `+${state.awardedPoints} estrellas`;
  }
  next.classList.toggle("hidden", !isCorrect);
  next.innerHTML = state.currentRound === state.totalRounds ? "VER MIS RESULTADOS <span>★</span>" : "SIGUIENTE <span>→</span>";
  const copy = {
    waiting:["🟡 ANALIZANDO", `Mantén la mano estable (${state.framesCollected || 0}/5).`],
    no_hand:["⚠ MANO NO DETECTADA", "Coloca una mano completa frente a la cámara."],
    analyzing:["🟡 ANALIZANDO", "Estamos comprobando la seña…"],
    correct:["✓ ¡CORRECTO!", `+${state.awardedPoints} XP · ¡Muy bien!`],
    incorrect:["✕ CASI", state.errorHint || "Mira la foto e inténtalo otra vez."],
  };
  [title.textContent, text.textContent] = copy[state.result] || copy.waiting;
  playFeedbackSound(state.result); previousResult = state.result;
}
function renderResults(state) { showState("results-state"); [["final-score",state.score],["final-correct",state.correctAnswers],["final-wrong",state.wrongAnswers],["final-streak",state.maxStreak],["final-accuracy",`${state.accuracy}%`]].forEach(([id,value]) => $(id).textContent=value); }
export function cameraReady(active, message) { $("camera-dot").classList.toggle("active", active); $("camera-label").textContent = message; $("camera-message").classList.toggle("hidden", active); if (!active) $("camera-message").textContent = message; }
