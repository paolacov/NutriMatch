"""Ensamblado del score de compatibilidad final: tres dimensiones ponderadas (decisiones A7, A10).

Combina los subpuntajes ya calculados de D1 (`nutrition_score`), D2 (`processing_score`, paso 6)
y D3 (`preference_score`) con los pesos de la usuaria (`user_weights`), aplicando la regla de
cobertura `cov` (`coverage`) y devolviendo una explicación completa por dimensión (A10).

**Fórmula de renormalización propuesta en el paso 7, pendiente de verificación en el
notebook**: cuando una dimensión no tiene dato, el score se calcula como el promedio ponderado
de las dimensiones disponibles, renormalizado sobre la suma de sus pesos
(``Σ wᵢ·Dᵢ / Σ wᵢ`` solo sobre las dimensiones con dato) — coherente con que `cov` ya mide
exactamente esa fracción de peso disponible. AGENTS.md (A7) fija que el score es "la suma
ponderada por los pesos de A6", pero no especifica esta renormalización para el caso de datos
parciales; se propone aquí y se documenta como tal.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict

from nutrimatch.engine.coverage import (
    UMBRAL_COV_INFORMACION_INSUFICIENTE,
    calcular_cov,
    es_informacion_insuficiente,
)

DIMENSIONES = ("D1", "D2", "D3")


def _es_nulo(valor: Any) -> bool:
    """True si `valor` no es un subpuntaje utilizable: `None` o `NaN` (float).

    Un caller que itere sobre un DataFrame de pandas entrega `NaN`, no `None`, cuando falta un
    subpuntaje — igual que en `nutrition_score._es_nulo`. Un chequeo ingenuo con `is not None`
    trataría un `NaN` como "disponible" por error, inflando `cov` artificialmente.
    """
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


class DetalleDimension(TypedDict):
    subpuntaje: float | None
    peso: float
    disponible: bool
    contribucion_ponderada: float | None


class ResultadoScore(TypedDict):
    score_final: float | None
    cov: float
    informacion_insuficiente: bool
    dimensiones: dict[str, DetalleDimension]


def calcular_score_compatibilidad(
    subpuntajes: dict[str, float | None],
    pesos: dict[str, float],
    umbral_cov: float = UMBRAL_COV_INFORMACION_INSUFICIENTE,
) -> ResultadoScore:
    """Ensambla el score final de compatibilidad para un producto y una usuaria.

    `subpuntajes` trae el subpuntaje (0-100) de cada dimensión o `None` si no es calculable para
    ese producto, con claves ``"D1"``, ``"D2"``, ``"D3"``. `pesos` trae el peso de cada
    dimensión para esa usuaria (ver `user_weights.convertir_prioridades_a_pesos`).

    Devuelve un diccionario con:
    - ``score_final``: `None` si `cov < umbral_cov` (banda "información insuficiente", A2);
      si no, el promedio ponderado renormalizado de las dimensiones disponibles.
    - ``cov``: la cobertura calculada (ver `coverage.calcular_cov`).
    - ``informacion_insuficiente``: booleano, resultado de comparar `cov` contra `umbral_cov`.
    - ``dimensiones``: detalle por dimensión (subpuntaje, peso, disponibilidad, contribución
      ponderada), listo para la explicación rica de la interfaz (decisión A10).
    """
    disponibilidad = {dimension: not _es_nulo(subpuntajes.get(dimension)) for dimension in DIMENSIONES}

    cov = calcular_cov(disponibilidad, pesos)
    insuficiente = es_informacion_insuficiente(cov, umbral_cov)

    peso_disponible = sum(pesos[d] for d in DIMENSIONES if disponibilidad[d])

    score_final: float | None = None
    if not insuficiente and peso_disponible > 0:
        suma_ponderada = sum(pesos[d] * subpuntajes[d] for d in DIMENSIONES if disponibilidad[d])
        score_final = suma_ponderada / peso_disponible

    detalle_dimensiones: dict[str, DetalleDimension] = {}
    for dimension in DIMENSIONES:
        disponible = disponibilidad[dimension]
        peso = pesos[dimension]
        subpuntaje = subpuntajes.get(dimension)
        detalle_dimensiones[dimension] = {
            "subpuntaje": subpuntaje,
            "peso": peso,
            "disponible": disponible,
            "contribucion_ponderada": (peso * subpuntaje) if disponible else None,
        }

    return {
        "score_final": score_final,
        "cov": cov,
        "informacion_insuficiente": insuficiente,
        "dimensiones": detalle_dimensiones,
    }
