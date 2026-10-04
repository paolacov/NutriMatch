# NutriMatch — criterios del sistema

Desarrollé NutriMatch como un sistema cerrado de apoyo a la compra de alimentos empacados en México. Este documento recoge los criterios con los que construí el motor, el catálogo y la interfaz. Son decisiones ya aplicadas sobre datos medidos. El detalle de columnas está en [`docs/diccionario_dataset_referencia.md`](docs/diccionario_dataset_referencia.md) y el recorrido técnico en [`docs/NutriMatch_Documentacion_Tecnica_Completa.md`](docs/NutriMatch_Documentacion_Tecnica_Completa.md).

---

## 1. Qué calcula el sistema

El resultado visible es un ranking personalizado y su explicación. El motor compara productos sobre una base de 100 g o 100 mL, la misma en la que Open Food Facts publica los nutrientes. Una porción solo aparece en las alertas, y solo cuando el producto declara `serving_size`.

Cada constructo se puntúa una sola vez:

- La nutrición es la primera dimensión. Usa percentiles dentro de la categoría de referencia.
- El procesamiento es la segunda dimensión. Usa el grupo NOVA y, dentro de ese grupo, el número de aditivos.
- Las preferencias son la tercera dimensión. Miden qué proporción de las etiquetas que la persona valora presenta el producto.
- Nutri-Score se muestra como referencia y sirve de contraste en la evaluación. Se deriva de nutrientes que la primera dimensión ya considera, así que queda fuera del puntaje.
- Los sellos frontales mexicanos se muestran y generan alertas. Quedan fuera del puntaje por la misma razón.
- El precio informa. Queda fuera del puntaje y fuera de los filtros.
- El historial y la lista de compras alimentan el registro de eventos. Son trazas de uso.

El país no filtra en la consulta. El mercado queda fijo en la ingesta: el snapshot ya es México.

## 2. Datos ausentes

Un cero afirma un hecho nutricional, por ejemplo que el producto no tiene azúcar. Un dato ausente es otra cosa. Lo guardé como NULL acompañado de una bandera explícita.

La cobertura de un producto, frente a un perfil, es la suma de los pesos de las dimensiones que sí tienen dato, dividida entre la suma de los pesos totales. Si esa fracción queda por debajo de 0,5, el producto no entra al ranking: va a la banda de información insuficiente, separada del orden. Comparar un producto a medias contra uno completo produciría un orden falso.

Cuando una dimensión no tiene subpuntaje, el resultado final es el promedio ponderado de las dimensiones disponibles. La dimensión ausente no se trata como cero. Si la cobertura queda por debajo de 0,5, el resultado final es NULL.

Los valores fuera de un rango físico plausible llevan una bandera de calidad. Ese producto deja de aportar a los percentiles y a las estadísticas de categoría de esa dimensión. El dato crudo sigue visible en la ficha.

La sal fuera de rango se corrige cuando su razón con el sodio del mismo producto es aproximadamente 2,5 y el valor dividido entre 1 000 cae en un rango válido. La corrección sale de los dos campos del propio producto y queda marcada. El caso que no cumple esa razón permanece fuera de rango, sin corrección.

## 3. Alergias y dieta

Alergias y dieta tienen tres estados: apto, no apto y no verificable.

La cobertura de alérgenos en el universo de México es baja. Tratar «sin dato» como «no apto» habría marcado la mayor parte del catálogo por ausencia de información, no por presencia del alérgeno. El estado no verificable se muestra en su propia banda, con la advertencia de que el dato está incompleto. Nunca se mezcla con apto.

Las fuentes de alergia son `allergens` (presencia confirmada) y `traces` (puede contener). La columna `allergens_en` existe en el export y llega vacía en todas las filas de México, así que no la uso.

La dieta usa `ingredients_analysis_tags`. Si los ingredientes no permiten afirmar que el producto cumple la dieta declarada, el estado es no verificable. Afirmar compatibilidad sin evidencia inventaría un hecho.

Un producto cae en una sola banda, en este orden:

1. **Excluido.** Alergia no apta o dieta incompatible. No se lista; solo se cuenta.
2. **No verificable.** Alergia o dieta no verificable, con advertencia propia.
3. **Información insuficiente.** Cobertura menor que 0,5.
4. **Ranking.** El resto, ordenado por el resultado final de mayor a menor.

La búsqueda por nombre o por código se aplica antes de puntuar, sobre todo el catálogo operativo.

## 4. Las tres dimensiones

