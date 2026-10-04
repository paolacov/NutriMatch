"""Pruebas de src/nutrimatch/engine/observations.py (paso 9, decisión A43)."""

from __future__ import annotations

import math

import pandas as pd

from nutrimatch.engine.observations import (
    COLUMNAS_OBSERVACION,
    construir_observaciones_nombre_recuperado,
    construir_observaciones_precio,
    resolver_observaciones,
    resolver_valor,
)

# --------------------------------------------------------------------------
# construir_observaciones_nombre_recuperado
# --------------------------------------------------------------------------


def _experimento_sintetico() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "code": "7622210571328",
                "es_hit": True,
                "nombre_recuperado": "Trident XtraCare yerbabuena",
                "status_valor": "REAL",
                "source": "openfoodfacts_api_producto",
                "source_url": "https://world.openfoodfacts.org/api/v2/product/7622210571328.json",
                "retrieved_at": "2026-09-26T23:41:02+00:00",
            },
            {
                "code": "0000000000000",
                "es_hit": False,
                "nombre_recuperado": None,
                "status_valor": "UNAVAILABLE",
                "source": "openfoodfacts_api_producto",
                "source_url": "https://world.openfoodfacts.org/api/v2/product/0000000000000.json",
                "retrieved_at": "2026-09-26T23:41:02+00:00",
            },
        ]
    )


def test_solo_convierte_hits_en_observaciones():
    resultado = construir_observaciones_nombre_recuperado(_experimento_sintetico())

    assert len(resultado) == 1
    assert list(resultado.columns) == list(COLUMNAS_OBSERVACION)
    fila = resultado.iloc[0]
    assert fila["code"] == "7622210571328"
    assert fila["field"] == "product_name"
    assert fila["value"] == "Trident XtraCare yerbabuena"
    assert fila["status"] == "REAL"
    assert fila["method"] == "api_producto_individual"
    assert fila["confidence"] is None


def test_experimento_vacio_devuelve_dataframe_vacio_con_columnas():
    resultado = construir_observaciones_nombre_recuperado(pd.DataFrame(columns=["code", "es_hit"]))
    assert resultado.empty
    assert list(resultado.columns) == list(COLUMNAS_OBSERVACION)


# --------------------------------------------------------------------------
# construir_observaciones_precio
# --------------------------------------------------------------------------


def _precios_sinteticos(source: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "code": "0074323081411",
                "price": 115.0,
                "price_status": "REAL",
                "source": source,
                "source_url": f"https://ejemplo.test/{source}",
                "retrieved_at": "2026-09-26T20:00:00+00:00",
                "match_method": "exact_gtin" if source == "open_prices" else "text_reviewed",
                "match_confidence": math.nan if source == "open_prices" else 0.9,
            }
        ]
    )


def test_construir_observaciones_precio_open_prices():
    resultado = construir_observaciones_precio(_precios_sinteticos("open_prices"))

    assert len(resultado) == 1
    fila = resultado.iloc[0]
    assert fila["field"] == "price"
    assert fila["value"] == "115.0"
    assert fila["status"] == "REAL"
    assert fila["method"] == "exact_gtin"
    assert fila["confidence"] is None  # NaN de match_confidence -> None, nunca NaN "colado"


def test_construir_observaciones_precio_qqp_incluye_confidence():
    resultado = construir_observaciones_precio(_precios_sinteticos("qqp_profeco"))

    fila = resultado.iloc[0]
    assert fila["method"] == "text_reviewed"
    assert fila["confidence"] == 0.9


def test_precios_vacio_devuelve_dataframe_vacio_con_columnas():
    resultado = construir_observaciones_precio(pd.DataFrame(columns=["code", "price"]))
    assert resultado.empty
    assert list(resultado.columns) == list(COLUMNAS_OBSERVACION)


# --------------------------------------------------------------------------
# resolver_observaciones / resolver_valor
# --------------------------------------------------------------------------


def _observaciones_multiples() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "code": "1111111111111",
                "field": "price",
                "value": "10.0",
                "status": "REAL",
                "source": "open_prices",
                "source_url": None,
                "retrieved_at": "2026-01-01T00:00:00+00:00",
                "snapshot_id": "off_csv_20260919",
                "method": "exact_gtin",
                "confidence": None,
                "quality_flag": None,
            },
            {
                "code": "1111111111111",
                "field": "price",
                "value": "12.0",
                "status": "REAL",
                "source": "open_prices",
                "source_url": None,
                "retrieved_at": "2026-06-01T00:00:00+00:00",  # más reciente: debe ganar
                "snapshot_id": "off_csv_20260919",
                "method": "exact_gtin",
                "confidence": None,
                "quality_flag": None,
            },
            {
                "code": "2222222222222",
                "field": "product_name",
                "value": "Nombre recuperado",
                "status": "REAL",
                "source": "openfoodfacts_api_producto",
                "source_url": None,
                "retrieved_at": "2026-01-01T00:00:00+00:00",
                "snapshot_id": "off_csv_20260919",
                "method": "api_producto_individual",
                "confidence": None,
                "quality_flag": None,
            },
        ]
    )


def test_resolver_observaciones_elige_la_mas_reciente_entre_reales():
    resueltas = resolver_observaciones(_observaciones_multiples())

    fila = resueltas[(resueltas["code"] == "1111111111111") & (resueltas["field"] == "price")].iloc[0]
    assert fila["value"] == "12.0"


def test_resolver_observaciones_nunca_prioriza_imputed_sobre_real():
    observaciones = pd.concat(
        [
            _observaciones_multiples(),
            pd.DataFrame(
                [
                    {
                        "code": "1111111111111",
                        "field": "price",
                        "value": "999.0",
                        "status": "IMPUTED",
                        "source": "fuente_imputada",
                        "source_url": None,
                        "retrieved_at": "2026-12-31T00:00:00+00:00",  # más reciente, pero IMPUTED
                        "snapshot_id": "off_csv_20260919",
                        "method": "modelo",
                        "confidence": None,
                        "quality_flag": None,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    resueltas = resolver_observaciones(observaciones)

    fila = resueltas[(resueltas["code"] == "1111111111111") & (resueltas["field"] == "price")].iloc[0]
    assert fila["value"] == "12.0"  # sigue ganando la REAL más reciente, no la IMPUTED
    assert fila["status"] == "REAL"


def test_resolver_observaciones_vacio():
    resultado = resolver_observaciones(pd.DataFrame(columns=list(COLUMNAS_OBSERVACION)))
    assert resultado.empty


def test_resolver_valor_encuentra_la_ganadora():
    resueltas = resolver_observaciones(_observaciones_multiples())
    valor = resolver_valor(resueltas, "2222222222222", "product_name")
    assert valor["value"] == "Nombre recuperado"
    assert valor["status"] == "REAL"


def test_resolver_valor_sin_observaciones_es_unavailable():
    resueltas = resolver_observaciones(_observaciones_multiples())
    valor = resolver_valor(resueltas, "9999999999999", "price")
    assert valor["status"] == "UNAVAILABLE"
    assert valor["value"] is None
