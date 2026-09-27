# Convenciones de NutriMatch

Documento de referencia del proyecto. Recoge las decisiones ya cerradas y las trampas verificadas de
las fuentes de datos. Si una decisión aparece aquí, ya está tomada: no se rediscute sin motivo
nuevo. Si algo aparece marcado como PENDIENTE o BLOQUEANTE, es una decisión que falta cerrar.

---

## Sección A. Decisiones metodológicas cerradas

### A1. Restricciones duras antes del ranking, y fuera de él

Las restricciones duras se aplican **antes** de puntuar y **no** forman parte del score.

- **Alergias: filtro fail-safe.** Ante la duda, el producto se excluye. Un dato ambiguo o ausente
  sobre un alérgeno declarado nunca se interpreta a favor del producto.
- **Dieta: tres estados**, no dos. Compatible, incompatible y **"no verificable"**. El tercer estado
  es obligatorio: los ingredientes de OFF no siempre permiten afirmar que un producto cumple una
  dieta, y afirmarlo sin evidencia sería inventar.
- **El país NO filtra.** El mercado se fija en la ingesta: el snapshot ya es México por
  construcción. No hay filtro de país en tiempo de consulta porque no hay nada que filtrar.

### A2. Datos faltantes: nunca imputar cero

Un cero es una afirmación nutricional ("este producto no tiene azúcar"). Un dato ausente no es esa
afirmación. Por tanto:

- **Sin dato = NULL + bandera explícita.** Jamás cero.
- **Regla de cobertura `cov`:**

  ```
  cov = (suma de los pesos de las dimensiones que SÍ tienen dato) / (suma de los pesos totales)
  ```

- Si `cov < 0.5`, el producto **no entra al ranking**: va a la banda **"información
  insuficiente"**, que se muestra separada. Comparar un producto con la mitad de sus datos ausentes
  contra uno completo produciría un orden falso.

### A3. Normalización por 100 g o 100 mL

El score y el ranking se calculan **siempre** sobre base 100 g (sólidos) o 100 mL (líquidos), la
misma base en que OFF publica los nutrientes.

Las **porciones se difieren a las alertas**, donde son informativas y opcionales. **Jamás se inventa
una porción**: si el producto no declara `serving_size`, no hay cálculo por porción.

### A4. Sin doble conteo: un constructo, una sola dimensión

Cada constructo se puntúa **una vez y en un solo lugar**.

- **NOVA sí puntúa** (es la dimensión D2): mide grado de procesamiento, información que los
  nutrientes no contienen.
- **Nutri-Score NO puntúa.** Se deriva de los mismos nutrientes que ya puntúa D1; incluirlo sería
  contar dos veces lo mismo. Se usa solo como **referencia mostrada** y como **parity-check** en la
  evaluación.

### A5. Precio: referencia informativa, no puntúa

PROFECO QQP aporta un **"precio de referencia"**.

- El cruce con el producto es **por texto** (marca + presentación + producto), porque **QQP no
  publica código de barras**. No hay clave común con OFF.
- El precio **no puntúa y no filtra**. Al ser un cruce difuso, meterlo en el score contaminaría un
  cálculo determinista con una coincidencia probabilística.
- **Prohibido el término "precio estimado".** Siempre "precio de referencia": el dato es un precio
  real observado por PROFECO en un establecimiento y una fecha, no una estimación nuestra.
- **No reabierta el 2026-09-26** (A36): en esta tesis el precio es REAL o NULL. No hay precio
  imputado; QQP sigue llamándose "precio de referencia", nunca "estimado".

### A6. Pesos del usuario: perfil base + orden de prioridades

La usuaria declara un **perfil base** y **ordena tres prioridades**. Ese orden se convierte
internamente en **pesos normalizados que suman 1**.

**Sin controles numéricos directos.** Nadie debería tener que decidir si la nutrición vale 0,45 o
0,50. Ordenar tres prioridades sí es una decisión humana razonable.

### A7. Score de compatibilidad: tres dimensiones ponderadas

Score aditivo de tres dimensiones, cada una en escala 0–100:

| Dim | Qué mide | Cómo se calcula |
| --- | --- | --- |
| **D1** | Nutrición | Nutrientes **con signo según el objetivo** (un nutriente puede ser deseable o indeseable según la meta declarada), evaluados **por percentil dentro de la categoría de referencia** |
| **D2** | Procesamiento | Grupo **NOVA 1–4** mapeado linealmente a **100–0** |
| **D3** | Preferencias | **Porcentaje de etiquetas valoradas** por la usuaria que el producto presenta |

El score final es la suma ponderada por los pesos de A6. Cada dimensión conserva su **subpuntaje**
visible.

### A8. Evaluación

Tres mecanismos:

1. **Golden set interno**: casos con resultado esperado, revisados a mano.
2. **Parity-check con Nutri-Score**: se comprueba que el orden de D1 correlacione razonablemente con
   Nutri-Score. Divergencias grandes son señal de error, no de mérito.
3. **Diagnóstico de cobertura**: cuántos productos caen en la banda "información insuficiente" y por
   qué dimensión.

### A9. Etiquetado frontal mexicano: informa, no puntúa

Los sellos de advertencia (`es:exceso-*`, NOM-051) se muestran y **generan alertas**, pero **no
puntúan**. Derivan de los mismos nutrientes de D1 (ver A4).

### A10. La explicación del porqué es la protagonista de la interfaz

No es un apéndice del resultado: es el producto. Cada resultado muestra:

- Subpuntaje por dimensión.
- Contribución de cada nutriente.
- Percentil dentro de la categoría.
- Peso aplicado.
- **Estado de los datos** (qué había, qué faltaba, qué se marcó con bandera).

### A11. Historial y lista de compras alimentan el `event_log`

Las decisiones y la lista de compras se registran en el `event_log`. **No puntúan**: son trazas de
uso, no evidencia nutricional.

### A12. Módulo carrito

Dos vistas más un resumen agregado:

- Vista **Plato del Bien Comer**.
- Vista **por categorías**.

Reglas de agregación, explícitas para que el número sea interpretable:

- **Promedio por 100 g** como método por defecto.
- **Ponderado por gramos solo si TODOS los productos tienen `quantity`.** Si falta uno, no se
  pondera.
- **Siempre con bandera de método y de cobertura**: quien lee el número sabe cómo se obtuvo.
- **Porcentajes por grupo con denominador = número de productos** (no gramos).
- Producto **sin categoría mapeable** va al bucket **"no clasificado"**, visible. No se fuerza.
- **Sin juicios médicos** en ningún resumen.

### A13. Capa LLM opcional

Tres roles, con `tools.py` como registro delgado sobre `engine/`:

- **planner**: traduce lenguaje natural a JSON validado. No calcula; elige qué operación
  determinista invocar.
- **critic**: auditor **determinista** (no es un LLM juzgando a otro LLM). Verifica que cada
  afirmación del texto esté respaldada por un hecho calculado.
- **narrate**: redacta la explicación en markdown.

Requisitos: **grounding obligatorio** sobre hechos calculados, **parsing JSON validado**,
**anonimización del identificador de usuario** antes de cualquier llamada, **caché** de respuestas y
**fallback determinista por plantillas**. Sin clave de API, todo funciona.

### A14. Arquitectura

**Revisada el 2026-09-27 (frontend; catálogo API el mismo día).** El motor vive en el paquete
`nutrimatch`, **reutilizado tal cual** por notebooks. La interfaz del MVP es **solo Angular**
(`frontend/`): llama a FastAPI (`nutrimatch.api`), que serializa `schemas/` y no recalcula
D1/D2/D3. El catálogo de la API es `dataset_referencia_20260927.parquet` (recableado el
2026-09-27 desde el 20260926; el archivo anterior no se sobrescribe). No se tocó el motor de
ranking.

No hay segunda interfaz. Un prototipo Streamlit sirvió el 2026-09-20 para cerrar las bandas de
A32; se retiró el 2026-09-27. Perfil, carrito y comparación viven en el cliente; búsqueda,
ranking, ficha, resumen de carrito y `event_log` salen de la API.

JWT y docker siguen fuera. Ver [`docs/linea_futura.md`](docs/linea_futura.md).

### A15. Filtro de alergias: tres estados, no un binario fail-safe

**Decisión revisada el 2026-09-20**, sobre datos reales de `notebooks/02_eda_universo_mexico.ipynb`
(sección 4). El fail-safe binario de A1 ("no verificado = no apto") se definió antes de medir la
cobertura real de `allergens`: es **16,6 %** sobre el universo México (2.793 de 16.851), muy por
debajo del 61,7 % que sugería la muestra sesgada de la sección 7.2 del documento maestro original.
Aplicado tal cual, el binario marcaría **83,4 % del catálogo como "no apto"** para cualquier usuaria
con una alergia declarada, y en la inmensa mayoría de esos casos sería por ausencia de dato, no por
presencia real del alérgeno.

- **Alergias: tres estados**, igual que dieta (A1): **apto / no apto / no verificable**.
- "No verificable" se muestra en su **propia banda**, con advertencia visible de que el dato de
  alérgenos del producto está incompleto. Nunca se mezcla con "apto".
- Fuentes: `allergens` (positivo confirmado) y `traces` ("puede contener", igual de relevante para
  el fail-safe). `allergens_en` existe en el export pero llega **vacía en el 100 % de las filas**
  (ver B11): no es una fuente utilizable.

### A16. Categoría de referencia para D1: retroceso ascendente con umbral mínimo

**Decisión cerrada el 2026-09-20**, resuelve el bloqueante B10. Verificado sobre
`notebooks/02_eda_universo_mexico.ipynb` (sección 5): ni la etiqueta más específica de
`categories_tags` (mediana de 14 miembros; 40,8 % de los productos con categoría cae en una
categoría específica de menos de 10 miembros) ni la más genérica (`en:plant-based-foods-and-beverages`
agrupa sola 3.048 productos heterogéneos) sirven por sí solas para calcular un percentil confiable.

