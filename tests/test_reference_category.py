"""Pruebas de src/nutrimatch/engine/reference_category.py (decisión A16)."""

from __future__ import annotations

import pandas as pd

from nutrimatch.engine.reference_category import (
    calcular_tamanos_de_categoria,
    resolver_categoria_referencia,
)


def test_categoria_especifica_suficientemente_grande_se_usa_sin_retroceso():
    # 30 productos comparten la etiqueta específica "en:yogurts": alcanza el mínimo.
    tags = pd.Series(["en:dairies,en:fermented-milk-products,en:yogurts"] * 30)
    resultado = resolver_categoria_referencia(tags, tamano_minimo=30)
    assert (resultado["categoria_referencia"] == "en:yogurts").all()
    assert (resultado["nivel_retroceso"] == 0).all()


def test_categoria_especifica_pequena_retrocede_a_la_siguiente():
    # "en:yogurts-de-fresa" solo la trae 1 producto; "en:yogurts" la traen 30.
    tags = pd.Series(
        ["en:dairies,en:yogurts,en:yogurts-de-fresa"]
        + ["en:dairies,en:yogurts"] * 29
    )
    resultado = resolver_categoria_referencia(tags, tamano_minimo=30)
    # El primer producto retrocede una vez: su específica no alcanza el mínimo.
    assert resultado["categoria_referencia"].iloc[0] == "en:yogurts"
    assert resultado["nivel_retroceso"].iloc[0] == 1


def test_sin_categoria_que_alcance_el_minimo_devuelve_na():
    tags = pd.Series(["en:categoria-unica-a,en:categoria-unica-b"])
    resultado = resolver_categoria_referencia(tags, tamano_minimo=30)
    assert pd.isna(resultado["categoria_referencia"].iloc[0])
    assert pd.isna(resultado["nivel_retroceso"].iloc[0])


def test_producto_sin_categories_tags_devuelve_na():
    tags = pd.Series([None, "", "  "])
    resultado = resolver_categoria_referencia(tags, tamano_minimo=30)
    assert resultado["categoria_referencia"].isna().all()


def test_tamano_de_categoria_cuenta_cualquier_posicion():
    # Un producto etiquetado con la más específica también cuenta para la ancestra.
    tags = pd.Series(["en:dairies,en:yogurts", "en:dairies,en:cheeses"])
    tamanos = calcular_tamanos_de_categoria(tags)
    assert tamanos["en:dairies"] == 2
    assert tamanos["en:yogurts"] == 1
    assert tamanos["en:cheeses"] == 1
