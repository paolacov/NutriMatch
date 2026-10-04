"""Prueba de humo contra el snapshot real versionado (mismo patrón que el golden set)."""

from __future__ import annotations

import pytest

from nutrimatch.core.config import get_settings
from nutrimatch.schemas.profile import UserProfile
from nutrimatch.schemas.ranking import RankingRequest
from nutrimatch.services.catalog import Catalog
from nutrimatch.services.ranking import RankingService

_PARQUETS_OK = get_settings().matriz_parquet().exists() and get_settings().snapshot_parquet().exists()


@pytest.fixture(scope="module")
def servicio_real() -> RankingService:
    return RankingService(Catalog.from_parquet())


@pytest.mark.skipif(not _PARQUETS_OK, reason="Requiere datos/procesados/*.parquet")
def test_gluten_confirmado_queda_excluido_en_snapshot_real(servicio_real: RankingService) -> None:
    item = servicio_real.explain("0000654193184", UserProfile(allergen_tags=["en:gluten"]))
    assert item.allergy_status == "no_apto"
    assert item.band == "excluido"


@pytest.mark.skipif(not _PARQUETS_OK, reason="Requiere datos/procesados/*.parquet")
def test_busqueda_por_code_real(servicio_real: RankingService) -> None:
    resultado = servicio_real.rank(
        RankingRequest(profile=UserProfile(), query="7501030457626", top_n=5)
    )
    assert resultado.n_matched == 1
    item = servicio_real.explain("7501030457626", UserProfile())
    assert item.product_name
    assert "centeno" in item.product_name.lower()
