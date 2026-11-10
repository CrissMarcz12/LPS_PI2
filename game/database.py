"""Ranking persistente: PostgreSQL en Render y SQLite solo para desarrollo."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any

DEFAULT_PROFILES = (("killa", "Killa", "🌟", "violet"), ("inti", "Inti", "☀️", "gold"), ("maki", "Maki", "🐻", "sky"), ("sumaq", "Sumaq", "🌈", "coral"))
THEMES = ("violet", "sky", "mint", "coral")

class GameDatabase:
    def __init__(self, path: Path, database_url: str = "") -> None:
        self.path, self.database_url = path, database_url
        self.postgres = database_url.startswith(("postgres://", "postgresql://"))

    @contextmanager
    def _connection(self):
        if self.postgres:
            from psycopg import connect
            from psycopg.rows import dict_row
            connection = connect(self.database_url, row_factory=dict_row)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _sql(self, statement: str) -> str:
        return statement.replace("?", "%s") if self.postgres else statement

    def _execute(self, connection, statement: str, params=()):
        return connection.execute(self._sql(statement), params)

    def initialize(self) -> None:
        identity = "BIGSERIAL PRIMARY KEY" if self.postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        statements = [
            """CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, name TEXT NOT NULL, avatar TEXT NOT NULL, theme TEXT NOT NULL DEFAULT 'violet', total_score INTEGER NOT NULL DEFAULT 0, max_streak INTEGER NOT NULL DEFAULT 0, games_played INTEGER NOT NULL DEFAULT 0, last_played_at TEXT)""",
            f"""CREATE TABLE IF NOT EXISTS game_results (id {identity}, profile_id TEXT NOT NULL REFERENCES profiles(id), score INTEGER NOT NULL, max_streak INTEGER NOT NULL, correct_answers INTEGER NOT NULL, wrong_answers INTEGER NOT NULL, letters_completed INTEGER NOT NULL, completed_at TEXT NOT NULL)""",
            "CREATE INDEX IF NOT EXISTS idx_game_results_profile ON game_results(profile_id)",
        ]
        with self._connection() as connection:
            for statement in statements: self._execute(connection, statement)
            for profile in DEFAULT_PROFILES:
                if self.postgres:
                    self._execute(connection, "INSERT INTO profiles (id, name, avatar, theme) VALUES (?, ?, ?, ?) ON CONFLICT (id) DO NOTHING", profile)
                else:
                    self._execute(connection, "INSERT OR IGNORE INTO profiles (id, name, avatar, theme) VALUES (?, ?, ?, ?)", profile)

    @staticmethod
    def _profile(row: Any, position: int | None = None) -> dict[str, Any]:
        data = {"id":row["id"], "name":row["name"], "avatar":row["avatar"], "theme":row["theme"], "totalScore":row["total_score"], "maxStreak":row["max_streak"], "gamesPlayed":row["games_played"], "lastPlayedAt":row["last_played_at"]}
        if position is not None: data["position"] = position
        return data

    def profiles(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = self._execute(connection, "SELECT * FROM profiles ORDER BY total_score DESC, max_streak DESC, name ASC").fetchall()
        return [self._profile(row, index) for index, row in enumerate(rows, 1)]

    def profile(self, profile_id: str) -> dict[str, Any] | None:
        return next((item for item in self.profiles() if item["id"] == profile_id), None)

    def choose_profile(self, profile_id: str, theme: str) -> dict[str, Any]:
        if theme not in THEMES: raise ValueError("El color elegido no existe.")
        with self._connection() as connection:
            updated = self._execute(connection, "UPDATE profiles SET theme = ? WHERE id = ?", (theme, profile_id)).rowcount
        if not updated: raise ValueError("El aventurero elegido no existe.")
        return self.profile(profile_id) or (_ for _ in ()).throw(ValueError("No se pudo cargar el aventurero."))

    def record_game(self, profile_id: str, state: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        score, streak = max(0, int(state.get("score", 0))), max(0, int(state.get("maxStreak", 0)))
        correct, wrong = max(0, int(state.get("correctAnswers", 0))), max(0, int(state.get("wrongAnswers", 0)))
        with self._connection() as connection:
            if not self._execute(connection, "SELECT 1 FROM profiles WHERE id = ?", (profile_id,)).fetchone(): raise ValueError("El aventurero elegido no existe.")
            self._execute(connection, "INSERT INTO game_results (profile_id, score, max_streak, correct_answers, wrong_answers, letters_completed, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (profile_id, score, streak, correct, wrong, correct, now))
            self._execute(connection, "UPDATE profiles SET total_score = total_score + ?, max_streak = CASE WHEN max_streak > ? THEN max_streak ELSE ? END, games_played = games_played + 1, last_played_at = ? WHERE id = ?", (score, streak, streak, now, profile_id))
        return self.profile(profile_id) or (_ for _ in ()).throw(ValueError("No se pudo actualizar el perfil."))
