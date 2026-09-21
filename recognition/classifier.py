"""Modelos por letra y reconocimiento entre los modelos disponibles."""
from __future__ import annotations
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
import json
import joblib
import numpy as np

MODEL_FILENAME = "classifier.joblib"
METADATA_FILENAME = "metadata.json"

@dataclass(frozen=True)
class Prediction:
    letter: str | None
    confidence: float
    stable: bool

class LetterModel:
    """Modelo de una clase basado en su postura media y variación real."""
    def fit(self, samples: np.ndarray) -> "LetterModel":
        self.center_ = np.mean(samples, axis=0).astype(np.float32)
        self.scale_ = np.maximum(np.std(samples, axis=0), 0.03).astype(np.float32)
        self.limit_ = max(float(np.percentile(self._distance(samples), 95)), 0.15)
        return self
    def _distance(self, samples: np.ndarray) -> np.ndarray:
        normalized = (samples - self.center_) / self.scale_
        return np.sqrt(np.mean(normalized * normalized, axis=1))
    def score(self, samples: np.ndarray) -> np.ndarray:
        return np.exp(-0.3 * np.square(self._distance(samples) / self.limit_))

def _safe_label(label: str) -> str:
    label = label.strip().upper()
    if not label or not label.isalpha() or len(label) != 1:
        raise ValueError("La clase debe ser una única letra.")
    return label

def save_letter_model(label: str, samples: np.ndarray, model_root: Path, sequence_length: int) -> Path:
    label = _safe_label(label); model = LetterModel().fit(samples); destination = model_root / label
    destination.mkdir(parents=True, exist_ok=True); joblib.dump(model, destination / MODEL_FILENAME)
    (destination / METADATA_FILENAME).write_text(json.dumps({"label": label, "sample_count": int(len(samples)), "sequence_length": sequence_length}, indent=2), encoding="utf-8")
    return destination / MODEL_FILENAME

def available_models(model_root: Path, sequence_length: int) -> dict[str, LetterModel]:
    """Solo carga directorios con metadata y modelo coherentes y utilizables."""
    found: dict[str, LetterModel] = {}
    if not model_root.exists(): return found
    for directory in model_root.iterdir():
        if not directory.is_dir(): continue
        try:
            metadata = json.loads((directory / METADATA_FILENAME).read_text(encoding="utf-8")); label = _safe_label(str(metadata["label"]))
            if label != directory.name or metadata.get("sequence_length") != sequence_length or not isinstance(metadata.get("sample_count"), int) or metadata["sample_count"] < 1: continue
            model = joblib.load(directory / MODEL_FILENAME)
            if (not isinstance(model, LetterModel) or not all(hasattr(model, key) for key in ("center_", "scale_", "limit_")) or model.center_.size != sequence_length * 63 or model.scale_.size != sequence_length * 63 or not isinstance(model.limit_, (int, float, np.floating))): continue
            found[label] = model
        except Exception: continue
    return dict(sorted(found.items()))

class AvailableLettersClassifier:
    def __init__(self, models: dict[str, LetterModel], min_confidence: float, stable_frames: int) -> None:
        self.models, self.min_confidence, self.stable_frames = models, min_confidence, stable_frames
        self.history: deque[str | None] = deque(maxlen=stable_frames)
    def reset(self) -> None: self.history.clear()
    def predict(self, features: np.ndarray) -> Prediction:
        if not self.models:
            return Prediction(None, 0.0, False)
        scores = {label: float(model.score(features.reshape(1, -1))[0]) for label, model in self.models.items()}
        label, confidence = max(scores.items(), key=lambda item: item[1]); self.history.append(label if confidence >= self.min_confidence else None)
        winner, count = Counter(self.history).most_common(1)[0]
        required = max(3, (self.stable_frames + 1) // 2)
        stable = winner is not None and count >= required
        return Prediction(winner if stable else None, confidence, stable)
