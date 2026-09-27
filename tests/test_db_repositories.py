"""Pruebas de repositorios SQLite (archivo temporal, modo WAL)."""

from __future__ import annotations

from pathlib import Path

from nutrimatch.db.connection import connect, init_db
from nutrimatch.db.repositories.event_log import EventLogRepository
from nutrimatch.db.repositories.profile import ProfileRepository
from nutrimatch.db.repositories.ranking_run import RankingRunRepository
from nutrimatch.schemas.profile import UserProfile
from nutrimatch.schemas.ranking import RankingRequest
from nutrimatch.services.ranking import RankingService
from tests.test_ranking_service import _catalogo_minimo


def test_perfil_roundtrip(tmp_path: Path) -> None:
    conexion = connect(tmp_path / "t.db")
    init_db(conexion)
    repo = ProfileRepository(conexion)
    assert repo.get() is None
    perfil = UserProfile(allergen_tags=["en:gluten"], diet="vegano", priority_order=["D2", "D1", "D3"])
    repo.save(perfil)
    leido = repo.get()
    assert leido is not None
    assert leido.allergen_tags == ["en:gluten"]
    assert leido.diet == "vegano"
    assert leido.priority_order == ["D2", "D1", "D3"]


def test_ranking_run_persiste_snapshot_y_version(tmp_path: Path) -> None:
    conexion = connect(tmp_path / "t.db")
    init_db(conexion)
    servicio = RankingService(_catalogo_minimo())
    perfil = UserProfile()
    resultado = servicio.rank(RankingRequest(profile=perfil, query="Pan", top_n=5))
    run_id = RankingRunRepository(conexion).save(resultado, perfil.model_dump_json())
    record = RankingRunRepository(conexion).get(run_id)
    assert record is not None
    assert record.snapshot_id == "test_snapshot"
    assert record.engine_version
    assert record.query == "Pan"
    EventLogRepository(conexion).append("ranking_run_created", {"ranking_run_id": run_id})
    n = conexion.execute("SELECT COUNT(*) AS n FROM event_log").fetchone()["n"]
    assert n == 1
    eventos = EventLogRepository(conexion).list(limit=10)
    assert eventos[0]["event_type"] == "ranking_run_created"
    assert eventos[0]["payload"]["ranking_run_id"] == run_id
    n_items = conexion.execute(
        "SELECT COUNT(*) AS n FROM ranking_run_item WHERE ranking_run_id = ?", (run_id,)
    ).fetchone()["n"]
    assert n_items >= 1
