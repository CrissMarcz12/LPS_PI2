"""Entrena el alfabeto LSP y palabras estáticas o dinámicas declaradas."""
from __future__ import annotations

import argparse

from config import (DATASET_PATH, DYNAMIC_DATASET_PATH, DYNAMIC_MODEL_PATH,
                    DYNAMIC_SEQUENCE_LENGTH, MIN_SAMPLES_PER_LETTER,
                    MODEL_PATH, SEQUENCE_LENGTH)
from data.dataset import load_dataset
from data.labels import dynamic_labels, static_labels
from recognition.classifier import train_model


def _train_kind(name: str, dataset_path, model_path, sequence_length: int, labels: tuple[str, ...], preview: bool) -> bool:
    feature_size = sequence_length * 63
    X, y = load_dataset(dataset_path, feature_size)
    counts = {label: int((y == label).sum()) for label in labels}
    if not len(y):
        if preview:
            print(f"Vista previa: no hay muestras {name}; se omite este modelo.")
            return False
        raise SystemExit(f"No hay muestras {name}.")
    required = {label: count for label, count in counts.items() if count > 0} if preview else counts
    insufficient = {label: count for label, count in required.items() if count < MIN_SAMPLES_PER_LETTER}
    if insufficient:
        detail = ", ".join(f"{letter}: {count}/{MIN_SAMPLES_PER_LETTER}" for letter, count in insufficient.items())
        if preview:
            print(f"Vista previa: faltan muestras {name}. " + detail)
            return False
        raise SystemExit(f"Faltan muestras {name}. " + detail)
    trained = train_model(X, y, model_path, tuple(required), require_all_classes=not preview)
    print(f"Modelo {name} guardado en {model_path}")
    print("Muestras por letra:", trained)


    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrena modelos LSP estáticos y dinámicos.")
    parser.add_argument("--preview", action="store_true", help="entrena solo las clases ya completas para realizar pruebas")
    args = parser.parse_args()
    static_done = _train_kind("ESTATICO", DATASET_PATH, MODEL_PATH, SEQUENCE_LENGTH, static_labels(), args.preview)
    dynamic_done = _train_kind("DINAMICO", DYNAMIC_DATASET_PATH, DYNAMIC_MODEL_PATH, DYNAMIC_SEQUENCE_LENGTH, dynamic_labels(), args.preview)
    if args.preview:
        if not static_done and not dynamic_done:
            raise SystemExit("No hay suficientes clases para crear una vista previa.")
        print("Vista previa creada: solo reconoce las clases completas capturadas.")
    else:
        print("Entrenamiento final completado.")


if __name__ == "__main__":
    main()
