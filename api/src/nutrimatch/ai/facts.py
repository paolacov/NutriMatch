"""Ensambla hechos deterministas para el LLM. Cero imputación. Cero recálculo de score."""

from __future__ import annotations

from typing import Any

from nutrimatch.ai.knowledge.plato import texto_educativo
from nutrimatch.ai.payload import construir_payload
from nutrimatch.core.errors import ProductNotFoundError
from nutrimatch.engine.cart_summary import PLATO_LABELS, grupo_plato
from nutrimatch.schemas.product import ProductDetail
from nutrimatch.schemas.profile import UserProfile
from nutrimatch.schemas.ranking import RankingItem
from nutrimatch.services.cart import resumir_codes
from nutrimatch.services.catalog import Catalog
from nutrimatch.services.product import _texto, _texto_nombre, detalle_desde_fila
from nutrimatch.services.ranking import RankingService

NUTRIENTE_ALIAS: dict[str, str] = {
    "proteina": "proteins",
    "proteína": "proteins",
    "protein": "proteins",
    "azucar": "sugars",
    "azúcar": "sugars",
    "azucares": "sugars",
    "azúcares": "sugars",
    "fibra": "fiber",
    "energia": "energy",
    "energía": "energy",
    "calorias": "energy",
    "calorías": "energy",
    "grasa saturada": "saturated-fat",
    "saturada": "saturated-fat",
    "grasa": "fat",
    "grasas": "fat",
    "carbohidrato": "carbohydrates",
    "carbohidratos": "carbohydrates",
    "sal": "salt",
    "sodio": "salt",
}


def detectar_nutriente(mensaje: str | None) -> str | None:
    if not mensaje:
        return None
    bajo = mensaje.lower()
    for alias, clave in NUTRIENTE_ALIAS.items():
        if alias in bajo:
            return clave
    return None


def _cargar_producto(
    catalogo: Catalog,
    servicio: RankingService,
    code: str,
    profile: UserProfile,
) -> tuple[ProductDetail, RankingItem]:
    detalle = detalle_desde_fila(catalogo.get_row(code))
    item = servicio.explain(code, profile)
    return detalle, item


def _nombre_mostrar(detalle: ProductDetail) -> str:
    return detalle.name.value or f"código {detalle.code}"


def comparar_nutriente(detalles: list[ProductDetail], clave: str) -> dict[str, Any]:
    filas: list[dict[str, Any]] = []
    label = clave
    unit = ""
    for detalle in detalles:
        fila_n = next((n for n in detalle.nutrients if n.key == clave), None)
        if fila_n is not None:
            label = fila_n.label
            unit = fila_n.unit
            valor = fila_n.per100g
        else:
            valor = None
        filas.append(
            {
                "code": detalle.code,
                "name": _nombre_mostrar(detalle),
                "value": valor,
                "unit": unit,
                "available": valor is not None,
            }
        )
    disponibles = [f for f in filas if f["available"]]
    complete = len(disponibles) == len(filas) and len(filas) >= 2
    highest_name = None
    highest_code = None
    if complete:
        ganador = max(disponibles, key=lambda f: float(f["value"]))
        highest_name = ganador["name"]
        highest_code = ganador["code"]
    return {
        "nutrient": clave,
        "label": label,
        "rows": filas,
        "complete": complete,
        "highest_name": highest_name,
        "highest_code": highest_code,
    }


def ensamblar_hechos(
    *,
    catalogo: Catalog,
    servicio: RankingService,
    codes: list[str],
    profile: UserProfile,
    intent: str,
    message: str | None,
    culinary_goal: str | None = None,
    surface: str = "product",
) -> dict[str, Any]:
    unicos = [c.strip() for c in codes if c and c.strip()]
    detalles: list[ProductDetail] = []
    items: list[RankingItem] = []
    for code in unicos:
        try:
            detalle, item = _cargar_producto(catalogo, servicio, code, profile)
        except ProductNotFoundError:
            continue
        detalles.append(detalle)
        items.append(item)

    payload: dict[str, Any] = {
        "intent": intent,
        "surface": surface,
        "message": (message or "").strip() or None,
        "profile": {
            "allergen_tags": list(profile.allergen_tags),
            "diet": profile.diet,
            "valued_labels": list(profile.valued_labels),
            "priority_order": list(profile.priority_order),
        },
        "plato_education": [] if intent == "fun_fact" else texto_educativo(),
        "codes_requested": unicos,
        "codes_found": [d.code for d in detalles],
    }

    if detalles:
        principal = construir_payload(
            detalle=detalles[0],
            item=items[0],
            profile=profile,
            case_id=intent,
            case_note=surface,
        )
        payload.update(principal)
        payload["products"] = [
            construir_payload(detalle=d, item=i, profile=profile, case_id=intent, case_note=surface)
            for d, i in zip(detalles, items, strict=True)
        ]

    if intent in {"compare", "ask"} and len(detalles) >= 2:
        clave = detectar_nutriente(message) or "proteins"
        payload["comparison"] = comparar_nutriente(detalles, clave)

    if intent in {"recipe", "ask"} and detalles:
        observados: list[str] = []
        for d in detalles:
            observados.extend(d.ingredients)
        restricciones: list[str] = []
        if profile.allergen_tags:
            restricciones.append("alergias: " + ", ".join(profile.allergen_tags))
        if profile.diet:
            restricciones.append(f"dieta: {profile.diet}")
        payload["recipe_context"] = {
            "product_names": [_nombre_mostrar(d) for d in detalles],
            "observed_ingredients": observados,
            "restrictions": restricciones,
            "culinary_goal": culinary_goal,
            "nutrition_available": False,
        }

    if intent in {"recipe", "normalize_product", "ask"} and detalles:
        fuentes: list[dict[str, Any]] = []
        for d in detalles:
            try:
                fila = catalogo.get_row(d.code)
            except ProductNotFoundError:
                fila = None
            original = None
            generic = None
            categories = None
            ingredients_text = None
            if fila is not None:
                original = _texto_nombre(fila.get("product_name"))
                generic = _texto(fila.get("generic_name"))
                categories = _texto(fila.get("categories_tags")) or _texto(fila.get("main_category")) or d.category
                ingredients_text = _texto(fila.get("ingredients_text"))
            fuentes.append(
                {
                    "code": d.code,
                    "original_name": original,
                    "generic_name": generic,
                    "brand": d.brand.value if isinstance(d.brand.value, str) else None,
                    "categories": categories,
                    "ingredients_text": (ingredients_text or "")[:500] or None,
                    "quantity": d.quantity,
                    "ingredients": list(d.ingredients)[:40],
                }
            )
        payload["normalize_sources"] = fuentes

    if intent in {"plato", "ask", "recipe", "fun_fact"} and detalles:
        grupos = []
        for d in detalles:
            grupo = grupo_plato(catalogo.get_row(d.code))
            grupos.append(
                {
                    "code": d.code,
                    "name": _nombre_mostrar(d),
                    "group": grupo,
                    "label": PLATO_LABELS.get(grupo, grupo),
                }
            )
        payload["plato_groups"] = grupos

    if intent in {"plato", "recipe"} and unicos:
        try:
            payload["cart_summary"] = resumir_codes(catalogo, unicos).model_dump()
        except Exception:
            payload["cart_summary"] = None

    return payload
