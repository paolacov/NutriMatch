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

Módulos del paso de modelo de recomendación (paso 7), ya implementados:

- ``user_weights``: convierte el orden de 3 prioridades del usuario en pesos normalizados (A6).
- ``hard_filters``: filtros de alergia y dieta, tres estados, fuera del score (A1, A15).
- ``nutrition_score``: subpuntaje D1 con signo, sobre 5 nutrientes de dirección fija (A7).
- ``preference_score``: subpuntaje D3, porcentaje de etiquetas valoradas presentes (A7).
- ``coverage``: regla de cobertura ``cov`` y banda de "información insuficiente" (A2).
- ``compatibility_score``: ensamblado del score final ponderado y explicación (A7, A10).

Utilidad complementaria (no forma parte del score de compatibilidad):

- ``product_naming``: resuelve el nombre de un producto para mostrar, con fallback entre columnas
  del propio OFF cuando ``product_name`` viene vacío (decisión A28).
- ``data_quality``: ``data_quality_score`` / ``data_quality_level`` (DERIVED). Miden
  disponibilidad y consistencia de la ficha, no calidad nutricional, y no puntúan.

Pendiente para una siguiente pasada (fuera del alcance del paso 7): extender D1 a
``energy-kcal_100g``, ``fat_100g`` y ``carbohydrates_100g`` cuando se defina una taxonomía de
objetivos nutricionales del usuario (el documento maestro los deja "según meta" sin especificarla).
"""
