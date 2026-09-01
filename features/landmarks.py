"""Normalizacion de los 21 landmarks de MediaPipe Hands."""
from __future__ import annotations

from collections import deque
import numpy as np


def normalized_hand_vector(hand_landmarks) -> np.ndarray:
    """Devuelve 63 valores centrados en la muñeca y escalados por la palma.

    La escala usa la distancia muñeca--nudillo medio, por lo que la posicion en
    pantalla y el tamaño aparente de la mano no cambian el vector aprendido.
    """
    points = np.array([(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark], dtype=np.float32)
    points -= points[0]  # muñeca como origen
    palm_scale = np.linalg.norm(points[9, :2])  # muñeca a MCP del dedo medio
    if palm_scale < 1e-6:
        palm_scale = 1.0
    return (points / palm_scale).reshape(-1)


class LandmarkSequence:
    """Buffer de longitud fija para letras estáticas y letras con movimiento."""

    def __init__(self, length: int, vector_size: int = 63) -> None:
        self.length = length
        self.vector_size = vector_size
        self._frames: deque[np.ndarray] = deque(maxlen=length)

    def add(self, vector: np.ndarray) -> None:
        self._frames.append(vector.astype(np.float32, copy=True))

    def clear(self) -> None:
        self._frames.clear()

    @property
    def ready(self) -> bool:
        return len(self._frames) == self.length

    def flattened(self) -> np.ndarray:
        if not self.ready:
            raise RuntimeError("Aun no hay suficientes frames en el buffer.")
        return np.concatenate(tuple(self._frames)).astype(np.float32)


class DynamicRecording:
    """Graba una seña y la re-muestrea a una longitud común para el modelo."""

    def __init__(self, output_length: int, min_frames: int, vector_size: int = 63) -> None:
        self.output_length = output_length
        self.min_frames = min_frames
        self.vector_size = vector_size
        self.frames: list[np.ndarray] = []
        self.active = False

    def start(self) -> None:
        self.frames.clear()
        self.active = True

    def add(self, vector: np.ndarray) -> None:
        if self.active:
            self.frames.append(vector.astype(np.float32, copy=True))

    def cancel(self) -> None:
        self.frames.clear()
        self.active = False

    def stop(self) -> np.ndarray | None:
        self.active = False
        if len(self.frames) < self.min_frames:
            self.frames.clear()
            return None
        source = np.arange(len(self.frames), dtype=np.float32)
        target = np.linspace(0, len(self.frames) - 1, self.output_length, dtype=np.float32)
        sequence = np.vstack(self.frames)
        normalized = np.vstack([np.interp(target, source, sequence[:, column]) for column in range(self.vector_size)]).T
        self.frames.clear()
        return normalized.reshape(-1).astype(np.float32)
