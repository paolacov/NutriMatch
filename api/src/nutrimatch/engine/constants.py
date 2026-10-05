"""Constantes compartidas del motor: núcleo nutricional y umbrales de saneamiento.

Los umbrales físicos de esta tabla son cotas de ingeniería, no datos medidos ni
verificados en una fuente externa: se documentan con su razonamiento y quedan
abiertos a ajuste. No confundir con las cifras de cobertura o de conteos, que
sí son mediciones reales citadas con fecha en AGENTS.md.
"""

from __future__ import annotations

# Núcleo nutricional global (decisión A20, AGENTS.md — fibra incluida desde
# el 2026-09-20: solo resta 3,1 puntos porcentuales sobre core7 en el
# universo real, mucho menos que lo que sugería la muestra sesgada de 7.2).
CORE8_NUTRIENTES: tuple[str, ...] = (
    "energy-kcal_100g",
    "fat_100g",
    "saturated-fat_100g",
    "carbohydrates_100g",
    "sugars_100g",
    "proteins_100g",
    "salt_100g",
    "fiber_100g",
)

# Cotas físicas de saneamiento (decisión A18, AGENTS.md).
#
# Los nutrientes en gramos no pueden exceder 100 g por 100 g de producto: es
# una imposibilidad matemática, no una medición. El máximo de energía es una
# cota conservadora de ingeniería (1 g de grasa aporta ~9 kcal; un producto
# compuesto en su totalidad por grasa rondaría 900 kcal/100 g), pensada para
# atrapar errores de captura como el detectado en el EDA (un producto con
# 277.183 kcal/100 g). Es un parámetro ajustable, no un dato verificado.
RANGO_VALIDO: dict[str, tuple[float, float]] = {
    "energy-kcal_100g": (0.0, 900.0),
    "fat_100g": (0.0, 100.0),
    "saturated-fat_100g": (0.0, 100.0),
    "carbohydrates_100g": (0.0, 100.0),
    "sugars_100g": (0.0, 100.0),
    "proteins_100g": (0.0, 100.0),
    "salt_100g": (0.0, 100.0),
    "fiber_100g": (0.0, 100.0),
}

# Decisión A16, AGENTS.md: tamaño mínimo de categoría de referencia. Cubre el
# 64,0 % de los productos categorizados sin necesitar retroceso (verificado
# en notebooks/02_eda_universo_mexico.ipynb, sección 5).
TAMANO_MINIMO_CATEGORIA = 30

# Decisión A24. El tamaño nominal de la categoría (A16) no garantiza efectivo
# con dato saneado para un nutriente. Por debajo de este mínimo el percentil
# de ese nutriente es NULL.
MINIMO_PEERS_PERCENTIL = 5
