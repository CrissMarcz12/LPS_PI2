import { sendFrame } from "./game.js";

const CONNECTIONS = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[0,17],[17,18],[18,19],[19,20]];

export class BrowserCamera {
  constructor(video, captureCanvas, landmarkCanvas, onFrame, onError, sender = sendFrame, intervalMs = 100) {
    this.video = video; this.captureCanvas = captureCanvas; this.landmarkCanvas = landmarkCanvas;
    this.onFrame = onFrame; this.onError = onError; this.sender = sender; this.intervalMs = intervalMs; this.timer = null; this.busy = false; this.sentAt = [];
  }
  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 720 } }, audio: false });
      this.video.srcObject = this.stream; await this.video.play(); this.timer = setInterval(() => this.capture(), this.intervalMs); return true;
    } catch (error) { console.error("No se pudo acceder a la cámara", error); this.onError(error); return false; }
  }
  async capture() {
    if (this.busy || !this.video.videoWidth) return;
    this.busy = true; this.captureCanvas.width = this.video.videoWidth; this.captureCanvas.height = this.video.videoHeight;
    const context = this.captureCanvas.getContext("2d");
    context.save(); context.translate(this.captureCanvas.width, 0); context.scale(-1, 1); context.drawImage(this.video, 0, 0); context.restore();
    this.captureCanvas.toBlob(async blob => {
      try { if (blob) { this.recordFrame(); const state = await this.sender(blob); state.clientCameraFps = this.cameraFps; this.onFrame(state); } }
      catch (error) { console.error("Error al enviar el fotograma", error); this.onError(error); }
      finally { this.busy = false; }
    }, "image/jpeg", .82);
  }
  recordFrame() { const now = performance.now(); this.sentAt.push(now); if (this.sentAt.length > 30) this.sentAt.shift(); }
  get cameraFps() { if (this.sentAt.length < 2) return 0; const elapsed = this.sentAt.at(-1) - this.sentAt[0]; return elapsed ? Math.round(((this.sentAt.length - 1) * 1000 / elapsed) * 10) / 10 : 0; }
  drawLandmarks(points = [], correctionHint = "") {
    const canvas = this.landmarkCanvas, width = this.video.videoWidth, height = this.video.videoHeight;
    if (!width || !height) return;
    canvas.width = width; canvas.height = height;
    const context = canvas.getContext("2d"); context.clearRect(0, 0, width, height);
    if (!points.length) return;
    const fingers = { pulgar:[1,2,3,4], "índice":[5,6,7,8], "dedo medio":[9,10,11,12], "dedo anular":[13,14,15,16], "meñique":[17,18,19,20] };
    const highlighted = Object.entries(fingers).filter(([name]) => correctionHint.includes(name)).flatMap(([, indexes]) => indexes);
    context.strokeStyle = "#ffffff"; context.fillStyle = "#ffdc5d"; context.lineWidth = Math.max(2, width / 360);
    context.shadowColor = "#24346d"; context.shadowBlur = 4;
    for (const [from, to] of CONNECTIONS) { context.strokeStyle = highlighted.includes(from) && highlighted.includes(to) ? "#ff3f5e" : "#ffffff"; context.beginPath(); context.moveTo(points[from].x * width, points[from].y * height); context.lineTo(points[to].x * width, points[to].y * height); context.stroke(); }
    for (const [index, point] of points.entries()) { context.fillStyle = highlighted.includes(index) ? "#ff3f5e" : "#ffdc5d"; context.beginPath(); context.arc(point.x * width, point.y * height, Math.max(3, width / 180), 0, Math.PI * 2); context.fill(); }
    context.shadowBlur = 0;
  }
  stop() { clearInterval(this.timer); this.timer = null; this.stream?.getTracks().forEach(track => track.stop()); this.stream = null; this.sentAt = []; this.drawLandmarks([]); }
}
