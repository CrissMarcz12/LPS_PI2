"""Servidor local de la experiencia de juego RimayMaki."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import threading
from uuid import uuid4
import webbrowser
from flask import Flask, abort, jsonify, render_template, request, send_file, session
from config import MODELS_DIR, SEQUENCE_LENGTH
from features.labels import normalize_label
from game.controller import GameController
from training.controller import TrainingController
from training.storage import initialize_storage, reference_path

def open_browser(url: str) -> None:
    candidates = [Path(os.environ.get(name, "")) / "Google/Chrome/Application/chrome.exe" for name in ("PROGRAMFILES", "PROGRAMFILES(X86)")]
    for chrome in candidates:
        if chrome.is_file():
            subprocess.Popen([str(chrome), url])
            return
    webbrowser.open(url)

def create_app() -> Flask:
    app = Flask(__name__)
    # La cookie permite que varios compañeros entrenen sin mezclar sus cámaras.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "rimaymaki-local-development-key")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    initialize_storage()
    controllers: dict[str, GameController] = {}
    controllers_lock = threading.Lock()
    training = TrainingController()
    app.extensions["rimaymaki_controllers"] = controllers
    app.extensions["rimaymaki_training"] = training

    def client_id() -> str:
        if "rimaymaki_client_id" not in session:
            session["rimaymaki_client_id"] = uuid4().hex
        return str(session["rimaymaki_client_id"])

    def controller() -> GameController:
        identifier = client_id()
        with controllers_lock:
            return controllers.setdefault(identifier, GameController(MODELS_DIR, SEQUENCE_LENGTH))

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/game")
    def game():
        controller().start()
        return render_template("game.html")

    @app.get("/training")
    def training_page():
        return render_template("training.html")

    @app.get("/api/session")
    def session_state():
        return jsonify(controller().payload())

    @app.post("/api/frame")
    def frame():
        upload = request.files.get("frame")
        if upload is None or not upload.filename:
            return jsonify({"message": "No se recibió una imagen de cámara."}), 400
        return jsonify(controller().submit_frame(upload.read()))

    @app.post("/api/retry")
    def retry():
        return jsonify(controller().retry())

    @app.post("/api/next")
    def next_round():
        return jsonify(controller().next_round())

    @app.get("/api/training")
    def training_overview():
        return jsonify(training.overview())

    @app.post("/api/training/configure")
    def training_configure():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(training.configure(client_id(), str(data.get("label", "")), bool(data.get("capturing", False))))
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)}), 400

    @app.post("/api/training/frame")
    def training_frame():
        upload = request.files.get("frame")
        if upload is None or not upload.filename:
            return jsonify({"success": False, "message": "No se recibió una imagen de cámara."}), 400
        try:
            return jsonify({"success": True, **training.submit_frame(client_id(), upload.read())})
        except (RuntimeError, ValueError) as exc:
            return jsonify({"success": False, "message": str(exc)}), 400

    @app.post("/api/training/train")
    def training_train():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(training.train(str(data.get("label", ""))))
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)}), 400

    @app.post("/api/training/clear")
    def training_clear():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(training.clear(str(data.get("label", ""))))
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)}), 400

    @app.post("/api/training/reference")
    def training_reference():
        upload = request.files.get("image")
        if upload is None or not upload.filename:
            return jsonify({"success": False, "message": "Selecciona una imagen de referencia."}), 400
        try:
            return jsonify(training.save_reference(str(request.form.get("label", "")), upload.read()))
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)}), 400

    @app.get("/references/<path:label>.png")
    def reference_image(label: str):
        try:
            image = reference_path(normalize_label(label))
        except ValueError:
            abort(404)
        if not image.is_file():
            abort(404)
        return send_file(image, mimetype="image/png", max_age=3600)

    return app

app = create_app()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    if not os.environ.get("RENDER"):
        threading.Timer(.8, lambda: open_browser(f"http://127.0.0.1:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
