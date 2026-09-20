"""Pruebas de src/nutrimatch/engine/hard_filters.py (decisiones A1, A15)."""

from __future__ import annotations

import math

import pytest

from nutrimatch.engine.hard_filters import evaluar_alergia, evaluar_dieta

# --- evaluar_alergia -------------------------------------------------------


def test_sin_alergenos_declarados_es_apto():
    assert evaluar_alergia("en:gluten,en:milk", None, []) == "apto"


def test_alergeno_declarado_presente_en_allergens_es_no_apto():
    assert evaluar_alergia("en:gluten,en:milk", None, ["en:gluten"]) == "no_apto"


def test_alergeno_declarado_presente_solo_en_traces_es_no_apto():
    # "Puede contener" cuenta igual que confirmado (A15): fail-safe.
    assert evaluar_alergia("en:soybeans", "en:peanuts", ["en:peanuts"]) == "no_apto"


def test_sin_ningun_dato_de_alergenos_es_no_verificable():
    assert evaluar_alergia(None, None, ["en:gluten"]) == "no_verificable"
    assert evaluar_alergia("", "", ["en:gluten"]) == "no_verificable"


def test_con_dato_que_no_coincide_es_apto():
    assert evaluar_alergia("en:milk", None, ["en:gluten"]) == "apto"
    assert evaluar_alergia(None, "en:soybeans", ["en:gluten"]) == "apto"


def test_nan_de_pandas_se_trata_como_ausente_no_como_texto():
    # Regresión: al leer un Parquet con DuckDB/pandas, un campo de texto ausente llega como
    # float('nan'), no como None. `bool(float('nan'))` es True en Python, así que un chequeo
    # ingenuo lo trataría como "sí hay dato" (y el texto literal "nan" incluso podría
    # interpretarse como un tag). Debe comportarse igual que None/cadena vacía.
    assert evaluar_alergia(math.nan, math.nan, ["en:gluten"]) == "no_verificable"
    assert evaluar_alergia("en:milk", math.nan, ["en:gluten"]) == "apto"


# --- evaluar_dieta ----------------------------------------------------------


def test_vegano_compatible():
    assert evaluar_dieta("en:palm-oil,en:vegan,en:vegetarian", "vegano") == "compatible"


def test_vegano_incompatible():
    assert evaluar_dieta("en:non-vegan,en:vegetarian", "vegano") == "incompatible"


def test_vegano_no_verificable_por_status_unknown():
    assert evaluar_dieta("en:vegan-status-unknown", "vegano") == "no_verificable"


def test_vegano_no_verificable_por_maybe():
    # "Tal vez" no equivale a "sí" (A1): no se afirma compatibilidad sin evidencia.
    assert evaluar_dieta("en:maybe-vegan", "vegano") == "no_verificable"


def test_vegano_no_verificable_sin_ingredients_analysis_tags():
    assert evaluar_dieta(None, "vegano") == "no_verificable"
    assert evaluar_dieta("", "vegano") == "no_verificable"


def test_vegetariano_compatible_e_incompatible():
    assert evaluar_dieta("en:vegetarian", "vegetariano") == "compatible"
    assert evaluar_dieta("en:non-vegetarian", "vegetariano") == "incompatible"


def test_dieta_declarada_invalida_lanza_value_error():
    with pytest.raises(ValueError):
        evaluar_dieta("en:vegan", "keto")


def test_dieta_con_nan_de_pandas_es_no_verificable():
    assert evaluar_dieta(math.nan, "vegano") == "no_verificable"
