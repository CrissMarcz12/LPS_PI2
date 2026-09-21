"""Entrena explícitamente un modelo para una única letra capturada."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATASETS_DIR, MIN_SAMPLES_PER_CLASS, MODELS_DIR, SEQUENCE_LENGTH, VECTOR_SIZE
from recognition.classifier import save_letter_model
def label_name(value: str) -> str:
    value = value.strip().upper()
    if not value or not value.isalpha() or len(value) != 1: raise argparse.ArgumentTypeError("Usa una única letra.")
    return value
def main() -> None:
    parser = argparse.ArgumentParser(description="Entrena una letra usando sus muestras reales.")
    parser.add_argument("letter", type=label_name); parser.add_argument("--min-samples", type=int, default=MIN_SAMPLES_PER_CLASS); args = parser.parse_args()
    source, vectors, expected = DATASETS_DIR / args.letter, [], SEQUENCE_LENGTH * VECTOR_SIZE
    for file in sorted(source.glob("*.npz")) if source.exists() else []:
        try:
            with np.load(file, allow_pickle=False) as data: features = data["features"].astype(np.float32).reshape(-1)
            if features.size == expected: vectors.append(features)
            else: print(f"Se omite {file.name}: longitud inválida.")
        except (OSError, KeyError, ValueError): print(f"Se omite {file.name}: archivo inválido.")
    if len(vectors) < args.min_samples: raise SystemExit(f"Faltan muestras para {args.letter}: {len(vectors)}/{args.min_samples}.")
    output = save_letter_model(args.letter, np.vstack(vectors), MODELS_DIR, SEQUENCE_LENGTH)
    print(f"Modelo válido creado: {output} ({len(vectors)} muestras)")
if __name__ == "__main__": main()
