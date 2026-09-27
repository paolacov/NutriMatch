# Diagnóstico: base analítica final de NutriMatch

Fecha de medición: **2026-09-27**.  
Alcance: **solo auditoría**. No se generaron sintéticos. No se modificó ningún Parquet.

Vocabulario de procedencia del proyecto (A33), mapeado al del brief:

| Brief | A33 (se conserva) | Uso |
| --- | --- | --- |
| real | `REAL` | Observado en una fuente identificable |
| derived | `DERIVED` | Calculado sobre REAL, sin modelo predictivo |
| synthetic | `SYNTHETIC` | Demo / fixture; nunca delante de REAL |
| llm_generated | no existe hoy | Reservado; 0 filas |
| missing | `UNAVAILABLE` | Se sabe que no hay dato; valor NULL |
| — | `IMPUTED` | 0 filas; no se abre |

No se introduce un esquema paralelo (`missing` / `real` en minúsculas) que choque con A33.

---

## A. Archivos encontrados

Fuente analítica = Parquet. SQLite (`nutrimatch.db`) es estado mutable (perfil, `ranking_run`, `event_log`), no catálogo.

| Archivo | Formato | Filas | Columnas | Rol |
| --- | --- | --- | --- | --- |
| `datos/procesados/dataset_referencia_20260926.parquet` | Parquet | 16.851 | 267 | **Candidato a fuente de verdad** |
| `datos/procesados/off_mexico_20260919.parquet` | Parquet | 16.851 | 211 | RAW OFF (países ⊃ `en:mexico`) |
| `datos/procesados/identidad_homologada_20260919.parquet` | Parquet | 16.851 | 12 | Nombre/marca DERIVED |
| `datos/procesados/matriz_nut_100g_20260919.parquet` | Parquet | 16.851 | 43 | Saneado + percentiles + D2 |
| `datos/procesados/category_stats_20260919.parquet` | Parquet | 1.608 | 9 | Stats por categoría (201 cats × nutrientes) |
| `datos/procesados/observaciones_20260926.parquet` | Parquet | 335 | 11 | Observaciones externas (A33) |
| `datos/procesados/precios_open_prices_20260926.parquet` | Parquet | 307 | 19 | Precios REAL por GTIN |
| `datos/procesados/precios_qqp_20260926.parquet` | Parquet | 22 | 22 | Precios REAL texto revisado |
| `datos/procesados/experimento_recuperacion_nombres_20260919.parquet` | Parquet | 80 | 17 | Experimento API nombres |
| `datos/snapshots/off_csv_20260919/en.openfoodfacts.org.products.csv.gz` | CSV.gz | — | 211 | Export crudo 1,2 GB |
| `datos/procesados/piloto_qqp_candidatos_20260926.csv` | CSV | 40 | — | Muestra QQP revisada |
| `datos/procesados/re_eda_20260926/*.csv` | CSV | varios | — | EDA / exploración, no catálogo |
| `nutrimatch.db` | SQLite | 1 perfil, 56 runs, 1.658 items, 27 events | — | Trazas locales |

Clave de producto: `code` (GTIN). 16.851 únicos, 0 duplicados, 0 vacíos. `off_mexico` y `dataset_referencia` tienen **los mismos 16.851 códigos** (0 solo-off, 0 solo-ref).

---

## B. Dataset actual que debe convertirse en fuente de verdad

**`datos/procesados/dataset_referencia_20260926.parquet`** (A43).

Ya es la tabla maestra de producto: 211 columnas OFF bit a bit + identidad + matriz + precio resuelto. La API (`Catalog.from_referencia`) ya lo lee. El ranking v1 se confirmó sobre él (A44).

No hace falta reconstruir el universo. El cierre es **versionar, documentar huecos y, si se aprueba, añadir columnas DERIVED de calidad** — no un Parquet nuevo que pise al actual.

SQLite no entra como fuente analítica.

---

## C. Variables reales (REAL)

Bloque OFF (211 columnas): export `off_csv_20260919`, URL y sha256 en `_metadata.json`. Incluye, entre otras:

