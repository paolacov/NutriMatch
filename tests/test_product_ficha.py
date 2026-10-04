"""Ficha de producto: saturada, traces, calidad y NULL. No toca ranking."""

from __future__ import annotations

import pandas as pd

from nutrimatch.engine.demo_price import NOTA_PRECIO_DEMOSTRACION, precio_demostracion_mxn
from nutrimatch.services.product import detalle_desde_fila, etiqueta_calidad


def test_ficha_completa_incluye_saturada_traces_y_calidad() -> None:
    detalle = detalle_desde_fila(
        pd.Series(
            {
                "code": "75000001",
                "product_name_homologated": "Yogur natural",
                "product_name_status": "DERIVED",
                "brand_original": "Lala",
                "brand_status": "REAL",
                "main_category": "en:yogurts",
                "ingredients_text": "leche, fermentos",
                "allergens": "en:milk",
                "traces": "en:nuts",
                "labels_tags": "es:exceso-azucares",
                "saturated-fat_100g_saneado": 2.5,
                "proteins_100g_saneado": 4.0,
                "price": 22.0,
                "price_status": "REAL",
                "price_source": "qqp_profeco",
                "data_quality_score": 0.86,
                "data_quality_level": "alta",
                "data_quality_detalle": "nutrition:1.0000;nova:1.0000",
            }
        )
    )
    claves = {n.key: n for n in detalle.nutrients}
    assert "saturated-fat" in claves
    assert claves["saturated-fat"].per100g == 2.5
    assert claves["saturated-fat"].status == "DERIVED"
    assert detalle.allergens == ["en:milk"]
    assert detalle.traces == ["en:nuts"]
    assert detalle.labels == ["es:exceso-azucares"]
    assert detalle.data_quality_level == "alta"
    assert detalle.data_quality_label == "Alta"
    assert detalle.price.status == "REAL"
    assert detalle.price.source == "qqp_profeco"


def test_ficha_incompleta_no_convierte_null_en_cero() -> None:
    detalle = detalle_desde_fila(
        pd.Series(
            {
                "code": "00000285",
                "product_name_homologated": None,
                "product_name": None,
                "allergens": None,
                "traces": None,
                "sugars_100g": None,
                "saturated-fat_100g": None,
                "price": None,
                "price_status": "UNAVAILABLE",
                "data_quality_score": 0.1,
                "data_quality_level": "insuficiente",
                "data_quality_detalle": "nutrition:0.0000",
            }
        )
    )
    assert detalle.name.value is None
    assert detalle.name.status == "UNAVAILABLE"
    assert detalle.allergens == []
    assert detalle.traces == []
    azucar = next(n for n in detalle.nutrients if n.key == "sugars")
    saturada = next(n for n in detalle.nutrients if n.key == "saturated-fat")
    assert azucar.per100g is None
    assert saturada.per100g is None
    assert azucar.status == "UNAVAILABLE"
    assert detalle.price.status == "SYNTHETIC"
    assert detalle.price.source == "demo"
    assert detalle.price.note == NOTA_PRECIO_DEMOSTRACION
    assert detalle.price.value == float(precio_demostracion_mxn("00000285"))
    assert detalle.data_quality_label == "Información insuficiente"


def test_etiqueta_calidad_tres_estados() -> None:
    assert etiqueta_calidad("alta") == "Alta"
    assert etiqueta_calidad("media") == "Media"
    assert etiqueta_calidad("baja") == "Información insuficiente"
    assert etiqueta_calidad("insuficiente") == "Información insuficiente"
    assert etiqueta_calidad(None) is None


def test_unavailable_con_gtin_sale_como_demostracion_y_no_como_real() -> None:
    detalle = detalle_desde_fila(
        pd.Series({"code": "12", "price": None, "price_status": "UNAVAILABLE", "price_source": None})
    )
    assert detalle.price.status == "SYNTHETIC"
    assert detalle.price.source == "demo"
    assert detalle.price.value == float(precio_demostracion_mxn("12"))
    assert detalle.price.note == NOTA_PRECIO_DEMOSTRACION


def test_imagen_invalida_de_off_queda_ausente() -> None:
    detalle = detalle_desde_fila(
        pd.Series(
            {
                "code": "00000140",
                "image_small_url": "https://images.openfoodfacts.org/images/products/invalid/front_fr.4.200.jpg",
                "image_url": "https://images.openfoodfacts.org/images/products/invalid/front_fr.4.400.jpg",
            }
        )
    )
    assert detalle.image_url is None


def test_imagen_real_se_conserva() -> None:
    url = "https://images.openfoodfacts.org/images/products/750/302/573/7362/front_fr.8.200.jpg"
    detalle = detalle_desde_fila(
        pd.Series({"code": "7503025737362", "image_small_url": url, "image_url": None})
    )
    assert detalle.image_url == url


def test_sin_codigo_el_precio_sigue_no_disponible() -> None:
    detalle = detalle_desde_fila(
        pd.Series({"code": "", "price": None, "price_status": "UNAVAILABLE"})
    )
    assert detalle.price.status == "UNAVAILABLE"
    assert detalle.price.value is None
    assert detalle.price.source is None
