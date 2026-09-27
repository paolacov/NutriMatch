"""Conexión SQLite en modo WAL: único acceso a la base de estado mutable."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from nutrimatch.core.config import Settings, get_settings
from nutrimatch.db.schema import SCHEMA_SQL


def connect(db_path: Path | None = None, settings: Settings | None = None) -> sqlite3.Connection:
    settings = settings or get_settings()
    ruta = db_path if db_path is not None else settings.db_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta, check_same_thread=False)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA journal_mode=WAL")
    conexion.execute("PRAGMA foreign_keys=ON")
    return conexion


def init_db(conexion: sqlite3.Connection) -> None:
    conexion.executescript(SCHEMA_SQL)
    conexion.commit()