- La categoría de referencia de un producto es su **etiqueta más específica** de `categories_tags`
  (última posición: OFF ordena la lista de lo genérico a lo específico).
- Si esa categoría tiene **menos de 30 productos** en el universo puntuable, se **sube un nivel** (la
  etiqueta inmediatamente anterior) y se repite la comprobación.
- Si se agota la jerarquía del producto sin alcanzar el umbral, el producto **no tiene categoría de
  referencia válida**: D1 queda "sin dato" para él (nunca se fuerza una categoría demasiado pequeña
  ni una demasiado genérica). Consistente con A2: sin dato es NULL + bandera, no una aproximación.
- El umbral de 30 se fijó porque cubre el 64,0 % de los productos con categoría específica sin
  necesitar retroceso; es un valor inicial, no una constante inamovible, y se revisa al construir
  `category_stats`.

### A17. D2 combina NOVA con `additives_n`, no NOVA en solitario

**Decisión cerrada el 2026-09-20**, sobre `notebooks/02_eda_universo_mexico.ipynb` (sección 3). NOVA
solo discrimina poco en el universo México: **69,5 %** de los 6.781 productos con NOVA son grupo 4,
que recibirían subpuntaje 0 sin distinción entre sí. `additives_n` tiene una relación **monótona y
clara** con NOVA (aditivos promedio: 0,09 en N1, 0,13 en N2, 0,49 en N3, 3,71 en N4) y una cobertura
ligeramente mayor (45,4 % vs 40,2 %).

- **D2 = NOVA como base + ajuste continuo por `additives_n` dentro de cada grupo.** No es un
  constructo nuevo: `additives_n` refina la medida de procesamiento *dentro* de los cuatro niveles de
  NOVA, de forma análoga a como D1 combina varios nutrientes dentro de una sola dimensión (A4). No
  duplica NOVA como dimensión aparte.
- La fórmula exacta de combinación se define en el paso de transformación (`src/nutrimatch/engine`),
  no aquí.

### A18. Saneamiento de valores físicamente imposibles antes de puntuar

**Decisión cerrada el 2026-09-20**, sobre `notebooks/02_eda_universo_mexico.ipynb` (sección 6). Se
detectaron errores de captura reales en OFF México: **58 productos** con `energy-kcal_100g > 900`
(máximo teórico, grasa pura), incluyendo un caso de **277.183 kcal/100 g**. La desviación
kJ↔kcal >5 % afecta al **20,1 %** de los productos con ambos campos (más del doble que la baselina
sesgada de 7.2, que reportaba 9,9 %).

- Los valores fuera de rango físico plausible se marcan con **flag de calidad** explícito.
- Un producto con flag de calidad se **excluye del cálculo de percentiles y de `category_stats`**
  para esa dimensión (no puede aportar una comparación válida).
- El dato crudo **permanece visible** en la ficha del producto: no se oculta ni se corrige en
  silencio. Es coherente con A2 (nunca imputar) y con no perder trazabilidad.
- Los umbrales exactos de saneamiento (qué cuenta como "fuera de rango" para cada nutriente) se
  definen en el paso de transformación.

### A19. Universo híbrido: buscar sobre todo, rankear solo sobre lo puntuable

**Decisión cerrada el 2026-09-20**, sobre `notebooks/02_eda_universo_mexico.ipynb` (sección 8). Solo
el **34,8 %** del universo México (5.856 de 16.851) cumple a la vez los requisitos de D1 (core5 +
categoría de referencia) y D2 (NOVA). Restringir todo el MVP a ese subconjunto dejaría fuera dos
tercios del catálogo, incluida búsqueda y escaneo.

- Los **16.851 productos** del snapshot son **buscables y consultables** en todo momento, mostrando
  la información disponible con sus banderas de dato faltante.
- Solo entran al **ranking comparativo** los productos que cumplen D1 + D2 **y** `cov ≥ 0.5` (A2)
  según las prioridades activas de la usuaria (el universo puntuable exacto varía por usuaria, porque
  D3 depende de qué etiquetas valoradas eligió).
- Los que no cumplen van a la banda "información insuficiente" de A2, que ya contemplaba este caso.

### A20. Fibra incluida en el núcleo nutricional global (core8)

**Decisión cerrada el 2026-09-20**, sobre `notebooks/02_eda_universo_mexico.ipynb` (sección 2). La
sección 7.7 del documento maestro original marcaba la fibra como candidata a "opcional o por
categoría" porque en la muestra sesgada de 7.2 derribaba mucho la cobertura de core7 en lácteos y
bebidas. Verificado sobre el universo real: `fiber_100g` resta solo **3,1 puntos porcentuales** sobre
core7 (49,6 % vs 52,7 %), un impacto mucho menor al que sugería la muestra sesgada.

- La fibra se incluye en el **núcleo nutricional global** (core8: los 7 nutrientes de core7 más
  fibra) desde ahora, sin excepción por categoría.
- Se revisa si conviene una excepción por categoría cuando exista `category_stats` con el desglose
  real por categoría (esta decisión se tomó sobre el agregado del universo, no por categoría).

### A21. Corrección de escala de sal cuando la razón con sodio es ≈2,5

**Decisión cerrada el 2026-09-20**, sobre `notebooks/03_transformacion_score.ipynb` (sección 1). Al
sanear `salt_100g` (A18), 56 productos quedaron fuera de rango; 55 de ellos mantienen exactamente la
razón sal ≈ 2,5 × sodio del producto (fórmula química estándar, no un ajuste del dataset) y, al
dividir entre 1000, caen en un rango de sal perfectamente normal para su tipo de producto (compatible
con una captura en miligramos donde se esperaban gramos). El caso restante (razón ≈2500) es un error
de otra naturaleza.

- Se corrige automáticamente `salt_100g` cuando, estando fuera de rango, su razón con `sodium_100g`
  es ≈2,5 (tolerancia ±0,02) **y** el valor reescalado (÷1000) cae dentro del rango válido.
- La corrección se deriva siempre del propio dato del producto (su `sodium_100g`), nunca de un valor
  externo o supuesto: no es "inventar" un dato, es reconciliar dos campos del mismo producto con una
  fórmula universal.
- Queda trazable vía `salt_100g_flag_correccion_escala_aplicada`: se puede distinguir siempre un dato
  "tal cual vino" de uno "corregido por esta regla".
- El caso que no cumple la razón se queda fuera de la regla y sigue marcado como fuera de rango sin
  corregir (A18 sin excepción).
- Implementado en `nutrimatch.engine.sanitize.corregir_escala_sal_por_sodio`.

### A22. Umbral del universo puntuable: ≥4 de 8 percentiles válidos + D2 calculable

**Decisión cerrada el 2026-09-20**, sobre `notebooks/03_transformacion_score.ipynb` (sección 6),
afinando A19. La estimación naive de A19 (34,8 %) no exigía categoría de referencia resuelta ni
mínimo de pares por percentil; recalculado con precisión, ese mismo 34,8 % se reproduce casi exacto
exigiendo **al menos 4 de los 8 percentiles de D1 sean válidos** (la mitad del núcleo nutricional) y
D2 sea calculable (el producto tiene NOVA): 5.864 productos (34,8 %). Exigir los 8 completos baja el
universo a 31,7 % (5.341); exigir solo 1 lo sube apenas a 34,9 % (5.888) — la diferencia entre los
tres umbrales es pequeña, y se elige el intermedio.

- Columna `universo_puntuable` (booleana) guardada en `matriz_nut_100g`, calculada con este umbral.
- No sustituye a `cov` (A2): `cov` sigue siendo la regla fina que pondera cada dimensión según los
  pesos de la usuaria; este umbral es un filtro previo, agnóstico del usuario, sobre qué productos
  tienen *suficiente dato crudo* para intentar puntuarse en absoluto.

### A23. Fórmula de D2 confirmada: bandas de 25 puntos por grupo NOVA, ajustadas por `additives_n`

**Decisión cerrada el 2026-09-20**, sobre `notebooks/03_transformacion_score.ipynb` (sección 4),
cerrando el "cómo" que A17 dejó abierto (A17 solo cerró el "qué": combinar NOVA con `additives_n`).

- Cada grupo NOVA ocupa una banda fija de 25 puntos en la escala 0-100 (NOVA=1 → 75-100, NOVA=2 →
  50-75, NOVA=3 → 25-50, NOVA=4 → 0-25), preservando que ningún producto de mejor NOVA puede puntuar
  por debajo de uno de peor NOVA.
- Dentro de su banda, `additives_n` empuja el subpuntaje hacia el piso, hasta un tope calibrado como
  el **percentil 95 de `additives_n` entre los productos NOVA=4 del propio snapshot** (recalculado en
  cada snapshot, no una constante fija; da 9,0 en `off_csv_20260919`).
- `additives_n` ausente se trata como 0 aditivos (la posición más favorable dentro de la banda), no
  como dato faltante que anule D2.
- D2 solo es calculable si el producto tiene NOVA; sin NOVA, D2 es NULL (A2).
- Implementado en `nutrimatch.engine.processing_score`.

### A24. Mínimo de pares para un percentil confiable: 5

**Decisión cerrada el 2026-09-20**, sobre `notebooks/03_transformacion_score.ipynb` (sección 3). Que
una categoría de referencia alcance el mínimo de A16 (30 productos con la etiqueta) no garantiza que
haya suficientes productos con dato válido para un nutriente concreto en particular. Se exige un
mínimo de **5 productos con dato saneado válido** en la categoría de referencia para calcular el
percentil de ese nutriente; si no se alcanza, el percentil es NULL para ese producto y ese nutriente,
aunque la categoría nominal cumpla A16. Implementado en `nutrimatch.engine.constants.MINIMO_PEERS_PERCENTIL`.

### A25. Fórmula de pesos del usuario: secuencia 3/2/1 normalizada según el orden de prioridades

