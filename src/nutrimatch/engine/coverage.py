"""Regla de cobertura `cov` y banda de "información insuficiente" (decisión A2, AGENTS.md).

    cov = (suma de los pesos de las dimensiones que SÍ tienen dato) / (suma de los pesos totales)

Si `cov < 0.5`, el producto no entra al ranking para esa usuaria: va a la banda "información
insuficiente", que se muestra separada (A2). El umbral 0.5 es el que fija A2 explícitamente.
"""

from __future__ import annotations

UMBRAL_COV_INFORMACION_INSUFICIENTE = 0.5


def calcular_cov(disponibilidad: dict[str, bool], pesos: dict[str, float]) -> float:
    """Calcula `cov` para un producto dado un perfil de usuario.

    `disponibilidad` indica, por dimensión (p. ej. ``{"D1": True, "D2": True, "D3": False}``),
    si el producto tiene subpuntaje calculable en esa dimensión. `pesos` trae el peso de cada
    dimensión para esa usuaria (deben sumar 1, ver `user_weights.convertir_prioridades_a_pesos`,
    pero esta función no lo exige para poder probarse de forma aislada).

    Devuelve 0.0 si `pesos` está vacío o la suma de sus valores es 0 (caso degenerado), en vez de
    lanzar una división por cero.
    """
    peso_total = sum(pesos.values())
    if peso_total == 0:
        return 0.0

    peso_disponible = sum(peso for dimension, peso in pesos.items() if disponibilidad.get(dimension, False))
    return peso_disponible / peso_total


def es_informacion_insuficiente(
    cov: float,
    umbral: float = UMBRAL_COV_INFORMACION_INSUFICIENTE,
) -> bool:
    """True si `cov` cae por debajo del umbral: el producto va a la banda "información insuficiente"."""
    return cov < umbral
