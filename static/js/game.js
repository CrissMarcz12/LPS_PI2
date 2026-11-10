export async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error("No se pudo conectar con el juego.");
  return response.json();
}
export const getSession = () => api("/api/session");
export const nextRound = () => api("/api/next", { method: "POST" });
export const retryRound = () => api("/api/retry", { method: "POST" });
export const restartGame = () => api("/api/restart", { method: "POST" });
export const getProfiles = () => api("/api/profiles");
export const selectProfile = (avatarId, code, theme) => api("/api/profiles/select", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({avatarId, code, theme}) });
export const completeGame = () => api("/api/game/complete", { method: "POST" });
export const saveProgress = state => api("/api/game/progress", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(state) });
export const leaveGame = () => api("/api/game/leave", { method: "POST" });
export function sendFrame(blob) { const form = new FormData(); form.append("frame", blob, "camera.jpg"); return api("/api/frame", { method: "POST", body: form }); }
export function sendLandmarks(payload) { return api("/api/landmarks", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) }); }
