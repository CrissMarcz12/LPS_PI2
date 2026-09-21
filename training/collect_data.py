"""Captura muestras reales de una letra; nunca forma parte de la interfaz web."""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import sys
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CAMERA_INDEX, DATASETS_DIR, MAX_HANDS, SEQUENCE_LENGTH
from features.landmarks import LandmarkSequence, normalized_hand_vector
from runtime.mediapipe_loader import load_mediapipe_solutions

def label_name(value: str) -> str:
    value = value.strip().upper()
    if not value or not value.isalpha() or len(value) != 1: raise argparse.ArgumentTypeError("Usa una única letra.")
    return value
def main() -> None:
    parser = argparse.ArgumentParser(description="Captura datos reales para una letra.")
    parser.add_argument("letter", type=label_name); args = parser.parse_args()
    target = DATASETS_DIR / args.letter; target.mkdir(parents=True, exist_ok=True)
    mp, sequence = load_mediapipe_solutions(), LandmarkSequence(SEQUENCE_LENGTH)
    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened(): raise RuntimeError("No se pudo abrir la cámara.")
    saved = len(list(target.glob("*.npz")))
    with mp.solutions.hands.Hands(False, MAX_HANDS, 1, .65, .65) as hands:
        while True:
            ok, frame = camera.read()
            if not ok: break
            frame = cv2.flip(frame, 1); result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if result.multi_hand_landmarks:
                hand = result.multi_hand_landmarks[0]; sequence.add(normalized_hand_vector(hand))
                mp.solutions.drawing_utils.draw_landmarks(frame, hand, mp.solutions.hands.HAND_CONNECTIONS)
            else: sequence.clear()
            cv2.putText(frame, f"{args.letter}: {saved} muestras | SPACE guarda | R reinicia | ESC sale", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, .55, (255,255,255), 2)
            cv2.imshow("RimayMaki - captura de desarrollo", frame); key = cv2.waitKey(1) & 0xFF
            if key == 27: break
            if key == ord("r"): sequence.clear()
            if key == ord(" ") and sequence.ready:
                file = target / f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex}.npz"
                np.savez_compressed(file, features=sequence.flattened()); saved += 1; print(f"Muestra guardada: {file}")
    camera.release(); cv2.destroyAllWindows()
if __name__ == "__main__": main()
