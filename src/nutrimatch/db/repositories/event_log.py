"""Repositorio del `event_log`: trazas de uso, no puntúan (A11)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any


class EventLogRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def append(self, event_type: str, payload: dict[str, Any]) -> None:
        ahora = datetime.now(UTC).isoformat()
        self.conexion.execute(
            "INSERT INTO event_log (event_type, payload_json, created_at) VALUES (?, ?, ?)",
            (event_type, json.dumps(payload, ensure_ascii=False), ahora),
        )
        self.conexion.commit()

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        filas = self.conexion.execute(
            """
            SELECT id, event_type, payload_json, created_at
            FROM event_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "id": fila["id"],
                "event_type": fila["event_type"],
                "payload": json.loads(fila["payload_json"]),
                "created_at": fila["created_at"],
            }
            for fila in filas
        ]