**Decisión cerrada el 2026-09-20**, sobre `notebooks/04_modelo_recomendacion.ipynb` (sección 2),
cierra el "cómo" que A6 dejó abierto (A6 solo cerró el "qué": ordenar 3 prioridades, sin controles
numéricos directos).

- El orden de las 3 prioridades declaradas (D1, D2, D3) se convierte en pesos proporcionales a la
  secuencia fija 3/2/1 según la posición (1º lugar = 3 puntos, 2º = 2, 3º = 1), normalizada para
  sumar 1: 0,50 / 0,33 / 0,17 para 1º/2º/3º lugar.
- Con exactamente 3 dimensiones hay solo 6 permutaciones posibles; los tres valores resultantes son
  siempre los mismos, solo cambia a qué dimensión se asigna cada uno. Es un reparto transparente y
  fácil de explicar en la interfaz, no una medición calibrada sobre datos.
- Implementado en `nutrimatch.engine.user_weights.convertir_prioridades_a_pesos`.

### A26. Renormalización del score cuando falta una dimensión: promedio ponderado sobre las disponibles

**Decisión cerrada el 2026-09-20**, sobre `notebooks/04_modelo_recomendacion.ipynb` (sección 6),
cierra el "cómo" que A7 dejó abierto para el caso de datos parciales (A7 solo fija que el score es
"la suma ponderada por los pesos de A6" para el caso completo).

- Cuando una dimensión no tiene subpuntaje calculable para un producto, el score final se calcula
  como `Σ wᵢ·Dᵢ / Σ wᵢ`, sumando solo sobre las dimensiones con dato disponible — no se trata la
  dimensión faltante como 0.
- Es coherente con la regla de cobertura `cov` (A2): `cov` ya mide exactamente esa fracción de peso
  disponible, así que cuando `cov ≥ 0,5` el score usa esa misma fracción como denominador. Si
  `cov < 0,5` (banda "información insuficiente"), el score final es NULL, nunca un número calculado
  sobre datos insuficientes.
- Verificado con el perfil "Caro" del notebook (no declaró ninguna etiqueta valorada): D3 es NULL
  para el 100 % del catálogo, y su score se calcula solo con D1 y D2 renormalizados sobre la suma de
  sus dos pesos — su `cov` máxima posible queda acotada exactamente en ese peso conjunto.
- Implementado en `nutrimatch.engine.compatibility_score.calcular_score_compatibilidad`.

### A27. Alcance de D1 v1: 5 nutrientes de signo fijo; energía, grasa total y carbohidratos quedan informativos

**Decisión cerrada el 2026-09-20**, sobre `notebooks/04_modelo_recomendacion.ipynb` (sección 4),
acota A7 para esta versión del motor.

- D1 puntúa únicamente los 5 nutrientes de core8 con dirección universal y sin ambigüedad:
  azúcares, sal y grasa saturada (signo −1, menos es mejor); fibra y proteína (signo +1, más es
  mejor).
- `energy-kcal_100g`, `fat_100g` (grasa total) y `carbohydrates_100g` siguen calculándose (tienen
  percentil en `matriz_nut_100g`, paso 6) y se muestran como información en la ficha del producto,
  pero no puntúan en esta versión: el documento maestro los deja "según meta" sin definir en ningún
  lugar del proyecto qué valores toma esa meta (el motor no modela una taxonomía de objetivos
  nutricionales del usuario). Inventar esa taxonomía sin una decisión explícita habría sido asumir
  un requisito que nadie cerró.
- Añadir estos 3 nutrientes a D1 en una versión futura es un cambio aditivo: no rompe la firma de
  `calcular_subpuntaje_d1` ni las llamadas existentes.
- D1 tiene dato disponible en 7.040 de 16.851 productos del universo México (41,8 %) — más amplio
  que `universo_puntuable` (A22, 34,8 %) porque ese umbral exige además D2 calculable y ≥4 de los 8
  percentiles de core8, no solo los 5 con signo de esta versión.
- Implementado en `nutrimatch.engine.nutrition_score`.

### A28. Resolución del nombre de un producto para mostrar: fallback entre columnas del propio OFF

**Decisión cerrada el 2026-09-20**, sobre `notebooks/04_modelo_recomendacion.ipynb` (Sección 1).
Detectado al revisar el ranking del paso 7: `product_name` viene vacío para 1.740 de los 16.851
productos del universo México (10,3 %); de esos, 68 (0,4 %) sí tienen `generic_name` (y en algunos
casos también `abbreviated_product_name`) con el nombre real del producto — por ejemplo el code
`5060323907641`, sin `product_name` pero con `generic_name = "Organic Smooth Almond Butter"`, que
sí aparece con ese nombre en `openfoodfacts.org`. No es un dato ausente en OFF: son campos del
propio registro que un contribuidor llenó sin sincronizar entre sí.

- El nombre a mostrar se resuelve por fallback en este orden: `product_name` → `generic_name` →
  `abbreviated_product_name`, usando siempre columnas del **mismo producto** (nunca un valor
  externo ni inventado, mismo principio que la corrección de sal de A21).
- El snapshot crudo (`off_mexico_20260919.parquet`) **no se modifica**: `product_name` sigue vacío
  ahí tal cual lo entrega OFF (A2 — el dato crudo se conserva). La resolución se aplica solo al
  construir el nombre para mostrar, guardando el original en `product_name_bruto`.
- Queda trazable vía `product_name_flag_respaldo_usado`: distingue un nombre "tal cual vino en
  `product_name`" de uno "resuelto por esta regla" — mismo patrón que
  `salt_100g_flag_correccion_escala_aplicada` (A21).
- Si ninguno de los tres campos tiene dato, el nombre resuelto es `None`: sigue siendo un NULL
  genuino, no se inventa un nombre placeholder.
- Implementado en `nutrimatch.engine.product_naming.resolver_nombre_producto`.

### A29. Golden set: 13 casos reales, revisados a mano, sobre productos del snapshot

**Decisión cerrada el 2026-09-20**, sobre `notebooks/05_evaluacion.ipynb` (Sección 1), cierra el
primero de los tres mecanismos de evaluación que A8 dejó pendientes.

- El golden set fija 13 `code` reales de `off_csv_20260919`, cada uno con una descripción de qué
  se espera y por qué, verificada a mano contra los valores crudos del snapshot: D1 y D2 en los
  dos extremos (muy malo / muy bueno), los tres estados del filtro de alergia (confirmado en
  `allergens`, "puede contener" en `traces`, sin dato → no_verificable), los tres estados de dieta
  vegana (compatible / incompatible / "tal vez" → no_verificable), independencia entre D1 y D2
  cuando falta solo una de las dos fuentes (categoría de referencia vs. NOVA), el fallback de
  nombre (A28), D3 con una etiqueta exacta, y un caso de regresión de score completo ya auditado
  a mano en `04_modelo_recomendacion.ipynb` (Sección 8).
- Si el snapshot se regenera y un producto cambia legítimamente en OFF, el caso correspondiente
  puede empezar a fallar: es señal de revisar ese caso puntual (¿sigue siendo válido con el dato
  nuevo? ¿hay que sustituir el `code`?), no necesariamente un bug del motor.
- Implementado en `evaluacion/golden_set.py`, con pruebas de regresión en `tests/test_golden_set.py`
  que leen directamente `datos/procesados/*.parquet` (versionado en el repo, ver Sección B12): no
  hace falta descargar ni reconstruir nada para correrlas.

### A30. Parity-check: correlación de Spearman D1 vs `nutriscore_score`, umbral −0,3

**Decisión cerrada el 2026-09-20**, sobre `notebooks/05_evaluacion.ipynb` (Sección 2), cierra el
segundo mecanismo de A8.

- D1 y Nutri-Score puntúan nutrientes parcialmente distintos y con metodologías distintas: D1 usa
  percentil dentro de la categoría de referencia sobre 5 nutrientes de signo fijo (A27);
  Nutri-Score usa puntos de penalización/bonificación calibrados por macrocategoría sobre un
  conjunto más amplio (incluye energía, sodio y fruta/verdura/legumbres, que D1 v1 no puntúa). No
  se espera una correlación fuerte, y exigirla sería incoherente con A4 (Nutri-Score no puntúa en
  NutriMatch justamente para no contar dos veces los mismos nutrientes que D1).
- Umbral fijado en **correlación de Spearman ≤ −0,3** (negativa porque D1 alto = mejor y
  `nutriscore_score` alto = peor). Deliberadamente laxo ("moderada" en la convención habitual de
  0,3-0,5): es un chequeo de sanidad ("¿va, a grandes rasgos, en la misma dirección?"), no una
  validación de que D1 deba replicar a Nutri-Score.
- Verificado sobre 6.041 productos con ambos datos disponibles: correlación real ≈ **−0,4747**,
  por encima del umbral en magnitud, y el promedio de D1 por `nutriscore_grade` decrece de forma
  estrictamente monótona de grado 'a' (≈59,6) a 'e' (≈41,6).
- La correlación se calcula como Pearson sobre rangos (`Series.rank().corr()`) en vez de
  `.corr(method="spearman")` para no añadir `scipy` como dependencia nueva solo por esta función.
- Implementado en `evaluacion/parity_check.py`.

### A31. Diagnóstico de cobertura: desglose por combinación de dimensiones faltantes

**Decisión cerrada el 2026-09-20**, sobre `notebooks/05_evaluacion.ipynb` (Sección 3), cierra el
tercer mecanismo de A8.

- Para un perfil de usuaria dado, se calcula `cov` producto a producto (reutilizando
  `nutrimatch.engine.coverage`, A2, sin recalcularla) y se desglosan los productos en la banda
  "información insuficiente" por la combinación exacta de dimensiones que les falta (p. ej.
  `"D1+D2"`, `"D1+D2+D3"`), no solo el conteo total.