- Identidad: `code`, `product_name`, `generic_name`, `abbreviated_product_name`, `brands`, `quantity`
- Categoría cruda: `categories_tags`, `main_category`, `pnns_groups_1`, `food_groups_tags`
- Ingredientes / seguridad: `ingredients_text`, `ingredients_tags`, `allergens`, `traces`, `ingredients_analysis_tags`, `labels_tags`
- Procesamiento crudo: `nova_group`, `additives_n`
- CORE8 y sodio: `energy-kcal_100g`, `proteins_100g`, `carbohydrates_100g`, `sugars_100g`, `fat_100g`, `saturated-fat_100g`, `fiber_100g`, `salt_100g`, `sodium_100g`
- Referencia no puntuada: `nutriscore_grade`, `nutriscore_score`
- Calidad OFF: `completeness`, `data_quality_errors_tags`

Copias trazables en la matriz: `*_100g_bruto`.

Observaciones externas REAL (tabla aparte, 335 filas):

| field | n | source | method |
| --- | --- | --- | --- |
| `price` | 307 | `open_prices` | `exact_gtin` |
| `price` | 22 | `qqp_profeco` | `text_reviewed` |
| `product_name` | 6 | `openfoodfacts_api_producto` | API individual |

En la ficha resuelta: **263 precios REAL** (242 Open Prices + 21 QQP únicos; 0 solape de `code`). **6 nombres** con override REAL de API.

`allergens_en`: columna existe, **0 filas con dato** (B11). No es fuente utilizable.

---

## D. Variables derivadas (DERIVED)

| Variable | Qué es | Decisión |
| --- | --- | --- |
| `product_name_homologated` y flags A28/A38 | Fallback + placeholder `"Cargando…"` | A28, A38 |
| `brand_homologated` | Plegado Unicode, no alias | A38 |
| `*_100g_saneado`, `*_flag_fuera_de_rango` | Rango físico; NULL si inválido | A18 |
| `salt_100g_flag_correccion_escala_aplicada` | Sal ÷1000 si razón ≈2,5 con sodio | A21 |
| `flag_suma_macros_excede_100` | Consistencia de macros | A18 |
| `categoria_referencia`, `nivel_retroceso` | Retroceso ascendente, umbral 30 | A16 |
| `percentil_*` (8) | Rank 0–100 dentro de la categoría; ≥5 pares | A24 |
| `n_percentiles_validos` | Conteo de percentiles CORE8 válidos | A22 |
| `d2` | Bandas NOVA + `additives_n` | A23 |
| `universo_puntuable` | ≥4/8 percentiles + D2 | A22 |
| `category_stats_*` | media/mediana/sd por (categoría, nutriente) | paso 6 |
| D1, D3, `cov`, `score_final`, banda | **No están en el Parquet**: se calculan en el motor por perfil | A7, A25, A26, A32 |

D1 no se materializa porque depende de qué percentiles hay; D3/`cov`/banda dependen del perfil.

---

## E. Variables faltantes (UNAVAILABLE / no existen)

**En el catálogo, valor NULL + status, no cero:**

| Hueco | n | % de 16.851 |
| --- | --- | --- |
| Sin nombre homologado | 1.679 | 10,0 % |
| Sin marca | 3.749 | 22,2 % |
| Sin `categories_tags` | 8.123 | 48,2 % |
| Sin categoría de referencia A16 | 8.750 | 51,9 % |
| Sin ingredientes (`ingredients_text`) | 9.201 | 54,6 % |
| Sin NOVA / sin D2 | 10.070 | 59,8 % |
| Sin `additives_n` | 9.201 | 54,6 % |
| Sin `labels_tags` | 12.585 | 74,7 % |
| Sin alérgenos ni trazas | 13.362 | 79,3 % |
| Precio UNAVAILABLE | 16.588 | 98,4 % |
| Nutri-Score numérico ausente | 10.420 | 61,8 % |

`nutriscore_grade` “presente” en 16.720 es engañoso: **9.845 son el literal `unknown`**. Grados a–e: 6.431 (igual que `nutriscore_score`).

**No existen en ningún dataset (y no se inventan ahora):**

- `data_quality_score` / `data_quality_level` (propuestos; hoy hay `completeness` de OFF + flags)
- Tabla de usuarios académica versionada
- Tabla de interacciones para ML
- Recetas (`llm_generated`): la pantalla Angular solo lista el carrito
- Precio SYNTHETIC en Parquet (el overlay vive solo en el cliente)

---

## F. Candidatas a sintéticos (propuesta, no ejecutada)

