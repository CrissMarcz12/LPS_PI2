"""Validación de etiquetas para las señas entrenadas."""
from __future__ import annotations

import re

# Permite letras, números y nombres cortos como "HOLA" o "NÚMERO 1", sin
# caracteres que puedan convertirse en rutas de archivos inseguras.
LABEL_PATTERN = re.compile(r"^[A-Z0-9ÁÉÍÓÚÜÑ][A-Z0-9ÁÉÍÓÚÜÑ _-]{0,31}$")


def normalize_label(label: str) -> str:
    value = " ".join(str(label).strip().upper().split())
    if not LABEL_PATTERN.fullmatch(value):
        raise ValueError(
            "Usa de 1 a 32 caracteres: letras, números, espacios, guiones o guion bajo."
        )
    return value
