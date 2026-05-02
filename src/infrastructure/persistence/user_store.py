from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from src.domain.entities import InteractionRecord, UserProfile


class UserStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._base_dir / "app.sqlite3"
        self._initialize()

    def load_profile(self, user_id: str) -> UserProfile:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT user_id, difficulty_level, total_interactions, correction_count,
                       grammar_count, talk_count, listen_count,
                       spelling_count, pronunciation_count, recent_errors, preferred_modes,
                       last_transcript, notes
                FROM profiles
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return UserProfile(user_id=user_id)
        return UserProfile(
            user_id=row["user_id"],
            difficulty_level=row["difficulty_level"],
            total_interactions=row["total_interactions"],
            correction_count=row["correction_count"],
            grammar_count=row["grammar_count"],
            talk_count=row["talk_count"],
            listen_count=row["listen_count"],
            spelling_count=row["spelling_count"],
            pronunciation_count=row["pronunciation_count"],
            recent_errors=_loads(row["recent_errors"], []),
            preferred_modes=_loads(row["preferred_modes"], {}),
            last_transcript=row["last_transcript"] or "",
            notes=_loads(row["notes"], []),
        )

    def save_profile(self, profile: UserProfile) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO profiles (
                    user_id, difficulty_level, total_interactions, correction_count,
                    grammar_count, talk_count, listen_count,
                    spelling_count, pronunciation_count, recent_errors, preferred_modes,
                    last_transcript, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    difficulty_level=excluded.difficulty_level,
                    total_interactions=excluded.total_interactions,
                    correction_count=excluded.correction_count,
                    grammar_count=excluded.grammar_count,
                    talk_count=excluded.talk_count,
                    listen_count=excluded.listen_count,
                    spelling_count=excluded.spelling_count,
                    pronunciation_count=excluded.pronunciation_count,
                    recent_errors=excluded.recent_errors,
                    preferred_modes=excluded.preferred_modes,
                    last_transcript=excluded.last_transcript,
                    notes=excluded.notes
                """,
                (
                    profile.user_id,
                    profile.difficulty_level,
                    profile.total_interactions,
                    profile.correction_count,
                    profile.grammar_count,
                    profile.talk_count,
                    profile.listen_count,
                    profile.spelling_count,
                    profile.pronunciation_count,
                    json.dumps(profile.recent_errors, ensure_ascii=True),
                    json.dumps(profile.preferred_modes, ensure_ascii=True),
                    profile.last_transcript,
                    json.dumps(profile.notes, ensure_ascii=True),
                ),
            )
            connection.commit()

    def load_interactions(self, user_id: str) -> list[InteractionRecord]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT user_id, source, original_input, selected_mode, final_text,
                       timestamp, difficulty_level, evaluation_score, errors
                FROM interactions
                WHERE user_id = ?
                ORDER BY id ASC
                """,
                (user_id,),
            ).fetchall()
        return [
            InteractionRecord(
                user_id=row["user_id"],
                source=row["source"],
                original_input=row["original_input"],
                selected_mode=row["selected_mode"],
                final_text=row["final_text"],
                timestamp=row["timestamp"],
                difficulty_level=row["difficulty_level"],
                evaluation_score=row["evaluation_score"],
                errors=_loads(row["errors"], []),
            )
            for row in rows
        ]

    def append_interaction(self, record: InteractionRecord) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO interactions (
                    user_id, source, original_input, selected_mode, final_text,
                    timestamp, difficulty_level, evaluation_score, errors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.user_id,
                    record.source,
                    record.original_input,
                    record.selected_mode,
                    record.final_text,
                    record.timestamp,
                    record.difficulty_level,
                    record.evaluation_score,
                    json.dumps(record.errors, ensure_ascii=True),
                ),
            )
            connection.commit()

    def save_session_summary(
        self,
        user_id: str,
        selected_mode: str,
        level: str,
        evaluation_score: float,
        next_focus: str,
        summary: str,
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO session_state (
                    user_id, selected_mode, level, evaluation_score, next_focus, summary
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    selected_mode=excluded.selected_mode,
                    level=excluded.level,
                    evaluation_score=excluded.evaluation_score,
                    next_focus=excluded.next_focus,
                    summary=excluded.summary,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user_id, selected_mode, level, evaluation_score, next_focus, summary),
            )
            connection.commit()

    def load_last_session(self, user_id: str) -> dict[str, object] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT selected_mode, level, evaluation_score, next_focus, summary, updated_at
                FROM session_state
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "selected_mode": row["selected_mode"],
            "level": row["level"],
            "evaluation_score": row["evaluation_score"],
            "next_focus": row["next_focus"],
            "summary": row["summary"],
            "updated_at": row["updated_at"],
        }

    def record_spelling_word(self, user_id: str, word: str, was_correct: bool) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO spelling_history (user_id, word, was_correct)
                VALUES (?, ?, ?)
                """,
                (user_id, word, 1 if was_correct else 0),
            )
            connection.commit()

    def load_spelling_history(self, user_id: str, limit: int = 20) -> list[dict[str, object]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT word, was_correct, used_at
                FROM spelling_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            {
                "word": row["word"],
                "was_correct": bool(row["was_correct"]),
                "used_at": row["used_at"],
            }
            for row in rows
        ]

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    difficulty_level TEXT NOT NULL,
                    total_interactions INTEGER NOT NULL,
                    correction_count INTEGER NOT NULL,
                    grammar_count INTEGER NOT NULL DEFAULT 0,
                    talk_count INTEGER NOT NULL DEFAULT 0,
                    listen_count INTEGER NOT NULL DEFAULT 0,
                    spelling_count INTEGER NOT NULL,
                    pronunciation_count INTEGER NOT NULL,
                    recent_errors TEXT NOT NULL,
                    preferred_modes TEXT NOT NULL,
                    last_transcript TEXT NOT NULL,
                    notes TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    original_input TEXT NOT NULL,
                    selected_mode TEXT NOT NULL,
                    final_text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    difficulty_level TEXT NOT NULL,
                    evaluation_score REAL NOT NULL,
                    errors TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS session_state (
                    user_id TEXT PRIMARY KEY,
                    selected_mode TEXT NOT NULL,
                    level TEXT NOT NULL,
                    evaluation_score REAL NOT NULL,
                    next_focus TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS spelling_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    word TEXT NOT NULL,
                    was_correct INTEGER NOT NULL,
                    used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_profile_columns(connection)
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_profile_columns(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute("PRAGMA table_info(profiles)").fetchall()
        existing_columns = {row["name"] for row in rows}
        for column_name in ("grammar_count", "talk_count", "listen_count"):
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE profiles ADD COLUMN {column_name} INTEGER NOT NULL DEFAULT 0"
                )


def _loads(raw: str, default):
    if not raw:
        return default
    return json.loads(raw)