| Candidata | ¿Hoy? | ¿Meter en la base final? |
| --- | --- | --- |
| Precio | Overlay Angular: hash del GTIN → $12–$180, status `SYNTHETIC`, para **los 16.588** sin precio REAL | **No en el Parquet maestro.** Si se materializa, archivo experimental aparte y **solo un subconjunto** con semilla |
| Perfiles Ana / Beto / Caro | Código de evaluación, no tabla | Opcional: JSON versionado de 3 personas, `SYNTHETIC` |
| Perfil de la UI | `localStorage` + 1 fila SQLite | No es catálogo |
| Interacciones | 27 eventos locales de demo | **No generar** corpus sintético |
| Recetas LLM | No hay | Fuera de este cierre |
| Nutrientes / NOVA / ingredientes | — | **Prohibido** en el dataset principal (punto 6 del brief = A2/A36) |

---

## G. Justificación de cada sintético propuesto

**Precio sintético — necesidad funcional, no de evidencia.**  
Cobertura REAL = 263 / 16.851 = **1,56 %**. Con eso no se demuestra una comparativa económica en anaquel. El precio **no puntúa** (A5). Un sintético solo sirve para que carrito/comparar no se vean vacíos.

El overlay actual cubre **todos** los UNAVAILABLE. El brief pide “productos seleccionados”. Eso es más estricto que lo que hace Angular hoy. Recomendación: la base analítica **no absorbe** ese overlay; la UI puede seguir mostrándolo con badge `SYNTHETIC`, o recortarse a una muestra cuando se pida.

**Usuarios sintéticos — solo si se versionan los 3 perfiles de evaluación.**  
Ya existen como diccionarios en `scripts/confirmar_ranking_v1.py`. No hace falta un `user_id` masivo.

**Interacciones — no.**  
No hay experimento de ML aprobado. Inventar clicks sería fingir comportamiento.

**LLM — no.**  
Capa LLM sigue opcional y apagada.

---

## H. Cobertura actual (medido 2026-09-27)

### Nutrición cruda OFF (texto casteado; 0 es 0 real, no NULL)

| Variable | con dato | % | ceros reales | negativos | máximo crudo |
| --- | --- | --- | --- | --- | --- |
| `energy-kcal_100g` | 12.241 | 72,6 | 327 | 0 | 277.183 |
| `proteins_100g` | 12.010 | 71,3 | 1.762 | 1 | 291,2 |
| `carbohydrates_100g` | 12.060 | 71,6 | 1.014 | 0 | 701 |
| `sugars_100g` | 10.554 | 62,6 | 2.143 | 0 | 209 |
| `fat_100g` | 12.024 | 71,4 | 2.167 | 0 | 407 |
| `saturated-fat_100g` | 10.491 | 62,3 | 2.642 | 0 | 1.963 |
| `fiber_100g` | 10.294 | 61,1 | 3.351 | 2 | 104 |
| `salt_100g` / `sodium_100g` | 10.223 | 60,7 | 1.051 / 1.006 | 0 | 68.425 / 27.370 |

Tras saneamiento (A18/A21), los máximos de `*_saneado` caben en el rango físico; los negativos desaparecen (NULL + flag). Flags fuera de rango: kcal 58, sal 56 (55 corregidas por escala), macros >100 g: 57.

`additives_n`: 7.650 con dato; **2.925 ceros reales** (0 aditivos ≠ missing); máximo 28.

### Percentiles / scoring

| Métrica | n | % |
| --- | --- | --- |
| D1 calculable (≥1 de 5 nutrientes con signo) | 7.040 | 41,8 |
| D2 calculable (tiene NOVA) | 6.781 | 40,2 |
| `universo_puntuable` | 5.864 | 34,8 |
| 8/8 percentiles válidos | 6.087 | 36,1 |
| 0/8 percentiles | 9.792 | 58,1 |

### Precio resuelto

| Estado | n | % |
| --- | --- | --- |
| REAL Open Prices | 242 | 1,4 |
| REAL QQP | 21 | 0,1 |
| UNAVAILABLE | 16.588 | 98,4 |
| SYNTHETIC en Parquet | **0** | 0 |
| IMPUTED | **0** | 0 |

Precio REAL: $8,50–$528,50 MXN; mediana $42; 0 ceros; 0 negativos. De los 5.864 puntuables, **216** tienen precio REAL.

### Categoría

`categoria_referencia` en 8.101 (48,1 %). Top: `en:groceries` 418, `en:biscuits` 393, `en:milks` 249.  
`pnns_groups_1`: 9.541 `unknown` + 131 NULL.  
`food_groups_tags`: 7.194 (42,7 %).

### Completitud OFF (`completeness`, REAL de OFF)

