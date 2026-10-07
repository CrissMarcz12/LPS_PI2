"""Almacenamiento de muestras reales compartido por CLI y panel de desarrollo."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import shutil
from uuid import uuid4

import numpy as np
from PIL import Image, UnidentifiedImageError

from config import (DATASETS_DIR, MODELS_DIR, REFERENCE_IMAGES_DIR,
                    SEED_MODELS_DIR, SEED_REFERENCE_IMAGES_DIR,
                    SEQUENCE_LENGTH, VECTOR_SIZE)
from features.labels import normalize_label


def initialize_storage() -> None:
    """Crea el volumen de datos y conserva los ejemplos incluidos al primer uso."""
    for directory in (DATASETS_DIR, MODELS_DIR, REFERENCE_IMAGES_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    for source_root, destination_root in ((SEED_MODELS_DIR, MODELS_DIR),
                                          (SEED_REFERENCE_IMAGES_DIR, REFERENCE_IMAGES_DIR)):
        if not source_root.exists():
            continue
        for source in source_root.iterdir():
            destination = destination_root / source.name
            if not destination.exists():
                if source.is_dir():
                    shutil.copytree(source, destination)
                elif source.is_file():
                    shutil.copy2(source, destination)


def reference_path(label: str) -> Path:
    return REFERENCE_IMAGES_DIR / f"{normalize_label(label)}.png"


def save_reference(label: str, image_bytes: bytes) -> Path:
    """Verifica y normaliza una imagen subida antes de guardarla como PNG."""
    label = normalize_label(label)
    if not image_bytes:
        raise ValueError("Selecciona una imagen de referencia.")
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
        with Image.open(BytesIO(image_bytes)) as image:
            image.convert("RGBA").save(reference_path(label), "PNG", optimize=True)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("La referencia debe ser una imagen válida (PNG, JPG o WEBP).") from exc
    return reference_path(label)


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
