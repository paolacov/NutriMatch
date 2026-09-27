"""Resumen agregado del carrito (decisión A12).

No puntúa: promedia nutrientes por 100 g (o pondera por gramos si *todos* tienen
``quantity`` parseable) y reparte los productos en cubetas. Un dato ausente es
NULL + cobertura, nunca cero (A2). El precio no entra (A5).
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any, Literal

MetodoAgregacion = Literal["promedio_100g", "ponderado_gramos"]

PLATO_FRUTAS_VERDURAS = "frutas_verduras"
PLATO_CEREALES = "cereales"
PLATO_LEGUMINOSAS_AOA = "leguminosas_aoa"
NO_CLASIFICADO = "unclassified"

PLATO_LABELS: dict[str, str] = {
    PLATO_FRUTAS_VERDURAS: "Verduras y frutas",
    PLATO_CEREALES: "Cereales",
    PLATO_LEGUMINOSAS_AOA: "Leguminosas y alimentos de origen animal",
    NO_CLASIFICADO: "no clasificado",
}

PLATO_ORDEN: tuple[str, ...] = (
    PLATO_FRUTAS_VERDURAS,
    PLATO_CEREALES,
    PLATO_LEGUMINOSAS_AOA,
    NO_CLASIFICADO,
)

# Mapa explícito y pequeño: solo tags que caen sin ambigüedad en un grupo NOM-043.
# Lo genérico (en:plant-based-foods-and-beverages, en:snacks, bebidas) no se fuerza.
_PLATO_POR_TAG: dict[str, str] = {
    "en:fruits": PLATO_FRUTAS_VERDURAS,
    "en:fresh-fruits": PLATO_FRUTAS_VERDURAS,
    "en:dried-fruits": PLATO_FRUTAS_VERDURAS,
    "en:fruits-based-foods": PLATO_FRUTAS_VERDURAS,
    "en:vegetables": PLATO_FRUTAS_VERDURAS,
    "en:fresh-vegetables": PLATO_FRUTAS_VERDURAS,
    "en:fruits-and-vegetables": PLATO_FRUTAS_VERDURAS,
    "en:vegetables-based-foods": PLATO_FRUTAS_VERDURAS,
    "en:cereals-and-potatoes": PLATO_CEREALES,
    "en:cereals": PLATO_CEREALES,
    "en:breakfast-cereals": PLATO_CEREALES,
    "en:breads": PLATO_CEREALES,
    "en:pastas": PLATO_CEREALES,
    "en:rice": PLATO_CEREALES,
    "en:rices": PLATO_CEREALES,
    "en:flours": PLATO_CEREALES,
    "en:cereal-flours": PLATO_CEREALES,
    "en:corn": PLATO_CEREALES,
    "en:oats": PLATO_CEREALES,
    "en:tortillas": PLATO_CEREALES,
    "en:corn-tortillas": PLATO_CEREALES,
    "en:potatoes": PLATO_CEREALES,
    "en:legumes": PLATO_LEGUMINOSAS_AOA,
    "en:legumes-and-their-products": PLATO_LEGUMINOSAS_AOA,
    "en:beans": PLATO_LEGUMINOSAS_AOA,
    "en:lentils": PLATO_LEGUMINOSAS_AOA,
    "en:chickpeas": PLATO_LEGUMINOSAS_AOA,
    "en:milk-and-dairy-products": PLATO_LEGUMINOSAS_AOA,
    "en:dairies": PLATO_LEGUMINOSAS_AOA,
    "en:cheeses": PLATO_LEGUMINOSAS_AOA,
    "en:yogurts": PLATO_LEGUMINOSAS_AOA,
    "en:milks": PLATO_LEGUMINOSAS_AOA,
    "en:meats": PLATO_LEGUMINOSAS_AOA,
    "en:meats-and-their-products": PLATO_LEGUMINOSAS_AOA,
    "en:fresh-meats": PLATO_LEGUMINOSAS_AOA,
    "en:poultry": PLATO_LEGUMINOSAS_AOA,
    "en:fish-and-seafood": PLATO_LEGUMINOSAS_AOA,
    "en:fishes": PLATO_LEGUMINOSAS_AOA,
    "en:eggs": PLATO_LEGUMINOSAS_AOA,
    "en:chicken-eggs": PLATO_LEGUMINOSAS_AOA,
}

NUTRIENTES_CARRITO: tuple[tuple[str, str, str, str], ...] = (
    ("energy", "Energía (kcal)", "energy-kcal_100g", "kcal"),
    ("proteins", "Proteína", "proteins_100g", "g"),
    ("carbohydrates", "Carbohidratos", "carbohydrates_100g", "g"),
    ("sugars", "Azúcares", "sugars_100g", "g"),
    ("fat", "Grasas", "fat_100g", "g"),
    ("fiber", "Fibra", "fiber_100g", "g"),
    ("salt", "Sal", "salt_100g", "g"),
)

_UNIDAD_A_GRAMOS: dict[str, float] = {
    "g": 1.0,
    "gr": 1.0,
    "grs": 1.0,
    "gramo": 1.0,
    "gramos": 1.0,
    "kg": 1000.0,
    "ml": 1.0,
    "l": 1000.0,
    "lt": 1000.0,
    "litro": 1000.0,
    "litros": 1000.0,
    "cl": 10.0,
}

_CANTIDAD = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*([a-záéíóú.]+)\s*$",
    re.IGNORECASE,
)


def _es_nulo(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return isinstance(valor, str) and valor.strip().lower() in {"", "nan", "none", "<na>"}


def _float_or_none(valor: Any) -> float | None:
    if _es_nulo(valor):
        return None
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        numero = float(valor)
        return None if math.isnan(numero) else numero
    texto = str(valor).strip().replace(",", ".")
    try:
        numero = float(texto)
    except ValueError:
        return None
    return None if math.isnan(numero) else numero


def parsear_gramos(quantity: Any) -> float | None:
    """Convierte ``quantity`` a gramos (mL cuenta igual). Multipacks o sin unidad → None."""
    if _es_nulo(quantity):
        return None
    texto = str(quantity).strip()
    if not texto or "x" in texto.lower():
        return None
    match = _CANTIDAD.match(texto)
    if match is None:
        return None
    numero = _float_or_none(match.group(1).replace(",", "."))
    unidad = match.group(2).rstrip(".").lower()
    factor = _UNIDAD_A_GRAMOS.get(unidad)
    if numero is None or factor is None or numero <= 0:
        return None
    return numero * factor


def _tags(valor: Any) -> list[str]:
    if _es_nulo(valor):
        return []
    if isinstance(valor, (list, tuple)):
        return [str(parte).strip() for parte in valor if not _es_nulo(parte) and str(parte).strip()]
    return [parte.strip() for parte in str(valor).split(",") if parte.strip() and parte.strip().lower() != "nan"]


def _nutriente_de_fila(fila: Mapping[str, Any], columna: str) -> float | None:
    for clave in (f"{columna}_saneado", f"{columna}_bruto", columna):
        numero = _float_or_none(fila.get(clave))
        if numero is not None:
            return numero
    return None


def _categoria_de_fila(fila: Mapping[str, Any]) -> str:
    for clave in ("main_category", "main_category_en", "categoria_referencia"):
        if not _es_nulo(fila.get(clave)):
            texto = str(fila[clave]).strip()
            if texto:
                return texto
    return NO_CLASIFICADO


def _primer_grupo(tags: list[str]) -> str | None:
    for tag in reversed(tags):
        grupo = _PLATO_POR_TAG.get(tag.lower())
        if grupo is not None:
            return grupo
    return None


def grupo_plato(fila: Mapping[str, Any]) -> str:
    """Asigna un solo grupo NOM-043. Sin match → no clasificado; no se inventa.

    Se mira primero ``food_groups_tags`` (más estable) y luego ``main_category``.
    No se recorre toda ``categories_tags``: un ancestro genérico como
    ``en:legumes-and-their-products`` clasificaría nueces como origen animal.
    """
    por_grupo = _primer_grupo(_tags(fila.get("food_groups_tags")))
    if por_grupo is not None:
        return por_grupo
    por_principal = _primer_grupo(_tags(fila.get("main_category")))
    if por_principal is not None:
        return por_principal
    return NO_CLASIFICADO


def _cubetas(claves: list[str], n_productos: int, orden: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    conteo: dict[str, int] = {}
    for clave in claves:
        conteo[clave] = conteo.get(clave, 0) + 1
    if orden is not None:
        keys = list(orden)
    else:
        keys = sorted(conteo, key=lambda k: (-conteo[k], k))
        if NO_CLASIFICADO in keys:
            keys.remove(NO_CLASIFICADO)
            keys.append(NO_CLASIFICADO)
    denominador = n_productos if n_productos else 1
    return [
        {
            "key": clave,
            "label": PLATO_LABELS.get(clave, clave),
            "n": conteo.get(clave, 0),
            "share": (conteo.get(clave, 0) / denominador) if n_productos else 0.0,
        }
        for clave in keys
    ]


def resumir_carrito(filas: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Agrega las filas del carrito. ``filas`` ya resueltas; no busca en el catálogo."""
    n = len(filas)
    gramos = [parsear_gramos(fila.get("quantity")) for fila in filas]
    pondera = n > 0 and all(g is not None for g in gramos)
    metodo: MetodoAgregacion = "ponderado_gramos" if pondera else "promedio_100g"
    if n == 0:
        nota = "Carrito vacío."
    elif pondera:
        nota = "Ponderado por gramos: todos los productos tienen quantity en g o mL."
    else:
        nota = "Promedio por 100 g. No se pondera: falta quantity parseable en al menos un producto."

    nutrientes: list[dict[str, Any]] = []
    for key, label, columna, unit in NUTRIENTES_CARRITO:
        valores = [_nutriente_de_fila(fila, columna) for fila in filas]
        con_dato = [v for v in valores if v is not None]
        n_con_dato = len(con_dato)
        valor: float | None
        if n_con_dato == 0:
            valor = None
        elif pondera:
            pares = [(v, g) for v, g in zip(valores, gramos, strict=True) if v is not None and g is not None]
            peso = sum(g for _, g in pares)
            valor = (sum(v * g for v, g in pares) / peso) if peso else None
        else:
            valor = sum(con_dato) / n_con_dato
        nutrientes.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "value": valor,
                "status": "DERIVED" if valor is not None else "UNAVAILABLE",
                "n_with_data": n_con_dato,
                "n_products": n,
            }
        )

    categorias = [_categoria_de_fila(fila) for fila in filas]
    platos = [grupo_plato(fila) for fila in filas]
    return {
        "n_products": n,
        "method": metodo,
        "method_note": nota,
        "status": "DERIVED",
        "nutrients": nutrientes,
        "plato": _cubetas(platos, n, PLATO_ORDEN),
        "categories": _cubetas(categorias, n),
    }
