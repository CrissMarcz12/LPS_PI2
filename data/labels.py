"""Vocabulario cerrado: alfabeto LSP y palabras estáticas declaradas."""
from __future__ import annotations

import json
from config import VOCABULARY_PATH
from config import DYNAMIC_LETTERS

# El alfabeto configurado contiene exactamente 27 clases. LL no es una clase.
LSP_ALPHABET = (
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "Ñ", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
)


def _normalize_word(word: str) -> str:
    normalized = word.strip().upper()
    if not normalized or not normalized.isalpha() or " " in normalized:
        raise ValueError("La palabra debe ser una sola palabra alfabetica, por ejemplo HOLA.")
    if normalized == "LL":
        raise ValueError("LL no es una clase valida en este proyecto.")
    return normalized


def _words_for(kind: str) -> tuple[str, ...]:
    if not VOCABULARY_PATH.exists():
        return ()
    try:
        payload = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))
        words = payload.get(f"{kind}_words", [])
        return tuple(_normalize_word(word) for word in words)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RuntimeError("No se pudo leer data/vocabulary.json") from exc


def static_words() -> tuple[str, ...]:
    return _words_for("static")


def dynamic_words() -> tuple[str, ...]:
    return _words_for("dynamic")


def static_labels() -> tuple[str, ...]:
    letters = tuple(letter for letter in LSP_ALPHABET if letter not in DYNAMIC_LETTERS)
    return letters + tuple(word for word in static_words() if word not in LSP_ALPHABET)


def dynamic_labels() -> tuple[str, ...]:
    return tuple(letter for letter in LSP_ALPHABET if letter in DYNAMIC_LETTERS) + tuple(
        word for word in dynamic_words() if word not in LSP_ALPHABET
    )


def active_labels() -> tuple[str, ...]:
    """Devuelve las 27 letras más todas las palabras declaradas."""
    return static_labels() + dynamic_labels()


def validate_label(label: str) -> str:
    """Valida que la clase exista en el vocabulario activo."""
    normalized = _normalize_word(label)
    if normalized not in active_labels():
        allowed = ", ".join(active_labels())
        raise ValueError(f"Clase invalida: {label!r}. Primero agregala con manage_vocabulary.py. Activas: {allowed}")
    return normalized


def _save_words(static: list[str], dynamic: list[str]) -> None:
    VOCABULARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    VOCABULARY_PATH.write_text(
        json.dumps({"static_words": static, "dynamic_words": dynamic}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _add_word(word: str, kind: str) -> str:
    normalized = _normalize_word(word)
    if normalized in LSP_ALPHABET:
        raise ValueError(f"{normalized} ya forma parte del alfabeto.")
    static, dynamic = list(static_words()), list(dynamic_words())
    if normalized in static or normalized in dynamic:
        raise ValueError(f"{normalized} ya esta registrada como clase.")
    (static if kind == "static" else dynamic).append(normalized)
    _save_words(static, dynamic)
    return normalized


def add_static_word(word: str) -> str:
    """Registra una palabra estática sin afirmar validación lingüística LSP."""
    return _add_word(word, "static")


def add_dynamic_word(word: str) -> str:
    """Registra una palabra que se capturará como trayectoria de landmarks."""
    return _add_word(word, "dynamic")


def _remove_word(word: str, kind: str) -> str:
    normalized = _normalize_word(word)
    static, dynamic = list(static_words()), list(dynamic_words())
    words = static if kind == "static" else dynamic
    if normalized not in words:
        raise ValueError(f"La palabra {normalized} no esta registrada.")
    words.remove(normalized)
    _save_words(static, dynamic)
    return normalized


def remove_static_word(word: str) -> str:
    return _remove_word(word, "static")


def remove_dynamic_word(word: str) -> str:
    return _remove_word(word, "dynamic")
