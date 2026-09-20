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

El motor vive en el paquete `nutrimatch`, **reutilizado tal cual** por notebooks y UI. **Streamlit**
es la interfaz del MVP. **FastAPI y Angular quedan documentados como línea futura** en
[`docs/linea_futura.md`](docs/linea_futura.md), fuera del alcance.

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

---

## Sección B. Trampas verificadas en vivo (2026-09-19 y 2026-09-20)

Todo lo de esta sección son **mediciones reales**, no supuestos. Cada entrada cita su propia fecha
porque los datos de OFF se regeneran a diario y los counts cambian; la mayoría es del 2026-09-19
(verificación de la API y descarga del export), y B10-B13 son del 2026-09-20 (EDA y transformación
sobre el snapshot ya construido).

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
