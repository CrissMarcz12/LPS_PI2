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


if __name__ == "__main__":
    unittest.main()
