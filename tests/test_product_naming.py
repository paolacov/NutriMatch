"""Pruebas de src/nutrimatch/engine/product_naming.py (decisión A28)."""

from __future__ import annotations

import math

from nutrimatch.engine.product_naming import resolver_nombre_producto


def test_product_name_presente_no_usa_respaldo():
    nombre, se_uso_respaldo = resolver_nombre_producto("Pan con Centeno", "Pan de centeno integral")
    assert nombre == "Pan con Centeno"
    assert se_uso_respaldo is False


def test_product_name_vacio_cae_a_generic_name():
    nombre, se_uso_respaldo = resolver_nombre_producto(None, "Organic Smooth Almond Butter", "Organic Smoth Almond Butter")
    assert nombre == "Organic Smooth Almond Butter"
    assert se_uso_respaldo is True


def test_product_name_y_generic_name_vacios_cae_a_abbreviated():
    nombre, se_uso_respaldo = resolver_nombre_producto(None, None, "Organic Smoth Almond Butter")
    assert nombre == "Organic Smoth Almond Butter"
    assert se_uso_respaldo is True


def test_ningun_campo_con_dato_devuelve_none_sin_respaldo():
    nombre, se_uso_respaldo = resolver_nombre_producto(None, None, None)
    assert nombre is None
    assert se_uso_respaldo is False


def test_cadenas_vacias_o_blancas_se_tratan_como_ausentes():
    nombre, se_uso_respaldo = resolver_nombre_producto("", "   ", "Organic Smoth Almond Butter")
    assert nombre == "Organic Smoth Almond Butter"
    assert se_uso_respaldo is True


def test_nan_de_pandas_se_trata_como_ausente():
    # Regresión (B13): un campo de texto ausente leído de un Parquet vía pandas llega como
    # float('nan'), no como None.
    nombre, se_uso_respaldo = resolver_nombre_producto(math.nan, "Organic Smooth Almond Butter")
    assert nombre == "Organic Smooth Almond Butter"
    assert se_uso_respaldo is True


def test_espacios_sobrantes_se_recortan():
    nombre, se_uso_respaldo = resolver_nombre_producto("  Pan con Centeno  ")
    assert nombre == "Pan con Centeno"
    assert se_uso_respaldo is False
