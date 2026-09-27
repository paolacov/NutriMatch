"""SQLite WAL: esquema del estado mutable (perfil, ranking_run, event_log)."""

from __future__ import annotations

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    profile_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ranking_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    query TEXT NOT NULL DEFAULT '',
    n_ranking INTEGER NOT NULL,
    n_no_verificable INTEGER NOT NULL,
    n_informacion_insuficiente INTEGER NOT NULL,
    n_excluded INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ranking_run_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ranking_run_id INTEGER NOT NULL REFERENCES ranking_run(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    band TEXT NOT NULL,
    score REAL,
    rank INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
