"""Flujo sencillo para compartir letras entrenadas mediante GitHub.

Uso:
  python training/team_sync.py entrenar C
  python training/team_sync.py publicar C
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DATASETS_DIR, MODELS_DIR, REFERENCE_IMAGES_DIR  # noqa: E402
from features.labels import normalize_label  # noqa: E402


def run_git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def overlay(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def prepare(label: str) -> None:
    """Obtiene el trabajo del equipo antes de iniciar una letra."""
    run_git("pull", "--rebase", "origin", "main")
    overlay(ROOT / "datasets" / label, DATASETS_DIR / label)
    overlay(ROOT / "models" / label, MODELS_DIR / label)
    overlay(ROOT / "static" / "assets" / "signs" / f"{label}.png", REFERENCE_IMAGES_DIR / f"{label}.png")
    print(f"Listo para entrenar {label}. Abre la ruta privada de entrenamiento y captura muestras.")


def publish(label: str) -> None:
    """Integra primero el trabajo ajeno y publica solo una letra terminada."""
    model = MODELS_DIR / label
    samples = DATASETS_DIR / label
    reference = REFERENCE_IMAGES_DIR / f"{label}.png"
    if not (model / "classifier.joblib").is_file() or not (model / "metadata.json").is_file():
        raise SystemExit(f"No hay un modelo entrenado para {label}. Pulsa 'ENTRENAR MODELO' primero.")
    if not samples.is_dir() or not any(samples.glob("*.npz")):
        raise SystemExit(f"No hay muestras para {label}.")

    # El pull sucede antes de copiar los resultados locales: así C y D de
    # distintas personas se integran sin sobrescribir la letra del otro.
    run_git("pull", "--rebase", "origin", "main")
    overlay(samples, ROOT / "datasets" / label)
    overlay(model, ROOT / "models" / label)
    if reference.is_file():
        overlay(reference, ROOT / "static" / "assets" / "signs" / f"{label}.png")
    paths = [f"models/{label}", f"datasets/{label}"]
    if reference.is_file():
        paths.append(f"static/assets/signs/{label}.png")
    run_git("add", "--force", *paths)
    unchanged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False
    ).returncode == 0
    if unchanged:
        print(f"No hay cambios nuevos de {label} para publicar.")
        return
    run_git("commit", "-m", f"Agrega entrenamiento de {label}")
    run_git("push", "origin", "main")
    print(f"{label} publicado en GitHub. Render lo incluirá en su próximo deploy.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza una letra entrenada con el repositorio del equipo.")
    parser.add_argument("action", choices=("preparar", "entrenar", "publicar"))
    parser.add_argument("label", type=normalize_label, help="Ejemplo: C, D, HOLA")
    args = parser.parse_args()
    if args.action == "publicar":
        publish(args.label)
    else:
        prepare(args.label)
        if args.action == "entrenar":
            print("Iniciando RimayMaki. La página de entrenamiento se abrirá en el navegador.")
            subprocess.run([sys.executable, "main.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
