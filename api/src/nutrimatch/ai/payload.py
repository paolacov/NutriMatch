"""Arma el payload de hechos. No recalcula. No imputa. NULL se conserva."""

from __future__ import annotations

from typing import Any

from nutrimatch.schemas.product import ProductDetail
from nutrimatch.schemas.profile import PRIORITY_LABELS, UserProfile
from nutrimatch.schemas.ranking import RankingItem

BANDA_ES = {
    "ranking": "En ranking",
    "no_verificable": "No verificable",
    "informacion_insuficiente": "Información insuficiente",
    "excluido": "Excluido",
}


def _campo(valor: Any, status: str, *, source: str | None = None, note: str | None = None) -> dict:
    return {
        "value": valor,
        "status": status,
        "source": source,
        "note": note,
        "available": valor is not None and status != "UNAVAILABLE",
    }


def construir_payload(
    *,
    detalle: ProductDetail,
    item: RankingItem | None,
    profile: UserProfile,
    case_id: str = "ask",
    case_note: str = "",
) -> dict[str, Any]:
    nombre = detalle.name.value
    precio = detalle.price
    alergia_evaluable = bool(profile.allergen_tags)
    dieta_evaluable = profile.diet is not None
    expl = item.explanation if item is not None else None

    nutrientes = [
        {
            "key": n.key,
            "label": n.label,
            "per100g": n.per100g,
            "unit": n.unit,
            "status": n.status,
            "available": n.per100g is not None,
        }
        for n in detalle.nutrients
    ]

    if expl is not None:
        dimensiones = {
            clave: {
                "label": PRIORITY_LABELS[clave],
                "subscore": dim.subscore,
                "weight": dim.weight,
                "available": dim.available,
                "weighted_contribution": dim.weighted_contribution,
            }
            for clave, dim in expl.dimensions.items()
        }
        d1_nutrientes = {
            clave: {
                "percentile": nut.percentile,
                "sign": nut.sign,
                "available": nut.available,
                "contribution": nut.contribution,
            }
            for clave, nut in expl.d1_nutrients.items()
        }
        missing_flags = list(expl.missing_flags)
        name_used_fallback = expl.name_used_fallback
    else:
        dimensiones = {}
        d1_nutrientes = {}
        missing_flags = []
        name_used_fallback = False

    observed = {
        "code": detalle.code,
        "name": _campo(nombre, detalle.name.status, source=detalle.name.source),
        "brand": _campo(detalle.brand.value, detalle.brand.status),
        "quantity": detalle.quantity,
        "category": detalle.category,
        "nova_group": detalle.nova_group,
        "labels": list(detalle.labels),
        "allergens": list(detalle.allergens),
        "traces": list(detalle.traces),
        "ingredients": list(detalle.ingredients)[:40],
        "nutrients": nutrientes,
        "data_quality": {
            "score": detalle.data_quality_score,
            "level": detalle.data_quality_level,
            "label": detalle.data_quality_label,
            "detalle": detalle.data_quality_detalle,
            "available": detalle.data_quality_label is not None,
        },
    }
    if item is None:
        calculated = {
            "score": None,
            "band": None,
            "band_label": None,
            "cov": None,
            "d1": None,
            "d2": None,
            "d3": None,
            "dimensions": dimensiones,
            "d1_nutrients": d1_nutrientes,
            "missing_flags": missing_flags,
            "name_used_fallback": name_used_fallback,
            "allergy_status": None,
            "diet_status": None,
        }
        d1_ausente = True
        d2_ausente = True
        d3_ausente = True
        score_ausente = True
        allergy_status = None
        diet_status = None
    else:
        calculated = {
            "score": item.score,
            "band": item.band,
            "band_label": BANDA_ES[item.band],
            "cov": item.cov,
            "d1": item.d1,
            "d2": item.d2,
            "d3": item.d3,
            "dimensions": dimensiones,
            "d1_nutrients": d1_nutrientes,
            "missing_flags": missing_flags,
            "name_used_fallback": name_used_fallback,
            "allergy_status": item.allergy_status,
            "diet_status": item.diet_status,
        }
        d1_ausente = item.d1 is None
        d2_ausente = item.d2 is None
        d3_ausente = item.d3 is None
        score_ausente = item.score is None
        allergy_status = item.allergy_status
        diet_status = item.diet_status

    unavailable = {
        "name": nombre is None,
        "brand": detalle.brand.value is None,
        "price": precio.status != "REAL" or precio.value is None,
        "d1": d1_ausente,
        "d2": d2_ausente,
        "d3": d3_ausente,
        "score": score_ausente,
        "allergens_registered": not detalle.allergens,
        "traces_registered": not detalle.traces,
        "labels_registered": not detalle.labels,
    }

    return {
        "spike": {
            "id": case_id,
            "note": case_note,
            "role": "capa_de_lenguaje",
            "engine_is_source_of_truth": True,
        },
        "profile": {
            "allergen_tags": list(profile.allergen_tags),
            "diet": profile.diet,
            "valued_labels": list(profile.valued_labels),
            "priority_order": list(profile.priority_order),
        },
        "product": observed,
        "decision": calculated,
        "constraints": {
            "allergy_status": allergy_status,
            "diet_status": diet_status,
            "allergy_evaluable": alergia_evaluable,
            "diet_evaluable": dieta_evaluable,
        },
        "price": {
            "value": precio.value if precio.status == "REAL" else None,
            "status": precio.status if precio.status != "SYNTHETIC" else "UNAVAILABLE",
            "source": precio.source if precio.status == "REAL" else None,
            "role": "informativo_no_puntua",
            "available": precio.status == "REAL" and precio.value is not None,
        },
        "availability": unavailable,
    }
