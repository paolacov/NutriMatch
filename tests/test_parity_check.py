from __future__ import annotations

import math

import pandas as pd
import pytest

from evaluacion.parity_check import UMBRAL_CORRELACION_RAZONABLE, calcular_parity_check


def test_correlacion_negativa_perfecta_es_razonable_y_monotona() -> None:
    d1 = pd.Series([90, 70, 50, 30, 10])
    nutriscore_score = pd.Series([-10, 0, 10, 20, 30])
    grado = pd.Series(["a", "b", "c", "d", "e"])

    reporte = calcular_parity_check(d1, nutriscore_score, grado)

    assert reporte["n"] == 5
    assert reporte["correlacion_spearman"] == pytest.approx(-1.0)
    assert reporte["correlacion_razonable"] is True
    assert reporte["monotono_por_grado"] is True
    assert list(reporte["promedio_d1_por_grado"].index) == ["a", "b", "c", "d", "e"]


def test_sin_relacion_no_es_razonable() -> None:
    d1 = pd.Series([50, 10, 90, 30, 70])
    nutriscore_score = pd.Series([10, 10, 10, 10, 10])  # constante: correlación indefinida o ~0
    grado = pd.Series(["a", "a", "a", "a", "a"])

    reporte = calcular_parity_check(d1, nutriscore_score, grado)

    assert reporte["correlacion_razonable"] is False


def test_correlacion_positiva_no_es_razonable() -> None:
    d1 = pd.Series([10, 30, 50, 70, 90])
    nutriscore_score = pd.Series([-10, 0, 10, 20, 30])  # D1 sube CON nutriscore_score: mal signo
    grado = pd.Series(["a", "b", "c", "d", "e"])

    reporte = calcular_parity_check(d1, nutriscore_score, grado)

    assert reporte["correlacion_spearman"] == pytest.approx(1.0)
    assert reporte["correlacion_razonable"] is False


def test_menos_de_dos_pares_validos_da_correlacion_none() -> None:
    d1 = pd.Series([90, math.nan, math.nan])
    nutriscore_score = pd.Series([-10, 5, math.nan])
    grado = pd.Series(["a", "b", "c"])

    reporte = calcular_parity_check(d1, nutriscore_score, grado)

    assert reporte["n"] == 1
    assert reporte["correlacion_spearman"] is None
    assert reporte["correlacion_razonable"] is False
    assert reporte["monotono_por_grado"] is False  # un solo grado no permite evaluar monotonia


def test_nan_se_excluyen_de_n_y_de_la_correlacion() -> None:
    d1 = pd.Series([90, 70, math.nan, 30, 10])
    nutriscore_score = pd.Series([-10, 0, 10, math.nan, 30])
    grado = pd.Series(["a", "b", "c", "d", "e"])

    reporte = calcular_parity_check(d1, nutriscore_score, grado)

    assert reporte["n"] == 3  # solo filas 0, 1 y 4 tienen ambos datos


def test_grados_desconocidos_se_excluyen_solo_del_desglose_por_grado() -> None:
    d1 = pd.Series([90, 70, 50, 30])
    nutriscore_score = pd.Series([-10, 0, 10, 20])
    grado = pd.Series(["a", "unknown", "not-applicable", "e"])

    reporte = calcular_parity_check(d1, nutriscore_score, grado)

    assert reporte["n"] == 4  # la correlacion SI usa las 4 filas
    assert list(reporte["promedio_d1_por_grado"].index) == ["a", "e"]


def test_monotono_permite_empates() -> None:
    d1 = pd.Series([80, 80, 60, 40])
    nutriscore_score = pd.Series([-5, 0, 10, 20])
    grado = pd.Series(["a", "b", "c", "d"])

    reporte = calcular_parity_check(d1, nutriscore_score, grado)

    assert reporte["monotono_por_grado"] is True


def test_no_monotono_cuando_un_grado_peor_promedia_mas_alto() -> None:
    d1 = pd.Series([50, 90, 30, 10])  # 'b' promedia mas alto que 'a': rompe la monotonia
    nutriscore_score = pd.Series([-5, 0, 10, 20])
    grado = pd.Series(["a", "b", "c", "d"])

    reporte = calcular_parity_check(d1, nutriscore_score, grado)

    assert reporte["monotono_por_grado"] is False


def test_umbral_es_negativo() -> None:
    assert UMBRAL_CORRELACION_RAZONABLE < 0
