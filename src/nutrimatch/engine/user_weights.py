"""Conversión del orden de 3 prioridades a pesos normalizados (decisión A6, AGENTS.md).

La usuaria ordena tres prioridades (nutrición D1, procesamiento D2, preferencias D3) sin
manipular ningún número directamente ("Sin controles numéricos directos", A6). Ese orden se
convierte aquí en pesos que suman 1.

**Fórmula propuesta en el paso 7, pendiente de verificación en el notebook**: pesos
proporcionales a una secuencia fija 3/2/1 según la posición (1º lugar = 3 puntos, 2º = 2,
3º = 1), normalizada para sumar 1. Da 0,50 / 0,33 / 0,17 para 1º/2º/3º lugar. Es una escala
simple y fácil de explicar en la interfaz, no una medición: se documenta como propuesta, igual
que se hizo con la fórmula de D2 en el paso 6 (decisión A17/A23).

`perfil_base` (Equilibrado / Salud máxima / Económico / Mínimo procesado) es un concepto de
UI/dominio que fija un orden de prioridades por defecto; este módulo no lo modela, solo recibe
el orden ya resuelto.
"""

from __future__ import annotations

DIMENSIONES = ("D1", "D2", "D3")

# Puntos por posición (1º, 2º, 3º lugar), antes de normalizar. Ver docstring del módulo.
PUNTOS_POR_POSICION: tuple[int, ...] = (3, 2, 1)


def convertir_prioridades_a_pesos(orden_prioridades: list[str]) -> dict[str, float]:
    """Convierte un orden de prioridades en pesos normalizados que suman 1.

    `orden_prioridades` debe ser una permutación de exactamente `DIMENSIONES` ("D1", "D2",
    "D3"), de mayor a menor prioridad (el primer elemento es la prioridad más alta).

    Devuelve un diccionario ``{"D1": peso, "D2": peso, "D3": peso}`` con los pesos
    correspondientes a `PUNTOS_POR_POSICION` normalizados.

    Lanza `ValueError` si `orden_prioridades` no es exactamente una permutación de las tres
    dimensiones (ni más, ni menos, ni repetidas): un orden de prioridades incompleto o inválido
    no debe convertirse en pesos silenciosamente.
    """
    if sorted(orden_prioridades) != sorted(DIMENSIONES):
        raise ValueError(
            f"orden_prioridades debe ser una permutación de {DIMENSIONES}, recibido: "
            f"{orden_prioridades!r}"
        )

    total_puntos = sum(PUNTOS_POR_POSICION)
    return {
        dimension: puntos / total_puntos
        for dimension, puntos in zip(orden_prioridades, PUNTOS_POR_POSICION, strict=True)
    }
