"""Indicadores DERIVED de calidad de información (no de calidad nutricional).

Materializa `data_quality_score` y `data_quality_level` a partir de columnas que **ya existen**
en el dataset de referencia. No imputa nutrientes, NOVA, ingredientes ni precio. No forma parte
del score de compatibilidad (D1/D2/D3/`cov`).

Las siete dimensiones son las que el diagnóstico de base final pidió evaluar. Cada una reutiliza
un indicador ya calculado o un campo REAL; no se inventa una señal nueva:

1. nutrición — `n_percentiles_validos` / 8 (A22)
2. ingredientes — presencia de `ingredients_text`
3. categoría — presencia de `categoria_referencia` (A16)
4. NOVA — presencia de `nova_group` (misma condición que D2 calculable, A23)
5. aditivos — presencia de `additives_n` (un 0 real cuenta como dato)
6. etiquetas — presencia de `labels_tags`
7. consistencia — ausencia de flags A18 (`*_flag_fuera_de_rango`, `flag_suma_macros_excede_100`)

`completeness` y `data_quality_errors_tags` de OFF se dejan como REAL; no se copian aquí para no
duplicar un score opaco con el checklist explícito.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from nutrimatch.engine.constants import CORE8_NUTRIENTES

COLUMNAS_CALIDAD: tuple[str, ...] = (
    "data_quality_score",
    "data_quality_level",
    "data_quality_detalle",
)

DIMENSIONES_CALIDAD: tuple[str, ...] = (
    "nutrition",
    "ingredients",
    "category",
    "nova",
    "additives",
    "labels",
    "consistency",
)

N_DIMENSIONES_CALIDAD = len(DIMENSIONES_CALIDAD)

NIVELES_CALIDAD: tuple[str, ...] = ("insuficiente", "baja", "media", "alta")

# Umbrales de banda sobre el promedio 0–1. No son un modelo: parten el intervalo en cuartos.
UMBRAL_BAJA = 0.25
UMBRAL_MEDIA = 0.50
UMBRAL_ALTA = 0.75

FLAGS_FUERA_DE_RANGO: tuple[str, ...] = tuple(
    f"{nutriente}_flag_fuera_de_rango" for nutriente in CORE8_NUTRIENTES
)
FLAG_MACROS = "flag_suma_macros_excede_100"


def _es_nulo(valor: Any) -> bool:
    """None / NaN / pd.NA (B13). Un 0 numérico no es nulo."""
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return bool(pd.isna(valor))


def _es_texto_nulo(valor: Any) -> bool:
    if _es_nulo(valor):
        return True
    return not str(valor).strip() or str(valor).strip().lower() in {"nan", "none"}


def _tiene_dato_numerico_o_cero(valor: Any) -> bool:
    """True si hay un número observado, incluido 0. False si NULL/NaN/texto vacío (B13)."""
    if _es_nulo(valor):
        return False
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto or texto.lower() in {"nan", "none"}:
            return False
        return True
    return True


def _es_flag_verdadero(valor: Any) -> bool:
    if _es_nulo(valor):
        return False
    if isinstance(valor, str):
        return valor.strip().lower() in {"true", "1"}
    return bool(valor)


def _fraccion_nutricion(n_percentiles_validos: Any) -> float:
    if _es_nulo(n_percentiles_validos):
        return 0.0
    try:
        n = float(n_percentiles_validos)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(n):
        return 0.0
    return max(0.0, min(1.0, n / float(len(CORE8_NUTRIENTES))))


def _nivel_calidad(score: float) -> str:
    if score < UMBRAL_BAJA:
        return "insuficiente"
    if score < UMBRAL_MEDIA:
        return "baja"
    if score < UMBRAL_ALTA:
        return "media"
    return "alta"


def _formatear_detalle(componentes: dict[str, float]) -> str:
    partes = [f"{nombre}:{componentes[nombre]:.4f}" for nombre in DIMENSIONES_CALIDAD]
    return ";".join(partes)


def calcular_componentes_calidad(fila: dict[str, Any]) -> dict[str, float]:
    """Siete componentes en [0, 1] para una fila. No escribe nutrientes ni precio."""
    inconsistente = _es_flag_verdadero(fila.get(FLAG_MACROS))
    for flag in FLAGS_FUERA_DE_RANGO:
        if _es_flag_verdadero(fila.get(flag)):
            inconsistente = True
            break

    return {
        "nutrition": _fraccion_nutricion(fila.get("n_percentiles_validos")),
        "ingredients": 0.0 if _es_texto_nulo(fila.get("ingredients_text")) else 1.0,
        "category": 0.0 if _es_texto_nulo(fila.get("categoria_referencia")) else 1.0,
        "nova": 0.0 if _es_texto_nulo(fila.get("nova_group")) else 1.0,
        "additives": 1.0 if _tiene_dato_numerico_o_cero(fila.get("additives_n")) else 0.0,
        "labels": 0.0 if _es_texto_nulo(fila.get("labels_tags")) else 1.0,
        "consistency": 0.0 if inconsistente else 1.0,
    }


def calcular_indicadores_calidad_fila(fila: dict[str, Any]) -> dict[str, Any]:
    componentes = calcular_componentes_calidad(fila)
    score = sum(componentes[nombre] for nombre in DIMENSIONES_CALIDAD) / N_DIMENSIONES_CALIDAD
    return {
        "data_quality_score": score,
        "data_quality_level": _nivel_calidad(score),
        "data_quality_detalle": _formatear_detalle(componentes),
    }


def calcular_indicadores_calidad(frame: pd.DataFrame) -> pd.DataFrame:
    """Calcula las tres columnas DERIVED fila a fila (listas Python; evita B13/A38).

    No muta `frame`. El score está definido para todas las filas: mide disponibilidad, no
    rellena el nutriente ausente. Un `additives_n == 0` es dato presente.
    """
    faltantes = [
        col
        for col in ("n_percentiles_validos", "ingredients_text", "categoria_referencia", "nova_group", "additives_n", "labels_tags", FLAG_MACROS, *FLAGS_FUERA_DE_RANGO)
        if col not in frame.columns
    ]
    if faltantes:
        raise KeyError(f"faltan columnas de entrada para calidad: {faltantes}")

    scores: list[float] = []
    niveles: list[str] = []
    detalles: list[str] = []

    registros = frame.to_dict(orient="records")
    for fila in registros:
        indicadores = calcular_indicadores_calidad_fila(fila)
        scores.append(indicadores["data_quality_score"])
        niveles.append(indicadores["data_quality_level"])
        detalles.append(indicadores["data_quality_detalle"])

    return pd.DataFrame(
        {
            "data_quality_score": scores,
            "data_quality_level": niveles,
            "data_quality_detalle": detalles,
        },
        index=frame.index,
    )


def anexar_indicadores_calidad(frame: pd.DataFrame) -> pd.DataFrame:
    """Copia de `frame` + columnas de calidad. Falla si alguna columna ya existe."""
    choque = [col for col in COLUMNAS_CALIDAD if col in frame.columns]
    if choque:
        raise ValueError(f"el frame ya trae columnas de calidad: {choque}")
    indicadores = calcular_indicadores_calidad(frame)
    salida = frame.copy()
    for columna in COLUMNAS_CALIDAD:
        salida[columna] = indicadores[columna].to_numpy()
    return salida
