"""Captura de desarrollo desde la cámara del navegador usando el mismo pipeline."""
from __future__ import annotations

import time
import cv2
import numpy as np

from config import (CONFIDENCE_THRESHOLD, MAX_HANDS, MODELS_DIR,
                    PREDICTION_HISTORY_SIZE, SAMPLE_CAPTURE_INTERVAL_SECONDS,
                    SEQUENCE_LENGTH, STABLE_FRAMES_REQUIRED)
from features.landmarks import LandmarkSequence, normalized_hand_vector
from recognition.classifier import AvailableLettersClassifier, available_models
from runtime.mediapipe_loader import load_mediapipe_solutions
from .storage import sample_count, save_sample


class BrowserTrainingCollector:
    def __init__(self) -> None:
        mp = load_mediapipe_solutions()
        self._hands = mp.solutions.hands.Hands(False, MAX_HANDS, 1, .65, .65)
        self.sequence = LandmarkSequence(SEQUENCE_LENGTH)
        self.capturing = False
        self.label = "A"
        self._last_save = 0.0
        self.preview_classifier = self._make_preview_classifier()

    def _make_preview_classifier(self) -> AvailableLettersClassifier | None:
        models = available_models(MODELS_DIR, SEQUENCE_LENGTH)
        return AvailableLettersClassifier(models, CONFIDENCE_THRESHOLD, PREDICTION_HISTORY_SIZE, STABLE_FRAMES_REQUIRED) if models else None

    def refresh_preview_model(self) -> None:
        self.preview_classifier = self._make_preview_classifier()

    def configure(self, label: str, capturing: bool) -> None:
        if label != self.label:
            self.label = label
            self.sequence.clear()
        self.capturing = capturing

    def process(self, image_bytes: bytes) -> dict:
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("La imagen de cámara no es válida.")
        result = self._hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        if not result.multi_hand_landmarks:
            self.sequence.clear()
            return {"handDetected": False, "landmarks": [], "framesCollected": 0, "saved": False, "sampleCount": sample_count(self.label), "prediction": None, "confidence": None}
        hand = result.multi_hand_landmarks[0]
        features = normalized_hand_vector(hand)
        self.sequence.add(features)
        saved = False
        now = time.monotonic()
        if self.capturing and self.sequence.ready and now - self._last_save >= SAMPLE_CAPTURE_INTERVAL_SECONDS:
            save_sample(self.label, self.sequence.flattened())
            self._last_save = now
            saved = True
        prediction = self.preview_classifier.predict(features) if self.preview_classifier else None
        return {
            "handDetected": True,
            "landmarks": [{"x": float(point.x), "y": float(point.y)} for point in hand.landmark],
            "framesCollected": self.sequence.frame_count,
            "saved": saved,
            "sampleCount": sample_count(self.label),
            "prediction": prediction.letter if prediction else None,
            "confidence": round(prediction.confidence * 100, 1) if prediction and prediction.letter else None,
        }
