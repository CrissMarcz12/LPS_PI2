"""Almacenamiento incremental de secuencias de landmarks etiquetadas."""
from __future__ import annotations

from pathlib import Path
import numpy as np


def load_dataset(path: Path, feature_size: int) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        return np.empty((0, feature_size), dtype=np.float32), np.empty((0,), dtype="U64")
    with np.load(path, allow_pickle=False) as saved:
        # U2 truncaba clases como HOLA a HO después de la segunda captura.
        return saved["X"].astype(np.float32), saved["y"].astype("U64")


def append_sample(path: Path, features: np.ndarray, label: str) -> int:
    """Guarda una muestra y devuelve el total almacenado para esa letra."""
    path.parent.mkdir(parents=True, exist_ok=True)
    X, y = load_dataset(path, features.size)
    if X.size and X.shape[1] != features.size:
        raise ValueError("El dataset fue creado con otra longitud de secuencia.")
    X = np.vstack((X, features.reshape(1, -1).astype(np.float32)))
    y = np.append(y, label)
    np.savez_compressed(path, X=X, y=y)
    return int(np.sum(y == label))


def class_counts(path: Path, feature_size: int) -> dict[str, int]:
    _, y = load_dataset(path, feature_size)
    return {str(label): int(np.sum(y == label)) for label in np.unique(y)}
