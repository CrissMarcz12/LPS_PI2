"""Entrena explícitamente un modelo para una única letra capturada."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import MIN_SAMPLES_PER_CLASS, MODELS_DIR, SEQUENCE_LENGTH
from recognition.classifier import save_letter_model
from training.storage import load_static_frame_samples, normalize_label, sample_count
def label_name(value: str) -> str:
    try: return normalize_label(value)
    except ValueError as exc: raise argparse.ArgumentTypeError(str(exc)) from exc
def main() -> None:
    parser = argparse.ArgumentParser(description="Entrena una letra usando sus muestras reales.")
    parser.add_argument("letter", type=label_name); parser.add_argument("--min-samples", type=int, default=MIN_SAMPLES_PER_CLASS); args = parser.parse_args()
    samples = load_static_frame_samples(args.letter)
    captured = sample_count(args.letter)
    if captured < args.min_samples: raise SystemExit(f"Faltan muestras para {args.letter}: {captured}/{args.min_samples}.")
    output = save_letter_model(args.letter, samples, MODELS_DIR, SEQUENCE_LENGTH)
    print(f"Modelo estático válido creado: {output} ({captured} capturas, {len(samples)} frames normalizados)")
if __name__ == "__main__": main()
