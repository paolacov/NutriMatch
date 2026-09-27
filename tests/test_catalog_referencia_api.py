"""Regresión del recableado API → dataset_referencia_20260927.parquet.

Carga el Parquet real. No toca fórmulas: comprueba conteos ya publicados y el contrato HTTP.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from nutrimatch.api.app import create_app
from nutrimatch.core.config import Settings, get_settings
from nutrimatch.services.catalog import Catalog

REPO_ROOT = Path(__file__).resolve().parents[1]
N = 16_851
N_PUNTUABLE = 5_864
N_PRICE_REAL = 263

CODE_PRECIO_REAL = "0074323081411"  # Cajeta, QQP, puntuable
CODE_PUNTUABLE = "0003800001921"  # Pop tarts, Open Prices, puntuable
CODE_NO_PUNTUABLE = "00000140"  # tisane, sin precio, sin nutrición útil
CODE_SIN_NOMBRE = "00000285"

COLUMNAS_API = (
    "code",
    "product_name",
    "product_name_homologated",
    "brands",
    "brand_original",
    "labels_tags",
    "allergens",
    "traces",
    "ingredients_analysis_tags",
    "ingredients_text",
    "d2",
    "universo_puntuable",
    "nova_group",
    "additives_n",
    "price",
    "price_status",
    "price_source",
    "main_category",
    "categoria_referencia",
    "percentil_proteins_100g",
    "percentil_sugars_100g",
    "data_quality_score",
    "data_quality_level",
    "data_quality_detalle",
)

ANA = {
    "profile": {
        "allergen_tags": [],
        "diet": None,
        "valued_labels": ["en:organic", "en:no-gluten"],
        "priority_order": ["D1", "D3", "D2"],
    },
    "query": "",
    "top_n": 3,
}
CARO = {
    "profile": {
        "allergen_tags": [],
        "diet": None,
        "valued_labels": [],
        "priority_order": ["D3", "D1", "D2"],
    },
    "query": "",
    "top_n": 3,
}


@pytest.fixture(scope="module")
def settings_api() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="module")
def parquet_crudo(settings_api: Settings):
    ruta = settings_api.referencia_parquet()
    assert ruta.name == "dataset_referencia_20260927.parquet"
    assert ruta.exists()
    return duckdb.connect().execute(f"SELECT * FROM read_parquet('{ruta.as_posix()}')").df()


@pytest.fixture(scope="module")
def catalogo(settings_api: Settings) -> Catalog:
    return Catalog.from_referencia(settings_api)


@pytest.fixture(scope="module")
def cliente(catalogo: Catalog, tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    db = tmp_path_factory.mktemp("ref_api") / "api.db"
    return TestClient(create_app(catalog=catalogo, db_path=db))


def test_config_apunta_al_20260927(settings_api: Settings) -> None:
    assert settings_api.referencia_filename == "dataset_referencia_20260927.parquet"
    assert settings_api.referencia_parquet() == REPO_ROOT / "datos" / "procesados" / "dataset_referencia_20260927.parquet"


def test_parquet_universo_y_calidad(parquet_crudo) -> None:
    assert len(parquet_crudo) == N
    assert parquet_crudo["code"].nunique() == N
    assert int(len(parquet_crudo) - parquet_crudo["code"].nunique()) == 0
    assert int(parquet_crudo["universo_puntuable"].sum()) == N_PUNTUABLE
    for col in COLUMNAS_API:
        assert col in parquet_crudo.columns, col
    for col in ("d1", "d3", "cov", "score_final"):
        assert col not in parquet_crudo.columns
    assert int((parquet_crudo["price_status"] == "REAL").sum()) == N_PRICE_REAL
    assert int((parquet_crudo["price_status"] == "SYNTHETIC").sum()) == 0
    assert int((parquet_crudo["price_status"] == "UNAVAILABLE").sum()) == N - N_PRICE_REAL
    reales = parquet_crudo.loc[parquet_crudo["price_status"] == "REAL", "price"]
    assert reales.notna().all()
    assert (parquet_crudo["price_status"] == "UNAVAILABLE").equals(parquet_crudo["price"].isna())


def test_catalogo_calcula_d1_en_runtime_sin_materializar_d3_cov_score(catalogo: Catalog) -> None:
    assert len(catalogo.df) == N
    assert "d1" in catalogo.df.columns
    assert int(catalogo.df["d1"].notna().sum()) == 7_040
    assert int(catalogo.n_puntuable()) == N_PUNTUABLE
    assert "d3" not in catalogo.df.columns
    assert "cov" not in catalogo.df.columns
    assert "score_final" not in catalogo.df.columns


def test_meta_y_ficha_por_gtin(cliente: TestClient) -> None:
    meta = cliente.get("/meta").json()
    assert meta["n_products"] == N
    assert meta["n_puntuable"] == N_PUNTUABLE

    cajeta = cliente.get(f"/products/{CODE_PRECIO_REAL}").json()
    assert cajeta["code"] == CODE_PRECIO_REAL
    assert cajeta["name"]["value"]
    assert cajeta["price"]["status"] == "REAL"
    assert cajeta["price"]["value"] is not None
    assert cajeta["price"]["source"] == "qqp_profeco"

    pop = cliente.get(f"/products/{CODE_PUNTUABLE}").json()
    assert pop["price"]["status"] == "REAL"
    assert pop["price"]["source"] == "open_prices"

    tisane = cliente.get(f"/products/{CODE_NO_PUNTUABLE}").json()
    assert tisane["price"]["status"] == "UNAVAILABLE"
    assert tisane["price"]["value"] is None
    assert any(n["per100g"] is None for n in tisane["nutrients"])

    sin_nombre = cliente.get(f"/products/{CODE_SIN_NOMBRE}").json()
    assert sin_nombre["name"]["value"] is None
    assert sin_nombre["name"]["status"] == "UNAVAILABLE"
    assert sin_nombre["price"]["value"] is None


def test_busqueda_por_nombre(cliente: TestClient) -> None:
    hits = cliente.get("/search", params={"q": "Cajeta", "limit": 20}).json()
    codes = [p["code"] for p in hits]
    assert CODE_PRECIO_REAL in codes
    assert all(p["name"]["value"] for p in hits)


def test_ranking_ana_y_caro_mismas_bandas(cliente: TestClient) -> None:
    ana = cliente.post("/ranking", json=ANA).json()
    assert ana["n_matched"] == N
    assert ana["informacion_insuficiente"]["total"] == 9_517
    assert ana["ranking"]["total"] == 7_334
    assert ana["excluded_count"] == 0
    item = ana["ranking"]["items"][0]
    assert item["explanation"] is not None
    assert "cov" in item["explanation"]
    assert "score" in item["explanation"]
    assert item["d1"] is not None or item["d2"] is not None or item["d3"] is not None

    caro = cliente.post("/ranking", json=CARO).json()
    assert caro["n_matched"] == N
    assert caro["informacion_insuficiente"]["total"] == 10_974
    assert caro["ranking"]["total"] == 5_877
    assert caro["ranking"]["items"][0]["d3"] is None


def test_explain_runtime_d3_cov_score(cliente: TestClient, catalogo: Catalog) -> None:
    perfil = ANA["profile"]
    puntuable = cliente.post(
        "/ranking/explain",
        json={"code": CODE_PUNTUABLE, "profile": perfil},
    ).json()
    assert puntuable["explanation"]["cov"] is not None
    assert "score" in puntuable["explanation"]
    assert catalogo.df.loc[catalogo.df["code"] == CODE_PUNTUABLE, "universo_puntuable"].iloc[0]

    hueco = cliente.post(
        "/ranking/explain",
        json={"code": CODE_NO_PUNTUABLE, "profile": perfil},
    ).json()
    # No es universo_puntuable (0 percentiles) pero D2+D3 de Ana pueden dar score (A26).
    assert hueco["d1"] is None
    assert hueco["d2"] is not None
    assert hueco["explanation"]["cov"] is not None
    assert "score" in hueco["explanation"]
    assert not catalogo.df.loc[catalogo.df["code"] == CODE_NO_PUNTUABLE, "universo_puntuable"].iloc[0]

    sin_dato = cliente.post(
        "/ranking/explain",
        json={"code": CODE_SIN_NOMBRE, "profile": perfil},
    ).json()
    assert sin_dato["d1"] is None
    assert sin_dato["d2"] is None
    assert sin_dato["explanation"]["score"] is None
    assert sin_dato["explanation"]["cov"] < 0.5
