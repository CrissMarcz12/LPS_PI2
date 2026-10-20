"""Coordina una sesión activa sin mezclar reglas de juego con rutas Flask."""
from __future__ import annotations
import threading
import numpy as np
from config import (CONFIDENCE_THRESHOLD, DEBUG_MODE, DRAW_LANDMARKS, LOW_CONFIDENCE_FRAMES_REQUIRED,
                    PREDICTION_HISTORY_SIZE, RECOGNITION_FPS,
                    STABLE_FRAMES_REQUIRED, TOTAL_ROUNDS)
from recognition.classifier import AvailableLettersClassifier, Prediction, available_models
from recognition.service import StaticHandRecognizer
from .session import SessionState

class GameController:
    def __init__(self, model_root, sequence_length: int) -> None:
        self.model_root, self.sequence_length = model_root, sequence_length
        self.state: SessionState | None = None
        self.recognizer: StaticHandRecognizer | None = None
        self.classifier: AvailableLettersClassifier | None = None
        self.error: str | None = None
        self._lock = threading.Lock()

    def start(self) -> dict:
        with self._lock:
            models = available_models(self.model_root, self.sequence_length)
            self.state = SessionState(tuple(models), TOTAL_ROUNDS)
            self.error = None
            self.recognizer = None
            self.classifier = None
            if models:
                try:
                    # El juego normal usa MediaPipe en la tableta y solo recibe
                    # landmarks; así evitamos enviar JPEGs pesados al servidor.
                    self.classifier = AvailableLettersClassifier(models, CONFIDENCE_THRESHOLD, PREDICTION_HISTORY_SIZE, STABLE_FRAMES_REQUIRED)
                except Exception:
                    self.error = "No se pudo iniciar el reconocimiento de cámara."
            return self.payload()

    def submit_frame(self, image_bytes: bytes) -> dict:
        with self._lock:
            if not self.state or not self.classifier:
                return self.payload()
            try:
                # Ruta de respaldo para navegadores sin MediaPipe Web.
                if self.recognizer is None:
                    self.recognizer = StaticHandRecognizer(self.classifier)
                prediction = self.recognizer.recognize(image_bytes)
                self.state.observe(
                    hand_detected=self.recognizer.last_hand_detected,
                    landmarks=self.recognizer.last_landmarks,
                    frames_collected=self.recognizer.frames_collected,
                    prediction=prediction,
                )
                error_hint = self.recognizer.classifier.guidance_for(self.state.target, self.recognizer.last_features)
                self.state.evaluate(prediction, CONFIDENCE_THRESHOLD, error_hint, LOW_CONFIDENCE_FRAMES_REQUIRED)
            except (ValueError, RuntimeError):
                self.error = "No pudimos analizar la imagen de cámara."
            return self.payload()

    def submit_landmarks(self, features: list[float], landmarks: list[dict[str, float]], hand_detected: bool) -> dict:
        """Clasifica landmarks ya detectados en el navegador, sin JPEG ni MediaPipe servidor."""
        with self._lock:
            if not self.state or not self.classifier:
                return self.payload()
            try:
                if not hand_detected:
                    self.classifier.reset()
                    prediction = Prediction(None, 0.0, False)
                    self.state.observe(hand_detected=False, landmarks=[], frames_collected=0, prediction=prediction)
                    self.state.evaluate(prediction, CONFIDENCE_THRESHOLD)
                else:
                    vector = np.asarray(features, dtype=np.float32).reshape(-1)
                    if vector.size != 63 or not np.isfinite(vector).all() or len(landmarks) != 21:
                        raise ValueError("Los landmarks recibidos no son válidos.")
                    prediction = self.classifier.predict(vector)
                    self.state.observe(hand_detected=True, landmarks=landmarks,
                                       frames_collected=self.classifier.frames_seen, prediction=prediction)
                    error_hint = self.classifier.guidance_for(self.state.target, vector)
                    self.state.evaluate(prediction, CONFIDENCE_THRESHOLD, error_hint, LOW_CONFIDENCE_FRAMES_REQUIRED)
            except (TypeError, ValueError, RuntimeError):
                self.error = "No pudimos analizar la posición de la mano."
            return self.payload()

    def retry(self) -> dict:
        with self._lock:
            if self.state:
                self.state.retry()
                self.classifier.reset() if self.classifier else None
                self.recognizer.reset() if self.recognizer else None
            return self.payload()

    def next_round(self) -> dict:
        with self._lock:
            if self.state:
                self.state.next_round()
                self.classifier.reset() if self.classifier else None
                self.recognizer.reset() if self.recognizer else None
            return self.payload()

    def payload(self) -> dict:
        if not self.state:
            return {"result": "not_started", "message": "Inicia una partida."}
        data = self.state.payload()
        data["message"] = self.error
        data["success"] = self.error is None
        data["showLandmarks"] = DRAW_LANDMARKS
        data["recognitionIntervalMs"] = int(1000 / RECOGNITION_FPS)
        data["inferenceMs"] = round(self.recognizer.last_inference_ms, 1) if self.recognizer else None
        if DEBUG_MODE:
            data["debug"] = {"prediction": data.get("prediction"), "confidence": data.get("confidence"), "stablePrediction": data.get("stablePrediction"), "stableConfidence": data.get("stableConfidence"), "handDetected": data.get("handDetected"), "landmarks": len(data.get("landmarks", [])), "framesStable": self.recognizer.stable_votes if self.recognizer else 0, "framesRequired": STABLE_FRAMES_REQUIRED, "recognitionFps": self.recognizer.recognition_fps if self.recognizer else 0.0, "metrics": self.recognizer.last_metrics if self.recognizer else {}, "endpoint": "/api/frame"}
        return data
