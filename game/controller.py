"""Coordina una sesión activa sin mezclar reglas de juego con rutas Flask."""
from __future__ import annotations
import threading
from config import CONFIDENCE_THRESHOLD, DEBUG_MODE, PREDICTION_HISTORY_SIZE, TOTAL_ROUNDS
from recognition.classifier import AvailableLettersClassifier, available_models
from recognition.service import StaticHandRecognizer
from .session import SessionState

class GameController:
    def __init__(self, model_root, sequence_length: int) -> None:
        self.model_root, self.sequence_length = model_root, sequence_length
        self.state: SessionState | None = None
        self.recognizer: StaticHandRecognizer | None = None
        self.error: str | None = None
        self._lock = threading.Lock()

    def start(self) -> dict:
        with self._lock:
            models = available_models(self.model_root, self.sequence_length)
            self.state = SessionState(tuple(models), TOTAL_ROUNDS)
            self.error = None
            self.recognizer = None
            if models:
                try:
                    self.recognizer = StaticHandRecognizer(AvailableLettersClassifier(models, CONFIDENCE_THRESHOLD, PREDICTION_HISTORY_SIZE))
                except Exception:
                    self.error = "No se pudo iniciar el reconocimiento de cámara."
            return self.payload()

    def submit_frame(self, image_bytes: bytes) -> dict:
        with self._lock:
            if not self.state or not self.recognizer:
                return self.payload()
            try:
                prediction = self.recognizer.recognize(image_bytes)
                self.state.observe(
                    hand_detected=self.recognizer.last_hand_detected,
                    landmarks=self.recognizer.last_landmarks,
                    frames_collected=self.recognizer.frames_collected,
                    prediction=prediction,
                )
                self.state.evaluate(prediction, CONFIDENCE_THRESHOLD)
            except (ValueError, RuntimeError):
                self.error = "No pudimos analizar la imagen de cámara."
            return self.payload()

    def retry(self) -> dict:
        with self._lock:
            if self.state:
                self.state.retry()
                self.recognizer.reset() if self.recognizer else None
            return self.payload()

    def next_round(self) -> dict:
        with self._lock:
            if self.state:
                self.state.next_round()
                self.recognizer.reset() if self.recognizer else None
            return self.payload()

    def payload(self) -> dict:
        if not self.state:
            return {"result": "not_started", "message": "Inicia una partida."}
        data = self.state.payload()
        data["message"] = self.error
        data["success"] = self.error is None
        data["inferenceMs"] = round(self.recognizer.last_inference_ms, 1) if self.recognizer else None
        if DEBUG_MODE:
            data["debug"] = {"prediction": data.get("prediction"), "confidence": data.get("confidence"), "handDetected": data.get("handDetected"), "landmarks": len(data.get("landmarks", [])), "inferenceMs": data.get("inferenceMs"), "endpoint": "/api/frame"}
        return data
