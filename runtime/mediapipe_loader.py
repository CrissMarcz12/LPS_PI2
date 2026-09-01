"""Carga segura de MediaPipe Solutions en equipos con App Control."""
from __future__ import annotations

import sys
import warnings
from types import ModuleType


def _install_unused_matplotlib_stub() -> None:
    """Evita una importacion opcional que no usa este proyecto.

    MediaPipe 0.10 importa la API Tasks al inicializarse; esa API importa
    ``matplotlib.pyplot`` solo para funciones de dibujo 3D que esta aplicacion
    no llama. En equipos donde Windows App Control bloquea kiwisolver, el
    import falla antes de llegar a ``mp.solutions.hands``. El stub existe solo
    durante este proceso y deja intacta la instalacion del usuario.
    """
    if "matplotlib" in sys.modules:
        return
    matplotlib = ModuleType("matplotlib")
    pyplot = ModuleType("matplotlib.pyplot")
    matplotlib.pyplot = pyplot
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot


def load_mediapipe_solutions():
    """Devuelve MediaPipe 0.10.x con la API ``mp.solutions`` disponible."""
    warnings.filterwarnings(
        "ignore",
        message=r"SymbolDatabase.GetPrototype\(\) is deprecated.*",
        category=UserWarning,
    )
    _install_unused_matplotlib_stub()
    try:
        import mediapipe as mp
    except ImportError as exc:
        raise RuntimeError(
            "No se pudo cargar MediaPipe. Ejecuta: "
            "python -m pip install --force-reinstall -r requirements.txt"
        ) from exc
    if not hasattr(mp, "solutions"):
        version = getattr(mp, "__version__", "desconocida")
        raise RuntimeError(
            f"MediaPipe {version} no ofrece mp.solutions. "
            "Instala la version fijada: python -m pip install --force-reinstall mediapipe==0.10.14"
        )
    return mp
