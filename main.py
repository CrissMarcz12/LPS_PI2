"""Servidor local de la experiencia de juego RimayMaki."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import threading
import webbrowser
from flask import Flask, jsonify, render_template, request
from config import MODELS_DIR, SEQUENCE_LENGTH
from game.controller import GameController

def open_browser(url: str) -> None:
    candidates = [Path(os.environ.get(name, "")) / "Google/Chrome/Application/chrome.exe" for name in ("PROGRAMFILES", "PROGRAMFILES(X86)")]
    for chrome in candidates:
        if chrome.is_file():
            subprocess.Popen([str(chrome), url])
            return
    webbrowser.open(url)

def create_app() -> Flask:
    app = Flask(__name__)
    controller = GameController(MODELS_DIR, SEQUENCE_LENGTH)
    app.extensions["rimaymaki_controller"] = controller

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/game")
    def game():
        controller.start()
        return render_template("game.html")

    @app.get("/api/session")
    def session():
        return jsonify(controller.payload())

    @app.post("/api/frame")
    def frame():
        upload = request.files.get("frame")
        if upload is None or not upload.filename:
            return jsonify({"message": "No se recibió una imagen de cámara."}), 400
        return jsonify(controller.submit_frame(upload.read()))

    @app.post("/api/retry")
    def retry():
        return jsonify(controller.retry())

    @app.post("/api/next")
    def next_round():
        return jsonify(controller.next_round())

    return app

app = create_app()
if __name__ == "__main__":
    url = "http://127.0.0.1:5000"
    threading.Timer(.8, lambda: open_browser(url)).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
