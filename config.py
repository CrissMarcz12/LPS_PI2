"""Configuracion del reconocedor exclusivo del alfabeto LSP."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
DATASET_PATH = DATA_DIR / "lsp_static_vocabulary_landmarks.npz"
MODEL_PATH = MODEL_DIR / "lsp_static_vocabulary_classifier.joblib"
DYNAMIC_DATASET_PATH = DATA_DIR / "lsp_dynamic_vocabulary_landmarks.npz"
DYNAMIC_MODEL_PATH = MODEL_DIR / "lsp_dynamic_vocabulary_classifier.joblib"
VOCABULARY_PATH = DATA_DIR / "vocabulary.json"

CAMERA_INDEX = 0
MAX_HANDS = 1
SEQUENCE_LENGTH = 20
DYNAMIC_SEQUENCE_LENGTH = 48
DYNAMIC_MIN_FRAMES = 12
MIN_CONFIDENCE = 0.72
STABLE_FRAMES = 8
MIN_SAMPLES_PER_LETTER = 40

# Segun la lamina aportada: J, Ñ y Z incluyen desplazamiento. Las otras letras
# se recogen como posturas estables, aunque todas usan el mismo vector temporal.
DYNAMIC_LETTERS = frozenset({"J", "Ñ", "Z"})
