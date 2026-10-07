"""Servicios HTTP del panel de desarrollo; comparte datasets y modelos con el juego."""
from __future__ import annotations

import threading

from config import MIN_SAMPLES_PER_CLASS, MODELS_DIR, RECOGNITION_FPS, SEQUENCE_LENGTH
from recognition.classifier import save_letter_model
from .storage import (all_counts, clear_samples, load_static_frame_samples,
                      normalize_label, sample_count, save_reference)
from .web_collector import BrowserTrainingCollector


class TrainingController:
    def __init__(self) -> None:
        self.collectors: dict[str, BrowserTrainingCollector] = {}
        self._lock = threading.Lock()

    def overview(self) -> dict:
        return {"counts": all_counts(), "minimumSamples": MIN_SAMPLES_PER_CLASS, "recognitionIntervalMs": int(1000 / RECOGNITION_FPS)}

    def configure(self, client_id: str, label: str, capturing: bool) -> dict:
        with self._lock:
            label = normalize_label(label)
            collector = self.collectors.setdefault(client_id, BrowserTrainingCollector())
            collector.configure(label, capturing)
            return {"label": label, "capturing": capturing, "sampleCount": sample_count(label)}

    def submit_frame(self, client_id: str, image_bytes: bytes) -> dict:
        with self._lock:
            collector = self.collectors.get(client_id)
            if collector is None:
                raise RuntimeError("Configura primero la letra de entrenamiento.")
            return collector.process(image_bytes)

    def train(self, label: str) -> dict:
        with self._lock:
            label = normalize_label(label)
            captured = sample_count(label)
            samples = load_static_frame_samples(label)
            if captured < MIN_SAMPLES_PER_CLASS:
                return {"success": False, "message": f"Se necesitan {MIN_SAMPLES_PER_CLASS} muestras; hay {captured}.", "sampleCount": captured}
            path = save_letter_model(label, samples, MODELS_DIR, SEQUENCE_LENGTH)
            for collector in self.collectors.values():
                collector.refresh_preview_model()
            return {"success": True, "message": f"Modelo de {label} actualizado con {captured} capturas.", "modelPath": str(path), "sampleCount": captured}

    def clear(self, label: str) -> dict:
        with self._lock:
            label = normalize_label(label)
            return {"removed": clear_samples(label), "sampleCount": 0}

    def save_reference(self, label: str, image_bytes: bytes) -> dict:
        with self._lock:
            label = normalize_label(label)
            save_reference(label, image_bytes)
            return {"success": True, "label": label, "referenceUrl": f"/references/{label}.png"}
