"""Diagnóstico de cobertura (decisión A8/A31, AGENTS.md).

Tercer mecanismo de evaluación (A8): "cuántos productos caen en la banda 'información
insuficiente' y por qué dimensión". Se apoya en `nutrimatch.engine.coverage` (regla `cov`, A2)
sin recalcularla: aquí solo se agrega y desglosa, producto a producto, para un perfil de usuaria
dado (los pesos y qué cuenta como "D3 disponible" dependen de las prioridades y etiquetas
valoradas que declaró, A19).
"""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

from nutrimatch.engine.coverage import (
    UMBRAL_COV_INFORMACION_INSUFICIENTE,
    calcular_cov,
    es_informacion_insuficiente,
)

DIMENSIONES = ("D1", "D2", "D3")

SIN_DIMENSIONES_FALTANTES = "(ninguna)"


class ReporteCobertura(TypedDict):
    n_total: int
    n_informacion_insuficiente: int
    porcentaje_informacion_insuficiente: float
    desglose_por_combinacion_faltante: pd.DataFrame
    cov: pd.Series


def _combinacion_faltante(fila: pd.Series) -> str:
    faltantes = [dimension for dimension in DIMENSIONES if not fila[dimension]]
    return "+".join(faltantes) if faltantes else SIN_DIMENSIONES_FALTANTES


def diagnosticar_cobertura(
    disponibilidad: pd.DataFrame,
    pesos: dict[str, float],
    umbral_cov: float = UMBRAL_COV_INFORMACION_INSUFICIENTE,
) -> ReporteCobertura:
    """Calcula `cov` producto a producto y desglosa la banda "información insuficiente" por
    combinación de dimensiones faltantes.

    `disponibilidad` debe traer columnas booleanas ``"D1"``, ``"D2"``, ``"D3"`` — una fila por
    producto, indicando si ese producto tiene subpuntaje calculable en cada dimensión PARA la
    usuaria de `pesos` (D3 en particular depende de qué etiquetas valoradas eligió, A19). Esta
    función no calcula esa disponibilidad: la recibe ya calculada por el caller (mismo patrón que
    `compatibility_score.calcular_score_compatibilidad`, que tampoco calcula los subpuntajes).

    Devuelve un `ReporteCobertura`:
    - ``n_total``: productos evaluados.
    - ``n_informacion_insuficiente``: cuántos caen bajo `umbral_cov` (`cov < umbral_cov`, A2).
    - ``porcentaje_informacion_insuficiente``: sobre `n_total` (0.0 si `n_total` es 0).
    - ``desglose_por_combinacion_faltante``: un DataFrame con una fila por combinación de
      dimensiones faltantes entre los productos EN la banda insuficiente (p. ej. ``"D1"`` si solo
      falta D1, ``"D1+D3"`` si faltan ambas), con columnas `n`, `porcentaje_del_total` y
      `porcentaje_de_insuficientes`, ordenado de mayor a menor `n`.
    - ``cov``: la cobertura calculada por producto, mismo índice que `disponibilidad`.
    """
    n_total = len(disponibilidad)

    if n_total == 0:
        cov = pd.Series(dtype=float)
        vacio = pd.DataFrame(
            columns=["dimensiones_faltantes", "n", "porcentaje_del_total", "porcentaje_de_insuficientes"]
        )
        return {
            "n_total": 0,
            "n_informacion_insuficiente": 0,
            "porcentaje_informacion_insuficiente": 0.0,
            "desglose_por_combinacion_faltante": vacio,
            "cov": cov,
        }

    cov = disponibilidad.apply(
        lambda fila: calcular_cov({dimension: bool(fila[dimension]) for dimension in DIMENSIONES}, pesos),
        axis=1,
    )
    insuficiente = cov.apply(lambda valor: es_informacion_insuficiente(valor, umbral_cov))
    n_insuficiente = int(insuficiente.sum())

    combinaciones = disponibilidad[insuficiente].apply(_combinacion_faltante, axis=1)
    conteo = combinaciones.value_counts().rename("n").to_frame()
    conteo["porcentaje_del_total"] = conteo["n"] / n_total * 100.0
    conteo["porcentaje_de_insuficientes"] = conteo["n"] / n_insuficiente * 100.0 if n_insuficiente else 0.0
    conteo = conteo.rename_axis("dimensiones_faltantes").reset_index().sort_values("n", ascending=False)
    conteo = conteo.reset_index(drop=True)

    return {
        "n_total": n_total,
        "n_informacion_insuficiente": n_insuficiente,
        "porcentaje_informacion_insuficiente": n_insuficiente / n_total * 100.0,
        "desglose_por_combinacion_faltante": conteo,
        "cov": cov,
    }
