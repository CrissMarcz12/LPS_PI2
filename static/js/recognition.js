import { sendFrame } from "./game.js";

const CONNECTIONS = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[0,17],[17,18],[18,19],[19,20]];

export class BrowserCamera {
  constructor(video, captureCanvas, landmarkCanvas, onFrame, onError) {
    this.video = video; this.captureCanvas = captureCanvas; this.landmarkCanvas = landmarkCanvas;
    this.onFrame = onFrame; this.onError = onError; this.timer = null; this.busy = false;
  }
  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 720 } }, audio: false });
      this.video.srcObject = this.stream; await this.video.play(); this.timer = setInterval(() => this.capture(), 100); return true;
    } catch (error) { console.error("No se pudo acceder a la cámara", error); this.onError(error); return false; }
  }
  async capture() {
    if (this.busy || !this.video.videoWidth) return;
    this.busy = true; this.captureCanvas.width = this.video.videoWidth; this.captureCanvas.height = this.video.videoHeight;
    const context = this.captureCanvas.getContext("2d");
    context.save(); context.translate(this.captureCanvas.width, 0); context.scale(-1, 1); context.drawImage(this.video, 0, 0); context.restore();
    this.captureCanvas.toBlob(async blob => {
      try { if (blob) this.onFrame(await sendFrame(blob)); }
      catch (error) { console.error("Error al enviar el fotograma", error); this.onError(error); }
      finally { this.busy = false; }
    }, "image/jpeg", .82);
  }
  drawLandmarks(points = []) {
    const canvas = this.landmarkCanvas, width = this.video.videoWidth, height = this.video.videoHeight;
    if (!width || !height) return;
    canvas.width = width; canvas.height = height;
    const context = canvas.getContext("2d"); context.clearRect(0, 0, width, height);
    if (!points.length) return;
    context.strokeStyle = "#ffffff"; context.fillStyle = "#ffdc5d"; context.lineWidth = Math.max(2, width / 360);
    context.shadowColor = "#24346d"; context.shadowBlur = 4;
    for (const [from, to] of CONNECTIONS) { context.beginPath(); context.moveTo(points[from].x * width, points[from].y * height); context.lineTo(points[to].x * width, points[to].y * height); context.stroke(); }
    for (const point of points) { context.beginPath(); context.arc(point.x * width, point.y * height, Math.max(3, width / 180), 0, Math.PI * 2); context.fill(); }
    context.shadowBlur = 0;
  }
  stop() { clearInterval(this.timer); this.timer = null; this.stream?.getTracks().forEach(track => track.stop()); this.stream = null; this.drawLandmarks([]); }
}