La persona declara un perfil base y ordena tres prioridades. Ese orden se convierte en pesos que suman 1, con la secuencia 3, 2 y 1 según el lugar: 0,50 para la primera, 0,33 para la segunda y 0,17 para la tercera. No hay controles numéricos sueltos.

| Dimensión | Qué mide | Cómo se calcula |
| --- | --- | --- |
| Nutrición | Azúcares, sal y grasa saturada (menos es mejor); fibra y proteína (más es mejor) | Percentil dentro de la categoría de referencia, en escala 0–100 |
| Procesamiento | Grado de procesamiento | Grupo NOVA en bandas de 25 puntos, ajustadas por el número de aditivos |
| Preferencias | Etiquetas que la persona valora | Porcentaje de esas etiquetas que el producto presenta |

El resultado final es la suma ponderada de los subpuntajes disponibles, dividida entre la suma de sus pesos. Cada subpuntaje sigue visible.

La dimensión nutricional usa cinco nutrientes de dirección clara. Energía, grasa total y carbohidratos conservan percentil y se muestran en la ficha. No entran al puntaje: el motor no asigna un signo distinto según una meta que no está modelada como taxonomía cerrada.

La categoría de referencia es la etiqueta más específica de `categories_tags`. Open Food Facts ordena esa lista de lo genérico a lo específico. Si la etiqueta tiene menos de 30 productos en el universo puntuable, se sube un nivel y se repite la comprobación. Si se agota la jerarquía sin alcanzar el umbral, la dimensión nutricional queda sin dato para ese producto.

Un percentil de un nutriente concreto exige al menos cinco productos con dato saneado en esa categoría. Por debajo de ese mínimo, el percentil de ese nutriente es NULL.

El grupo NOVA, por sí solo, discrimina poco en México: la mayoría de los productos con NOVA caen en el grupo 4. El número de aditivos tiene una relación monótona con el grupo y una cobertura algo mayor. Lo usé para afinar el subpuntaje dentro de la banda del grupo, no como una cuarta dimensión.

Cada grupo ocupa una banda fija de 25 puntos: el grupo 1 entre 75 y 100, el 2 entre 50 y 75, el 3 entre 25 y 50, y el 4 entre 0 y 25. Dentro de la banda, los aditivos empujan el subpuntaje hacia el piso, hasta el percentil 95 de aditivos entre los productos del grupo 4 del propio snapshot. Si el número de aditivos falta, el ajuste es neutro: se resta media banda, 12,5 puntos, y el producto queda en el centro de su piso. Sin grupo NOVA, la dimensión de procesamiento es NULL.

Entran al universo puntuable los productos con al menos cuatro de los ocho percentiles del núcleo válidos y con procesamiento calculable. En el catálogo operativo son 5 864 de 13 093. Esa marca es previa al perfil. La cobertura frente a las prioridades de la persona sigue siendo el filtro fino del ranking.

## 5. Precio

El precio es real o está ausente. No imputé un precio de mercado.

- **Open Prices.** Cruce exacto por código de barras, en pesos mexicanos. En el catálogo operativo hay 239 precios de esta fuente.
- **PROFECO.** Quién es Quién en los Precios no publica código de barras. El cruce es por texto (marca, producto y presentación) y solo entra al catálogo cuando la coincidencia quedó revisada. En el catálogo operativo hay 20 precios de esta fuente. Se presentan como precio de referencia de una presentación parecida, con el método de coincidencia y la confianza visibles.
- **Sin observación.** 12 834 productos. El Parquet guarda NULL y procedencia no disponible. Al armar la ficha, la API emite un fallback dinámico de tipo `SYNTHETIC`: un entero de demostración entre 12 y 180 pesos, determinista a partir del código de barras. El ranking no lo usa. El Parquet no lo almacena.

Las dos fuentes reales no comparten códigos en la tabla de observaciones. Si un código tiene varias observaciones, gana la real más reciente.

## 6. Nombre, marca y unidad de análisis

La unidad de análisis es el código de barras (`code`). No agrupé presentaciones. Sabores, tamaños y errores de captura pueden repetir marca y nombre sin ser el mismo producto.

El nombre que se muestra sale del propio registro, en este orden: `product_name`, `generic_name`, `abbreviated_product_name`. El texto literal «Cargando…» se trata como vacío. El snapshot crudo no se modifica. Si ninguno de los campos tiene dato, el nombre resuelto queda vacío. Un lote de recuperación contra la ficha viva de Open Food Facts aportó nombres reales adicionales, guardados como observaciones de esa fuente, sin sobrescribir el export.

