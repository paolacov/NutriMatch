"""Motor determinista de scoring y las operaciones que lo acompañan.

Score aditivo de tres dimensiones (D1 nutrición, D2 procesamiento NOVA, D3 preferencias) con
subpuntajes, percentiles calculados dentro de la categoría de referencia, regla de cobertura `cov`
y banda de "información insuficiente". Incluye las operaciones deterministas de filtro, ranking,
comparación, alertas y carrito. Es la única capa autorizada a calcular.

Módulos del paso de transformación (paso 6 del plan), ya implementados:

- ``constants``: núcleo nutricional (CORE8) y umbrales de saneamiento.
- ``sanitize``: saneamiento de valores fuera de rango físico (decisión A18).
- ``reference_category``: resolución de la categoría de referencia para D1 (decisión A16).
- ``nutrition_percentile``: percentiles de D1 dentro de la categoría y ``category_stats``.
- ``processing_score``: subpuntaje D2, NOVA combinado con ``additives_n`` (decisión A17).

Pendientes del paso de modelo de recomendación (paso 7): aplicar el signo de D1 según el
objetivo del usuario, D3 (preferencias), la regla de cobertura ``cov`` con pesos del usuario,
los filtros duros (alergias, dieta) y el ensamblado del score final.
"""
