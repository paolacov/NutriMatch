"""Catálogo operativo de 13 093 filas y contrato de precio.

El Parquet no guarda SYNTHETIC. La ficha lo emite. El ranking no se recalcula.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nutrimatch.api.app import create_app
from nutrimatch.core.config import Settings, get_settings
from nutrimatch.engine.compatibility_score import calcular_score_compatibilidad
from nutrimatch.engine.coverage import UMBRAL_COV_INFORMACION_INSUFICIENTE
from nutrimatch.engine.demo_price import precio_demostracion_mxn
from nutrimatch.engine.nutrition_score import NUTRIENTES_D1_SIGNO
from nutrimatch.engine.operational_dataset import aplicar_nombres_reales, unir_precios_reales
from nutrimatch.engine.processing_score import ANCHO_BANDA, FRACCION_AJUSTE_ADITIVOS_AUSENTES
from nutrimatch.engine.user_weights import PUNTOS_POR_POSICION
from nutrimatch.services.catalog import Catalog

REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATIVO = REPO_ROOT / "datos" / "procesados" / "dataset_referencia_20261002.parquet"
ORIGEN = REPO_ROOT / "datos" / "procesados" / "dataset_referencia_20260929.parquet"
N = 13_093
N_REAL = 259
N_OPEN = 239
N_QQP = 20
N_NOMBRES_API = 5
CODE_NOMBRE = "7501017660339"
CODE_FUERA = "7622210571328"


def test_formulas_de_ranking_siguen_iguales() -> None:
    assert NUTRIENTES_D1_SIGNO == {
        "sugars_100g": -1,
        "salt_100g": -1,
        "saturated-fat_100g": -1,
        "fiber_100g": 1,
        "proteins_100g": 1,
    }
    assert PUNTOS_POR_POSICION == (3, 2, 1)
    assert UMBRAL_COV_INFORMACION_INSUFICIENTE == 0.5
    assert ANCHO_BANDA == 25.0
    assert FRACCION_AJUSTE_ADITIVOS_AUSENTES == 0.5
    score = calcular_score_compatibilidad(
        {"D1": 80.0, "D2": 50.0, "D3": None},
        {"D1": 0.5, "D2": 1 / 3, "D3": 1 / 6},
    )
    assert score["informacion_insuficiente"] is False
    assert score["score_final"] == pytest.approx((0.5 * 80 + (1 / 3) * 50) / (0.5 + 1 / 3))


def test_unir_precios_no_inventa_real_ni_trata_qqp_como_gtin() -> None:
    base = pd.DataFrame({"code": ["75000001", "75000002"], "product_name": ["A", "B"]})
    observaciones = pd.DataFrame(
        [
            {
                "code": "75000001",
                "field": "price",
                "value": "18.5",
                "status": "REAL",
                "source": "qqp_profeco",
                "source_url": "https://ejemplo",
                "retrieved_at": "2026-07-01",
                "snapshot_id": "off_csv_20260919",
                "method": "text_reviewed",
                "confidence": 0.8,
                "quality_flag": None,
            },
            {
                "code": "999",
                "field": "price",
                "value": "9",
                "status": "REAL",
                "source": "open_prices",
                "source_url": None,
                "retrieved_at": "2026-07-01",
                "snapshot_id": "off_csv_20260919",
                "method": "exact_gtin",
                "confidence": None,
                "quality_flag": None,
            },
        ]
    )
    salida = unir_precios_reales(base, observaciones)
    assert list(salida["price_status"]) == ["REAL", "UNAVAILABLE"]
    assert salida.loc[0, "price_source"] == "qqp_profeco"
    assert salida.loc[0, "price_match_method"] == "text_reviewed"
    assert salida.loc[0, "price_confidence"] == pytest.approx(0.8)
    assert pd.isna(salida.loc[1, "price"])
    assert int((salida["price_status"] == "SYNTHETIC").sum()) == 0


def test_nombres_reales_solo_pisan_el_codigo_observado() -> None:
    base = pd.DataFrame(
        {
            "code": ["7501017660339", "75000002"],
            "product_name": [None, "Leche"],
            "product_name_homologated": [None, "Leche"],
            "product_name_status": ["UNAVAILABLE", "DERIVED"],
            "product_name_field_source": [None, "product_name"],
        }
    )
    observaciones = pd.DataFrame(
        [
            {
                "code": "7501017660339",
                "field": "product_name",
                "value": "horchata el yucateco",
                "status": "REAL",
                "source": "openfoodfacts_api_producto",
                "source_url": None,
                "retrieved_at": "2026-09-26",
                "snapshot_id": "off_csv_20260919",
                "method": "api_producto_individual",
                "confidence": None,
                "quality_flag": None,
            }
        ]
    )
    salida = aplicar_nombres_reales(base, observaciones)
    assert salida.loc[0, "product_name"] == "horchata el yucateco"
    assert salida.loc[0, "product_name_status"] == "REAL"
    assert salida.loc[0, "product_name_source"] == "openfoodfacts_api_producto"
    assert salida.loc[1, "product_name"] == "Leche"
    assert salida.loc[1, "product_name_source"] == "off_export"


@pytest.fixture(scope="module")
def operativo():
    if not OPERATIVO.exists():
        pytest.skip("falta el catálogo operativo")
    return duckdb.connect().execute(
        f"SELECT * FROM read_parquet('{OPERATIVO.as_posix()}')"
    ).df()


def test_parquet_operativo_tiene_universo_precios_y_nombres(operativo: pd.DataFrame) -> None:
    assert len(operativo) == N
    assert operativo["code"].nunique() == N
    assert int((operativo["price_status"] == "REAL").sum()) == N_REAL
    assert int((operativo["price_status"] == "UNAVAILABLE").sum()) == N - N_REAL
    assert int((operativo["price_status"] == "SYNTHETIC").sum()) == 0
    reales = operativo.loc[operativo["price_status"] == "REAL"]
    assert int((reales["price_source"] == "open_prices").sum()) == N_OPEN
    assert set(reales.loc[reales["price_source"] == "open_prices", "price_match_method"]) == {"exact_gtin"}
    assert int((reales["price_source"] == "qqp_profeco").sum()) == N_QQP
    assert set(reales.loc[reales["price_source"] == "qqp_profeco", "price_match_method"]) == {"text_reviewed"}
    assert reales["price"].notna().all()
    assert operativo.loc[operativo["price_status"] == "UNAVAILABLE", "price"].isna().all()
    assert int((operativo["product_name_source"] == "openfoodfacts_api_producto").sum()) == N_NOMBRES_API
    fila = operativo.loc[operativo["code"].astype(str) == CODE_NOMBRE].iloc[0]
    assert fila["product_name"] == "horchata el yucateco"
    assert fila["product_name_status"] == "REAL"
    assert CODE_FUERA not in set(operativo["code"].astype(str))
    assert operativo["data_quality_score"].notna().all()
    assert set(operativo["data_quality_level"]) <= {"insuficiente", "baja", "media", "alta"}
    for col in ("d1", "d3", "cov", "score_final"):
        assert col not in operativo.columns


def test_columnas_de_ranking_iguales_al_origen_20260929() -> None:
    if not OPERATIVO.exists() or not ORIGEN.exists():
        pytest.skip("faltan parquets")
    diff = duckdb.connect().execute(
        f"""
        SELECT count(*) FROM read_parquet('{OPERATIVO.as_posix()}') a
        JOIN read_parquet('{ORIGEN.as_posix()}') b USING (code)
        WHERE a.d2 IS DISTINCT FROM b.d2
           OR a.universo_puntuable IS DISTINCT FROM b.universo_puntuable
           OR a.percentil_sugars_100g IS DISTINCT FROM b.percentil_sugars_100g
        """
    ).fetchone()
    assert diff is not None
    assert diff[0] == 0


def test_api_operativa_emite_real_y_demostracion(tmp_path: Path) -> None:
    if not OPERATIVO.exists():
        pytest.skip("falta el catálogo operativo")
    get_settings.cache_clear()
    settings = Settings(
        referencia_filename=OPERATIVO.name,
        snapshot_id="off_csv_20260929",
        _env_file=None,
    )
    assert Settings(_env_file=None).referencia_filename == OPERATIVO.name
    catalogo = Catalog.from_referencia(settings)
    assert len(catalogo.df) == N
    assert catalogo.n_puntuable() == 5_864
    cliente = TestClient(create_app(catalog=catalogo, db_path=tmp_path / "op.db"))
    meta = cliente.get("/meta").json()
    assert meta["n_products"] == N
    assert meta["snapshot_id"] == "off_csv_20260929"
    assert meta["n_puntuable"] == 5_864

    real_code = str(catalogo.df.loc[catalogo.df["price_status"] == "REAL", "code"].iloc[0])
    demo_code = str(catalogo.df.loc[catalogo.df["price_status"] == "UNAVAILABLE", "code"].iloc[0])
    real = cliente.get(f"/products/{real_code}").json()
    assert real["price"]["status"] == "REAL"
    assert real["price"]["source"] in {"open_prices", "qqp_profeco"}
    assert real["price"]["value"] not in (None, 0)
    if real["data_quality_score"] is not None:
        assert real["data_quality_level"] in {"insuficiente", "baja", "media", "alta"}

    demo = cliente.get(f"/products/{demo_code}").json()
    assert demo["price"]["status"] == "SYNTHETIC"
    assert demo["price"]["source"] == "demo"
    assert demo["price"]["value"] == float(precio_demostracion_mxn(demo_code))

    perfil = {
        "allergen_tags": [],
        "diet": None,
        "valued_labels": [],
        "priority_order": ["D1", "D2", "D3"],
    }
    explicado = cliente.post("/ranking/explain", json={"code": demo_code, "profile": perfil}).json()
    assert set(explicado["explanation"]["dimensions"]) == {"D1", "D2", "D3"}
    ranking = cliente.post(
        "/ranking",
        json={"profile": perfil, "query": demo_code, "top_n": 3},
    )
    assert ranking.status_code == 200
    assert ranking.json()["n_matched"] == 1
