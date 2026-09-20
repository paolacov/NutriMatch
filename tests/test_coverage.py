"""Pruebas de src/nutrimatch/engine/coverage.py (decisión A2)."""

from __future__ import annotations

import pytest

from nutrimatch.engine.coverage import calcular_cov, es_informacion_insuficiente


def test_todas_las_dimensiones_disponibles_cov_es_1():
    pesos = {"D1": 0.5, "D2": 0.3333, "D3": 0.1667}
    disponibilidad = {"D1": True, "D2": True, "D3": True}
    assert calcular_cov(disponibilidad, pesos) == pytest.approx(1.0)


def test_una_dimension_faltante_reduce_cov_segun_su_peso():
    pesos = {"D1": 0.5, "D2": 0.3, "D3": 0.2}
    disponibilidad = {"D1": True, "D2": True, "D3": False}
    assert calcular_cov(disponibilidad, pesos) == pytest.approx(0.8)


def test_ninguna_dimension_disponible_cov_es_0():
    pesos = {"D1": 0.5, "D2": 0.3, "D3": 0.2}
    disponibilidad = {"D1": False, "D2": False, "D3": False}
    assert calcular_cov(disponibilidad, pesos) == pytest.approx(0.0)


def test_pesos_vacios_no_lanza_division_por_cero():
    assert calcular_cov({}, {}) == 0.0


def test_es_informacion_insuficiente_umbral_0_5():
    assert es_informacion_insuficiente(0.49) is True
    assert es_informacion_insuficiente(0.5) is False
    assert es_informacion_insuficiente(0.51) is False


def test_es_informacion_insuficiente_umbral_personalizado():
    assert es_informacion_insuficiente(0.6, umbral=0.7) is True
    assert es_informacion_insuficiente(0.8, umbral=0.7) is False
