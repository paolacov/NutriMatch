"""D1 — subpuntaje de nutrición, con signo, sobre percentiles ya calculados (decisión A7).

Los percentiles que consume este módulo vienen de
`nutrimatch.engine.nutrition_percentile.calcular_percentiles_por_categoria` (paso 6): son
agnósticos del objetivo, 0 el valor más bajo del grupo de referencia y 100 el más alto. Este
módulo les aplica el signo y los agrega en un único subpuntaje D1.

El alcance de D1 está cerrado en A27. Se puntúan cinco nutrientes de signo fijo:
azúcares, sal y grasa saturada (signo −1) y fibra y proteína (signo +1).
Energía, grasa total y carbohidratos conservan percentil y se muestran en la
ficha; no entran al subpuntaje mientras no exista una taxonomía de objetivos.
"""

from __future__ import annotations

import math
from typing import TypedDict

# +1 = "más alto es mejor" (se usa el percentil tal cual).
# -1 = "más bajo es mejor" (se usa 100 - percentil).
NUTRIENTES_D1_SIGNO: dict[str, int] = {
    "sugars_100g": -1,
    "salt_100g": -1,
    "saturated-fat_100g": -1,
    "fiber_100g": 1,
    "proteins_100g": 1,
}

# Percentil calculado en la matriz. Fuera de D1 por A27: no tienen signo fijo.
NUTRIENTES_D1_PENDIENTES: tuple[str, ...] = (
    "energy-kcal_100g",
    "fat_100g",
    "carbohydrates_100g",
)


class DetalleNutriente(TypedDict):
    percentil: float | None
    signo: int
    disponible: bool
    contribucion: float | None


def _es_nulo(valor: float | None) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def calcular_subpuntaje_d1(
    percentiles_producto: dict[str, float | None],
) -> tuple[float | None, dict[str, DetalleNutriente]]:
    """Calcula D1 (0-100) a partir de los percentiles agnósticos de un producto.

    `percentiles_producto` debe mapear el nombre **desnudo** del nutriente (p. ej.
    ``"sugars_100g"``, sin el prefijo ``percentil_`` de `matriz_nut_100g`) a su percentil (0-100)
    o `None`/`NaN` si no está disponible. Solo se leen las claves de `NUTRIENTES_D1_SIGNO`; el
    resto se ignora (pueden pasarse los 8 nutrientes de CORE8 sin que esto falle).

    Devuelve una tupla `(d1, detalle)`:
    - `d1`: promedio de las contribuciones con signo de los nutrientes disponibles, en escala
      0-100. `None` si ninguno de los 5 nutrientes tiene percentil disponible (sin dato,
      decisión A2 — nunca se fuerza un valor).
    - `detalle`: un diccionario por nutriente con su percentil, signo, disponibilidad y
      contribución, listo para alimentar la explicación por dimensión (decisión A10).
    """
    detalle: dict[str, DetalleNutriente] = {}
    contribuciones: list[float] = []

    for nutriente, signo in NUTRIENTES_D1_SIGNO.items():
        percentil = percentiles_producto.get(nutriente)
        disponible = not _es_nulo(percentil)

        if disponible:
            contribucion = float(percentil) if signo == 1 else 100.0 - float(percentil)
            contribuciones.append(contribucion)
        else:
            percentil = None
            contribucion = None

        detalle[nutriente] = {
            "percentil": percentil,
            "signo": signo,
            "disponible": disponible,
            "contribucion": contribucion,
        }

    d1 = sum(contribuciones) / len(contribuciones) if contribuciones else None
    return d1, detalle
