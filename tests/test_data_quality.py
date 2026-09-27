"""Pruebas de indicadores DERIVED de calidad (no puntúan, no imputan)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from nutrimatch.engine.constants import CORE8_NUTRIENTES
from nutrimatch.engine.data_quality import (
    COLUMNAS_CALIDAD,
    FLAGS_FUERA_DE_RANGO,
    anexar_indicadores_calidad,
    calcular_indicadores_calidad_fila,
)


def _fila_base(**overrides):
    fila = {
        "n_percentiles_validos": 0,
        "ingredients_text": None,
        "categoria_referencia": None,
        "nova_group": None,
        "additives_n": None,
        "labels_tags": None,
        "flag_suma_macros_excede_100": False,
    }
    for nutriente in CORE8_NUTRIENTES:
        fila[f"{nutriente}_flag_fuera_de_rango"] = False
    fila.update(overrides)
    return fila


def test_registro_completo_es_alta_y_score_uno():
    fila = _fila_base(
        n_percentiles_validos=8,
        ingredients_text="agua, sal",
        categoria_referencia="en:milks",
        nova_group="1",
        additives_n=0,
        labels_tags="en:organic",
    )
    out = calcular_indicadores_calidad_fila(fila)
    assert out["data_quality_score"] == 1.0
    assert out["data_quality_level"] == "alta"
    assert "nutrition:1.0000" in out["data_quality_detalle"]
    assert "additives:1.0000" in out["data_quality_detalle"]


def test_cero_de_aditivos_es_dato_presente_no_nulo():
    fila = _fila_base(additives_n=0)
    out = calcular_indicadores_calidad_fila(fila)
    assert "additives:1.0000" in out["data_quality_detalle"]


def test_nan_de_pandas_en_ingredientes_es_ausencia(b13=True):
    fila = _fila_base(ingredients_text=math.nan)
    out = calcular_indicadores_calidad_fila(fila)
    assert "ingredients:0.0000" in out["data_quality_detalle"]


def test_sin_dato_salvo_consistencia_es_insuficiente():
    out = calcular_indicadores_calidad_fila(_fila_base())
    assert out["data_quality_score"] == pytest.approx(1 / 7)
    assert out["data_quality_level"] == "insuficiente"


def test_flag_fuera_de_rango_baja_solo_consistencia():
    completo = _fila_base(
        n_percentiles_validos=8,
        ingredients_text="maíz",
        categoria_referencia="en:crisps",
        nova_group="4",
        additives_n=3,
        labels_tags="en:no-gluten",
    )
    sucio = dict(completo)
    sucio["energy-kcal_100g_flag_fuera_de_rango"] = True
    limpio = calcular_indicadores_calidad_fila(completo)
    marcado = calcular_indicadores_calidad_fila(sucio)
    assert limpio["data_quality_score"] == 1.0
    assert marcado["data_quality_score"] == pytest.approx(6 / 7)
    assert "consistency:0.0000" in marcado["data_quality_detalle"]


def test_anexar_no_altera_columnas_originales_ni_ceros():
    frame = pd.DataFrame(
        [
            {
                **_fila_base(
                    n_percentiles_validos=4,
                    ingredients_text="leche",
                    categoria_referencia="en:milks",
                    nova_group="3",
                    additives_n=0,
                ),
                "code": "0074323081411",
                "proteins_100g": 0.0,
                "universo_puntuable": True,
                "d2": 40.0,
                "price_status": "UNAVAILABLE",
                "price_source": None,
            }
        ]
    )
    salida = anexar_indicadores_calidad(frame)
    assert list(salida.columns[: len(frame.columns)]) == list(frame.columns)
    assert salida["proteins_100g"].tolist() == [0.0]
    assert salida["universo_puntuable"].tolist() == [True]
    assert salida["d2"].tolist() == [40.0]
    assert salida["price_source"].isna().all()
    assert set(COLUMNAS_CALIDAD) <= set(salida.columns)
    assert salida["data_quality_score"].notna().all()


def test_anexar_falla_si_la_columna_ya_existe():
    frame = pd.DataFrame([_fila_base()])
    frame["data_quality_score"] = 0.5
    with pytest.raises(ValueError, match="calidad"):
        anexar_indicadores_calidad(frame)


def test_flags_esperadas_coinciden_con_core8():
    assert len(FLAGS_FUERA_DE_RANGO) == 8
    assert "proteins_100g_flag_fuera_de_rango" in FLAGS_FUERA_DE_RANGO
    assert "protein_g_flag_fuera_de_rango" not in FLAGS_FUERA_DE_RANGO
