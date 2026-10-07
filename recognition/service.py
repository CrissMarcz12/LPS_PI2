"""Puente entre un fotograma recibido desde Chrome y los modelos entrenados."""
from __future__ import annotations
import threading
import time
from collections import deque
import cv2
import numpy as np
from config import HAND_DETECTION_CONFIDENCE, HAND_TRACKING_CONFIDENCE, MAX_HANDS
from features.landmarks import normalized_hand_vector
from .classifier import AvailableLettersClassifier, Prediction
from runtime.mediapipe_loader import load_mediapipe_solutions

class StaticHandRecognizer:
    def __init__(self, classifier: AvailableLettersClassifier) -> None:
        self.classifier = classifier
        self._lock = threading.Lock()
        self.last_hand_detected = False
        self.last_landmarks: list[dict[str, float]] = []
        self.last_features: np.ndarray | None = None
        self.last_inference_ms = 0.0
        self.last_metrics = {"decodeMs": 0.0, "mediapipeMs": 0.0, "normalizationMs": 0.0, "classificationMs": 0.0, "totalMs": 0.0}
        self._processed_at: deque[float] = deque(maxlen=30)
        mp = load_mediapipe_solutions()
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=MAX_HANDS,
            model_complexity=1,
            min_detection_confidence=HAND_DETECTION_CONFIDENCE,
            min_tracking_confidence=HAND_TRACKING_CONFIDENCE,
        )

    def recognize(self, image_bytes: bytes) -> Prediction:
        started = time.perf_counter()
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("La imagen de cámara no es válida.")
        with self._lock:
            decoded = time.perf_counter()
            result = self._hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            mediapipe_done = time.perf_counter()
            if not result.multi_hand_landmarks:
                self.classifier.reset()
                self.last_hand_detected = False
                self.last_landmarks = []
                self.last_features = None
                self.last_inference_ms = (time.perf_counter() - started) * 1000
                self._record_processed()
                self.last_metrics = {"decodeMs": round((decoded-started)*1000, 1), "mediapipeMs": round((mediapipe_done-decoded)*1000, 1), "normalizationMs": 0.0, "classificationMs": 0.0, "totalMs": round(self.last_inference_ms, 1)}
                return Prediction(None, 0.0, False)
            hand = result.multi_hand_landmarks[0]
            self.last_hand_detected = True
            self.last_landmarks = [{"x": float(point.x), "y": float(point.y)} for point in hand.landmark]
            features = normalized_hand_vector(hand)
            self.last_features = features
            normalized_done = time.perf_counter()
            prediction = self.classifier.predict(features)
            finished = time.perf_counter()
            self.last_inference_ms = (finished - started) * 1000
            self._record_processed()
            self.last_metrics = {"decodeMs": round((decoded-started)*1000, 1), "mediapipeMs": round((mediapipe_done-decoded)*1000, 1), "normalizationMs": round((normalized_done-mediapipe_done)*1000, 2), "classificationMs": round((finished-normalized_done)*1000, 2), "totalMs": round(self.last_inference_ms, 1)}
            return prediction

    @property
    def frames_collected(self) -> int:
        return self.classifier.frames_seen

    @property
    def stable_votes(self) -> int:
        return self.classifier.dominant_vote_count

    @property
    def recognition_fps(self) -> float:
        if len(self._processed_at) < 2:
            return 0.0
        elapsed = self._processed_at[-1] - self._processed_at[0]
        return round((len(self._processed_at) - 1) / elapsed, 1) if elapsed else 0.0

    def _record_processed(self) -> None:
        self._processed_at.append(time.perf_counter())

    def reset(self) -> None:
        with self._lock:
            self.classifier.reset()
            self.last_hand_detected = False
            self.last_landmarks = []
            self.last_features = None
            self.last_inference_ms = 0.0
            self.last_metrics = {"decodeMs": 0.0, "mediapipeMs": 0.0, "normalizationMs": 0.0, "classificationMs": 0.0, "totalMs": 0.0}
            self._processed_at.clear()
