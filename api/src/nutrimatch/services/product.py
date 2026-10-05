"""Ensambla la ficha de anaquel desde una fila del catálogo. No calcula scores."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from nutrimatch.engine.demo_price import (
    FUENTE_PRECIO_DEMOSTRACION,
    NOTA_PRECIO_DEMOSTRACION,
    precio_demostracion_mxn,
)
from nutrimatch.schemas.product import NutrientRow, ProductDetail, ProvenanceStatus, ProvenanceValue

NUTRIENTES_FICHA: tuple[tuple[str, str, str, str], ...] = (
    ("energy", "Energía (kcal)", "energy-kcal_100g", "kcal"),
    ("proteins", "Proteína", "proteins_100g", "g"),
    ("carbohydrates", "Carbohidratos", "carbohydrates_100g", "g"),
    ("sugars", "Azúcares", "sugars_100g", "g"),
    ("fat", "Grasas", "fat_100g", "g"),
    ("saturated-fat", "Grasa saturada", "saturated-fat_100g", "g"),
    ("fiber", "Fibra", "fiber_100g", "g"),
    ("salt", "Sal", "salt_100g", "g"),
)

_ETIQUETA_CALIDAD = {
    "alta": "Alta",
    "media": "Media",
    "baja": "Información insuficiente",
    "insuficiente": "Información insuficiente",
}

_STATUS_VALIDOS = {"REAL", "DERIVED", "IMPUTED", "SYNTHETIC", "UNAVAILABLE"}
_SENTINELAS_TEXTO_AUSENTE = frozenset({"", "none", "<na>"})
_SENTINELAS_TEXTO_AUSENTE_O_NAN = _SENTINELAS_TEXTO_AUSENTE | {"nan"}


def _es_nulo(valor: Any, *, literal_nan_es_nulo: bool = True) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    if isinstance(valor, str):
        sentinelas = _SENTINELAS_TEXTO_AUSENTE_O_NAN if literal_nan_es_nulo else _SENTINELAS_TEXTO_AUSENTE
        return valor.strip().lower() in sentinelas
    return False


def _texto(valor: Any, *, literal_nan_es_nulo: bool = True) -> str | None:
    if _es_nulo(valor, literal_nan_es_nulo=literal_nan_es_nulo):
        return None
    texto = str(valor).strip()
    return texto or None


def _url_imagen(fila: pd.Series) -> str | None:
    """Foto de anaquel usable. Una URL de Open Food Facts bajo ``/invalid/`` no carga.

    El export guarda esa ruta cuando el código no es un GTIN válido. El navegador
    recibe 404 y la ficha se queda sin imagen. En ese caso el dato es ausencia.
    """
    url = _texto(fila.get("image_small_url")) or _texto(fila.get("image_url"))
    if url is None:
        return None
    if "/invalid/" in url.lower():
        return None
    if not url.lower().startswith(("http://", "https://")):
        return None
    return url


def _texto_nombre(valor: Any) -> str | None:
    """Nombre para mostrar: conserva el literal ``NAN`` del dataset.

    ``_texto`` trata la cadena ``nan`` como nulo porque es el residuo de B13
    (``str(float("nan"))``). Ese sentinel no debe borrar un ``product_name``
    real. El float NaN de pandas sigue siendo nulo.
    """
    return _texto(valor, literal_nan_es_nulo=False)


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


def etiqueta_calidad(nivel: Any) -> str | None:
    texto = _texto(nivel)
    if texto is None:
        return None
    return _ETIQUETA_CALIDAD.get(texto.lower())


def _calidad(fila: pd.Series) -> tuple[float | None, str | None, str | None, str | None]:
    score = _float_or_none(fila.get("data_quality_score"))
    nivel = _texto(fila.get("data_quality_level"))
    etiqueta = etiqueta_calidad(nivel)
    detalle = _texto(fila.get("data_quality_detalle"))
    return score, nivel, etiqueta, detalle


def _precio(fila: pd.Series) -> ProvenanceValue:
    """REAL se conserva. UNAVAILABLE con GTIN sale como SYNTHETIC de demostración.

    El monto sintético no se lee del Parquet. IMPUTED no se promociona a REAL.
    Un REAL sin número no se rellena: queda UNAVAILABLE.
    """
    status = _status(fila.get("price_status"), "UNAVAILABLE")
    if status == "REAL":
        numero = _float_or_none(fila.get("price"))
        if numero is None:
            return ProvenanceValue(value=None, status="UNAVAILABLE")
        return ProvenanceValue(value=numero, status="REAL", source=_texto(fila.get("price_source")))
    if status == "SYNTHETIC":
        numero = _float_or_none(fila.get("price"))
        if numero is None:
            return _precio_demostracion(fila)
        return ProvenanceValue(
            value=numero,
            status="SYNTHETIC",
            source=_texto(fila.get("price_source")) or FUENTE_PRECIO_DEMOSTRACION,
            note=_texto(fila.get("price_note")) or NOTA_PRECIO_DEMOSTRACION,
        )
    if status == "UNAVAILABLE":
        return _precio_demostracion(fila)
    return ProvenanceValue(value=None, status=status)


def _precio_demostracion(fila: pd.Series) -> ProvenanceValue:
    codigo = _texto(fila.get("code"))
    if not codigo:
        return ProvenanceValue(value=None, status="UNAVAILABLE")
    return ProvenanceValue(
        value=float(precio_demostracion_mxn(codigo)),
        status="SYNTHETIC",
        source=FUENTE_PRECIO_DEMOSTRACION,
        note=NOTA_PRECIO_DEMOSTRACION,
    )


def detalle_desde_fila(fila: pd.Series) -> ProductDetail:
    nombre = _texto_nombre(fila.get("product_name_homologated")) or _texto_nombre(fila.get("product_name"))
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
    calidad_score, calidad_nivel, calidad_label, calidad_detalle = _calidad(fila)
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
        image_url=_url_imagen(fila),
        image_hint="Anaquel",
        nutrients=[_nutriente(fila, key, label, col, unit) for key, label, col, unit in NUTRIENTES_FICHA],
        ingredients=ingredientes,
        allergens=_tags(fila.get("allergens")),
        traces=_tags(fila.get("traces")),
        labels=_tags(fila.get("labels_tags")),
        price=_precio(fila),
        nova_group=_float_or_none(fila.get("nova_group")),
        data_quality_score=calidad_score,
        data_quality_level=calidad_nivel,
        data_quality_label=calidad_label,
        data_quality_detalle=calidad_detalle,
    )
