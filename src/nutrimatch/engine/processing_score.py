"""D2 — subpuntaje de procesamiento: NOVA combinado con `additives_n` (decisión A17).

**Fórmula propuesta el 2026-09-20, pendiente de aprobación final de Paola.**
La decisión A17 (AGENTS.md) cierra QUÉ combinar (NOVA como base, `additives_n`
como ajuste dentro de cada grupo) pero no fijó la fórmula exacta; se propone
aquí, calibrada con datos del propio snapshot, no con constantes inventadas.

Cada grupo NOVA ocupa una banda de 25 puntos en la escala 0-100, de forma que
NOVA=1 sea siempre la banda más alta (75-100) y NOVA=4 la más baja (0-25).
Esto preserva la primacía de NOVA sobre `additives_n`: ningún producto de un
grupo NOVA mejor puede terminar por debajo de uno de un grupo peor, solo se
reordena dentro de la banda de su propio grupo. Dentro de su banda,
`additives_n` empuja el subpuntaje hacia el piso, hasta un tope de aditivos
que se calibra empíricamente como un percentil alto de `additives_n` entre
los productos NOVA=4 del propio snapshot (el grupo con más aditivos): no es
un número inventado, se recalcula cada vez que cambie el snapshot.
"""

from __future__ import annotations

import pandas as pd

ANCHO_BANDA = 25.0  # 100 puntos / 4 grupos NOVA


def calibrar_tope_aditivos(
    nova_group: pd.Series,
    additives_n: pd.Series,
    percentil: float = 0.95,
) -> float:
    """Percentil `percentil` de `additives_n` entre los productos NOVA=4 del snapshot.

    Devuelve al menos 1.0 para evitar una división por cero si el snapshot no
    trajera productos NOVA=4 con `additives_n` (caso degenerado).
    """
    nova_texto = nova_group.astype("string").str.strip()
    aditivos = pd.to_numeric(additives_n.astype("string").str.strip(), errors="coerce")
    en_grupo_4 = aditivos[(nova_texto == "4") & aditivos.notna()]
    if en_grupo_4.empty:
        return 1.0
    return max(float(en_grupo_4.quantile(percentil)), 1.0)


def calcular_d2(
    nova_group: pd.Series,
    additives_n: pd.Series,
    tope_aditivos: float,
) -> pd.Series:
    """Subpuntaje D2 (0-100).

    NaN si el producto no tiene NOVA (D2 no es computable sin NOVA: es el
    dato base de la dimensión). La ausencia de `additives_n` NO anula D2: se
    trata como 0 aditivos, que es la posición más favorable dentro de la
    banda, y es coherente con no penalizar por un dato que puede simplemente
    no haberse declarado.
    """
    nova_num = pd.to_numeric(nova_group.astype("string").str.strip(), errors="coerce")
    aditivos_num = (
        pd.to_numeric(additives_n.astype("string").str.strip(), errors="coerce")
        .fillna(0.0)
        .clip(lower=0.0, upper=tope_aditivos)
    )

    techo_banda = 100.0 - (nova_num - 1.0) * ANCHO_BANDA
    ajuste = (aditivos_num / tope_aditivos) * ANCHO_BANDA
    d2 = techo_banda - ajuste
    return d2.where(nova_num.notna())
