export async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error("No se pudo conectar con el juego.");
  return response.json();
}
export const getSession = () => api("/api/session");
export const nextRound = () => api("/api/next", { method: "POST" });
export const retryRound = () => api("/api/retry", { method: "POST" });
export function sendFrame(blob) { const form = new FormData(); form.append("frame", blob, "camera.jpg"); return api("/api/frame", { method: "POST", body: form }); }
