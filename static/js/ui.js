const $ = id => document.getElementById(id);
export function showState(name) { ["empty-state","game-state","results-state"].forEach(id => $(id).classList.toggle("hidden", id !== name)); }
export function render(state) {
  if (!state.target) { showState("empty-state"); return; }
  if (state.result === "completed") { renderResults(state); return; }
  showState("game-state");
  $("target-letter").textContent = state.target; $("detected-letter").textContent = state.prediction || "—";
  $("progress-label").textContent = `Actividad ${state.currentRound} / ${state.totalRounds}`;
  $("progress-bar").style.width = `${((state.currentRound - 1) / state.totalRounds) * 100}%`;
  $("header-xp").textContent = state.score; $("header-streak").textContent = state.currentStreak;
  [["score",state.score],["streak",state.currentStreak],["correct",state.correctAnswers],["wrong",state.wrongAnswers]].forEach(([id,value]) => $(id).textContent = value);
  $("detected-confidence").textContent = state.confidence == null ? "Esperando una mano" : `Confianza: ${state.confidence}%`;
  $("frames-status").textContent = state.handDetected ? `Landmarks activos · ${state.framesCollected || 0}/20 frames` : "⚠ Mano no detectada";
  const debug = $("debug-status");
  if (state.debug) { debug.classList.remove("hidden"); debug.textContent = `${state.debug.endpoint} · ${state.debug.inferenceMs} ms · ${state.debug.landmarks} landmarks`; }
  const image = $("reference-image"), placeholder = $("reference-placeholder");
  if (image.dataset.letter !== state.target) { image.dataset.letter = state.target; image.src = `/static/assets/signs/${encodeURIComponent(state.target)}.png`; image.classList.remove("missing"); placeholder.classList.add("hidden"); image.onerror = () => { image.classList.add("missing"); placeholder.classList.remove("hidden"); }; }
  const feedback = $("feedback"), title = $("feedback-title"), text = $("feedback-text"); feedback.className = `feedback ${state.result}`;
  const copy = {
    waiting:["🟡 ANALIZANDO", `Mantén la mano estable (${state.framesCollected || 0}/20).`],
    no_hand:["⚠ MANO NO DETECTADA", "Coloca una mano completa frente a la cámara."],
    analyzing:["🟡 ANALIZANDO", "Estamos comprobando la seña…"],
    correct:["✓ ¡CORRECTO!", `+${state.awardedPoints} XP · ¡Muy bien!`],
    incorrect:["✕ INCORRECTO", `Detectado: ${state.prediction || "—"}. Intenta nuevamente.`],
  };
  [title.textContent, text.textContent] = copy[state.result] || copy.waiting;
  $("retry").classList.toggle("hidden", state.result !== "incorrect");
}
function renderResults(state) { showState("results-state"); [["final-score",state.score],["final-correct",state.correctAnswers],["final-wrong",state.wrongAnswers],["final-streak",state.maxStreak],["final-accuracy",`${state.accuracy}%`]].forEach(([id,value]) => $(id).textContent=value); }
export function cameraReady(active, message) { $("camera-dot").classList.toggle("active", active); $("camera-label").textContent = message; $("camera-message").classList.toggle("hidden", active); if (!active) $("camera-message").textContent = message; }