| Bucket | n |
| --- | --- |
| 0–0,2 | 2.284 |
| 0,2–0,4 | 5.847 |
| 0,4–0,6 | 1.930 |
| 0,6–0,8 | 2.368 |
| 0,8–1 | 4.422 |

---

## I. Universo principal

**16.851 productos** con `countries_tags` ⊃ `en:mexico`. Todos son buscables y consultables (A19).  
Ninguno se elimina por incompleto.

---

## J. Utilizables / parciales / insuficientes

| Capa | Criterio | n |
| --- | --- | --- |
| Ranking comparativo (agnóstico de perfil) | `universo_puntuable` | 5.864 |
| Parcial con categoría pero no puntuable | tiene `categoria_referencia` y no `universo_puntuable` | 2.237 |
| Sin categoría de referencia | no se puede D1 por pares | 8.750 |
| Banda “información insuficiente” (depende del perfil) | `cov < 0,5` | Ana 9.517; Caro 10.974 |
| Excluido / no verificable | alergia o dieta; se decide en runtime | no es atributo fijo del producto |

“Parcial” ≠ “se imputa”. Se muestra lo que hay, con banderas.

---

## K. Tratamiento propuesto para precios

1. En el Parquet maestro: **seguir como ahora**. `price` REAL o NULL. `price_status` = `REAL` | `UNAVAILABLE`. Nunca 0 por ausencia.
2. **No escribir** precios sintéticos en `dataset_referencia`.
3. No reutilizar `price_source` para `real|synthetic|missing`: esa columna ya es el **proveedor** (`open_prices` / `qqp_profeco` / NULL). El estado de procedencia es `price_status`.
4. Overlay Angular: es demo UI, no evidencia. Si se materializa un extracto de demo, archivo nuevo (`precios_sinteticos_demo_*.parquet`), semilla fija, subconjunto, `status=SYNTHETIC`.
5. El ranking principal **sigue sin precio**. Un ranking con precio sería otra variante, no el v1.

---

## L. Tratamiento propuesto para usuarios

No crear una tabla masiva de `user_id`.  
Versionar, si se pide, los 3 perfiles de evaluación (Ana, Beto, Caro) como JSON `SYNTHETIC` en `evaluacion/` o `datos/procesados/perfiles_ejemplo.json`.  
El perfil de la app es input de sesión, no fila del catálogo.

---

## M. Tratamiento propuesto para interacciones

**No generar.**  
`event_log` (27 filas locales) son trazas de esta máquina, no un dataset de comportamiento. Fuera del cierre de la base de productos.

---

## N. Estructura final de Parquet (propuesta)

Conservar `dataset_referencia_20260926.parquet` como núcleo.  
Si se aprueba el indicador de calidad, **nuevo archivo versionado** (no overwrite), p. ej. `dataset_referencia_20260927.parquet` = el actual + columnas DERIVED:

| Columna nueva | Procedencia | Notas |
| --- | --- | --- |
| `data_quality_score` | DERIVED | 0–1 a partir de flags y presencia; **no rellena NULLs** |
| `data_quality_level` | DERIVED | p. ej. `alta` / `media` / `baja` / `insuficiente` umbralizado sobre el score |
| `record_status` | DERIVED | `active` para las 16.851 (todas válidas en el universo) |
| `data_source` | REAL (metadato de tabla) | `off_csv_20260919`; no clonar por fila salvo que se pida |

**No renombrar** `proteins_100g` → `protein_g` en el archivo: rompe el motor. El diccionario documenta el alias académico.

`category_stats` sigue **fuera** de la tabla por producto.

Observaciones siguen en `observaciones_*.parquet`.

---

## O. Diccionario de datos (propuesta de las variables del brief)

El diccionario vigente de las 267 columnas es [`docs/diccionario_dataset_referencia.md`](diccionario_dataset_referencia.md). Mapeo al listado pedido:

