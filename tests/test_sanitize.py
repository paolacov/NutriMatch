"""Pruebas de src/nutrimatch/engine/sanitize.py (decisión A18)."""

from __future__ import annotations

import pandas as pd

from nutrimatch.engine.sanitize import (
    corregir_escala_sal_por_sodio,
    flag_suma_macros_excede_100,
    parsear_numerico,
    sanear_nucleo_nutricional,
)


def _fila_minima(**overrides) -> dict:
    base = {
        "energy-kcal_100g": "",
        "fat_100g": "",
        "saturated-fat_100g": "",
        "carbohydrates_100g": "",
        "sugars_100g": "",
        "proteins_100g": "",
        "salt_100g": "",
        "fiber_100g": "",
    }
    base.update(overrides)
    return base


def test_parsear_numerico_trata_vacio_como_ausente_no_como_cero():
    serie = pd.Series(["", "  ", "3.5", None])
    resultado = parsear_numerico(serie)
    assert resultado.isna().tolist() == [True, True, False, True]
    assert resultado.iloc[2] == 3.5


def test_valor_dentro_de_rango_no_se_marca():
    df = pd.DataFrame([_fila_minima(fat_100g="12.5")])
    saneado = sanear_nucleo_nutricional(df)
    assert saneado["fat_100g_bruto"].iloc[0] == 12.5
    assert not bool(saneado["fat_100g_flag_fuera_de_rango"].iloc[0])
    assert saneado["fat_100g_saneado"].iloc[0] == 12.5


def test_valor_fuera_de_rango_se_marca_y_se_anula_solo_ese_nutriente():
    # Caso real del EDA: "Flora 0" con 277.183 kcal/100g.
    df = pd.DataFrame([_fila_minima(**{"energy-kcal_100g": "277183.33", "fat_100g": "10"})])
    saneado = sanear_nucleo_nutricional(df)

    assert saneado["energy-kcal_100g_bruto"].iloc[0] == 277183.33  # el bruto se conserva
    assert bool(saneado["energy-kcal_100g_flag_fuera_de_rango"].iloc[0])
    assert pd.isna(saneado["energy-kcal_100g_saneado"].iloc[0])  # el saneado se anula

    # Un nutriente fuera de rango no debe afectar a los demás de la misma fila.
    assert not bool(saneado["fat_100g_flag_fuera_de_rango"].iloc[0])
    assert saneado["fat_100g_saneado"].iloc[0] == 10


def test_valor_ausente_no_se_marca_como_fuera_de_rango():
    df = pd.DataFrame([_fila_minima()])  # todo vacío
    saneado = sanear_nucleo_nutricional(df)
    assert not bool(saneado["fat_100g_flag_fuera_de_rango"].iloc[0])
    assert pd.isna(saneado["fat_100g_saneado"].iloc[0])


def test_negativo_se_marca_fuera_de_rango():
    df = pd.DataFrame([_fila_minima(fiber_100g="-1")])
    saneado = sanear_nucleo_nutricional(df)
    assert bool(saneado["fiber_100g_flag_fuera_de_rango"].iloc[0])


def test_corregir_escala_sal_aplica_cuando_razon_es_2_5_y_resultado_es_valido():
    # Caso real: "Steakos carne seca", salt=6532.5, sodium=2613 (razón exacta 2.5).
    df = pd.DataFrame([
        _fila_minima(salt_100g="6532.5") | {"sodium_100g": "2613"},
    ])
    saneado = sanear_nucleo_nutricional(df)
    assert saneado["salt_100g_flag_fuera_de_rango"].iloc[0]  # confirma que arranca marcado

    corregido = corregir_escala_sal_por_sodio(df, saneado)
    assert corregido["salt_100g_flag_correccion_escala_aplicada"].iloc[0]
    assert corregido["salt_100g_saneado"].iloc[0] == 6.5325


def test_corregir_escala_sal_no_aplica_si_la_razon_no_es_2_5():
    # Caso real: "Queso panela", salt=1292.5, sodium=0.517 (razón ≈2500, no 2.5).
    df = pd.DataFrame([
        _fila_minima(salt_100g="1292.5") | {"sodium_100g": "0.517"},
    ])
    saneado = sanear_nucleo_nutricional(df)
    corregido = corregir_escala_sal_por_sodio(df, saneado)
    assert not corregido["salt_100g_flag_correccion_escala_aplicada"].iloc[0]
    assert pd.isna(corregido["salt_100g_saneado"].iloc[0])  # sigue anulado, sin corregir


def test_corregir_escala_sal_no_aplica_si_el_valor_ya_esta_en_rango():
    df = pd.DataFrame([
        _fila_minima(salt_100g="1.5") | {"sodium_100g": "0.6"},  # razón 2.5, pero ya válido
    ])
    saneado = sanear_nucleo_nutricional(df)
    corregido = corregir_escala_sal_por_sodio(df, saneado)
    assert not corregido["salt_100g_flag_correccion_escala_aplicada"].iloc[0]
    assert corregido["salt_100g_saneado"].iloc[0] == 1.5  # el original, sin tocar


def test_corregir_escala_sal_no_aplica_sin_sodium():
    df = pd.DataFrame([
        _fila_minima(salt_100g="6532.5") | {"sodium_100g": ""},
    ])
    saneado = sanear_nucleo_nutricional(df)
    corregido = corregir_escala_sal_por_sodio(df, saneado)
    assert not corregido["salt_100g_flag_correccion_escala_aplicada"].iloc[0]
    assert pd.isna(corregido["salt_100g_saneado"].iloc[0])


def test_flag_suma_macros_excede_100():
    df = pd.DataFrame(
        [
            _fila_minima(fat_100g="50", carbohydrates_100g="40", proteins_100g="20"),  # 110
            _fila_minima(fat_100g="10", carbohydrates_100g="10", proteins_100g="10"),  # 30
            _fila_minima(fat_100g="10", carbohydrates_100g="10"),  # falta proteína: no evaluable
        ]
    )
    saneado = sanear_nucleo_nutricional(df)
    flags = flag_suma_macros_excede_100(saneado)
    assert flags.tolist() == [True, False, False]
