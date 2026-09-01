"""Captura, reconocimiento y modo educativo del abecedario LSP."""
from __future__ import annotations

import argparse
import random

import cv2

from config import (CAMERA_INDEX, DATASET_PATH, DYNAMIC_DATASET_PATH,
                    DYNAMIC_MIN_FRAMES, DYNAMIC_MODEL_PATH,
                    DYNAMIC_SEQUENCE_LENGTH, MAX_HANDS, MIN_CONFIDENCE,
                    MODEL_PATH, SEQUENCE_LENGTH, STABLE_FRAMES)
from data.dataset import append_sample, class_counts
from data.labels import active_labels, dynamic_labels, validate_label
from features.landmarks import (DynamicRecording, LandmarkSequence,
                                normalized_hand_vector)
from recognition.classifier import AlphabetClassifier, Prediction
from runtime.mediapipe_loader import load_mediapipe_solutions


class EducationSession:
    def __init__(self, target: str) -> None:
        self.target = target
        self.score = 0
        self.attempts = 0
        self.result = "ESPERANDO"
        self.last_accepted: str | None = None

    def choose_next(self) -> None:
        choices = [label for label in active_labels() if label != self.target]
        self.target = random.choice(choices)
        self.result = "ESPERANDO"
        self.last_accepted = None

    def evaluate(self, prediction: Prediction) -> None:
        if not prediction.stable or prediction.letter is None or prediction.letter == self.last_accepted:
            return
        self.last_accepted = prediction.letter
        self.attempts += 1
        if prediction.letter == self.target:
            self.score += 1
            self.result = "CORRECTO"
        else:
            self.result = "INCORRECTO"