La marca de coincidencia interna se obtiene en minúsculas, sin acentos y con espacios colapsados. Sirve para cruzar texto. No es el valor que se muestra. Las marcas múltiples permanecen en una sola cadena.

## 7. Procedencia y calidad

Toda variable enriquecida, derivada o ausente lleva uno de estos estados:

| Estado | Significado |
| --- | --- |
| `REAL` | Observado en una fuente identificable |
| `DERIVED` | Calculado a partir de datos reales, sin un modelo predictivo |
| `IMPUTED` | Estimado porque el valor no existía. El catálogo operativo no usa este estado |
| `SYNTHETIC` | Creado para demostración en la respuesta de la ficha. No se escribe en el Parquet |
| `UNAVAILABLE` | Se sabe que no hay dato. El valor es NULL |

La calidad física es independiente de la procedencia: un valor puede ser real y, a la vez, estar fuera de rango.

Las columnas del export son reales por construcción. El metadato del snapshot (`snapshot_id`, URL, fecha de recuperación) cubre ese bloque. Lo que no viene del export vive en la tabla de observaciones: código, campo, valor, estado, fuente, URL, fecha, snapshot, método, confianza y bandera de calidad. Puede haber varias filas por código y campo.

La calidad de información del catálogo operativo es un promedio de siete componentes de disponibilidad y consistencia: nutrición, ingredientes, categoría, NOVA, aditivos, etiquetas y coherencia física. No mide si el producto es más saludable y no entra al puntaje. Sobre los 13 093 productos medí 6 102 en nivel alto, 1 511 en nivel medio, 1 274 en nivel bajo y 4 206 en nivel insuficiente.

Medí el mecanismo de los faltantes del núcleo nutricional, de la categoría y de variables afines. La ausencia depende de si el registro trae ingredientes y de la completitud que ya calcula Open Food Facts. Es un patrón ligado a qué tan documentado está el registro. Por eso los faltantes permanecen ausentes: inventar un nutriente, un alérgeno o un grupo NOVA cambiaría el significado del ranking y, en alergias, el riesgo.

## 8. Evaluación

Evalué el motor con tres mecanismos:

1. **Conjunto de oro.** Trece códigos reales del snapshot, revisados a mano, con el resultado esperado de cada caso. Vive en `evaluacion/` y se contrasta en `tests/test_golden_set.py`.
2. **Contraste con Nutri-Score.** Correlación de Spearman entre la dimensión nutricional y `nutriscore_score`. El umbral de sanidad es una correlación menor o igual a −0,3. El signo es negativo porque en este sistema un valor alto es mejor y en Nutri-Score un valor alto es peor. Sobre los productos con ambos datos, la correlación medida queda por encima de ese umbral en magnitud, y el promedio de la dimensión nutricional decrece de la letra «a» a la letra «e».
3. **Diagnóstico de cobertura.** Para un perfil dado, los productos de la banda de información insuficiente se desglosan por la combinación exacta de dimensiones ausentes.

Con los pesos 0,50 / 0,33 / 0,17, cualquier par de dimensiones suma al menos 0,5. Perder una sola dimensión no basta para salir del ranking.

## 9. Carrito y explicación

El carrito tiene dos vistas: el Plato del Bien Comer y las categorías. El resumen por defecto es el promedio por 100 g. El promedio ponderado por gramos solo se usa cuando todos los productos tienen cantidad. El resumen declara el método y la cobertura. Los porcentajes por grupo usan como denominador el número de productos. Un producto sin categoría mapeable va al grupo «no clasificado». El resumen no emite juicios médicos.

La explicación es parte del resultado. Muestra el subpuntaje de cada dimensión, la contribución de cada nutriente, el percentil en la categoría, el peso aplicado y el estado de los datos.

## 10. Capa de lenguaje

La implementación está en `nutrimatch.ai` y se expone en `POST /ai/ask`. Tiene tres roles:

- **planner.** Traduce lenguaje natural a una operación ya validada. No calcula.
- **critic.** Auditor determinista. Comprueba que cada afirmación del texto esté respaldada por un hecho calculado.
- **narrate.** Redacta la explicación.

El identificador de la persona se anonimiza antes de cualquier llamada. Las respuestas se pueden cachear. Sin clave, las plantillas deterministas cubren la respuesta. El motor de compatibilidad permanece en `nutrimatch.engine`.

## 11. Arquitectura de ejecución

El motor vive en el paquete `nutrimatch`. Los cuadernos lo reutilizan tal cual. La interfaz es Angular (`frontend/`) y llama a FastAPI (`nutrimatch.api`). La API serializa `schemas/` y no vuelve a derivar las fórmulas de las tres dimensiones: la nutricional y las preferencias se resuelven en la petición; el procesamiento ya está en el Parquet.

