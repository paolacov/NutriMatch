"""Pruebas de src/nutrimatch/engine/identity_homologation.py (decisión A38)."""

from __future__ import annotations

import math

from nutrimatch.engine.identity_homologation import (
    homologar_marca,
    normalizar_texto_cosmetico,
    resolver_nombre_homologado,
)

# --------------------------------------------------------------------------
# normalizar_texto_cosmetico
# --------------------------------------------------------------------------


def test_normalizar_recorta_y_colapsa_espacios():
    assert normalizar_texto_cosmetico("  Pan   con  Centeno  ") == "Pan con Centeno"


def test_normalizar_no_toca_mayusculas_ni_acentos():
    assert normalizar_texto_cosmetico("Café Orgánico NIDO") == "Café Orgánico NIDO"


def test_normalizar_nan_de_pandas_es_none():
    assert normalizar_texto_cosmetico(math.nan) is None


def test_normalizar_cadena_vacia_es_none():
    assert normalizar_texto_cosmetico("   ") is None


# --------------------------------------------------------------------------
# resolver_nombre_homologado
# --------------------------------------------------------------------------


def test_product_name_valido_no_usa_respaldo():
    nombre, campo, removio_placeholder = resolver_nombre_homologado(
        "Pan con Centeno", "Pan de centeno integral"
    )
    assert nombre == "Pan con Centeno"
    assert campo == "product_name"
    assert removio_placeholder is False


def test_product_name_vacio_cae_a_generic_name():
    nombre, campo, removio_placeholder = resolver_nombre_homologado(
        None, "Organic Smooth Almond Butter", "Organic Smoth Almond Butter"
    )
    assert nombre == "Organic Smooth Almond Butter"
    assert campo == "generic_name"
    assert removio_placeholder is False


def test_ningun_campo_con_dato_devuelve_none():
    nombre, campo, removio_placeholder = resolver_nombre_homologado(None, None, None)
    assert nombre is None
    assert campo is None
    assert removio_placeholder is False


def test_placeholder_cargando_se_descarta_y_cae_a_generic_name():
    # Caso real del snapshot: code 7503028965717 (notebooks/08_re_eda_identidad.ipynb).
    nombre, campo, removio_placeholder = resolver_nombre_homologado(
        "Cargando…", "Totopos de maíz horneados con nopal", None
    )
    assert nombre == "Totopos de maíz horneados con nopal"
    assert campo == "generic_name"
    assert removio_placeholder is True


def test_placeholder_insensible_a_mayusculas_y_puntos_suspensivos_ascii():
    nombre, campo, removio_placeholder = resolver_nombre_homologado("CARGANDO...", None, None)
    assert nombre is None
    assert campo is None
    assert removio_placeholder is True


def test_placeholder_sin_ningun_respaldo_devuelve_none_pero_marca_flag():
    nombre, campo, removio_placeholder = resolver_nombre_homologado("Cargando…", None, None)
    assert nombre is None
    assert campo is None
    assert removio_placeholder is True


def test_nan_de_pandas_se_trata_como_ausente():
    nombre, campo, removio_placeholder = resolver_nombre_homologado(
        math.nan, "Organic Smooth Almond Butter"
    )
    assert nombre == "Organic Smooth Almond Butter"
    assert campo == "generic_name"
    assert removio_placeholder is False


def test_resultado_se_normaliza_cosmeticamente():
    nombre, campo, _ = resolver_nombre_homologado("  Pan   con  Centeno  ")
    assert nombre == "Pan con Centeno"
    assert campo == "product_name"


# --------------------------------------------------------------------------
# homologar_marca
# --------------------------------------------------------------------------


def test_homologar_marca_funde_variantes_por_acento_y_caja():
    assert homologar_marca("Nestlé") == homologar_marca("nestle")


def test_homologar_marca_colapsa_espacios():
    assert homologar_marca("  La   Costeña  ") == "la costena"


def test_homologar_marca_none_si_no_hay_dato():
    assert homologar_marca(None) is None
    assert homologar_marca(math.nan) is None
    assert homologar_marca("   ") is None


def test_homologar_marca_conserva_multi_marca_como_una_cadena():
    assert homologar_marca("Walmart,Sam's Club") == "walmart,sam's club"
