"""Repositorio de `ranking_run`: traza de una consulta (no forma parte del score)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from nutrimatch.schemas.ranking import RankingResult


@dataclass(frozen=True)
class RankingRunRecord:
    id: int
    snapshot_id: str
    engine_version: str
    query: str
    n_ranking: int
    n_no_verificable: int
    n_informacion_insuficiente: int
    n_excluded: int
    created_at: str


class RankingRunRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def save(self, resultado: RankingResult, profile_json: str) -> int:
        ahora = datetime.now(UTC).isoformat()
        cursor = self.conexion.execute(
            """
            INSERT INTO ranking_run (
                snapshot_id, engine_version, profile_json, query,
                n_ranking, n_no_verificable, n_informacion_insuficiente, n_excluded,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resultado.snapshot_id,
                resultado.engine_version,
                profile_json,
                resultado.query,
                resultado.ranking.total,
                resultado.no_verificable.total,
                resultado.informacion_insuficiente.total,
                resultado.excluded_count,
                ahora,
            ),
        )
        run_id = int(cursor.lastrowid)
        filas = []
        for banda, slice_ in (
            ("ranking", resultado.ranking),
            ("no_verificable", resultado.no_verificable),
            ("informacion_insuficiente", resultado.informacion_insuficiente),
        ):
            for item in slice_.items:
                filas.append((run_id, item.code, banda, item.score, item.rank or 0))
        self.conexion.executemany(
            """
            INSERT INTO ranking_run_item (ranking_run_id, code, band, score, rank)
            VALUES (?, ?, ?, ?, ?)
            """,
            filas,
        )
        self.conexion.commit()
        return run_id

    def get(self, run_id: int) -> RankingRunRecord | None:
        fila = self.conexion.execute(
            """
            SELECT id, snapshot_id, engine_version, query,
                   n_ranking, n_no_verificable, n_informacion_insuficiente, n_excluded,
                   created_at
            FROM ranking_run WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
        if fila is None:
            return None
        return RankingRunRecord(
            id=fila["id"],
            snapshot_id=fila["snapshot_id"],
            engine_version=fila["engine_version"],
            query=fila["query"],
            n_ranking=fila["n_ranking"],
            n_no_verificable=fila["n_no_verificable"],
            n_informacion_insuficiente=fila["n_informacion_insuficiente"],
            n_excluded=fila["n_excluded"],
            created_at=fila["created_at"],
        )
