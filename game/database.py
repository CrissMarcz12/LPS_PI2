"""Ranking persistente: PostgreSQL en Render y SQLite solo para desarrollo."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any

AVATARS = {"robo": ("Robo", "/static/assets/avatars/robot-base.png"), "llamabot": ("LlamaBot", "/static/assets/avatars/robot-llama.png"), "navibot": ("NaviBot", "/static/assets/avatars/robot-navidad.png"), "perubot": ("PeruBot", "/static/assets/avatars/robot-peru.png")}
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
            """CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, name TEXT NOT NULL, avatar_id TEXT NOT NULL, avatar TEXT NOT NULL, theme TEXT NOT NULL DEFAULT 'violet', total_score INTEGER NOT NULL DEFAULT 0, live_score INTEGER NOT NULL DEFAULT 0, max_streak INTEGER NOT NULL DEFAULT 0, games_played INTEGER NOT NULL DEFAULT 0, last_played_at TEXT)""",
            f"""CREATE TABLE IF NOT EXISTS player_results (id {identity}, player_id TEXT NOT NULL REFERENCES players(id), score INTEGER NOT NULL, max_streak INTEGER NOT NULL, correct_answers INTEGER NOT NULL, wrong_answers INTEGER NOT NULL, letters_completed INTEGER NOT NULL, completed_at TEXT NOT NULL)""",
            "CREATE INDEX IF NOT EXISTS idx_player_results_player ON player_results(player_id)",
        ]
        with self._connection() as connection:
            for statement in statements: self._execute(connection, statement)

    @staticmethod
    def _profile(row: Any, position: int | None = None) -> dict[str, Any]:
        data = {"id":row["id"], "name":row["name"], "avatar":row["avatar"], "theme":row["theme"], "totalScore":row["total_score"], "maxStreak":row["max_streak"], "gamesPlayed":row["games_played"], "lastPlayedAt":row["last_played_at"]}
        if position is not None: data["position"] = position
        return data

    def profiles(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = self._execute(connection, "SELECT id, name, avatar, theme, total_score + live_score AS total_score, max_streak, games_played, last_played_at FROM players ORDER BY total_score + live_score DESC, max_streak DESC, name ASC").fetchall()
        return [self._profile(row, index) for index, row in enumerate(rows, 1)]

    def profile(self, profile_id: str) -> dict[str, Any] | None:
        return next((item for item in self.profiles() if item["id"] == profile_id), None)

    def choose_profile(self, avatar_id: str, code: str, theme: str) -> dict[str, Any]:
        if theme not in THEMES: raise ValueError("El color elegido no existe.")
        if avatar_id not in AVATARS or len(code) != 4 or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for char in code): raise ValueError("El nombre debe tener cuatro letras o números.")
        base_name, avatar = AVATARS[avatar_id]
        profile_id, name = f"{avatar_id}-{code}", f"{base_name}-{code}"
        with self._connection() as connection:
            if self.postgres:
                self._execute(connection, "INSERT INTO players (id, name, avatar_id, avatar, theme) VALUES (?, ?, ?, ?, ?) ON CONFLICT (id) DO UPDATE SET theme = EXCLUDED.theme", (profile_id, name, avatar_id, avatar, theme))
            else:
                self._execute(connection, "INSERT INTO players (id, name, avatar_id, avatar, theme) VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET theme = excluded.theme", (profile_id, name, avatar_id, avatar, theme))
        return self.profile(profile_id) or (_ for _ in ()).throw(ValueError("No se pudo cargar el aventurero."))

    def update_progress(self, profile_id: str, state: dict[str, Any]) -> dict[str, Any]:
        score, streak = max(0, int(state.get("score", 0))), max(0, int(state.get("maxStreak", 0)))
        with self._connection() as connection:
            self._execute(connection, "UPDATE players SET live_score = ?, max_streak = CASE WHEN max_streak > ? THEN max_streak ELSE ? END WHERE id = ?", (score, streak, streak, profile_id))
        return self.profile(profile_id) or (_ for _ in ()).throw(ValueError("El aventurero elegido no existe."))

    def record_game(self, profile_id: str, state: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        score, streak = max(0, int(state.get("score", 0))), max(0, int(state.get("maxStreak", 0)))
        correct, wrong = max(0, int(state.get("correctAnswers", 0))), max(0, int(state.get("wrongAnswers", 0)))
        with self._connection() as connection:
            if not self._execute(connection, "SELECT 1 FROM players WHERE id = ?", (profile_id,)).fetchone(): raise ValueError("El aventurero elegido no existe.")
            self._execute(connection, "INSERT INTO player_results (player_id, score, max_streak, correct_answers, wrong_answers, letters_completed, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (profile_id, score, streak, correct, wrong, correct, now))
            self._execute(connection, "UPDATE players SET total_score = total_score + ?, live_score = 0, max_streak = CASE WHEN max_streak > ? THEN max_streak ELSE ? END, games_played = games_played + 1, last_played_at = ? WHERE id = ?", (score, streak, streak, now, profile_id))
        return self.profile(profile_id) or (_ for _ in ()).throw(ValueError("No se pudo actualizar el perfil."))
