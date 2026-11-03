import tempfile
import unittest
from pathlib import Path

import numpy as np

from config import CONFIDENCE_THRESHOLD, PREDICTION_HISTORY_SIZE, SEQUENCE_LENGTH
from game.session import SessionState
from recognition.classifier import AvailableLettersClassifier, Prediction, available_models, save_letter_model


class GamePipelineTests(unittest.TestCase):
    def test_valid_models_are_the_only_available_letters(self):
        root = Path(tempfile.mkdtemp())
        samples = np.zeros((3, 63), dtype=np.float32)
        save_letter_model("A", samples, root, SEQUENCE_LENGTH)
        (root / "O").mkdir()
        self.assertEqual(tuple(available_models(root, SEQUENCE_LENGTH)), ("A",))

    def test_live_prediction_precedes_stable_confirmation(self):
        root = Path(tempfile.mkdtemp())
        samples = np.zeros((3, 63), dtype=np.float32)
        save_letter_model("A", samples, root, SEQUENCE_LENGTH)
        classifier = AvailableLettersClassifier(available_models(root, SEQUENCE_LENGTH), .8, PREDICTION_HISTORY_SIZE)
        first = classifier.predict(samples[0])
        self.assertEqual(first.letter, "A")
        self.assertFalse(first.stable)
        for _ in range(PREDICTION_HISTORY_SIZE):
            final = classifier.predict(samples[0])
        self.assertTrue(final.stable)

    def test_session_only_resolves_after_stable_prediction(self):
        session = SessionState(("A",), 1)
        session.evaluate(Prediction("A", .9, False), CONFIDENCE_THRESHOLD)
        self.assertEqual(session.prediction, "A")
        self.assertEqual(session.result, "analyzing")
        session.evaluate(Prediction("A", .9, True), CONFIDENCE_THRESHOLD)
        self.assertEqual(session.result, "correct")
        self.assertEqual(session.score, 100)

    def test_session_practices_each_available_letter_in_order(self):
        session = SessionState(("A", "B", "C"), 3)
        self.assertEqual(session.target, "A")
        self.assertEqual(session.payload()["totalRounds"], 3)
        session.next_round()
        self.assertEqual((session.current_round, session.target), (2, "B"))
        session.next_round()
        self.assertEqual((session.current_round, session.target), (3, "C"))
        session.next_round()
        self.assertTrue(session.completed)

    def test_guidance_uses_the_most_different_finger(self):
        root = Path(tempfile.mkdtemp())
        samples = np.zeros((4, 63), dtype=np.float32)
        save_letter_model("A", samples, root, SEQUENCE_LENGTH)
        classifier = AvailableLettersClassifier(available_models(root, SEQUENCE_LENGTH), .8, PREDICTION_HISTORY_SIZE)
        observed = np.zeros(63, dtype=np.float32)
        observed[5 * 3:9 * 3] = 4  # Índice: landmarks 5 al 8.
        self.assertEqual(classifier.guidance_for("A", observed), "Revisa la posición de: índice.")

    def test_guidance_marks_multiple_similarly_wrong_fingers(self):
        root = Path(tempfile.mkdtemp())
        samples = np.zeros((4, 63), dtype=np.float32)
        save_letter_model("A", samples, root, SEQUENCE_LENGTH)
        classifier = AvailableLettersClassifier(available_models(root, SEQUENCE_LENGTH), .8, PREDICTION_HISTORY_SIZE)
        observed = np.zeros(63, dtype=np.float32)
        observed[5 * 3:17 * 3] = 4
        self.assertEqual(classifier.guidance_for("A", observed), "Revisa la posición de: índice, dedo medio, dedo anular.")

    def test_low_confidence_becomes_a_correctable_error(self):
        session = SessionState(("A",), 1)
        uncertain = Prediction(None, .5, False)
        session.evaluate(uncertain, CONFIDENCE_THRESHOLD, "Revisa la posición de tu pulgar.", low_confidence_limit=2)
        self.assertEqual(session.result, "analyzing")
        session.evaluate(uncertain, CONFIDENCE_THRESHOLD, "Revisa la posición de tu pulgar.", low_confidence_limit=2)
        self.assertEqual(session.result, "incorrect")
        self.assertEqual(session.error_hint, "Revisa la posición de tu pulgar.")


if __name__ == "__main__":
    unittest.main()