| Pedido | Columna real | Tipo | Procedencia | Unidad | NULL | Cero | Uso |
| --- | --- | --- | --- | --- | --- | --- | --- |
| product_code | `code` | texto | REAL | GTIN | no aplica | n/a | llave |
| product_name | `product_name` / `product_name_homologated` | texto | REAL / DERIVED / UNAVAILABLE | — | se conserva | n/a | mostrar |
| generic_name | `generic_name` | texto | REAL | — | se conserva | n/a | fallback A28 |
| brand | `brands` / `brand_homologated` | texto | REAL / DERIVED | — | se conserva | n/a | mostrar / join |
| category | `categories_tags` REAL; `categoria_referencia` DERIVED | texto | REAL / DERIVED | tag OFF | se conserva | n/a | D1 |
| ingredients | `ingredients_text` | texto | REAL | — | se conserva | n/a | filtro / ficha |
| energy_kcal | `energy-kcal_100g` / `_saneado` | float | REAL / DERIVED | kcal/100 g | se conserva | 0 real posible | informativo v1 |
| protein_g | `proteins_100g` / `_saneado` | float | REAL / DERIVED | g/100 g | se conserva | 0 real posible | D1 |
| carbohydrates_g | `carbohydrates_100g` | float | REAL | g/100 g | se conserva | 0 real posible | informativo |
| sugars_g | `sugars_100g` | float | REAL | g/100 g | se conserva | 0 real posible | D1 (−) |
| fat_g | `fat_100g` | float | REAL | g/100 g | se conserva | 0 real posible | informativo |
| saturated_fat_g | `saturated-fat_100g` | float | REAL | g/100 g | se conserva | 0 real posible | D1 (−) |
| fiber_g | `fiber_100g` | float | REAL | g/100 g | se conserva | 0 real posible | D1 (+) |
| sodium_g | `sodium_100g` | float | REAL | g/100 g | se conserva | 0 real posible | ficha; D1 usa sal |
| nova_group | `nova_group` | entero 1–4 | REAL | — | se conserva | n/a | D2 |
| additives_n | `additives_n` | entero | REAL | conteo | se conserva | 0 = cero aditivos | D2 |
| labels | `labels_tags` | texto | REAL | tags | se conserva | n/a | D3 |
| price | `price` | float (hoy texto, B14) | REAL o NULL | MXN | se conserva | no por ausencia | no puntúa |
| price_source | `price_source` = proveedor; `price_status` = procedencia | texto | REAL / UNAVAILABLE | — | NULL si no hay precio | n/a | ficha |
| data_quality_* | **no existe** | — | DERIVED propuesto | — | n/a | n/a | diagnóstico |
| protein_percentile | `percentil_proteins_100g` | float | DERIVED | 0–100 | NULL si no hay pares | n/a | D1 |
| nutrition_score | D1 en runtime | float | DERIVED | 0–100 | NULL si sin dato | n/a | scoring |
| user_* / interaction / recipe | no en catálogo | — | SYNTHETIC / llm si se crean | — | — | — | fuera |

---

## P. Archivos que se modificarían (solo si se aprueba el siguiente paso)

Ninguno en este corte.

Tras aprobación, candidatos:

- `docs/diccionario_dataset_referencia.md` — ampliar calidad / alias
- `AGENTS.md` — una decisión A-nueva si se materializa calidad
- `src/nutrimatch/services/catalog.py` — solo si la API debe exponer `data_quality_*`
- **No** `engine/*_score.py` (baseline intacto)

---

## Q. Archivos nuevos que se crearían (solo si se aprueba)

| Archivo | Condición |
| --- | --- |
| `scripts/construir_indicadores_calidad.py` | Si se pide `data_quality_score` |
| `datos/procesados/dataset_referencia_<fecha>.parquet` | Nueva versión + columnas DERIVED; no pisa la del 26 |
| `notebooks/09_eda_base_final.ipynb` | EDA de validación |
| `datos/procesados/perfiles_ejemplo.json` | Si se versionan Ana/Beto/Caro |
| `datos/procesados/precios_sinteticos_demo_*.parquet` | Solo si se pide extracto SYNTHETIC con semilla; **nunca** nutrientes |

No se toca Streamlit (ya retirado). No ML. No LLM.

---

## Criterio de cierre (para validar)

1. La fuente de verdad de producto **ya existe** y es reproducible (script A43 + confirmación A44).
2. REAL y DERIVED ya están separados; SYNTHETIC de precio **no está en el Parquet** (sí en la UI).
3. El hueco grande es precio (98,4 % UNAVAILABLE) y cobertura nutricional/NOVA (~35 % puntuable), no un error de join.
4. Cerrar la base = **documentar + indicador de calidad DERIVED + no contaminar el maestro**, no rellenar NULLs.

**Siguiente paso, cuando lo apruebes:** una sola etapa. La más útil y alineada con el brief es materializar `data_quality_score` / `data_quality_level` en un Parquet versionado nuevo, sin sintéticos.
