"""Repositorio del perfil local (una sola fila, id=1: el MVP no tiene autenticación)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from nutrimatch.schemas.profile import UserProfile


class ProfileRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def get(self) -> UserProfile | None:
        fila = self.conexion.execute("SELECT profile_json FROM user_profile WHERE id = 1").fetchone()
        if fila is None:
            return None
        return UserProfile.model_validate_json(fila["profile_json"])

    def save(self, profile: UserProfile) -> None:
        ahora = datetime.now(UTC).isoformat()
        payload = profile.model_dump_json()
        self.conexion.execute(
            """
            INSERT INTO user_profile (id, profile_json, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET profile_json = excluded.profile_json,
                                          updated_at = excluded.updated_at
            """,
            (payload, ahora),
        )
        self.conexion.commit()
