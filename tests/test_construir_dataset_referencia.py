"""Pruebas de scripts/construir_dataset_referencia.py (paso 9, decisión A43).

Usa fixtures sintéticas: no lee los Parquets de 16.851 filas. Cubre la regla de resolución
(F.2), el relleno UNAVAILABLE (A2) y que las columnas de OFF no se renombran al unir con
la matriz (colisión `nova_group`/`additives_n`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from construir_dataset_referencia import (
    _asegurar_sin_colision_de_columnas,
    aplicar_nombres_homologados,
    construir_dataset_referencia,
    construir_tabla_observaciones,
)

from nutrimatch.engine.observations import resolver_observaciones


def _off_sintetico() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"code": "0074323081411", "product_name": "Cajeta", "brands": "Coronado", "nova_group": "4", "additives_n": "2"},
            {"code": "7501300801197", "product_name": "Yogurt", "brands": "Lala", "nova_group": "3", "additives_n": "0"},
            {"code": "0000000000001", "product_name": None, "brands": None, "nova_group": None, "additives_n": None},
            {"code": "7622210571328", "product_name": None, "brands": None, "nova_group": None, "additives_n": None},
        ]
    )


def _identidad_sintetica() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "code": "0074323081411",
                "product_name_homologated": "Cajeta",
                "product_name_status": "DERIVED",
                "brand_homologated": "coronado",
                "brand_status": "DERIVED",
                "snapshot_id": "off_csv_20260919",
                "generated_at": "2026-09-26T00:00:00+00:00",
            },
            {
                "code": "7501300801197",
                "product_name_homologated": "Yogurt",
                "product_name_status": "DERIVED",
                "brand_homologated": "lala",
                "brand_status": "DERIVED",
                "snapshot_id": "off_csv_20260919",
                "generated_at": "2026-09-26T00:00:00+00:00",
            },
            {
                "code": "0000000000001",
                "product_name_homologated": None,
                "product_name_status": "UNAVAILABLE",
                "brand_homologated": None,
                "brand_status": "UNAVAILABLE",
                "snapshot_id": "off_csv_20260919",
                "generated_at": "2026-09-26T00:00:00+00:00",
            },
            {
                "code": "7622210571328",
                "product_name_homologated": None,
                "product_name_status": "UNAVAILABLE",
                "brand_homologated": None,
                "brand_status": "UNAVAILABLE",
                "snapshot_id": "off_csv_20260919",
                "generated_at": "2026-09-26T00:00:00+00:00",
            },
        ]
    )


def _matriz_sintetica() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"code": "0074323081411", "snapshot_id": "off_csv_20260919", "nova_group": "4", "additives_n": "2", "d2": 12.5, "universo_puntuable": True},
            {"code": "7501300801197", "snapshot_id": "off_csv_20260919", "nova_group": "3", "additives_n": "0", "d2": 50.0, "universo_puntuable": True},
            {"code": "0000000000001", "snapshot_id": "off_csv_20260919", "nova_group": None, "additives_n": None, "d2": None, "universo_puntuable": False},
            {"code": "7622210571328", "snapshot_id": "off_csv_20260919", "nova_group": None, "additives_n": None, "d2": None, "universo_puntuable": False},
        ]
    )


def _precio(code: str, source: str, price: float, method: str, confidence) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "code": code,
                "price": price,
                "price_status": "REAL",
                "source": source,
                "source_url": f"https://ejemplo.test/{source}",
                "retrieved_at": "2026-09-26T20:00:00+00:00",
                "match_method": method,
                "match_confidence": confidence,
            }
        ]
    )


def _experimento_hit() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "code": "7622210571328",
                "es_hit": True,
                "nombre_recuperado": "Trident XtraCare yerbabuena",
                "status_valor": "REAL",
                "source": "openfoodfacts_api_producto",
                "source_url": "https://world.openfoodfacts.org/api/v2/product/7622210571328.json",
                "retrieved_at": "2026-09-26T23:41:02+00:00",
            }
        ]
    )


def _ensamblar() -> pd.DataFrame:
    observaciones = construir_tabla_observaciones(
        _experimento_hit(),
        _precio("7501300801197", "open_prices", 25.0, "exact_gtin", None),
        _precio("0074323081411", "qqp_profeco", 115.0, "text_reviewed", 0.9),
    )
    return construir_dataset_referencia(
        _off_sintetico(),
        _identidad_sintetica(),
        _matriz_sintetica(),
        resolver_observaciones(observaciones),
    )


def test_una_fila_por_code_sin_duplicados():
    resultado = _ensamblar()
    assert len(resultado) == 4
    assert resultado["code"].nunique() == 4


def test_columnas_de_off_no_se_renombran():
    resultado = _ensamblar()
    for columna in ("product_name", "brands", "nova_group", "additives_n"):
        assert columna in resultado.columns
        assert f"{columna}_x" not in resultado.columns
        assert f"{columna}_y" not in resultado.columns
    assert resultado.loc[resultado["code"] == "0074323081411", "product_name"].iloc[0] == "Cajeta"
    assert resultado.loc[resultado["code"] == "0074323081411", "nova_group"].iloc[0] == "4"


def test_precio_qqp_queda_real_con_metodo_text_reviewed():
    fila = _ensamblar().set_index("code").loc["0074323081411"]
    assert fila["price"] == "115.0"
    assert fila["price_status"] == "REAL"
    assert fila["price_source"] == "qqp_profeco"
    assert fila["price_match_method"] == "text_reviewed"
    assert fila["price_match_confidence"] == 0.9


def test_precio_open_prices_queda_real_con_metodo_exact_gtin():
    fila = _ensamblar().set_index("code").loc["7501300801197"]
    assert fila["price"] == "25.0"
    assert fila["price_status"] == "REAL"
    assert fila["price_source"] == "open_prices"
    assert fila["price_match_method"] == "exact_gtin"


def test_sin_observacion_de_precio_es_unavailable_nunca_cero():
    fila = _ensamblar().set_index("code").loc["0000000000001"]
    assert fila["price_status"] == "UNAVAILABLE"
    assert pd.isna(fila["price"]) or fila["price"] is None


def test_nombre_recuperado_por_api_pisa_unavailable_y_marca_source():
    fila = _ensamblar().set_index("code").loc["7622210571328"]
    assert fila["product_name_homologated"] == "Trident XtraCare yerbabuena"
    assert fila["product_name"] == "Trident XtraCare yerbabuena"
    assert fila["product_name_crudo"] is None or pd.isna(fila["product_name_crudo"])
    assert fila["product_name_status"] == "REAL"
    assert fila["product_name_source"] == "openfoodfacts_api_producto"


def test_nombre_sin_recuperacion_sigue_off_export():
    fila = _ensamblar().set_index("code").loc["0074323081411"]
    assert fila["product_name_homologated"] == "Cajeta"
    assert fila["product_name_status"] == "DERIVED"
    assert fila["product_name_source"] == "off_export"


def test_left_join_duckdb_pisa_product_name_y_conserva_crudo(tmp_path: Path) -> None:
    catalogo = tmp_path / "catalogo.parquet"
    identidad = tmp_path / "identidad.parquet"
    salida = tmp_path / "salida.parquet"
    pd.DataFrame(
        {
            "code": ["7501293300110", "0000000000001"],
            "product_name": ["PROVI  Surtido Carnaval", "Leche"],
            "brands": ["Provi", "Lala"],
        }
    ).to_parquet(catalogo, index=False)
    pd.DataFrame(
        {
            "code": ["7501293300110"],
            "product_name_homologated": ["PROVI Surtido Carnaval"],
            "product_name_status": ["DERIVED"],
            "product_name_field_source": ["product_name"],
            "product_name_flag_respaldo_usado": [False],
            "product_name_flag_placeholder_removido": [False],
            "product_name_original": ["PROVI  Surtido Carnaval"],
            "brand_original": ["Provi"],
            "brand_homologated": ["provi"],
            "brand_status": ["DERIVED"],
        }
    ).to_parquet(identidad, index=False)

    aplicar_nombres_homologados(catalogo, identidad, salida)
    resultado = pd.read_parquet(salida).set_index("code")
    assert len(resultado) == 2
    assert resultado.loc["7501293300110", "product_name"] == "PROVI Surtido Carnaval"
    assert resultado.loc["7501293300110", "product_name_crudo"] == "PROVI  Surtido Carnaval"
    assert resultado.loc["7501293300110", "brands"] == "Provi"
    assert resultado.loc["0000000000001", "product_name"] == "Leche"
    assert pd.isna(resultado.loc["0000000000001", "product_name_homologated"])


def test_colision_de_columnas_falla_ruidosamente():
    izquierda = pd.DataFrame({"code": ["1"], "nova_group": ["4"]})
    derecha = pd.DataFrame({"code": ["1"], "nova_group": ["4"]})
    with pytest.raises(ValueError, match="Colisión de columnas"):
        _asegurar_sin_colision_de_columnas(izquierda, derecha, "off", "matriz")
