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
    stable_letter: str | None = None
    stable_confidence: float | None = None

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
    (destination / METADATA_FILENAME).write_text(json.dumps({"label": label, "sample_count": int(len(samples)), "sequence_length": sequence_length, "feature_size": int(samples.shape[1]), "pipeline": "static-frame-v2"}, indent=2), encoding="utf-8")
    return destination / MODEL_FILENAME

def available_models(model_root: Path, sequence_length: int) -> dict[str, LetterModel]:
    """Solo carga directorios con metadata y modelo coherentes y utilizables."""
    found: dict[str, LetterModel] = {}
    if not model_root.exists(): return found
    for directory in model_root.iterdir():
        if not directory.is_dir(): continue
        try:
            metadata = json.loads((directory / METADATA_FILENAME).read_text(encoding="utf-8")); label = _safe_label(str(metadata["label"]))
            if label != directory.name or metadata.get("pipeline") != "static-frame-v2" or metadata.get("feature_size") != 63 or not isinstance(metadata.get("sample_count"), int) or metadata["sample_count"] < 1: continue
            model = joblib.load(directory / MODEL_FILENAME)
            if (not isinstance(model, LetterModel) or not all(hasattr(model, key) for key in ("center_", "scale_", "limit_")) or model.center_.size != 63 or model.scale_.size != 63 or not isinstance(model.limit_, (int, float, np.floating))): continue
            found[label] = model
        except Exception: continue
    return dict(sorted(found.items()))

class AvailableLettersClassifier:
    def __init__(self, models: dict[str, LetterModel], min_confidence: float, stable_frames: int, stable_frames_required: int = 4) -> None:
        self.models, self.min_confidence, self.stable_frames = models, min_confidence, stable_frames
        self.stable_frames_required = stable_frames_required
        self.history: deque[tuple[str | None, float]] = deque(maxlen=stable_frames)
    def reset(self) -> None: self.history.clear()
    def predict(self, features: np.ndarray) -> Prediction:
        if not self.models:
            return Prediction(None, 0.0, False)
        scores = {label: float(model.score(features.reshape(1, -1))[0]) for label, model in self.models.items()}
        label, confidence = max(scores.items(), key=lambda item: item[1])
        accepted = label if confidence >= self.min_confidence else None
        self.history.append((accepted, confidence))
        labels = [item[0] for item in self.history]
        winner, count = Counter(labels).most_common(1)[0]
        required = min(self.stable_frames, self.stable_frames_required)
        stable = winner is not None and count >= required
        stable_scores = [score for candidate, score in self.history if candidate == winner]
        stable_confidence = float(np.mean(stable_scores)) if stable_scores else None
        return Prediction(accepted, confidence, stable, str(winner) if stable else None, stable_confidence if stable else None)

    def guidance_for(self, label: str | None, features: np.ndarray | None) -> str | None:
        """Indica la zona con mayor diferencia frente a la seña objetivo real."""
        if not label or features is None or label not in self.models:
            return None
        model = self.models[label]
        deviation = np.abs((features.reshape(-1) - model.center_) / model.scale_).reshape(21, 3)
        groups = {
            "pulgar": (1, 5), "índice": (5, 9), "dedo medio": (9, 13),
            "dedo anular": (13, 17), "meñique": (17, 21),
        }
        scores = {name: float(np.mean(deviation[slice(*range_)])) for name, range_ in groups.items()}
        highest = max(scores.values())
        # Una mano abierta ante una seña cerrada puede desviar varios dedos:
        # se señalan todos los que alcanzan una desviación comparable, no solo el peor.
        fingers = [name for name, score in scores.items() if score >= max(.5, highest * .60)]
        return f"Revisa la posición de: {', '.join(fingers)}."

    @property
    def frames_seen(self) -> int:
        return len(self.history)

    @property
    def dominant_vote_count(self) -> int:
        if not self.history:
            return 0
        return Counter(item[0] for item in self.history).most_common(1)[0][1]