- Verificado con los 3 perfiles de ejemplo de `04_modelo_recomendacion.ipynb` (Ana, Beto, Caro)
  sobre el universo completo: la banda va de 56,5 % a 65,1 % (idéntico al paso 7, es el mismo
  cálculo). La causa dominante en los tres perfiles es la combinación `"D1+D2+D3"` (81-82 % de los
  insuficientes de cada uno): productos sin dato nutricional ni NOVA a la vez, no una debilidad de
  una sola dimensión.
- Con la fórmula de pesos de A25 (0,50/0,33/0,17), cualquier par de dos dimensiones suma ≥ 0,5
  exacto, así que perder una sola dimensión nunca es suficiente por sí sola para cruzar el umbral
  de A2 — de ahí que ninguna combinación de una sola dimensión faltante aparezca en el desglose
  con esta fórmula de pesos concreta. Si A25 cambiara en el futuro (más de 3 dimensiones, u otra
  secuencia de puntos), esta conclusión habría que revisarla.
- Implementado en `evaluacion/coverage_diagnostic.py`.

### A32. Bandas exclusivas de la interfaz: excluido, no verificable, información insuficiente, ranking

**Decisión cerrada el 2026-09-20** (bandas de interfaz; el 2026-09-27 se muestran solo en
Angular). A15 ya exigía que "no verificable" no se mezcle con "apto"; A2 ya exigía la banda de
`cov < 0.5`. Faltaba el orden cuando un producto cumple más de una condición a la vez.

Un producto cae en **exactamente una** banda, en este orden:

1. **Excluido** (no se lista; solo se cuenta): alergia `no_apto` o dieta `incompatible`.
2. **No verificable** (banda propia, con advertencia): alergia `no_verificable` o dieta
   `no_verificable`.
3. **Información insuficiente**: `cov < 0.5` (A2).
4. **Ranking**: el resto, ordenado por `score_final` descendente.

La búsqueda (nombre o `code`) se aplica **antes** de puntuar, sobre los 16.851 productos (A19).
Implementado en `nutrimatch.services.ranking.asignar_banda`. La UI que las lista es Angular
(`/recomendaciones`, ficha, comparar): no hay otra capa de presentación.

### A33. Procedencia: vocabulario de cinco estados y tabla de observaciones

**Decisión cerrada el 2026-09-26**, sobre
[`docs/diagnostico_calidad_datos.md`](docs/diagnostico_calidad_datos.md) (sección F). No se
implementa todavía: solo se cierra el criterio.

Toda variable enriquecida, derivada o ausente se etiqueta con **exactamente uno** de:

```
REAL | DERIVED | IMPUTED | SYNTHETIC | UNAVAILABLE
```

- **REAL**: observado en una fuente identificable (export OFF, Open Prices, QQP, GS1).
- **DERIVED**: calculado a partir de REAL sin modelo predictivo (D1/D2/D3, percentil, fallback
  A28, corrección de escala de sal A21, `cov`).
- **IMPUTED**: estimado por un método estadístico porque el valor no existía. Ninguna variable
  del catálogo de producción está en este estado hoy (A36 cierra el precio).
- **SYNTHETIC**: creado para demo o test. Solo fixtures; nunca el Parquet de producción.
- **UNAVAILABLE**: se sabe que no hay dato; el valor es NULL. Un cero no sustituye este estado
  (A2).

La **calidad** (`fuera_de_rango`, `data_quality_errors_tags`) es **ortogonal** al status: un valor
puede ser REAL y a la vez de mala calidad.

Las 211 columnas del Parquet México son REAL por construcción. No se clona un `*_status` por
columna. El metadato de tabla (`snapshot_id`, URL del export, `retrieved_at` en
`_metadata.json`) basta para ese bloque.

Lo que no viene del export (nombre externo, precio, imputación futura) vive en una **tabla de
observaciones** `(code, field, value, status, source, source_url, retrieved_at, snapshot_id,
method, confidence, quality_flag)`. Varias observaciones por `(code, field)` son válidas. La
ficha elige según regla explícita: REAL más reciente; si no hay, UNAVAILABLE; nunca IMPUTED ni
SYNTHETIC por delante de REAL.

El trío `*_bruto` / `*_saneado` / `*_flag_*` de la matriz (paso 6) es el patrón a generalizar,
no a sustituir.

### A34. El objeto de análisis es el GTIN (`code`)

**Decisión cerrada el 2026-09-26.** No se agrupan presentaciones.

`code` es la llave. Hay 16.851 códigos únicos, 0 duplicados, 96,9 % con checksum GS1 válido
(medido el 2026-09-26). Los 885 pares marca+nombre repetidos y los 2.667 nombres repetidos no
son el mismo producto: pueden ser sabores, tamaños o errores de captura. Colapsarlos sin
revisión a mano mezclaría observaciones distintas.

Agrupar “el mismo producto comercial” (marca + receta + presentación) es un paso posterior, con
llave explícita y muestra revisada. Hasta entonces, cada GTIN es una fila.

### A35. Precio: piloto Open Prices por EAN; QQP después, solo con match revisado

**Decisión cerrada el 2026-09-26**, sobre el diagnóstico de precios (sección D).

- **Ahora:** materializar —cuando se implemente el piloto, no en este corte— los precios MXN de
  Open Prices que ya cruzan por `product_code` con el universo México: 242 códigos (1,4 %),
  medidos el 2026-09-26. Son REAL, con establecimiento, fecha y EAN. El resto del catálogo queda
  `price = NULL`, `price_status = UNAVAILABLE`.
- **Después:** QQP sigue siendo la fuente oficial más grande de precios reales en México, pero
  **no publica código de barras** (A5). El cruce es por texto. **Prohibido el join automático
  `QQP → code`.** Solo una muestra pequeña con match revisado a mano; el precio no se presenta
  como “el” precio de ese EAN, sino como precio de referencia de una presentación parecida, con
  `match_method` y `match_confidence` visibles.
- Retailers (Walmart, Soriana, etc.) y scraping: fuera de alcance.

El precio **no puntúa** (A5). El piloto sirve para diseñar el esquema `price_*` y la tabla de
observaciones (A33), no para completar el catálogo.

### A36. Precio en esta tesis: solo REAL o NULL

**Decisión cerrada el 2026-09-26.** A5 **no se reabre**.

No se imputa precio. 242 observaciones sesgadas a quien subió un ticket no entrenan un modelo
generalizable a 16.851 productos.

- QQP, si entra más adelante, se llama **"precio de referencia"**, nunca "estimado".
- Datos sintéticos de precio: solo fixtures de test, nunca el Parquet de producción, y con
  status SYNTHETIC (A33).
- Si en una versión futura hubiera un precio IMPUTED, el rótulo sería **"precio imputado por
  modelo"**, no se recicla "precio de referencia".

Tampoco se imputan alérgenos, sellos, dieta, NOVA ni los nutrientes CORE8: el faltante va con
ingredientes incompletos (**MAR**, no MNAR — corregido en A42 con evidencia medida el
2026-09-26). Inventarlos cambiaría el significado del ranking y, en alergias, el riesgo. Los
tres estados de A15 y el NULL+bandera de A2 cubren esos casos.

### A37. Nombres ausentes: conservar el original; recuperar por EAN, no imputar

**Decisión cerrada el 2026-09-26.** El snapshot crudo **no se modifica** (A2, A28).

Orden, de menor invención a mayor:

1. `product_name_original` = `product_name` de OFF, aunque sea NULL (1.740 vacíos; 1.672 sin
   ninguno de los tres campos de nombre, 9,9 %, medido el 2026-09-26).
2. Fallback interno A28 (`generic_name` → `abbreviated_product_name`) = DERIVED del **mismo**
   registro. Recupera 68 casos; no inventa.
3. Normalización cosmética (trim, Unicode, MAYÚSCULAS) = DERIVED. No pisa el original.
4. **Experimento de recuperación** (cuando se pida, no en este corte): muestra de 50–100 de los
   1.672 vía API de producto OFF, un `code` a la vez, respetando B4–B5 (15 req/min, 503
   anti-crawl). Se mide la tasa de hit. Un nombre recuperado es REAL de esa fuente, otra
   observación (A33), no un overwrite del export.
5. GS1 México / Verified: solo si el hit de (4) es bajo **y** hay membresía. No es una fuente
   abierta.

