"""Pruebas de src/nutrimatch/engine/preference_score.py (D3, decisión A7)."""

from __future__ import annotations

import math

import pytest

from nutrimatch.engine.preference_score import calcular_d3


def test_sin_etiquetas_valoradas_devuelve_none():
    assert calcular_d3("en:organic,en:no-gluten", []) is None


def test_sin_labels_tags_devuelve_none_no_cero():
    # Sin dato de labels_tags no se puede confirmar la ausencia de las etiquetas valoradas.
    assert calcular_d3(None, ["en:organic"]) is None
    assert calcular_d3("", ["en:organic"]) is None
    assert calcular_d3("   ", ["en:organic"]) is None


def test_todas_las_etiquetas_valoradas_presentes_es_100():
    assert calcular_d3("en:organic,en:no-gluten,en:green-dot", ["en:organic", "en:no-gluten"]) == 100.0


def test_ninguna_etiqueta_valorada_presente_es_0_no_none():
    # El producto sí tiene labels_tags (dato disponible); simplemente no coincide con lo valorado.
    assert calcular_d3("en:green-dot", ["en:organic", "en:no-gluten"]) == 0.0


def test_porcentaje_parcial():
    resultado = calcular_d3("en:organic", ["en:organic", "en:no-gluten", "en:fair-trade"])
    assert resultado == pytest.approx(100 / 3)


def test_nan_de_pandas_se_trata_como_ausente_no_como_cero():
    # Regresión: al leer un Parquet con DuckDB/pandas, labels_tags ausente llega como
    # float('nan'), no como None. Debe devolver None (sin dato), no 0.0.
    assert calcular_d3(math.nan, ["en:organic"]) is None
