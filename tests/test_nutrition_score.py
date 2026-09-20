"""Pruebas de src/nutrimatch/engine/nutrition_score.py (D1, decisión A7)."""

from __future__ import annotations

import math

import pytest

from nutrimatch.engine.nutrition_score import calcular_subpuntaje_d1


def test_nutriente_menos_es_mejor_se_invierte():
    # Un producto en el percentil 90 de azúcar (mucha azúcar respecto a su categoría) debe
    # recibir una contribución baja (10), no alta.
    d1, detalle = calcular_subpuntaje_d1({"sugars_100g": 90.0})
    assert d1 == pytest.approx(10.0)
    assert detalle["sugars_100g"]["contribucion"] == pytest.approx(10.0)
    assert detalle["sugars_100g"]["signo"] == -1


def test_nutriente_mas_es_mejor_no_se_invierte():
    d1, detalle = calcular_subpuntaje_d1({"fiber_100g": 90.0})
    assert d1 == pytest.approx(90.0)
    assert detalle["fiber_100g"]["contribucion"] == pytest.approx(90.0)
    assert detalle["fiber_100g"]["signo"] == 1


def test_promedia_solo_sobre_nutrientes_disponibles():
    d1, detalle = calcular_subpuntaje_d1({"sugars_100g": 80.0, "fiber_100g": 60.0})
    # sugars: 100-80=20; fiber: 60. Promedio = 40.
    assert d1 == pytest.approx(40.0)
    assert detalle["salt_100g"]["disponible"] is False
    assert detalle["salt_100g"]["contribucion"] is None


def test_sin_ningun_dato_devuelve_none():
    d1, detalle = calcular_subpuntaje_d1({})
    assert d1 is None
    assert all(not d["disponible"] for d in detalle.values())


def test_nan_se_trata_como_ausente():
    d1, detalle = calcular_subpuntaje_d1({"sugars_100g": math.nan, "fiber_100g": 50.0})
    assert d1 == pytest.approx(50.0)
    assert detalle["sugars_100g"]["disponible"] is False


def test_nutrientes_pendientes_se_ignoran_si_se_pasan():
    # energy-kcal, fat total y carbohydrates no tienen signo definido en esta versión (v1):
    # deben ignorarse silenciosamente si el caller pasa el diccionario completo de core8.
    d1, detalle = calcular_subpuntaje_d1(
        {"energy-kcal_100g": 20.0, "fat_100g": 30.0, "carbohydrates_100g": 40.0, "fiber_100g": 70.0}
    )
    assert d1 == pytest.approx(70.0)
    assert "energy-kcal_100g" not in detalle
    assert "fat_100g" not in detalle
    assert "carbohydrates_100g" not in detalle


def test_detalle_incluye_los_cinco_nutrientes_de_signo_fijo():
    _, detalle = calcular_subpuntaje_d1({})
    assert set(detalle.keys()) == {
        "sugars_100g",
        "salt_100g",
        "saturated-fat_100g",
        "fiber_100g",
        "proteins_100g",
    }
