"""Motor determinista de compatibilidad y las operaciones que lo acompañan.

El resultado es la suma ponderada de tres dimensiones, cada una en escala 0–100:

- Nutrición: percentiles dentro de la categoría de referencia, con signo fijo
  en azúcares, sal, grasa saturada, fibra y proteína.
- Procesamiento: grupo NOVA afinado con el número de aditivos.
- Preferencias: porcentaje de etiquetas valoradas que el producto presenta.

La cobertura decide si el producto entra al ranking o a la banda de información
insuficiente. Esta es la única capa que calcula esos números.

Módulos de transformación:

- ``constants``: núcleo nutricional y umbrales de saneamiento.
- ``sanitize``: valores fuera de rango físico.
- ``reference_category``: categoría usada para el percentil.
- ``nutrition_percentile``: percentiles y estadísticas de categoría.
- ``processing_score``: subpuntaje de procesamiento.

Módulos del resultado personalizado:

- ``user_weights``: convierte el orden de tres prioridades en pesos que suman 1.
- ``hard_filters``: alergia y dieta, en tres estados, fuera del resultado.
- ``nutrition_score``: subpuntaje nutricional.
- ``preference_score``: subpuntaje de preferencias.
- ``coverage``: fracción de peso con dato disponible.
- ``compatibility_score``: resultado final y explicación por dimensión.

Utilidades que no entran al resultado:

- ``product_naming``: nombre visible, con respaldo entre columnas del mismo registro.
- ``data_quality``: disponibilidad y coherencia de la ficha. No puntúa.

Energía, grasa total y carbohidratos conservan percentil para la ficha y quedan
fuera del subpuntaje nutricional.
"""
