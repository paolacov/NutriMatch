"""Pruebas de src/nutrimatch/engine/processing_score.py (decisión A17)."""

from __future__ import annotations

import pandas as pd

from nutrimatch.engine.processing_score import (
    ANCHO_BANDA,
    FRACCION_AJUSTE_ADITIVOS_AUSENTES,
    calcular_d2,
    calibrar_tope_aditivos,
)


def test_nova_1_nunca_puntua_por_debajo_de_nova_2_sin_importar_aditivos():
    # NOVA=1 con el peor caso de aditivos (penalización máxima) toca el mismo
    # límite que NOVA=2 en el mejor caso (75, borde compartido de ambas
    # bandas), pero nunca cae por debajo: la primacía de NOVA nunca se invierte.
    nova = pd.Series(["1", "2"])
    aditivos = pd.Series([10, 0])
    d2 = calcular_d2(nova, aditivos, tope_aditivos=10)
    assert d2.iloc[0] >= d2.iloc[1]
    assert d2.iloc[0] == 75.0  # peor caso de N1 == mejor caso de N2 (borde de banda)
    assert d2.iloc[1] == 75.0

    # Con un caso que no toca el borde, N1 sí queda estrictamente por encima.
    d2_no_borde = calcular_d2(pd.Series(["1", "2"]), pd.Series([5, 0]), tope_aditivos=10)
    assert d2_no_borde.iloc[0] > d2_no_borde.iloc[1]


def test_mas_aditivos_reduce_el_subpuntaje_dentro_del_mismo_grupo_nova():
    nova = pd.Series(["4", "4"])
    aditivos = pd.Series([0, 9])
    d2 = calcular_d2(nova, aditivos, tope_aditivos=9)
    assert d2.iloc[0] > d2.iloc[1]
    assert d2.iloc[0] == 25.0  # techo de la banda de NOVA=4 (0-25)
    assert d2.iloc[1] == 0.0  # tope de aditivos alcanzado: piso de la banda


def test_sin_nova_no_es_computable():
    nova = pd.Series(["", None])
    aditivos = pd.Series([3, 5])
    d2 = calcular_d2(nova, aditivos, tope_aditivos=9)
    assert d2.isna().all()


def test_sin_additives_n_no_anula_d2_usa_ajuste_neutro_de_media_banda():
    nova = pd.Series(["3"])
    aditivos = pd.Series([None])
    d2 = calcular_d2(nova, aditivos, tope_aditivos=9)
    techo_nova_3 = 100.0 - (3 - 1) * ANCHO_BANDA
    esperado = techo_nova_3 - FRACCION_AJUSTE_ADITIVOS_AUSENTES * ANCHO_BANDA
    assert not d2.isna().any()
    assert d2.iloc[0] == esperado  # centro de la banda NOVA=3 (25-50) → 37.5
    assert 25.0 <= d2.iloc[0] <= 50.0


def test_additives_n_ausente_queda_en_el_centro_de_cada_banda_nova():
    nova = pd.Series(["1", "2", "3", "4"])
    aditivos = pd.Series([None, float("nan"), None, float("nan")])
    d2 = calcular_d2(nova, aditivos, tope_aditivos=9)
    centros = [87.5, 62.5, 37.5, 12.5]
    bandas = [(75.0, 100.0), (50.0, 75.0), (25.0, 50.0), (0.0, 25.0)]
    for valor, centro, (piso, techo) in zip(d2.tolist(), centros, bandas, strict=True):
        assert valor == centro
        assert piso <= valor <= techo


def test_calibrar_tope_aditivos_usa_percentil_de_nova_4():
    nova = pd.Series(["4"] * 10 + ["1"] * 5)
    aditivos = pd.Series(list(range(1, 11)) + [100] * 5)  # los NOVA=1 no deben influir
    tope = calibrar_tope_aditivos(nova, aditivos, percentil=0.9)
    assert tope < 100  # confirma que se ignoraron los aditivos de NOVA=1
    assert tope == pd.Series(range(1, 11)).quantile(0.9)


def test_calibrar_tope_aditivos_devuelve_al_menos_uno_si_no_hay_nova_4():
    nova = pd.Series(["1", "2"])
    aditivos = pd.Series([0, 0])
    assert calibrar_tope_aditivos(nova, aditivos) == 1.0
