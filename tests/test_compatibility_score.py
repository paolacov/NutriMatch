"""Pruebas de src/nutrimatch/engine/compatibility_score.py (decisiones A7, A10)."""

from __future__ import annotations

import math

import pytest

from nutrimatch.engine.compatibility_score import calcular_score_compatibilidad

PESOS_EJEMPLO = {"D1": 0.5, "D2": 1 / 3, "D3": 1 / 6}


def test_con_las_tres_dimensiones_disponibles_score_es_promedio_ponderado():
    resultado = calcular_score_compatibilidad(
        {"D1": 80.0, "D2": 60.0, "D3": 100.0}, PESOS_EJEMPLO
    )
    esperado = 0.5 * 80.0 + (1 / 3) * 60.0 + (1 / 6) * 100.0
    assert resultado["score_final"] == pytest.approx(esperado)
    assert resultado["cov"] == pytest.approx(1.0)
    assert resultado["informacion_insuficiente"] is False


def test_dimension_faltante_se_renormaliza_sobre_las_disponibles():
    # Falta D3 (peso 1/6). cov = 1 - 1/6 = 5/6 >= 0.5, sigue siendo puntuable.
    resultado = calcular_score_compatibilidad({"D1": 80.0, "D2": 60.0, "D3": None}, PESOS_EJEMPLO)
    peso_disponible = PESOS_EJEMPLO["D1"] + PESOS_EJEMPLO["D2"]
    esperado = (PESOS_EJEMPLO["D1"] * 80.0 + PESOS_EJEMPLO["D2"] * 60.0) / peso_disponible
    assert resultado["score_final"] == pytest.approx(esperado)
    assert resultado["cov"] == pytest.approx(5 / 6)
    assert resultado["informacion_insuficiente"] is False
    assert resultado["dimensiones"]["D3"]["disponible"] is False
    assert resultado["dimensiones"]["D3"]["contribucion_ponderada"] is None


def test_cov_bajo_el_umbral_devuelve_score_none_y_bandera():
    # Solo D3 disponible (peso 1/6): cov = 1/6 < 0.5.
    resultado = calcular_score_compatibilidad({"D1": None, "D2": None, "D3": 90.0}, PESOS_EJEMPLO)
    assert resultado["score_final"] is None
    assert resultado["informacion_insuficiente"] is True
    assert resultado["cov"] == pytest.approx(1 / 6)


def test_ninguna_dimension_disponible():
    resultado = calcular_score_compatibilidad({"D1": None, "D2": None, "D3": None}, PESOS_EJEMPLO)
    assert resultado["score_final"] is None
    assert resultado["cov"] == pytest.approx(0.0)
    assert resultado["informacion_insuficiente"] is True


def test_detalle_por_dimension_incluye_peso_y_subpuntaje():
    resultado = calcular_score_compatibilidad({"D1": 80.0, "D2": None, "D3": 50.0}, PESOS_EJEMPLO)
    detalle_d1 = resultado["dimensiones"]["D1"]
    assert detalle_d1["subpuntaje"] == 80.0
    assert detalle_d1["peso"] == PESOS_EJEMPLO["D1"]
    assert detalle_d1["disponible"] is True
    assert detalle_d1["contribucion_ponderada"] == pytest.approx(PESOS_EJEMPLO["D1"] * 80.0)


def test_nan_de_pandas_se_trata_igual_que_none():
    # Regresión: iterar un DataFrame de pandas entrega NaN (float), no None, para un subpuntaje
    # ausente. `NaN is not None` es True en Python, así que un chequeo ingenuo con `is not None`
    # marcaría la dimensión como "disponible" e infla cov artificialmente a 1.0.
    resultado_none = calcular_score_compatibilidad(
        {"D1": 80.0, "D2": 60.0, "D3": None}, PESOS_EJEMPLO
    )
    resultado_nan = calcular_score_compatibilidad(
        {"D1": 80.0, "D2": 60.0, "D3": math.nan}, PESOS_EJEMPLO
    )
    assert resultado_nan["cov"] == pytest.approx(resultado_none["cov"])
    assert resultado_nan["score_final"] == pytest.approx(resultado_none["score_final"])
    assert resultado_nan["dimensiones"]["D3"]["disponible"] is False


def test_umbral_cov_personalizado():
    # cov = 5/6 (falta D3). Con un umbral de 0.9, esto ahora sí cuenta como insuficiente.
    resultado = calcular_score_compatibilidad(
        {"D1": 80.0, "D2": 60.0, "D3": None}, PESOS_EJEMPLO, umbral_cov=0.9
    )
    assert resultado["informacion_insuficiente"] is True
    assert resultado["score_final"] is None
