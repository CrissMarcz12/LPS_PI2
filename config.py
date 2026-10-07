"""Rutas y parámetros compartidos por RimayMaki."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# En Render esta variable debe apuntar al disco persistente (/var/data).
# Localmente se conserva todo dentro de data/ para no mezclarlo con el código.
PERSISTENT_DATA_DIR = Path(os.environ.get("RIMAYMAKI_DATA_DIR", ROOT / "data"))
DATASETS_DIR = PERSISTENT_DATA_DIR / "datasets"
MODELS_DIR = PERSISTENT_DATA_DIR / "models"
REFERENCE_IMAGES_DIR = PERSISTENT_DATA_DIR / "references"
SEED_MODELS_DIR = ROOT / "models"
SEED_REFERENCE_IMAGES_DIR = ROOT / "static" / "assets" / "signs"

CAMERA_INDEX = 0
MAX_HANDS = 1
HAND_DETECTION_CONFIDENCE = 0.65
HAND_TRACKING_CONFIDENCE = 0.65
SEQUENCE_LENGTH = 20
VECTOR_SIZE = 63
CLASSIFICATION_FEATURE_SIZE = VECTOR_SIZE
PREDICTION_HISTORY_SIZE = 5
STABLE_FRAMES_REQUIRED = 4
LOW_CONFIDENCE_FRAMES_REQUIRED = 5
MIN_SAMPLES_PER_CLASS = 20
CONFIDENCE_THRESHOLD = 0.80
RECOGNITION_FPS = 15
# La interfaz final para niños no muestra métricas técnicas de reconocimiento.
DEBUG_MODE = False
SHOW_LANDMARKS = True
DRAW_LANDMARKS = SHOW_LANDMARKS
SAMPLE_CAPTURE_INTERVAL_SECONDS = 0.45
TOTAL_ROUNDS = 10
POINTS_PER_CORRECT = 100
STREAK_BONUS_PER_LEVEL = 10
