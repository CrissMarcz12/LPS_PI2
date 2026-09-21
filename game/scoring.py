"""Reglas de puntuación independientes de la interfaz."""
from config import POINTS_PER_CORRECT, STREAK_BONUS_PER_LEVEL

def points_for_correct(next_streak: int) -> int:
    """Cada acierto suma 100 y la racha añade una bonificación gradual."""
    return POINTS_PER_CORRECT + max(0, next_streak - 1) * STREAK_BONUS_PER_LEVEL
