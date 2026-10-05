"""Ensambla el resumen A12 desde el catálogo. No recalcula D1/D2/D3."""

from __future__ import annotations

from nutrimatch.engine.cart_summary import resumir_carrito
from nutrimatch.schemas.cart import CartSummary
from nutrimatch.services.catalog import Catalog


def resumir_codes(catalog: Catalog, codes: list[str]) -> CartSummary:
    vistos: set[str] = set()
    filas = []
    for code in codes:
        clave = str(code).strip()
        if not clave or clave in vistos:
            continue
        vistos.add(clave)
        coincidencias = catalog.df.loc[catalog.df["code"] == clave]
        if coincidencias.empty:
            continue
        filas.append(coincidencias.iloc[0])
    return CartSummary.model_validate(resumir_carrito(filas))
