"""Ensambla la ficha de anaquel desde una fila del catálogo. No calcula scores."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from nutrimatch.schemas.product import NutrientRow, ProductDetail, ProvenanceStatus, ProvenanceValue

NUTRIENTES_FICHA: tuple[tuple[str, str, str, str], ...] = (
    ("energy", "Energía (kcal)", "energy-kcal_100g", "kcal"),
    ("proteins", "Proteína", "proteins_100g", "g"),
    ("carbohydrates", "Carbohidratos", "carbohydrates_100g", "g"),
    ("sugars", "Azúcares", "sugars_100g", "g"),
    ("fat", "Grasas", "fat_100g", "g"),
    ("fiber", "Fibra", "fiber_100g", "g"),
    ("salt", "Sal", "salt_100g", "g"),
)

_STATUS_VALIDOS = {"REAL", "DERIVED", "IMPUTED", "SYNTHETIC", "UNAVAILABLE"}


def _es_nulo(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return isinstance(valor, str) and valor.strip().lower() in {"", "nan", "none", "<na>"}


def _texto(valor: Any) -> str | None:
    if _es_nulo(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def _float_or_none(valor: Any) -> float | None:
    if _es_nulo(valor):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _status(valor: Any, por_defecto: ProvenanceStatus) -> ProvenanceStatus:
    texto = _texto(valor)
    if texto in _STATUS_VALIDOS:
        return texto  # type: ignore[return-value]
    return por_defecto


def _tags(valor: Any) -> list[str]:
    texto = _texto(valor)
    if texto is None:
        return []
    return [parte.strip() for parte in texto.split(",") if parte.strip() and parte.strip().lower() != "nan"]


def _nutriente(fila: pd.Series, key: str, label: str, columna: str, unit: str) -> NutrientRow:
    saneado = _float_or_none(fila.get(f"{columna}_saneado"))
    if saneado is not None:
        return NutrientRow(key=key, label=label, per100g=saneado, unit=unit, status="DERIVED")
    bruto = _float_or_none(fila.get(f"{columna}_bruto"))
    if bruto is not None:
        return NutrientRow(key=key, label=label, per100g=bruto, unit=unit, status="REAL")
    crudo = _float_or_none(fila.get(columna))
    if crudo is not None:
        return NutrientRow(key=key, label=label, per100g=crudo, unit=unit, status="REAL")
    return NutrientRow(key=key, label=label, per100g=None, unit=unit, status="UNAVAILABLE")


def _precio(fila: pd.Series) -> ProvenanceValue:
    status = _status(fila.get("price_status"), "UNAVAILABLE")
    if status != "REAL":
        return ProvenanceValue(value=None, status="UNAVAILABLE" if status == "UNAVAILABLE" else status)
    numero = _float_or_none(fila.get("price"))
    if numero is None:
        return ProvenanceValue(value=None, status="UNAVAILABLE")
    return ProvenanceValue(value=numero, status="REAL", source=_texto(fila.get("price_source")))


def detalle_desde_fila(fila: pd.Series) -> ProductDetail:
    nombre = _texto(fila.get("product_name_homologated")) or _texto(fila.get("product_name"))
    nombre_status = _status(fila.get("product_name_status"), "DERIVED" if nombre else "UNAVAILABLE")
    if nombre is None:
        nombre_status = "UNAVAILABLE"
    marca = _texto(fila.get("brand_original")) or _texto(fila.get("brands"))
    marca_status = _status(fila.get("brand_status"), "DERIVED" if marca else "UNAVAILABLE")
    if marca is None:
        marca_status = "UNAVAILABLE"
    categoria = (
        _texto(fila.get("main_category"))
        or _texto(fila.get("main_category_en"))
        or _texto(fila.get("categoria_referencia"))
    )
    ingredientes = _tags(fila.get("ingredients_text")) or _tags(fila.get("ingredients_tags"))
    return ProductDetail(
        code=str(fila["code"]),
        name=ProvenanceValue(
            value=nombre,
            status=nombre_status,
            source=_texto(fila.get("product_name_source")),
        ),
        brand=ProvenanceValue(value=marca, status=marca_status),
        quantity=_texto(fila.get("quantity")),
        category=categoria,
        image_url=_texto(fila.get("image_small_url")) or _texto(fila.get("image_url")),
        image_hint="Anaquel",
        nutrients=[_nutriente(fila, key, label, col, unit) for key, label, col, unit in NUTRIENTES_FICHA],
        ingredients=ingredientes,
        allergens=_tags(fila.get("allergens")),
        labels=_tags(fila.get("labels_tags")),
        price=_precio(fila),
        nova_group=_float_or_none(fila.get("nova_group")),
    )
