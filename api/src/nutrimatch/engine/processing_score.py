"""D2 — subpuntaje de procesamiento: NOVA combinado con `additives_n` (A17, A23).

La fórmula queda cerrada en A23. NOVA define la banda y `additives_n` ajusta
dentro de ella. El tope de aditivos se calibra en cada snapshot como el
percentil 95 de `additives_n` entre los productos NOVA 4. No se usa una
constante fija.

Cada grupo NOVA ocupa una banda de 25 puntos en la escala 0-100:
NOVA 1 queda en 75-100 y NOVA 4 en 0-25. Un producto de mejor grupo NOVA
no queda por debajo de uno de peor grupo. Dentro de la banda, `additives_n`
desplaza el subpuntaje hacia el piso hasta el tope calibrado.

Si `additives_n` falta, no se imputa cero. Se resta media banda (12,5 puntos)
y el producto queda en el centro de su banda. Sin NOVA, D2 es NULL.
"""

from __future__ import annotations

import pandas as pd

ANCHO_BANDA = 25.0  # 100 puntos / 4 grupos NOVA
# Fracción de la banda que se resta cuando `additives_n` es NULL (punto medio).
FRACCION_AJUSTE_ADITIVOS_AUSENTES = 0.5


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
    dato base de la dimensión). La ausencia de `additives_n` no anula D2 y
    tampoco se imputa a 0 aditivos: el ajuste es neutro (mitad de la banda),
    de modo que el producto queda en el centro de su piso NOVA y no en el techo.
    """
    nova_num = pd.to_numeric(nova_group.astype("string").str.strip(), errors="coerce")
    aditivos_raw = pd.to_numeric(additives_n.astype("string").str.strip(), errors="coerce")
    aditivos_conocido = aditivos_raw.notna()
    aditivos_num = aditivos_raw.clip(lower=0.0, upper=tope_aditivos)

    techo_banda = 100.0 - (nova_num - 1.0) * ANCHO_BANDA
    ajuste_observado = (aditivos_num / tope_aditivos) * ANCHO_BANDA
    ajuste_neutro = FRACCION_AJUSTE_ADITIVOS_AUSENTES * ANCHO_BANDA
    ajuste = ajuste_observado.where(aditivos_conocido, ajuste_neutro)
    d2 = techo_banda - ajuste
    return d2.where(nova_num.notna())
