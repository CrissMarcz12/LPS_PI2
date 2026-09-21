"""Puente entre un fotograma recibido desde Chrome y los modelos entrenados."""
from __future__ import annotations
import threading
import time
import cv2
import numpy as np
from config import MAX_HANDS, SEQUENCE_LENGTH
from features.landmarks import LandmarkSequence, normalized_hand_vector
from .classifier import AvailableLettersClassifier, Prediction
from runtime.mediapipe_loader import load_mediapipe_solutions

class StaticHandRecognizer:
    def __init__(self, classifier: AvailableLettersClassifier) -> None:
        self.classifier = classifier
        self.sequence = LandmarkSequence(SEQUENCE_LENGTH)
        self._lock = threading.Lock()
        self.last_hand_detected = False
        self.last_landmarks: list[dict[str, float]] = []
        self.last_inference_ms = 0.0
        mp = load_mediapipe_solutions()
        self._hands = mp.solutions.hands.Hands(False, MAX_HANDS, 1, .65, .65)

    def recognize(self, image_bytes: bytes) -> Prediction:
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("La imagen de cámara no es válida.")
        with self._lock:
            started = time.perf_counter()
            result = self._hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            if not result.multi_hand_landmarks:
                self.sequence.clear(); self.classifier.reset()
                self.last_hand_detected = False
                self.last_landmarks = []
                self.last_inference_ms = (time.perf_counter() - started) * 1000
                return Prediction(None, 0.0, False)
            hand = result.multi_hand_landmarks[0]
            self.last_hand_detected = True
            self.last_landmarks = [{"x": float(point.x), "y": float(point.y)} for point in hand.landmark]
            self.sequence.add(normalized_hand_vector(hand))
            self.last_inference_ms = (time.perf_counter() - started) * 1000
            return self.classifier.predict(self.sequence.flattened()) if self.sequence.ready else Prediction(None, 0.0, False)

    @property
    def frames_collected(self) -> int:
        return self.sequence.frame_count

    def reset(self) -> None:
        with self._lock:
            self.sequence.clear()
            self.classifier.reset()
            self.last_hand_detected = False
            self.last_landmarks = []
            self.last_inference_ms = 0.0
