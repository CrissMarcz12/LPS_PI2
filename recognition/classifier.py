"""Entrenamiento y prediccion para las 27 letras exclusivamente."""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC



@dataclass(frozen=True)
class Prediction:
    letter: str | None
    confidence: float
    stable: bool


class PrototypeAlphabetModel:
    """Verificador temporal para un alfabeto que aun se esta recolectando.

    Con una sola letra no es posible entrenar una SVM multiclase. Este modelo
    usa la dispersion de los ejemplos capturados para aceptar solo posturas
    parecidas a las letras ya guardadas. Se reemplaza automaticamente por la
    SVM al entrenar el conjunto completo de 27 letras.
    """

    def fit(self, X: np.ndarray, y: np.ndarray) -> "PrototypeAlphabetModel":
        self.classes_ = np.unique(y)
        self.scale_ = np.maximum(np.std(X, axis=0), 0.03)
        self.centers_ = np.vstack([np.mean(X[y == label], axis=0) for label in self.classes_])
        distances = self._distances(X)
        self.limits_ = np.array([
            max(float(np.percentile(distances[y == label, index], 95)), 0.15)
            for index, label in enumerate(self.classes_)
        ])
        return self

    def _distances(self, X: np.ndarray) -> np.ndarray:
        normalized = (X[:, None, :] - self.centers_[None, :, :]) / self.scale_[None, None, :]
        return np.sqrt(np.mean(normalized * normalized, axis=2))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        distances = self._distances(X)
        # Una muestra en el borde habitual conserva ~74% de confianza; fuera
        # de ese rango decae con rapidez y el umbral normal la rechaza.
        confidence = np.exp(-0.3 * np.square(distances / self.limits_[None, :]))
        if confidence.shape[1] == 1:
            return confidence
        return confidence / np.maximum(confidence.sum(axis=1, keepdims=True), 1e-9)


class AlphabetClassifier:
    def __init__(self, model_path: Path, min_confidence: float, stable_frames: int) -> None:
        self.model_path = model_path
        self.min_confidence = min_confidence
        self.stable_frames = stable_frames
        self.model: Pipeline | None = joblib.load(model_path) if model_path.exists() else None
        self.history: deque[str | None] = deque(maxlen=stable_frames)

    @property
    def available(self) -> bool:
        return self.model is not None

    def reset(self) -> None:
        self.history.clear()

    def predict(self, features: np.ndarray) -> Prediction:
        if self.model is None:
            return Prediction(None, 0.0, False)
        probabilities = self.model.predict_proba(features.reshape(1, -1))[0]
        position = int(np.argmax(probabilities))
        candidate = str(self.model.classes_[position])
        confidence = float(probabilities[position])
        accepted = candidate if confidence >= self.min_confidence else None
        self.history.append(accepted)
        most_common, count = Counter(self.history).most_common(1)[0] if self.history else (None, 0)
        stable = most_common is not None and count == self.stable_frames
        return Prediction(most_common if stable else None, confidence, stable)


def train_model(
    X: np.ndarray, y: np.ndarray, model_path: Path, labels: tuple[str, ...], *, require_all_classes: bool = True
) -> dict[str, int]:
    """Entrena la SVM final o un verificador provisional de letras capturadas."""
    counts = {label: int(np.sum(y == label)) for label in labels}
    missing = [letter for letter, count in counts.items() if count == 0]
    if require_all_classes and missing:
        raise ValueError("Faltan muestras para: " + ", ".join(missing))
    unexpected = sorted(set(y) - set(labels))
    if unexpected:
        raise ValueError("El dataset contiene etiquetas no permitidas: " + ", ".join(unexpected))
    if len(set(y)) == 1:
        model = PrototypeAlphabetModel().fit(X, y)
    else:
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", SVC(C=8.0, kernel="rbf", probability=True, class_weight="balanced")),
        ])
        model.fit(X, y)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    return counts
