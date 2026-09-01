"""Administra palabras estáticas sin abrir la cámara."""
from __future__ import annotations

import argparse

from data.labels import (add_dynamic_word, add_static_word, dynamic_words,
                         remove_dynamic_word, remove_static_word, static_words)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestiona palabras estáticas del reconocedor LSP.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add = subparsers.add_parser("add", help="agrega una palabra estática, por ejemplo HOLA")
    add.add_argument("word")
    add_dynamic = subparsers.add_parser("add-dynamic", help="agrega una palabra con movimiento")
    add_dynamic.add_argument("word")
    remove = subparsers.add_parser("remove", help="elimina una palabra estática antes de entrenar")
    remove.add_argument("word")
    remove_dynamic = subparsers.add_parser("remove-dynamic", help="elimina una palabra con movimiento")
    remove_dynamic.add_argument("word")
    subparsers.add_parser("list", help="muestra las palabras estáticas activas")
    args = parser.parse_args()
    if args.command == "add":
        print(f"Palabra estatica registrada: {add_static_word(args.word)}")
    elif args.command == "add-dynamic":
        print(f"Palabra dinamica registrada: {add_dynamic_word(args.word)}")
    elif args.command == "remove":
        print(f"Palabra estatica eliminada: {remove_static_word(args.word)}")
    elif args.command == "remove-dynamic":
        print(f"Palabra dinamica eliminada: {remove_dynamic_word(args.word)}")
    else:
        static, dynamic = static_words(), dynamic_words()
        print("Palabras estaticas:", ", ".join(static) if static else "ninguna")
        print("Palabras dinamicas:", ", ".join(dynamic) if dynamic else "ninguna")


if __name__ == "__main__":
    main()
