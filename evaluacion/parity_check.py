"""Parity-check entre D1 y Nutri-Score (decisión A8/A30, AGENTS.md).

D1 y Nutri-Score puntúan nutrientes parcialmente distintos y con metodologías distintas: D1 usa
percentil dentro de la categoría de referencia sobre 5 nutrientes de signo fijo (A27); Nutri-Score
usa puntos de penalización/bonificación calibrados por macrocategoría sobre un conjunto más amplio
(incluye energía, sodio y fruta/verdura/legumbres, que D1 v1 no puntúa). No se espera una
correlación fuerte: el parity-check es un chequeo de sanidad — "¿el orden va, a grandes rasgos, en
la misma dirección?" — no una validación de que D1 deba replicar a Nutri-Score. Replicarlo sería
además incorrecto: Nutri-Score NO puntúa en NutriMatch justamente para no contar dos veces lo
mismo que D1 (A4).
"""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

# Spearman D1 vs nutriscore_score: se espera NEGATIVA (D1 alto = mejor, nutriscore_score alto =
# peor). -0.3 es un umbral deliberadamente laxo ("moderada" en la convención habitual de 0,3-0,5):
# D1 solo cubre 5 de los nutrientes que pesa Nutri-Score, así que una correlación fuerte no es
# esperable ni deseable como criterio de éxito. Verificado sobre off_csv_20260919: -0.4747 (A30).
UMBRAL_CORRELACION_RAZONABLE = -0.3

ORDEN_GRADOS = ("a", "b", "c", "d", "e")


class ReporteParityCheck(TypedDict):
    n: int
    correlacion_spearman: float | None
    correlacion_razonable: bool
    promedio_d1_por_grado: pd.Series
    monotono_por_grado: bool


def _es_no_creciente(serie: pd.Series) -> bool:
    """True si `serie` no sube en ningún paso (permite empates), con al menos 2 puntos.

    No se exige estrictamente decreciente: con conteos reales por grado, un empate entre grados
    vecinos no debería contarse como una divergencia del motor.
    """
    if len(serie) < 2:
        return False
    valores = serie.to_numpy()
    return bool((valores[:-1] >= valores[1:]).all())


def calcular_parity_check(
    d1: pd.Series,
    nutriscore_score: pd.Series,
    nutriscore_grade: pd.Series,
) -> ReporteParityCheck:
    """Compara el orden de D1 contra Nutri-Score sobre los productos con ambos datos disponibles.

    `nutriscore_score`: más alto = peor (rango típico observado en OFF: -15 a 40). `d1`: más alto
    = mejor (0-100). Los tres argumentos deben venir alineados por posición/índice (misma fila =
    mismo producto); los productos con `d1` o `nutriscore_score` ausente (NaN) se excluyen antes
    de calcular.

    `nutriscore_grade` acepta valores fuera de `ORDEN_GRADOS` (p. ej. ``"unknown"`` o
    ``"not-applicable"``, que sí aparecen en el snapshot México, ver notebooks/05_evaluacion): se
    ignoran silenciosamente solo para el desglose por grado, no para la correlación global.

    Devuelve un `ReporteParityCheck`:
    - `n`: productos con `d1` y `nutriscore_score` simultáneamente disponibles.
    - `correlacion_spearman`: coeficiente de Spearman entre ambos (`None` si `n` < 2).
    - `correlacion_razonable`: `True` si `correlacion_spearman <= UMBRAL_CORRELACION_RAZONABLE`.
    - `promedio_d1_por_grado`: D1 promedio por `nutriscore_grade`, ordenado de 'a' a 'e' (solo
      grados presentes en los datos).
    - `monotono_por_grado`: `True` si ese promedio no sube en ningún paso de 'a' a 'e' (empates
      permitidos), con al menos dos grados presentes.
    """
    df = pd.DataFrame(
        {
            "d1": pd.Series(d1).reset_index(drop=True),
            "nutriscore_score": pd.Series(nutriscore_score).reset_index(drop=True),
            "nutriscore_grade": pd.Series(nutriscore_grade).reset_index(drop=True),
        }
    )
    df_valido = df.dropna(subset=["d1", "nutriscore_score"])
    n = len(df_valido)

    correlacion: float | None = None
    if n >= 2:
        # Spearman = Pearson sobre rangos. Se calcula así (en vez de `.corr(method="spearman")`)
        # para no añadir `scipy` como dependencia solo por esta función: pandas ya trae `.rank()`
        # y `.corr()` (Pearson) sin dependencias externas.
        correlacion_calculada = df_valido["d1"].rank().corr(df_valido["nutriscore_score"].rank())
        correlacion = None if pd.isna(correlacion_calculada) else float(correlacion_calculada)
    correlacion_razonable = correlacion is not None and correlacion <= UMBRAL_CORRELACION_RAZONABLE

    df_grados = df_valido[df_valido["nutriscore_grade"].isin(ORDEN_GRADOS)]
    promedio_por_grado = df_grados.groupby("nutriscore_grade")["d1"].mean()
    promedio_por_grado = promedio_por_grado.reindex(
        [grado for grado in ORDEN_GRADOS if grado in promedio_por_grado.index]
    )

    return {
        "n": n,
        "correlacion_spearman": correlacion,
        "correlacion_razonable": correlacion_razonable,
        "promedio_d1_por_grado": promedio_por_grado,
        "monotono_por_grado": _es_no_creciente(promedio_por_grado),
    }
