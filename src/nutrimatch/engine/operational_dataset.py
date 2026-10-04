"""Cierra el catálogo operativo de 13 093 filas sin recalcular el ranking.

Parte de ``dataset_referencia_20260929.parquet`` (percentiles, D2, identidad) y le
une solo observaciones REAL que siguen en ese universo:

- precio Open Prices (``exact_gtin``) y QQP (``text_reviewed``);
- nombres recuperados por la API de producto.

Los productos sin precio observado quedan ``price_status=UNAVAILABLE`` y
``price`` nulo. El precio de demostración no se escribe aquí: lo emite la ficha.
Las columnas de score (``d1``, ``d3``, ``cov``, ``score_final``) no se materializan.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from nutrimatch.engine.data_quality import anexar_indicadores_calidad
from nutrimatch.engine.observations import _es_nulo, resolver_observaciones

FUENTES_PRECIO_REAL = frozenset({"open_prices", "qqp_profeco"})
METODO_POR_FUENTE = {
    "open_prices": "exact_gtin",
    "qqp_profeco": "text_reviewed",
}
FUENTE_NOMBRE_API = "openfoodfacts_api_producto"
COLUMNAS_PRECIO = (
    "price",
    "price_status",
    "price_source",
    "price_source_url",
    "price_retrieved_at",
    "price_match_method",
    "price_match_confidence",
    "price_confidence",
)


def _codigo(valor: Any) -> str:
    if _es_nulo(valor):
        return ""
    return str(valor).strip()


def _texto(valor: Any) -> str | None:
    if _es_nulo(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def _float_o_none(valor: Any) -> float | None:
    if _es_nulo(valor):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _observaciones_de_campo(observaciones: pd.DataFrame, campo: str) -> pd.DataFrame:
    if observaciones.empty or "field" not in observaciones.columns:
        return observaciones.iloc[0:0]
    return observaciones.loc[observaciones["field"].astype(str) == campo].copy()


def aplicar_nombres_reales(frame: pd.DataFrame, observaciones: pd.DataFrame) -> pd.DataFrame:
    """Pisa el nombre visible solo donde hay una observación REAL de ``product_name``.

    No inventa nombre para el resto. No toca ``product_name_original`` ni ``product_name_crudo``.
    """
    if "code" not in frame.columns:
        raise KeyError("el catálogo no trae code")
    salida = frame.copy()
    salida["code"] = [_codigo(c) for c in salida["code"].tolist()]
    if "product_name_source" not in salida.columns:
        salida["product_name_source"] = ["off_export"] * len(salida)

    nombres = _observaciones_de_campo(observaciones, "product_name")
    if nombres.empty:
        return salida
    nombres["code"] = [_codigo(c) for c in nombres["code"].tolist()]
    resueltas = resolver_observaciones(nombres)
    por_codigo: dict[str, dict[str, Any]] = {}
    for fila in resueltas.to_dict(orient="records"):
        if str(fila.get("status")) != "REAL":
            continue
        valor = _texto(fila.get("value"))
        if valor is None:
            continue
        por_codigo[_codigo(fila.get("code"))] = fila

    codigos = salida["code"].tolist()
    visibles = salida["product_name"].tolist() if "product_name" in salida.columns else [None] * len(salida)
    homologados = (
        salida["product_name_homologated"].tolist()
        if "product_name_homologated" in salida.columns
        else list(visibles)
    )
    estados = (
        salida["product_name_status"].tolist()
        if "product_name_status" in salida.columns
        else ["DERIVED"] * len(salida)
    )
    fuentes = salida["product_name_source"].tolist()
    campos = (
        salida["product_name_field_source"].tolist()
        if "product_name_field_source" in salida.columns
        else [None] * len(salida)
    )
    for i, codigo in enumerate(codigos):
        obs = por_codigo.get(codigo)
        if obs is None:
            continue
        valor = _texto(obs.get("value"))
        fuente = _texto(obs.get("source")) or FUENTE_NOMBRE_API
        visibles[i] = valor
        homologados[i] = valor
        estados[i] = "REAL"
        fuentes[i] = fuente
        campos[i] = fuente
    salida["product_name"] = visibles
    salida["product_name_homologated"] = homologados
    salida["product_name_status"] = estados
    salida["product_name_source"] = fuentes
    if "product_name_field_source" in frame.columns or any(c is not None for c in campos):
        salida["product_name_field_source"] = campos
    return salida


def unir_precios_reales(frame: pd.DataFrame, observaciones: pd.DataFrame) -> pd.DataFrame:
    """Une el precio REAL más reciente. QQP no se trata como match por GTIN.

    Una fila sin observación queda UNAVAILABLE con precio nulo. No escribe SYNTHETIC.
    """
    if "code" not in frame.columns:
        raise KeyError("el catálogo no trae code")
    choque = [col for col in COLUMNAS_PRECIO if col in frame.columns]
    if choque:
        raise ValueError(f"el catálogo ya trae columnas de precio: {choque}")

    salida = frame.copy()
    salida["code"] = [_codigo(c) for c in salida["code"].tolist()]
    codigos = salida["code"].tolist()
    universo = set(codigos)

    precios = _observaciones_de_campo(observaciones, "price")
    por_codigo: dict[str, dict[str, Any]] = {}
    if not precios.empty:
        precios["code"] = [_codigo(c) for c in precios["code"].tolist()]
        precios = precios.loc[precios["code"].isin(universo)]
        if not precios.empty:
            resueltas = resolver_observaciones(precios)
            for fila in resueltas.to_dict(orient="records"):
                if str(fila.get("status")) != "REAL":
                    continue
                codigo = _codigo(fila.get("code"))
                if codigo not in universo:
                    continue
                fuente = _texto(fila.get("source"))
                metodo = _texto(fila.get("method"))
                if fuente not in FUENTES_PRECIO_REAL:
                    raise ValueError(f"fuente de precio no reconocida para {codigo}: {fuente}")
                if metodo != METODO_POR_FUENTE[fuente]:
                    raise ValueError(
                        f"{codigo}: {fuente} debe ir con {METODO_POR_FUENTE[fuente]}, llegó {metodo}"
                    )
                monto = _float_o_none(fila.get("value"))
                if monto is None:
                    raise ValueError(f"{codigo}: price_status REAL sin monto")
                por_codigo[codigo] = {
                    "price": monto,
                    "price_status": "REAL",
                    "price_source": fuente,
                    "price_source_url": _texto(fila.get("source_url")),
                    "price_retrieved_at": _texto(fila.get("retrieved_at")),
                    "price_match_method": metodo,
                    "price_match_confidence": _float_o_none(fila.get("confidence")),
                    "price_confidence": _float_o_none(fila.get("confidence")),
                }

    filas: list[dict[str, Any]] = []
    for codigo in codigos:
        obs = por_codigo.get(codigo)
        if obs is None:
            filas.append(
                {
                    "code": codigo,
                    "price": None,
                    "price_status": "UNAVAILABLE",
                    "price_source": None,
                    "price_source_url": None,
                    "price_retrieved_at": None,
                    "price_match_method": None,
                    "price_match_confidence": None,
                    "price_confidence": None,
                }
            )
        else:
            filas.append({"code": codigo, **obs})
    tabla = pd.DataFrame(filas)
    tabla["price"] = pd.array(tabla["price"].tolist(), dtype="Float64")
    tabla["price_match_confidence"] = pd.array(tabla["price_match_confidence"].tolist(), dtype="Float64")
    tabla["price_confidence"] = pd.array(tabla["price_confidence"].tolist(), dtype="Float64")
    unido = salida.merge(tabla, on="code", how="left", validate="one_to_one")
    if len(unido) != len(salida):
        raise RuntimeError("el join de precios cambió el número de filas")
    if (unido["price_status"] == "SYNTHETIC").any():
        raise RuntimeError("el catálogo operativo no materializa precios SYNTHETIC")
    return unido


def cerrar_dataset_operativo(base: pd.DataFrame, observaciones: pd.DataFrame) -> pd.DataFrame:
    """Nombres REAL, precios REAL/UNAVAILABLE y calidad DERIVED. No recalcula D1/D2/D3."""
    con_nombres = aplicar_nombres_reales(base, observaciones)
    con_precios = unir_precios_reales(con_nombres, observaciones)
    return anexar_indicadores_calidad(con_precios)
