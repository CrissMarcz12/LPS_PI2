"""Estado de una sesión; no conoce HTTP, cámara ni HTML."""
from __future__ import annotations
import random
from dataclasses import dataclass
from recognition.classifier import Prediction
from .scoring import points_for_correct

@dataclass
class SessionState:
    available_letters: tuple[str, ...]
    total_rounds: int
    current_round: int = 1
    score: int = 0
    correct_answers: int = 0
    wrong_answers: int = 0
    current_streak: int = 0
    max_streak: int = 0
    target: str | None = None
    prediction: str | None = None
    confidence: float | None = None
    result: str = "waiting"
    awarded_points: int = 0
    hand_detected: bool = False
    landmarks: list[dict[str, float]] | None = None
    frames_collected: int = 0
    prediction_stable: bool = False

    def __post_init__(self) -> None:
        if self.available_letters:
            self.target = random.choice(self.available_letters)

    @property
    def completed(self) -> bool:
        return self.current_round > self.total_rounds

    def evaluate(self, prediction: Prediction, threshold: float) -> None:
        if self.completed or self.result in {"correct", "incorrect"}:
            return
        if prediction.confidence <= 0:
            self.prediction = None
            self.confidence = None
            self.result = "no_hand"
            return
        self.confidence = prediction.confidence
        if prediction.confidence < threshold:
            self.prediction = None
            self.result = "analyzing"
            return
        if not prediction.stable or prediction.letter is None:
            self.result = "analyzing"
            return
        self.prediction = prediction.letter
        if prediction.letter == self.target:
            self.current_streak += 1
            self.max_streak = max(self.max_streak, self.current_streak)
            self.awarded_points = points_for_correct(self.current_streak)
            self.score += self.awarded_points
            self.correct_answers += 1
            self.result = "correct"
        else:
            self.current_streak = 0
            self.wrong_answers += 1
            self.awarded_points = 0
            self.result = "incorrect"

    def retry(self) -> None:
        if self.result == "incorrect":
            self.prediction = None
            self.confidence = None
            self.result = "waiting"

    def next_round(self) -> None:
        if self.completed:
            return
        self.current_round += 1
        self.prediction = None
        self.confidence = None
        self.result = "waiting"
        self.awarded_points = 0
        self.target = None if self.completed else random.choice(self.available_letters)

    def observe(self, *, hand_detected: bool, landmarks: list[dict[str, float]], frames_collected: int, prediction: Prediction) -> None:
        self.hand_detected = hand_detected
        self.landmarks = landmarks
        self.frames_collected = frames_collected
        self.prediction_stable = prediction.stable

    def payload(self) -> dict:
        attempts = self.correct_answers + self.wrong_answers
        return {
            "availableLetters": len(self.available_letters), "currentRound": self.current_round,
            "totalRounds": self.total_rounds, "score": self.score, "correctAnswers": self.correct_answers,
            "wrongAnswers": self.wrong_answers, "currentStreak": self.current_streak,
            "maxStreak": self.max_streak, "target": self.target, "prediction": self.prediction,
            "confidence": round(self.confidence * 100, 1) if self.confidence is not None else None,
            "result": "completed" if self.completed else self.result, "awardedPoints": self.awarded_points,
            "accuracy": round(self.correct_answers / attempts * 100) if attempts else 0,
            "handDetected": self.hand_detected, "landmarks": self.landmarks or [],
            "framesCollected": self.frames_collected, "predictionStable": self.prediction_stable,
        }
