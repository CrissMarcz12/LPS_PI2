"""Almacenamiento de muestras reales compartido por CLI y panel de desarrollo."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np

from config import DATASETS_DIR, SEQUENCE_LENGTH, VECTOR_SIZE


def normalize_label(label: str) -> str:
    value = label.strip().upper()
    if not value.isalpha() or len(value) != 1:
        raise ValueError("La clase debe ser una única letra.")
    return value


def sample_files(label: str) -> list[Path]:
    directory = DATASETS_DIR / normalize_label(label)
    return sorted(directory.glob("*.npz")) if directory.exists() else []


def sample_count(label: str) -> int:
    return len(sample_files(label))


def all_counts() -> dict[str, int]:
    if not DATASETS_DIR.exists():
        return {}
    return {directory.name: len(list(directory.glob("*.npz"))) for directory in DATASETS_DIR.iterdir() if directory.is_dir()}


def save_sample(label: str, features: np.ndarray) -> Path:
    label = normalize_label(label)
    expected = SEQUENCE_LENGTH * VECTOR_SIZE
    values = np.asarray(features, dtype=np.float32).reshape(-1)
    if values.size != expected:
        raise ValueError("La secuencia no tiene la longitud esperada.")
    destination = DATASETS_DIR / label
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex}.npz"
    np.savez_compressed(path, features=values)
    return path


def load_samples(label: str) -> np.ndarray:
    expected = SEQUENCE_LENGTH * VECTOR_SIZE
    rows: list[np.ndarray] = []
    for path in sample_files(label):
        try:
            with np.load(path, allow_pickle=False) as saved:
                values = saved["features"].astype(np.float32).reshape(-1)
            if values.size == expected:
                rows.append(values)
        except (OSError, KeyError, ValueError):
            continue
    return np.vstack(rows) if rows else np.empty((0, expected), dtype=np.float32)


def load_static_frame_samples(label: str) -> np.ndarray:
    """Convierte las secuencias capturadas en posturas individuales reales.

    Las letras de esta etapa son estáticas: cada uno de los 20 landmarks
    normalizados de una toma es un ejemplo válido de la misma seña. Esto evita
    que el juego tenga que esperar 20 frames antes de empezar a clasificar.
    """
    sequences = load_samples(label)
    if not len(sequences):
        return np.empty((0, VECTOR_SIZE), dtype=np.float32)
    return sequences.reshape(-1, SEQUENCE_LENGTH, VECTOR_SIZE).reshape(-1, VECTOR_SIZE)


def clear_samples(label: str) -> int:
    files = sample_files(label)
    for path in files:
        path.unlink()
    directory = DATASETS_DIR / normalize_label(label)
    if directory.exists() and not any(directory.iterdir()):
        directory.rmdir()
    return len(files)