El catálogo de la API es `dataset_referencia_20261002.parquet` (13 093 filas, 273 columnas). Parte del corte del 29 de septiembre de 2026 y le une los precios reales que siguen en ese universo, más la calidad de información. Los identificadores de código, las columnas y los nombres de tablas están en inglés con `snake_case`. La documentación, los comentarios y los textos de la interfaz están en español.

El entorno local usa uv y Python 3.12.13, fijado en `.python-version`, que es la versión del runtime de Google Colab. `requires-python = ">=3.11"` es el suelo del paquete.

En Vercel, `api/index.py` expone la misma aplicación. `vercel.json` separa las rutas de la API de las rutas de Angular y las sirve en el mismo dominio. El historial de esa función se escribe en `/tmp`.

## 12. Hallazgos verificados en las fuentes

Estos puntos salieron de mediciones directas. Los datos de Open Food Facts se regeneran a diario; las cifras de conteo citan su fecha.

**Entornos.** `world.openfoodfacts.org` es producción. `world.openfoodfacts.net` es staging: pide autenticación básica y contiene una copia parcial. El snapshot y los conteos salen de producción. Un HTTP 401 contra staging era autenticación, no un límite de tasa.

**Conteos del 19 de septiembre de 2026.** Producción reportó 17 741 productos de México. El export filtrado por `countries_tags` con `en:mexico` dio 16 851 productos, 0 códigos duplicados y 0 filas rechazadas por malformación. La diferencia, 890 productos (5,0 %), cabe en la tolerancia del 10 % de la ingesta. El archivo comprimido del 29 de septiembre tiene el mismo SHA-256 que el del 19. La baja de 16 851 a 13 093 la producen los tres candados de ingesta, no un export distinto.

**Límites de la API.** La búsqueda admite 10 peticiones por minuto y la ficha de un producto, 15. Además hay un límite anti-crawl que responde HTTP 503 con independencia de la IP. Por eso el catálogo se construye desde el export CSV comprimido (1,28 GB medidos el 19 de septiembre de 2026). La API queda para consultar un producto individual. Toda petición a Open Food Facts lleva un `User-Agent` identificable, configurado en `OFF_USER_AGENT`. La búsqueda estructurada está en la versión 2 de la API.

**Esquema real del CSV.** El export trae 211 columnas separadas por tabulación. `allergens_tags` no está en el CSV; la fuente taxonomizada es `allergens`. `traces` y `traces_tags` sí están y alimentan el estado de alergia. `ingredients_analysis_tags` alimenta la dieta.

**Lectura de Parquet.** Un texto ausente leído con DuckDB hacia pandas llega como `NaN`, no como `None`. `bool(float("nan"))` es verdadero y `str(float("nan"))` es el texto `"nan"`. Los módulos que reciben un DataFrame tratan `None` y `NaN` como ausencia antes de partir etiquetas o de decidir si una dimensión tiene dato. `nutriscore_score` llega como texto en el snapshot crudo; se convierte a número antes de ordenarlo o correlacionarlo. Un código de barras leído con `pandas.read_csv` sin `dtype` puede perder el cero inicial. `code` se lee siempre como texto.

**PROFECO.** El portal de datos abiertos responde HTTP 403 a un `User-Agent` que no parece un navegador, incluido el identificable que Open Food Facts sí exige. Para este proveedor, y solo para este, el cliente envía un `User-Agent` de navegador. El portal es público, con licencia CC-BY 4.0, y el bloqueo corresponde a la configuración por defecto de su cortafuegos. El esquema real no trae claves de producto ni de marca: trae producto, presentación, marca, categoría, precio, fecha, cadena y ubicación. El campo marca viene compuesto (`marca. variante`). El match es por texto completo, acotado por la marca homologada.

**Open Prices.** El filtro por código de país de la ubicación no existe en su API y se ignora en silencio. El filtro que sí acota los precios mexicanos es `currency=MXN`.

## 13. Convenciones de código

- Identificadores, tablas y columnas en inglés con `snake_case`. Documentación, comentarios y textos de interfaz en español.
- El nombre del concepto de una corrida es `ranking_run`.
- Un faltante es NULL más bandera.
- Todo dato lleva `snapshot_id` o versión, de modo que un resultado se pueda atribuir a los datos y al motor que lo produjeron.
- El paquete se instala en modo editable y es el mismo código que importan los cuadernos.