def put(frame, text: str, xy: tuple[int, int], color=(245, 245, 245), scale=0.65, thickness=2) -> None:
    cv2.putText(frame, text, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def draw_ui(frame, prediction: Prediction, education: EducationSession | None,
            mode: str, capture_count: int | None, model_available: bool, recording: bool) -> None:
    height, width = frame.shape[:2]
    panel = frame.copy()
    cv2.rectangle(panel, (0, 0), (width, 205), (20, 29, 52), -1)
    frame[:] = cv2.addWeighted(panel, 0.82, frame, 0.18, 0)
    put(frame, "LSP: ALFABETO Y SIGNOS", (18, 31), (120, 205, 255), 0.75)
    # cv2.putText no representa de forma fiable el guion largo Unicode y lo
    # convertia en "???" en algunos equipos Windows.
    letter = prediction.letter if prediction.letter else "SIN CLASIFICAR"
    put(frame, f"LETRA RECONOCIDA: {letter}", (18, 65), (255, 255, 255), 0.85)
    put(frame, f"CONFIANZA: {prediction.confidence * 100:.1f}%", (18, 94))
    if education:
        color = (80, 220, 120) if education.result == "CORRECTO" else (90, 130, 255) if education.result == "INCORRECTO" else (245, 245, 245)
        put(frame, f"REALIZA: {education.target}", (18, 124), (255, 220, 105), 0.78)
        put(frame, f"RESULTADO: {education.result}   PUNTAJE: {education.score}/{education.attempts}", (18, 154), color)
        if not model_available:
            put(frame, "SIN MODELO: captura las clases y ejecuta python train.py", (18, 184), (90, 180, 255), 0.52)
    elif mode == "collect":
        put(frame, f"CAPTURA: {capture_count or 0} muestras | SPACE guarda | R limpia buffer", (18, 124), (255, 220, 105), 0.58)
    elif mode == "collect_dynamic":
        action = "GRABANDO: realiza el movimiento y pulsa SPACE" if recording else "SPACE inicia una secuencia de movimiento"
        put(frame, f"DINAMICA: {capture_count or 0} muestras | {action}", (18, 124), (255, 220, 105), 0.52)
        put(frame, "R cancela la grabacion actual", (18, 154), (255, 220, 105), 0.52)
    elif not model_available:
        put(frame, "MODELO AUN NO ENTRENADO: usa captura y luego python train.py", (18, 124), (90, 180, 255), 0.54)
    put(frame, "SPACE: grabar movimiento | ENTER: nueva clase | ESC: salir", (18, height - 18), (230, 230, 230), 0.48)


def run(args: argparse.Namespace) -> None:
    mp = load_mediapipe_solutions()
    static_label = validate_label(args.label) if args.label else None
    dynamic_label = validate_label(args.dynamic_label) if args.dynamic_label else None
    label = static_label or dynamic_label
    educational = EducationSession(validate_label(args.target)) if args.educational else None
    sequence = LandmarkSequence(SEQUENCE_LENGTH)
    recording = DynamicRecording(DYNAMIC_SEQUENCE_LENGTH, DYNAMIC_MIN_FRAMES)
    # Recopilar datos no depende de ningun modelo previo: evita que un modelo
    # provisional distraiga o influya visualmente durante la captura.
    static_classifier = None if label else AlphabetClassifier(MODEL_PATH, MIN_CONFIDENCE, STABLE_FRAMES)
    dynamic_classifier = None if label else AlphabetClassifier(DYNAMIC_MODEL_PATH, MIN_CONFIDENCE, 1)
    dataset_path = DYNAMIC_DATASET_PATH if dynamic_label else DATASET_PATH
    feature_size = DYNAMIC_SEQUENCE_LENGTH * 63 if dynamic_label else SEQUENCE_LENGTH * 63
    sample_count = class_counts(dataset_path, feature_size).get(label, 0) if label else None
    dynamic_prediction = Prediction(None, 0.0, False)

    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        raise RuntimeError("No se pudo abrir la camara configurada.")
    hands_api = mp.solutions.hands
    drawer = mp.solutions.drawing_utils
    connections = hands_api.HAND_CONNECTIONS
    with hands_api.Hands(static_image_mode=False, max_num_hands=MAX_HANDS,
                        model_complexity=1, min_detection_confidence=0.65,
                        min_tracking_confidence=0.65) as hands:
        while True:
            ok, frame = camera.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            prediction = Prediction(None, 0.0, False)
            if result.multi_hand_landmarks:
                hand = result.multi_hand_landmarks[0]
                drawer.draw_landmarks(frame, hand, connections)
                vector = normalized_hand_vector(hand)
                sequence.add(vector)
                recording.add(vector)
                if sequence.ready and static_classifier and static_classifier.available and not recording.active:
                    prediction = static_classifier.predict(sequence.flattened())
                    if educational:
                        if educational.target not in dynamic_labels():
                            educational.evaluate(prediction)
            else:
                sequence.clear()
                if static_classifier:
                    static_classifier.reset()

            if educational and educational.target in dynamic_labels():
                prediction = dynamic_prediction

            draw_ui(
                frame,
                prediction,
                educational,
                "collect_dynamic" if dynamic_label else "collect" if static_label else "recognize",
                sample_count,
                bool((static_classifier and static_classifier.available) or (dynamic_classifier and dynamic_classifier.available)),
                recording.active,
            )
            cv2.imshow("LSP - alfabeto y signos estaticos", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            if key == ord("r"):
                sequence.clear()
                recording.cancel()
                if static_classifier:
                    static_classifier.reset()
            elif key == ord(" ") and dynamic_label:
                if not recording.active:
                    recording.start()
                    print(f"Grabacion iniciada para {dynamic_label}")
                else:
                    features = recording.stop()
                    if features is None:
                        print(f"Grabacion muy corta: usa al menos {DYNAMIC_MIN_FRAMES} cuadros.")
                    else:
                        sample_count = append_sample(DYNAMIC_DATASET_PATH, features, dynamic_label)
                        print(f"Secuencia {sample_count} guardada para {dynamic_label}")
            elif key == ord(" ") and static_label:
                if sequence.ready:
                    sample_count = append_sample(DATASET_PATH, sequence.flattened(), static_label)
                    print(f"Muestra {sample_count} guardada para {static_label}")
                else:
                    print("Mantén la mano visible hasta llenar el buffer.")
            elif key == ord(" ") and dynamic_classifier and dynamic_classifier.available:
                if not recording.active:
                    recording.start()
                    print("Grabacion dinamica iniciada")
                else:
                    features = recording.stop()
                    if features is None:
                        print("Grabacion muy corta.")
                    else:
                        dynamic_prediction = dynamic_classifier.predict(features)
                        if educational and educational.target in dynamic_labels():
                            educational.evaluate(dynamic_prediction)
            elif key in (13, 10) and educational:
                educational.choose_next()
    camera.release()
    cv2.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconocedor LSP de posturas y signos con movimiento.")
    parser.add_argument("--collect", metavar="CLASE", dest="label", help="guarda muestras de una clase estatica")
    parser.add_argument("--collect-dynamic", metavar="CLASE", dest="dynamic_label", help="graba una clase con movimiento")
    parser.add_argument("--educational", action="store_true", help="activa letra solicitada, resultado y puntaje")
    parser.add_argument("--target", default="A", help="letra inicial del modo educativo")
    args = parser.parse_args()
    if sum(bool(value) for value in (args.label, args.dynamic_label, args.educational)) > 1:
        parser.error("Usa captura o modo educativo, no ambos a la vez.")
    if args.label and validate_label(args.label) in dynamic_labels():
        parser.error("Esta clase requiere movimiento: usa --collect-dynamic.")
    if args.dynamic_label and validate_label(args.dynamic_label) not in dynamic_labels():
        parser.error("Esta clase es estatica: usa --collect.")
    return args


if __name__ == "__main__":
    run(parse_args())