Prohibido imputar el nombre con un modelo estadístico y prohibido un placeholder ("Producto
750…") presentado como nombre real.

### A38. Homologación determinista de nombre y marca: sin diccionario de alias

**Decisión cerrada el 2026-09-26**, paso 3 del plan de trabajo de
[`docs/diagnostico_calidad_datos.md`](docs/diagnostico_calidad_datos.md) (sección H), sobre
`notebooks/08_re_eda_identidad.ipynb`. Construye el Parquet **nuevo**
`datos/procesados/identidad_homologada_20260919.parquet` (DERIVED, A33); no toca
`off_mexico_20260919.parquet` (A2, A28, A37).

- **Placeholder de captura en `product_name`.** 14 de los 16.851 productos traen literalmente
  `"Cargando…"` — un texto de la interfaz de contribución de OFF grabado por error, no un
  nombre. Se trata como si `product_name` estuviera vacío y se sigue la cadena de fallback de
  A28: 1 de los 14 (`7503028965717`) recupera un nombre real desde `generic_name`
  ("Totopos de maíz horneados con nopal"); los otros 13 quedan `UNAVAILABLE`. Total tras
  homologar: **1.685 productos sin nombre** (los 1.672 de A37 más estos 13), **69** usaron
  respaldo (los 68 de A28 más este caso).
- **Homologación de marca: plegado de acentos, no diccionario.** `brands` trae la misma marca
  escrita de formas distintas (`Nestlé` 140 filas, `nestle` 106). La regla es
  minúsculas + plegado Unicode de acentos (NFKD, se descartan los caracteres combinantes) +
  colapso de espacios — **no** una lista de alias mantenida a mano, que sería arbitraria y
  dejaría de servir en el próximo snapshot. Verificado: funde automáticamente 73 de 4.189
  marcas únicas del universo México (`Nestlé`/`nestle`, `La Costeña`/`la costena`,
  `Nescafé`/`nescafe`, `Tajín`/`tajin`, entre otras).
- `brand_homologated` es una **llave de coincidencia interna** (pierde acento y mayúsculas a
  propósito), no un valor para mostrarse en la interfaz — a diferencia de
  `product_name_homologated`, que conserva acentos y mayúsculas porque sí es para mostrarse.
  Pensada para el cruce de texto con QQP (A35), todavía no implementado.
- No se separan marcas múltiples (`"walmart,sams club"`): se homologan como una sola cadena.
  Partirlas en lista es un paso posterior si hace falta.
- Implementado en `nutrimatch.engine.identity_homologation`, ejecutado por
  `scripts/homologar_identidad.py`.
- **Trampa de implementación (extiende B13):** construir estas columnas con
  `DataFrame.apply(..., result_type="expand")` o `Series.map` sobre pandas 3.x hace que la
  columna resultante adopte el nuevo dtype `str` nativo y convierta cada `None` en
  `float("nan")` en silencio — la misma trampa de B13, pero disparada por código de
  transformación en vez de por la lectura del Parquet. Un chequeo `campo is not None` sobre esa
  columna ya coercionada marca *todas* las filas como "con dato". Se evita calculando cada fila
  con Python puro sobre listas (no sobre una `Series` intermedia) y derivando
  `*_status`/`*_flag_*` con un chequeo de nulidad que cubre `None` y `NaN` por igual, antes de
  ensamblar el `DataFrame` final.

### A39. Experimento de recuperación de nombres por API OFF: tasa de hit 7,5 %, no justifica escalar sin pedirlo

**Decisión cerrada el 2026-09-26**, sobre `scripts/experimento_recuperacion_nombres.py`, cierra el
punto 4 de A37 ("cuando se pida") y el paso 4 del plan de trabajo de
[`docs/diagnostico_calidad_datos.md`](docs/diagnostico_calidad_datos.md) (sección H).

- **Muestra:** 80 de los 1.685 códigos sin ningún nombre tras homologar (A38), semilla `20260926`
  (reproducible), un `code` a la vez contra `world.openfoodfacts.org` (producción), espaciado de
  4,5 s entre peticiones (~13,3/min, por debajo del límite de 15/min de B4).
- **Resultado:** los 80 códigos **sí existen** en la ficha viva (100 % `encontrado`, 0 errores
  anti-crawl 503/429 en todo el lote). De esos 80, **6 (7,5 %)** tienen un nombre real en la API
  viva que el export CSV del snapshot no capturó (p. ej. `7622210571328` → "Trident XtraCare
  yerbabuena", `7501017660339` → "horchata el yucateco") — revisados a mano, ninguno es un
  placeholder ni texto basura. 0 de los 80 repite el placeholder "Cargando…" (A38) en la ficha
  viva.
- **Lectura:** 7,5 % está por debajo del umbral de 20 % fijado como referencia informal en el
  script para "vale la pena ampliar". No es cero — hay señal real, y extrapolar sugiere unos
  ~126 nombres recuperables sobre los 1.685 completos —, pero tampoco es el "hueco grande" que
  A37 (paso 5) pone como condición para evaluar GS1 México. Correr el experimento sobre el
  universo completo de 1.685 (≈2,1 horas al mismo ritmo, sin motivo para esperar más 503 que en
  la muestra) es una extensión de bajo costo y cero riesgo nuevo, pero es una decisión de alcance
  (cuántos recursos dedicar a un 7,5 %), no una consecuencia automática de este resultado — queda
  pendiente de pedirse explícitamente.
- Cada nombre recuperado así es **REAL** de la fuente `openfoodfacts_api_producto` (A33), no un
  overwrite del export: vive en un Parquet aparte,
  `datos/procesados/experimento_recuperacion_nombres_20260919.parquet`, con
  `source_url`/`retrieved_at`/`status_valor` por fila — el embrión de la tabla de observaciones
  de A33, no la tabla final todavía.
- Implementado en `nutrimatch.providers.off_product_api` (cliente con caché en disco en
  `datos/cache/off_producto_api/`, no versionada, y límite de tasa) y
  `scripts/experimento_recuperacion_nombres.py`.

### A40. Piloto de precios Open Prices materializado: 242 códigos, esquema `price_*` implementado

**Decisión cerrada el 2026-09-26**, sobre `scripts/piloto_precios_open_prices.py`, cierra la
parte (a) del paso 6 del plan de trabajo de
[`docs/diagnostico_calidad_datos.md`](docs/diagnostico_calidad_datos.md) (sección H) y ejecuta
lo que A35 dejaba para "cuando se implemente el piloto".

- **Contrato real de la API de Open Prices, verificado en vivo el 2026-09-26** (no existía
  código propio antes; la sonda previa citada en A35 no se persistió): el filtro
  `location_country_code` **no existe** en `PriceFilter` del backend de Open Prices y
  django-filter lo ignora en silencio en vez de fallar — devuelve resultados sin filtrar. El
  filtro correcto es **`currency=MXN`** (`currency` sí es un campo exacto del filtro),
  paginado con `size`/`page` (máx. 100/página). Verificado leyendo
  `open_prices/api/prices/filters.py` y `open_prices/api/pagination.py` del propio repo de
  Open Prices, no por prueba y error sobre el esquema de respuesta.
- **Resultado, medido de nuevo el 2026-09-26** (reproduce exacto la sonda de A35): 346 precios
  en MXN en total en Open Prices, 276 códigos de producto únicos, de los cuales **242 (1,4 %)**
  cruzan por `product_code` con el universo México de 16.851 — 307 filas (varias observaciones
  por código son válidas, A33). Rango de precio $8.50–$528.50 MXN; fechas 2024-06-10 a
  2026-09-02. No se observó ningún 429/503 en las 4 páginas necesarias (a diferencia de la API
  de producto de OFF, B4): esta API no tiene, o no expone, el mismo límite anti-crawl.
- Las 307 filas son **REAL** (A33), con `match_method = "exact_gtin"` (sin ambigüedad:
  `product_code` es el mismo GTIN que `code`) y `match_confidence = NULL` (solo aplica a
  coincidencias de texto, no a esta). Ninguna fila pisa un Parquet existente: se escribió
  `datos/procesados/precios_open_prices_20260926.parquet`, nuevo, con el esquema `price_*` de
  la sección D.3 del diagnóstico (`code`, `product_code`, `price`, `currency`, `date_observado`,
  `retailer`, `location*`, `source`, `source_url`, `match_method`, `match_confidence`,
  `price_status`, `retrieved_at`, `pull_id`).
- El precio **no puntúa** (A5): este piloto no toca `score_final`, D1/D2/D3, `cov`, bandas de
  ranking ni la interfaz.
- **Fuera de esta decisión**, deliberadamente: el diseño y piloto de match por texto con QQP
  (parte b del paso 6) — QQP no publica GTIN (A5) y requiere descargar su CSV actual y revisión
  manual de una muestra; queda como paso aparte, a pedirse explícitamente.
- Implementado en `nutrimatch.providers.open_prices_api` (cliente con caché en disco en
  `datos/cache/open_prices_api/`, no versionada) y `scripts/piloto_precios_open_prices.py`.

### A41. Piloto de match QQP por texto (Fase A): esquema real corregido, 40 candidatos con score visible, sin join automático

**Decisión cerrada el 2026-09-26**, sobre `scripts/piloto_precios_qqp.py`, cierra la parte (b)
del paso 6 del plan de trabajo de
[`docs/diagnostico_calidad_datos.md`](docs/diagnostico_calidad_datos.md) (sección H), que A40
dejó explícitamente fuera. Ejecuta la Fase A que A35 exige antes de cualquier materialización de
precio QQP; la Fase B (materializar) queda lista pero **bloqueada** hasta que exista revisión
humana (ver "Qué sigue" más abajo).

- **Fuente real, verificada en vivo el 2026-09-26**: `datos.gob.mx` (portal CKAN de datos
  abiertos de PROFECO), dataset `programa_quien_es_quien_precios_2026`, verificado vía
  `package_show`. **El esquema real no tiene `cv_producto`/`cv_marca`** — columnas que
  `docs/diagnostico_calidad_datos.md` (sección D.1) suponía por analogía con otras fuentes de
  PROFECO, nunca verificadas contra la API real; esa fila del diagnóstico queda corregida.
  Esquema real: `producto, presentacion, marca, categoria, catalogo, precio, fecha_registro,
  cadena_comercial, giro, nombre_comercial, direccion, estado, municipio, latitud, longitud`.
  Sin ningún campo de código de barras (confirma A5).
- **No hizo falta descargar ningún CSV completo.** Cada recurso mensual ya está en el
  "datastore" de CKAN, consultable con `datastore_search` (`resource_id` + `filters` exacto +
  paginación). El recurso de julio 2026 (primera parte) tiene **665.909 filas totales**;
  `datastore_search_sql` (que habría permitido `DISTINCT` en servidor) devuelve `400 Bad
  Request` en esta instancia — deshabilitado —, así que el vocabulario de `categoria` se
  enumeró muestreando 40.000 filas ordenadas por ese campo: **42 categorías distintas**. Se
  eligieron 20 de alimentos/bebidas envasados con marca (p. ej. "Refrescos Envasados", "Leche
  Procesada", "Café", "Cerveza"), excluyendo frescos sin marca (`marca="S/M"` casi siempre, p.
  ej. "Hortalizas Frescas") y no-alimentos (Medicamentos, Material Escolar, Aparatos
  Eléctricos/Electrónicos, Detergentes, Juguetes, Cigarrillos, etc.).
- **Trampa real, no hipotética: un WAF (Akamai) frente a `www.datos.gob.mx` responde `HTTP 403`
  a cualquier `User-Agent` no-navegador** — incluido el `User-Agent` identificable que exige la
  convención B7 (`NombreApp/Version (contacto)`) y el `User-Agent` por defecto de `httpx`.
  Verificado aislando la variable: mismo request, mismos parámetros, solo cambia el
  `User-Agent`: `403` con uno identificable o el de `httpx`, `200` con uno de navegador
  (Chrome/Mac). **Decisión explícita de Paola (2026-09-26)**: usar un `User-Agent` de navegador
  **solo para este proveedor**, porque es un portal de datos abiertos público (CC-BY 4.0) y el
  bloqueo es una configuración de WAF por defecto, no una política anti-bot documentada de
  PROFECO — no es el mismo caso que OFF (B7), que sí controla su propio límite de tasa y pide
  explícitamente identificación. Documentado en el docstring de
  `nutrimatch.providers.qqp_api` como excepción explícita, no como el patrón por defecto de
  proveedores futuros.
- **El campo `marca` de QQP viene compuesto**, no es una llave de marca limpia: `"Nescafé.
  Clásico"`, `"La Lechera. Original"`, `"Nido. Entera. Forticrece"` — marca + variante separadas
  por punto. Confirma que el match debe ser holístico por texto (marca + producto + presentación
  juntos, vía `rapidfuzz.fuzz.WRatio`), no un join de llave de marca exacta contra
  `brand_homologated` (A38). El espacio de comparación se acota, aun así, por coincidencia del
  primer segmento de `marca` (homologado con la misma función de A38) contra
  `brand_homologated`, con una segunda pasada por primera palabra si la exacta no encuentra
  candidatos — evita un producto cruzado inviable (miles de filas QQP × 16.851 del catálogo).
- **Resultado de la Fase A, medido el 2026-09-26**: de las 20 categorías curadas, en ambas
  partes de julio 2026, con un tope de 150 filas por (recurso, categoría) — nunca la categoría
  completa —, se recolectaron **782 filas de QQP tras deduplicar** por
  (`marca`, `producto`, `presentacion`). De esas, **647 (82,7 %)** superan el piso de score 60
  contra el catálogo homologado (`identidad_homologada_20260919.parquet`, 12.543 productos con
  marca y nombre disponibles), con **275 `code` candidatos únicos** y un score promedio de 85,7.
  Muestra estratificada final de **40 filas** (semilla `20260926`, reproducible): 10 en
  [60-70), 7 en [70-80), 13 en [80-90), 10 en [90-100] — escrita en
  `datos/procesados/piloto_qqp_candidatos_20260926.csv`, columna `revisado` vacía.
- **La inspección manual de la muestra confirma que el score solo no basta** (justo lo que A35
  exige prevenir con revisión humana): varios candidatos en la banda alta (80-90) son
  claramente incorrectos pese al score — p. ej. QQP "Schettino · Maíz Palomero" emparejado con
  un `code` de "Schettino Lenteja" (85,5: misma marca, producto distinto), o "Mc Cormick ·
  Orégano" con un `code` de "Mermelada McCormick" (85,5). Ningún precio QQP se materializa a
  partir de este score sin que Paola marque la fila "correcto" a mano.
- **`price_status` sigue siendo `"REAL"` para las filas que Paola confirme**, nunca
  `"estimado"` (A5, A36): el precio que PROFECO observó es real; la incertidumbre vive en
  `match_method="text_reviewed"` y `match_confidence=score/100`, visibles por separado.
- Implementado en `nutrimatch.providers.qqp_api` (cliente con caché en disco en
  `datos/cache/qqp_api/`, no versionada), `scripts/piloto_precios_qqp.py` (Fase A, ejecutada) y
  `scripts/materializar_precios_qqp.py` (Fase B, con pruebas sobre un CSV sintético en
  `tests/test_materializar_precios_qqp.py` — no corrida contra datos reales todavía).
- **Qué sigue, y de quién**: la revisión manual de
  `datos/procesados/piloto_qqp_candidatos_20260926.csv` (marcar cada fila `"correcto"` o
  `"incorrecto"` en la columna `revisado`) es un paso que **solo Paola puede hacer** — es
  precisamente lo que A35 prohíbe automatizar. Cuando esté lista, `materializar_precios_qqp.py`
  escribe `datos/procesados/precios_qqp_<fecha>.parquet` con las filas confirmadas.
- **Cómo se hizo la revisión en la práctica (2026-09-26), para que quede trazable:** el agente
  añadió al mismo CSV dos columnas de apoyo, `sugerencia_ia` (`correcto`/`incorrecto`/`dudoso`)
  y `razon_ia` (una línea de justificación por fila, comparando marca/producto/variante entre
  QQP y el candidato), **antes** de que Paola llenara `revisado` — decisión explícita de Paola
  ante la disyuntiva planteada (no delegar la revisión, ni reabrir A35, sino usar la sugerencia
  como borrador acelerador). Paola confirmó verbalmente que, tras leer `sugerencia_ia` y
  `razon_ia`, adopta esos veredictos como su decisión final; `revisado` se llenó copiando
  `sugerencia_ia` literal (conservando el tercer estado `"dudoso"`, no forzado a binario).
  `materializar_precios_qqp.py` solo materializa `revisado == "correcto"` exacto, así que las
  10 filas `"dudoso"` quedaron excluidas automáticamente — mismo criterio fail-safe que A1/A15
  ("ante la duda, se excluye"), sin necesidad de una regla nueva.
- **Resultado de la Fase B, ejecutado el 2026-09-26**: de las 40 filas, **22 `"correcto"`**
  (10 en dudoso, 8 en incorrecto) se materializaron en
  `datos/procesados/precios_qqp_20260926.parquet`: 22 filas, **21 `code` únicos** (una fila
  duplica `code` con otra por dos presentaciones distintas de QQP del mismo producto — válido,
  A33), 100 % `price_status="REAL"`, 100 % `match_method="text_reviewed"`,
  `match_confidence` entre 0,60 y 0,95. Columnas de texto original de QQP (`qqp_marca`,
  `qqp_producto`, `qqp_presentacion`) se conservan en el Parquet para trazabilidad, aunque no
  son parte del esquema mínimo `price_*` de D.3.
- **Nota de honestidad metodológica**, por si se audita esta tesis: el primer borrador de cada
  veredicto fue de la IA, no de Paola desde cero. La revisión humana real consistió en leer las
  40 justificaciones y **confirmar** (no en juzgar cada match de forma independiente sin
  ayuda). Es una forma más débil de "revisado a mano" que la que A35 imaginaba originalmente
  (donde el humano parte de cero), aunque sigue habiendo una decisión humana explícita en cada
  fila — no un join automático silencioso, que es lo que A35 prohíbe en el fondo. Se documenta
  aquí sin maquillaje para que el criterio quede disponible si en el futuro se decide que la
  tesis requiere una revisión independiente desde cero antes de usar este Parquet en algo más
  que un piloto.

### A42. Mecanismo de faltantes en CORE8, categoría y variables afines: MAR condicionado a `completeness`/ingredientes, no MNAR

**Decisión cerrada el 2026-09-26**, sobre `scripts/analisis_mecanismo_faltantes.py`, cierra el
paso 7 del plan de trabajo de [`docs/diagnostico_calidad_datos.md`](docs/diagnostico_calidad_datos.md)
(sección H) y la fila "Decisión por variable de la tabla E" que ese paso exigía. **Corrige el
término usado en A36** ("MNAR") — la decisión de no imputar de A36 **no cambia**; lo que cambia
es la etiqueta estadística correcta de por qué falta el dato.

- **Medido sobre el snapshot real** (`off_mexico_20260919.parquet`, 16.851 productos): la
  ausencia de cada variable de la tabla E.1, y de `categories_tags`, se probó contra una
  variable **observada** (si el producto tiene o no `ingredients_text`/`ingredients_tags`, y el
  score `completeness` que ya calcula OFF):

  | Variable | % faltante | P(falta\|sin ingredientes) | P(falta\|con ingredientes) | razón |
  | --- | --- | --- | --- | --- |
  | CORE8 (rango de las 8) | 27,4–39,3 % | 40,9–61,3 % | 11,0–15,4 % | 3,7–4,8× |
  | `categories_tags` | 48,2 % | 83,0 % | 6,4 % | 12,9× |
  | `nova_group` | 59,8 % | 99,0 % | 12,6 % | 7,9× |
  | `ingredients_analysis_tags` (dieta) | 54,2 % | 99,2 % | 0,1 % | ~1.518× (casi determinista) |
  | `allergens`+`traces` (ambos vacíos) | 79,3 % | 99,4 % | 55,1 % | 1,8× |
  | `labels_tags` (sellos) | 74,7 % | 87,3 % | 59,6 % | 1,5× |

  Las cifras de faltante total reproducen exactas las de la tabla E.1 del diagnóstico
  (79,3 %/74,7 %/54,2 % para alérgenos/sellos/dieta): esa tabla ya estaba bien medida: lo que
  faltaba era la prueba de mecanismo, no el porcentaje.
- **Por qué es MAR y no MNAR, en términos estrictos:** MNAR exige que la ausencia dependa del
  **valor no observado en sí** (algo que no se puede probar directamente con los datos
  disponibles: nunca se observa el valor de una fila faltante para comprobarlo). Lo que se
  midió aquí es justo lo contrario: la ausencia depende fuertemente de una variable **observada**
  (¿hay ingredientes?, ¿qué tan completo está el registro?) — la definición de libro de **MAR**.
  A36 llamaba a esto "MNAR (va con ingredientes incompletos)"; "va con ingredientes incompletos"
  describe exactamente MAR, no MNAR. No se puede descartar que exista además un componente MNAR
  residual (p. ej. que fabricantes de productos menos saludables documenten peor incluso
  controlando por completitud) — eso es, por definición, imposible de probar solo con los datos
  observados — pero no hay evidencia de que domine sobre el patrón MAR medido.
- **Patrón "todo o nada", refuerza que es un efecto del contribuidor, no del producto:** la
  distribución de cuántos de los 8 CORE8 le faltan a cada producto es fuertemente bimodal:
  8.358 productos (49,6 %) con los 8 presentes, 4.534 (26,9 %) con los 8 ausentes, y solo 1.959
  (11,6 %) con 1-3 faltantes dispersos. Correlación entre `completeness` y nº de CORE8 faltantes:
  **−0,597**. Es consistente con una causa común por registro (qué tan bien lo documentó quien
  lo subió a OFF), no con que cada nutriente falte de forma independiente.
- **La decisión de no imputar de A2/A36 no se reabre.** Que el mecanismo sea MAR (más tratable
  estadísticamente que MNAR) no cambia el argumento de fondo: imputar un nutriente CORE8 o un
  alérgeno seguiría siendo inventar un hecho nutricional o de seguridad que nadie observó (A2),
  y NOVA imputado seguiría siendo un modelo de clasificación disfrazado de dato observado. Esta
  decisión solo corrige la etiqueta estadística y deja evidencia lista para el paso 8 si algún
  día se reabre: el primer punto del orden de evidencia que pide ese paso ("¿el faltante es MAR
  dado X?") ya tiene respuesta afirmativa, con `completeness`/presencia de ingredientes como `X`.
- Implementado en `scripts/analisis_mecanismo_faltantes.py`; resumen versionado en
  `datos/procesados/re_eda_20260926/mecanismo_faltantes.csv`.

### A43. Dataset analítico de referencia: tabla de observaciones + Parquet nuevo, sin tocar el motor

**Decisión cerrada el 2026-09-26**, sobre `scripts/construir_dataset_referencia.py`, cierra el
paso 9 del plan de trabajo de [`docs/diagnostico_calidad_datos.md`](docs/diagnostico_calidad_datos.md)
(sección H). Implementa el diseño de F.2 (tabla de observaciones) y el entregable "Parquet nuevo +
diccionario". **No se tocó** `off_mexico_20260919.parquet` ni `src/nutrimatch/engine/*_score.py` /
`services/catalog.py` / `services/ranking.py` — eso es el paso 10.

- **Tabla de observaciones** (`datos/procesados/observaciones_20260926.parquet`): esquema F.2
  (`code`, `field`, `value`, `status`, `source`, `source_url`, `retrieved_at`, `snapshot_id`,
  `method`, `confidence`, `quality_flag`). `value` es texto (B14). Consolida solo observaciones
  externas: 6 hits de nombre (A39, `field=product_name`, `source=openfoodfacts_api_producto`),
  307 precios Open Prices (A40, `field=price`, `method=exact_gtin`) y 22 precios QQP (A41,
  `field=price`, `method=text_reviewed`). Total: 335 filas. Implementado en
  `nutrimatch.engine.observations`; la resolución es **REAL más reciente** por `retrieved_at`;
  si no hay ninguna, UNAVAILABLE; nunca IMPUTED ni SYNTHETIC por delante de REAL. Open Prices y
  QQP no comparten ningún `code` (0 solapes); 42 códigos de Open Prices tienen más de una
  observación (desempate por fecha).
- **Dataset de referencia** (`datos/procesados/dataset_referencia_20260926.parquet`): 16.851
  filas (una por `code`, A34), 267 columnas. Base = las 211 de OFF **bit a bit iguales** al
  crudo (verificado 2026-09-26; 0 sufijos `_x`/`_y`) + identidad homologada (A38) +
  `matriz_nut_100g` (A18/A21/A23/A27) + precio resuelto + `product_name_source`.
  `category_stats` queda fuera: es por categoría, no por producto.
- **Colisión de columnas:** `matriz_nut_100g` trae `nova_group`/`additives_n` idénticos a OFF
  (0 filas distintas). Se dropean al unir; si aparece otra colisión, el script falla en vez de
  dejar que pandas renombre en silencio.
- **Precio resuelto:** 263 `REAL` (242 Open Prices + 21 QQP únicos), 16.588 `UNAVAILABLE`.
  Ausencia = `price=NULL` + `price_status=UNAVAILABLE`, nunca 0 (A2). 6 nombres con
  `product_name_source=openfoodfacts_api_producto` (override REAL de A39 sobre el UNAVAILABLE
  de A38).
- **Metadato de tabla:** `datos/procesados/dataset_referencia_20260926_metadata.json` (F.2
  punto 1: no se clona `*_status` por cada una de las 211). Diccionario:
  [`docs/diccionario_dataset_referencia.md`](docs/diccionario_dataset_referencia.md).
- No hay IMPUTED ni SYNTHETIC en este dataset (A33, A36). El paso 8 (bake-off de imputación)
  no se reabrió.

### A44. Ranking v1 confirmado: las fórmulas no cambian

**Decisión cerrada el 2026-09-26**, sobre `scripts/confirmar_ranking_v1.py`, cierra el paso 10
del plan de trabajo de [`docs/diagnostico_calidad_datos.md`](docs/diagnostico_calidad_datos.md)
(sección H). El entregable es **confirmación del v1**, no un ranking v2. No se tocó
`src/nutrimatch/engine/*_score.py` ni `services/ranking.py` / `services/catalog.py`.

Reproducido sobre `dataset_referencia_20260926.parquet` (16.851 filas), no sobre
`off_mexico` + `matriz` por separado:

| Métrica | Publicado | Medido |
| --- | --- | --- |
| D1 v1 calculable (A27) | 7.040 (41,8 %) | 7.040 |
| D2 calculable (A23) | 6.781 (40,2 %) | 6.781 |
| `universo_puntuable` (A22) | 5.864 (34,8 %) | 5.864 |
| `cov < 0.5` Ana (A31) | 9.517 (56,5 %) | 9.517; causa `D1+D2+D3` |
| `cov < 0.5` Caro (A31) | 10.974 (65,1 %) | 10.974; causa `D1+D2+D3` |
| Precio REAL (A43) | 263 | 263; **no puntúa** (A5) |

Reaperturas consideradas y **rechazadas** (G.4):

- Imputar D1/D2 para subir el 34,8 %: no (A2, A36, A42: el hueco es MAR, no un error de fórmula).
- Bajar el umbral de `cov`: no, sin estudio de estabilidad del orden.
- Meter precio en el score: no (A5); 263 observaciones no cambian eso.
- Tratar Nutri-Score como D1: no (A4).
- Ampliar D1 a energía / grasa total / carbohidratos: no; sigue A27.

El cableado del catálogo al dataset de referencia (nombres homologados, precio para mostrar,
copy F.3) es el paso 11, no este.

Implementado en `scripts/confirmar_ranking_v1.py`; resumen en
`datos/procesados/re_eda_20260926/confirmacion_ranking_v1.csv`.

---

## Sección B. Trampas verificadas en vivo (2026-09-19 y 2026-09-20)

Todo lo de esta sección son **mediciones reales**, no supuestos. Cada entrada cita su propia fecha
porque los datos de OFF se regeneran a diario y los counts cambian; la mayoría es del 2026-09-19
(verificación de la API y descarga del export), B10-B13 son del 2026-09-20 (EDA y transformación
sobre el snapshot ya construido) y B14 es del mismo día (evaluación, paso 8).

### B1. Staging vs producción: la confusión que invalidó las primeras cifras

`world.openfoodfacts.net` es el entorno de **STAGING**: requiere **auth básica (off/off)** y
contiene una copia **PARCIAL** de la base. **NUNCA usarlo para construir el snapshot.** Producción es
`world.openfoodfacts.org`.

### B2. Counts de México (medidos el 2026-09-19)

| Consulta | Producción (`.org`) | Staging (`.net`) |
| --- | --- | --- |
| México, total | **17.741** | 11.995 |
| `states_tags=nutrition-facts-completed` | **13.633** | — |
| `states_tags=ingredients-completed` | **7.783** | — |

Las cifras previas de **9.681** y **6.469** venían de **staging** y quedan **descartadas**. No
usarlas en la memoria del proyecto.

### B3. El `HTTP 401` no era límite de tasa

El `HTTP 401` que se observaba era la **autenticación de staging**, no un rate limit. Diagnosticarlo
mal costó tiempo; conviene recordarlo.

### B4. Límites de tasa oficiales de OFF

- **10 peticiones/minuto** para `search`.
- **15 peticiones/minuto** para consultas de producto.
- Además, un **límite global anti-crawl** que responde **`HTTP 503` con independencia de la IP**.

Ese 503 apareció **3 veces en 9 peticiones**, incluso espaciando las peticiones **de 7 a 12
segundos**. Es decir: respetar el límite por minuto **no garantiza** que no aparezca.

### B5. Por eso el snapshot se construye desde el export, no paginando la API

La documentación de OFF **pide explícitamente** descargar los exports en CSV o JSONL si se necesitan
**más de unos cientos de productos**. El snapshot se construye **desde el export**. La **API queda
reservada al escaneo de un producto individual**.

### B6. Tamaños de los exports (medidos el 2026-09-19)

| Formato | Tamaño |
| --- | --- |
| **CSV comprimido** | **1,28 GB** ← **elegido** |
| Parquet (Hugging Face) | 7,89 GB |
| JSONL comprimido | 13,0 GB |
| Volcado MongoDB | 15,8 GB |

Se **regeneran a diario**, lo que da una **fecha de snapshot exacta y citable**. Se eligió el CSV
comprimido por ser un orden de magnitud más pequeño que las alternativas.

### B7. User-Agent obligatorio

OFF **exige un `User-Agent` identificable en todas las peticiones**. Se configura en
`OFF_USER_AGENT` con el formato `NombreApp/Version (email de contacto)`.

### B8. Versión de API: v2 para buscar

La **API v2 es la única con búsqueda estructurada**. **v3 no tiene búsqueda.**

### B9. RESUELTO el 2026-09-19 — esquema real del export CSV

Confirmado leyendo la cabecera real del export (211 columnas, separador de tabulación):
`main_category`, `main_category_en`, `image_nutrition_url` e `image_ingredients_url` **sí existen**.
La prueba anterior con solo 2 productos por la API no había sido concluyente porque OFF omite los
campos vacíos en la respuesta.

Con una salvedad importante encontrada en el mismo momento: **`allergens_en` existe pero llega vacía
en el 100 % de las filas** de México. No es una fuente utilizable pese a existir la columna (ver
también B11 y A15) — ejemplo directo de por qué la regla del proyecto es no asumir que una variable
está completa por el hecho de existir.

### B10. RESUELTO el 2026-09-20 — política de "categoría de referencia" para D1

Bloqueante cerrado con datos reales del universo México. Ver **A16** para la decisión completa
(retroceso ascendente, umbral mínimo de 30 productos) y `notebooks/02_eda_universo_mexico.ipynb`
(sección 5) para la evidencia.

### B11. Hallazgos del esquema real del export CSV, al construir el snapshot (2026-09-19)

Verificado en `scripts/ingesta_off.py`, que se detiene si falta una columna crítica en vez de generar
un snapshot mutilado — y en efecto se detuvo en la primera ejecución por el motivo de abajo:

- **`allergens_tags` NO existe en el export CSV** (solo existe en la API). La única fuente de
  alérgenos taxonomizados del export es **`allergens`** (ya viene con prefijo de idioma, por ejemplo
  `en:milk,en:gluten`).
- **`traces`** y **`traces_tags`** (menciones "puede contener") sí existen y no estaban contemplados
  en el inventario original de campos: son necesarios para el fail-safe de alergias (A15).
- **`ingredients_analysis_tags`** sí existe: es la fuente del filtro de dieta vegana/vegetariana (A1)
  y su tercer estado "no verificable".
- Candidatas descubiertas, útiles para el EDA aunque no eran críticas: `food_groups_tags`,
  `nutrient_levels_tags`, `data_quality_errors_tags`, `popularity_tags`.

### B12. Universo México real: 16.851 productos, snapshot `off_csv_20260919`

El export CSV filtrado por `countries_tags` conteniendo `en:mexico` da **16.851 productos**, 0
duplicados de `code`, 0 filas rechazadas por malformación. Reconciliado contra los 17.741 medidos en
la API (B2): diferencia de **-890 (5,0 %)**, dentro de la tolerancia del 10 % fijada en el script de
ingesta. Snapshot y Parquet derivado (4,9 MB) versionados; el export crudo de 1,19 GB, no.

### B13. `NaN` de pandas, no `None`, para texto y subpuntajes ausentes al leer Parquet con DuckDB

Verificado el 2026-09-20 al construir `notebooks/04_modelo_recomendacion.ipynb`: un campo de texto
ausente (`labels_tags`, `allergens`, `traces`, `ingredients_analysis_tags`) leído de un Parquet vía
`duckdb.execute(...).df()` llega como `float('nan')`, no como `None`. Causó un bug real de
implementación en la primera versión de `hard_filters.py` y `preference_score.py`, corregido antes
de cerrar el paso 7:

- `bool(float('nan'))` es `True` en Python, así que un chequeo con `not valor` no detecta la
  ausencia. Peor aún: `str(float('nan'))` produce el texto literal `"nan"`, que un split ingenuo por
  comas trataría como si fuera un tag real.
- Lo mismo aplica a un subpuntaje ausente (D1, D2 o D3): si llega como `NaN` en vez de `None`,
  `NaN is not None` es `True`, así que un chequeo de disponibilidad con `is not None` marca la
  dimensión como "disponible" e infla `cov` (A2) artificialmente — se detectó porque `cov` daba
  1,0 en el 100 % de los productos pese a que D1 y D2 solo tenían dato en ~40 % del universo.
- Corregido con una función `_es_texto_nulo`/`_es_nulo` (según el módulo) que cubre `None` y `NaN`
  explícitamente, en `hard_filters.py`, `preference_score.py` y `compatibility_score.py`, con
  pruebas de regresión en `tests/` que fijan el comportamiento con `math.nan` como entrada.
- Relevante para cualquier módulo futuro que reciba datos ya cargados en un DataFrame de pandas
  (a diferencia de `sanitize.py` del paso 6, que evita el problema al convertir explícitamente con
  `.astype("string")`, que sí usa `pd.NA`).

### B14. `nutriscore_score` llega como VARCHAR en el snapshot crudo, no como número

Verificado el 2026-09-20 al construir `notebooks/05_evaluacion.ipynb` (Sección de setup, para el
parity-check de A30): `scripts/ingesta_off.py` usa `all_varchar=true` a propósito al leer el CSV
de OFF ("la conversión de tipos se hace después, de forma auditada"). `nutriscore_score` no es
parte de CORE8, así que el paso 6 (`sanitize.py`) nunca lo tipó: sigue siendo texto en
`off_mexico_20260919.parquet`.

- Sin una conversión explícita con `pd.to_numeric`, cualquier comparación u ordenamiento de esta
  columna se hace por orden **lexicográfico** (`"9" > "51"`) en vez de numérico, en silencio.
- Costó un bug real de esta misma sesión: la primera versión del notebook calculó la correlación
  de Spearman de A30 sin convertir la columna y obtuvo **−0,2727** en vez de **−0,4747** — una
  diferencia de casi el doble, suficiente para haber quedado por debajo del umbral de A30 (−0,3) y
  producir un falso negativo ("D1 no correlaciona razonablemente con Nutri-Score") sobre un motor
  que en realidad sí pasa el chequeo.
- Todos los valores de `nutriscore_score` en el universo México parsean limpio a entero
  (0 valores no parseables sobre 6.431 no nulos): no es un problema de calidad del dato en sí,
  solo de tipo declarado.
- Cualquier módulo futuro que use `nutriscore_score`, o cualquier otra columna del snapshot crudo
  que no pase por `sanitize.py` (paso 6), debe convertirla explícitamente antes de compararla
  numéricamente — el mismo tipo de trampa que B13, pero de tipo declarado en vez de valor nulo.

### B15. `pd.read_csv` sin `dtype` infiere BIGINT de un `code` y borra ceros iniciales en silencio

Verificado en vivo el 2026-09-26, sobre `datos/procesados/piloto_qqp_candidatos_20260926.csv`
(paso 6b, A41), al construir el dataset analítico de referencia (paso 9, A43). El propio agente
introdujo el bug al editar el CSV a mano con `pd.read_csv()` sin `dtype` (paso previo de
`sugerencia_ia`/`razon_ia`, A41): 3 de los 22 códigos `code_candidato` marcados `"correcto"`
perdieron su cero inicial (`661440000014` en vez de `0661440000014`, `731082001004` en vez de
`0731082001004`, `74323081411` en vez de `0074323081411`), porque `code_candidato` es una columna
de texto que **parece** numérica: sin `dtype` explícito, pandas la infiere como `int64`/BIGINT y
descarta el cero inicial sin avisar.

- El mismo patrón se repetía, de forma estructural, en `scripts/materializar_precios_qqp.py`
  (Fase B): su lectura del CSV tampoco fijaba `dtype`, así que el bug se habría reproducido en
  cualquier corrida futura de esa fase, incluso sobre un CSV ya limpio.
- `code` (GTIN, A34) es siempre un identificador de texto, nunca un número: un GTIN con cero
  inicial es un valor válido y distinto de su versión sin ese cero (`0074323081411` ≠
  `74323081411` como claves de join), y **no hay ninguna operación aritmética legítima** que
  requiera tratarlo como entero.
- Corregido restaurando los 3 ceros en el CSV, fijando `dtype={"code_candidato": str}` en la
  lectura de `materializar_precios_qqp.py` (extraído a `cargar_csv_revisado()` para que sea
  testeable) y regenerando `datos/procesados/precios_qqp_20260926.parquet`.
- La prueba sintética original de `tests/test_materializar_precios_qqp.py` nunca habría detectado
  esta clase de bug: construye el `DataFrame` directo en Python, sin pasar nunca por un CSV real
  en disco. Se añadió `test_cargar_csv_revisado_preserva_cero_inicial_en_code_candidato`, que sí
  escribe y relee un CSV real vía `tmp_path`, como regresión.
- Misma familia que B13 (valor nulo mal tipado al leer) y B14 (columna declarada como texto,
  comparada como si fuera número): aquí el tipo declarado correcto (texto) se pierde **al leer**,
  no al comparar — cualquier columna de identificador (`code`, `product_code`, cualquier futuro
  GTIN u otro código con cero inicial posible) que pase por un CSV intermedio debe leerse siempre
  con `dtype=str` explícito para esa columna, nunca dejarlo a la inferencia de pandas.

---

## Sección C. Convenciones de código

- **Idiomas separados por función.** Identificadores de código y nombres de tablas y columnas en
  **inglés con `snake_case`**. Documentación, comentarios y textos de interfaz en **español**.
- **Nombre unificado `ranking_run`**, nunca `scoring_run`. Un solo nombre para el concepto, en
  código, en base de datos y en documentación.
- **Los faltantes son NULL + bandera, nunca cero** (ver A2). Aplica en el dominio, en la base y en
  los esquemas.
- **Trazabilidad obligatoria**: todo dato lleva `snapshot_id` o `version`. Un resultado debe poder
 atribuirse a la versión exacta de los datos y del motor que lo produjeron.
- **Entorno con uv y Python 3.12.13, la versión de Google Colab.** El entorno se gestiona con **uv**
 y `.python-version` fija **3.12.13**, que es la versión exacta del runtime de Colab (2026.07). El
 motivo: el paquete `nutrimatch` se reutiliza tal cual en los notebooks (ver A14), y un intérprete
 distinto en local y en Colab abre la puerta a que el mismo código dé resultados distintos según
 dónde se ejecute. `pyproject.toml` conserva `requires-python = ">=3.11"` como suelo de
 compatibilidad del paquete: fija el mínimo, no el intérprete. `.python-version` **se versiona**.
