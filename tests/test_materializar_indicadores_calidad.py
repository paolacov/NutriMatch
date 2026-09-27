"""Pruebas del script que versiona el Parquet de referencia con calidad DERIVED."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

from nutrimatch.engine.constants import CORE8_NUTRIENTES
from nutrimatch.engine.data_quality import COLUMNAS_CALIDAD

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from materializar_indicadores_calidad import validar_antes_despues


def _frame_minimo() -> pd.DataFrame:
    fila = {
        "code": "0074323081411",
        "proteins_100g": 0.0,
        "ingredients_text": "leche",
        "labels_tags": None,
        "nova_group": "3",
        "additives_n": 0,
        "categoria_referencia": "en:milks",
        "n_percentiles_validos": 4,
        "universo_puntuable": True,
        "d2": 40.0,
        "price": None,
        "price_status": "UNAVAILABLE",
        "price_source": None,
        "flag_suma_macros_excede_100": False,
        "percentil_sugars_100g": 10.0,
        "percentil_salt_100g": None,
        "percentil_saturated-fat_100g": None,
        "percentil_fiber_100g": None,
        "percentil_proteins_100g": 20.0,
    }
    for nutriente in CORE8_NUTRIENTES:
        fila[f"{nutriente}_flag_fuera_de_rango"] = False
    return pd.DataFrame([fila])


def test_validar_acepta_solo_columnas_de_calidad():
    from nutrimatch.engine.data_quality import anexar_indicadores_calidad

    origen = _frame_minimo()
    destino = anexar_indicadores_calidad(origen)
    reporte = validar_antes_despues(origen, destino)
    assert reporte["ok"].all()
    assert set(COLUMNAS_CALIDAD) <= set(destino.columns)
    assert "protein_g" not in destino.columns
    assert destino["proteins_100g"].iloc[0] == 0.0


def test_validar_no_confunde_nombre_literal_nan_con_nulo():
    from nutrimatch.engine.data_quality import anexar_indicadores_calidad

    origen = _frame_minimo()
    origen = origen.copy()
    origen["product_name"] = "NAN"
    destino = anexar_indicadores_calidad(origen)
    reporte = validar_antes_despues(origen, destino)
    assert reporte["ok"].all()
    assert destino["product_name"].iloc[0] == "NAN"


def test_validar_detecta_alteracion_de_una_columna_original():
    from nutrimatch.engine.data_quality import anexar_indicadores_calidad

    origen = _frame_minimo()
    destino = anexar_indicadores_calidad(origen)
    destino = destino.copy()
    destino.loc[0, "proteins_100g"] = 8.0
    try:
        validar_antes_despues(origen, destino)
    except ValueError as exc:
        assert "columnas_existentes_alteradas" in str(exc)
    else:
        raise AssertionError("debía fallar al alterar proteins_100g")
