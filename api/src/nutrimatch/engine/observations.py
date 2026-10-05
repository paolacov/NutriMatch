"""Tabla de observaciones — paso 9 del plan de trabajo (decisión A43, `AGENTS.md`).

Diseño tomado de `docs/diagnostico_calidad_datos.md` (sección F.2): las **211 columnas** del
export de OFF son REAL por construcción y no se clonan aquí (basta el metadato de tabla del
snapshot, `datos/snapshots/off_csv_20260919/_metadata.json`). Lo que sí vive en esta tabla es lo
que **no** viene del export — nombre recuperado por API (A39) y precio (A40/A41) — consolidado en
un esquema único, consultable por `(code, field)`:

    code, field, value, status, source, source_url, retrieved_at, snapshot_id, method,
    confidence, quality_flag

Cada observación es una fila; puede haber varias por `(code, field)` (A33: "varias observaciones
por `(code, field)` son válidas"). La ficha del producto elige según una regla explícita (F.2):
**REAL más reciente**; si no hay ninguna, **UNAVAILABLE**; **nunca** IMPUTED ni SYNTHETIC por
delante de REAL. Esa regla se implementa aquí en `resolver_observaciones`.

`value` se guarda siempre como texto (mismo patrón que `nutriscore_score`, B14: "la conversión de
tipos se hace después, de forma auditada"), porque el campo varía de observación a observación
(un nombre es texto; un precio es un número que igual se representa como texto en este nivel).

Este módulo **no construye la tabla desde cero por sí mismo**: recibe los Parquets ya
materializados por pasos anteriores (`experimento_recuperacion_nombres_*`, A39;
`precios_open_prices_*`, A40; `precios_qqp_*`, A41) y los homogeneiza a este esquema. No toca
ninguno de esos Parquets ni el snapshot crudo (A2).
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

COLUMNAS_OBSERVACION: tuple[str, ...] = (
    "code",
    "field",
    "value",
    "status",
    "source",
    "source_url",
    "retrieved_at",
    "snapshot_id",
    "method",
    "confidence",
    "quality_flag",
)

# Orden de prioridad al resolver varias observaciones para el mismo (code, field). REAL siempre
# gana; "nunca IMPUTED ni SYNTHETIC por delante de REAL" (F.2, A33). SYNTHETIC no debería
# aparecer nunca en datos de producción (A33: "solo fixtures; nunca el Parquet de producción"),
# pero se incluye en la prioridad para que, si alguna vez se filtra por error, quede siempre al
# final — nunca elegida sobre una observación real.
PRIORIDAD_STATUS: dict[str, int] = {
    "REAL": 0,
    "DERIVED": 1,
    "IMPUTED": 2,
    "SYNTHETIC": 3,
    "UNAVAILABLE": 4,
}


def _es_nulo(valor: Any) -> bool:
    """`None`, `NaN` de pandas o `pd.NA` (B13, `AGENTS.md`): un valor ausente nunca es cero ni
    texto "nan". `pd.NA` aparece al leer con DuckDB columnas nullable (p. ej.
    `match_confidence` DOUBLE con nulos) vía `.df()`; ni `is None` ni `math.isnan` lo cubren
    (no es `None` ni `float`). Se llama siempre sobre un escalar de una fila (nunca sobre una
    `Series` completa), así que `pd.isna` devuelve un booleano simple, sin ambigüedad."""
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return bool(pd.isna(valor))


def construir_observaciones_nombre_recuperado(
    experimento: pd.DataFrame, *, snapshot_id: str = "off_csv_20260919"
) -> pd.DataFrame:
    """Convierte los hits del experimento de recuperación de nombres (A39) en observaciones.

    Solo las filas con `es_hit=True`: un intento sin hit ya documenta "se buscó y no había nada
    nuevo" en su propio Parquet (`experimento_recuperacion_nombres_*.parquet`); no aporta una
    observación de valor nuevo para la tabla de resolución, así que no se duplica aquí.
    """
    if experimento.empty:
        return pd.DataFrame(columns=COLUMNAS_OBSERVACION)

    hits = experimento[experimento["es_hit"].eq(True)]
    filas: list[dict[str, Any]] = []
    for _, fila in hits.iterrows():
        filas.append(
            {
                "code": str(fila["code"]),
                "field": "product_name",
                "value": None if _es_nulo(fila["nombre_recuperado"]) else str(fila["nombre_recuperado"]),
                "status": str(fila["status_valor"]),
                "source": str(fila["source"]),
                "source_url": None if _es_nulo(fila["source_url"]) else str(fila["source_url"]),
                "retrieved_at": None if _es_nulo(fila["retrieved_at"]) else str(fila["retrieved_at"]),
                "snapshot_id": snapshot_id,
                "method": "api_producto_individual",
                "confidence": None,
                "quality_flag": None,
            }
        )
    return pd.DataFrame(filas, columns=COLUMNAS_OBSERVACION)


def construir_observaciones_precio(
    precios: pd.DataFrame, *, snapshot_id: str = "off_csv_20260919"
) -> pd.DataFrame:
    """Convierte un Parquet `price_*` (esquema D.3: Open Prices A40 o QQP A41) en observaciones.

    Ambas fuentes ya comparten el mismo esquema `price_*`, así que un solo mapeo genérico sirve
    para las dos: se llama una vez por cada Parquet de precio y el resultado se concatena.
    """
    if precios.empty:
        return pd.DataFrame(columns=COLUMNAS_OBSERVACION)

    filas: list[dict[str, Any]] = []
    for _, fila in precios.iterrows():
        filas.append(
            {
                "code": str(fila["code"]),
                "field": "price",
                "value": None if _es_nulo(fila["price"]) else str(fila["price"]),
                "status": str(fila["price_status"]),
                "source": str(fila["source"]),
                "source_url": None if _es_nulo(fila["source_url"]) else str(fila["source_url"]),
                "retrieved_at": None if _es_nulo(fila["retrieved_at"]) else str(fila["retrieved_at"]),
                "snapshot_id": snapshot_id,
                "method": None if _es_nulo(fila["match_method"]) else str(fila["match_method"]),
                "confidence": None if _es_nulo(fila["match_confidence"]) else float(fila["match_confidence"]),
                "quality_flag": None,
            }
        )
    return pd.DataFrame(filas, columns=COLUMNAS_OBSERVACION)


def resolver_observaciones(observaciones: pd.DataFrame) -> pd.DataFrame:
    """Elige, para cada `(code, field)`, la observación ganadora según la regla de F.2.

    Regla: **REAL más reciente** (por `retrieved_at`); si no hay ninguna REAL, la de mejor
    status disponible (`PRIORIDAD_STATUS`); **nunca** IMPUTED ni SYNTHETIC por delante de REAL.
    Un `(code, field)` sin ninguna observación simplemente no aparece en el resultado — el
    llamador (`resolver_valor`, o un LEFT JOIN contra el universo completo) es responsable de
    tratar esa ausencia como UNAVAILABLE, nunca como cero (A2).

    No modifica `observaciones` in place; devuelve una fila por `(code, field)` con las mismas
    columnas de entrada.
    """
    if observaciones.empty:
        return observaciones.copy()

    df = observaciones.copy()
    df["_prioridad"] = df["status"].map(PRIORIDAD_STATUS).fillna(len(PRIORIDAD_STATUS))
    df["_retrieved_at_dt"] = pd.to_datetime(df["retrieved_at"], utc=True, errors="coerce")
    df = df.sort_values(["_prioridad", "_retrieved_at_dt"], ascending=[True, False])
    ganadoras = df.groupby(["code", "field"], as_index=False).first()
    return ganadoras.drop(columns=["_prioridad", "_retrieved_at_dt"])


def resolver_valor(observaciones_resueltas: pd.DataFrame, code: str, field: str) -> dict[str, Any]:
    """Devuelve la observación ganadora ya resuelta para un `(code, field)`, o UNAVAILABLE.

    `observaciones_resueltas` debe venir ya pasada por `resolver_observaciones` (una fila por
    `(code, field)`). Útil para consultas puntuales (p. ej. una ficha de producto); para
    construir una columna sobre todo el universo, un LEFT JOIN vectorizado es preferible a
    llamar esta función fila por fila.
    """
    coincidencia = observaciones_resueltas[
        (observaciones_resueltas["code"] == code) & (observaciones_resueltas["field"] == field)
    ]
    if coincidencia.empty:
        return {"value": None, "status": "UNAVAILABLE", "source": None, "source_url": None,
                "retrieved_at": None, "method": None, "confidence": None, "quality_flag": None}
    return coincidencia.iloc[0].to_dict()
