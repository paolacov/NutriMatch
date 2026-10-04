# Diccionario del dataset operativo

Catálogo que carga la API: `datos/procesados/dataset_referencia_20261002.parquet`.

- 13 093 filas, una por código de barras.
- 273 columnas.
- Metadato: `datos/procesados/dataset_referencia_20261002_metadata.json`.
- Tabla de observaciones (varias filas por código y campo): `datos/procesados/observaciones_20260926.parquet`.

El archivo parte del corte del 29 de septiembre de 2026 y conserva sus percentiles, su subpuntaje de procesamiento y la marca de universo puntuable. Le une los precios reales que siguen dentro de las 13 093 filas y la calidad de información. El export crudo no se modifica.

Medido sobre este archivo:

| Indicador | Valor |
| --- | --- |
| Universo puntuable | 5 864 |
| Calidad alta | 6 102 |
| Calidad media | 1 511 |
| Calidad baja | 1 274 |
| Calidad insuficiente | 4 206 |
| Precio real | 259 (239 Open Prices y 20 PROFECO) |
| Precio no disponible en el Parquet | 12 834 |
| Precio sintético dentro del Parquet | 0 |
| Nombres recuperados por la ficha viva | 5 |

---

## 1. Columnas del export de Open Food Facts

Las columnas del export llegan iguales al original.

- Procedencia: `REAL`.
- Fuente: Open Food Facts, export CSV, snapshot `off_csv_20260929` (el mismo archivo comprimido que el del 19 de septiembre de 2026).
- Metadato de descarga: `datos/snapshots/off_csv_20260929/_metadata.json`.
- Documentación de campo: [wiki de Open Food Facts](https://wiki.openfoodfacts.org/Main_fields).

`nova_group` y `additives_n` viven en este bloque. La matriz nutricional los traía repetidos e idénticos; se descartan al unir para que pandas no los renombre.

## 2. Identidad

| Columna | Tipo | Procedencia | Significado |
| --- | --- | --- | --- |
| `product_name_original` | texto | REAL del export; puede ser NULL | `product_name` tal como llegó |
| `product_name_field_source` | texto | DERIVED | Campo del mismo registro que aportó el nombre visible |
| `product_name_flag_respaldo_usado` | bool | DERIVED | Verdadero si el nombre no vino de `product_name` |
| `product_name_flag_placeholder_removido` | bool | DERIVED | Verdadero si se descartó el literal «Cargando…» |
| `product_name_homologated` | texto | DERIVED, o REAL si hay nombre de la ficha viva | Nombre para mostrar |
| `product_name_status` | texto | `DERIVED`, `REAL` o `UNAVAILABLE` | Procedencia del nombre |
| `product_name_source` | texto | `off_export` o `openfoodfacts_api_producto` | Fuente que ganó |
| `brand_original` | texto | REAL; puede ser NULL | `brands` del export |
| `brand_homologated` | texto | DERIVED | Llave interna: minúsculas y sin acentos. No se muestra |
| `brand_status` | texto | `DERIVED` o `UNAVAILABLE` | Procedencia de la marca homologada |

El orden de respaldo del nombre es `product_name`, luego `generic_name`, luego `abbreviated_product_name`. Si ninguno tiene dato, el nombre queda vacío.

## 3. Matriz nutricional

Patrón por nutriente del núcleo (`energy-kcal`, `fat`, `saturated-fat`, `carbohydrates`, `sugars`, `proteins`, `salt`, `fiber`):

| Sufijo | Significado | Procedencia |
| --- | --- | --- |
| `*_100g_bruto` | Valor crudo del export | REAL |
| `*_100g_flag_fuera_de_rango` | Verdadero si el bruto está fuera de rango físico | DERIVED |
| `*_100g_saneado` | Valor usado para percentiles; NULL si hay bandera | DERIVED. Un ausente sigue ausente |

| Columna | Tipo | Procedencia | Significado |
| --- | --- | --- | --- |
| `salt_100g_flag_correccion_escala_aplicada` | bool | DERIVED | La sal se reescaló con el sodio del mismo producto |
| `flag_suma_macros_excede_100` | bool | DERIVED | La suma de macros supera 100 g |
| `categoria_referencia` | texto o NULL | DERIVED | Categoría usada para el percentil |
| `nivel_retroceso` | entero o NULL | DERIVED | Cuántos niveles se subió en la jerarquía |
| `percentil_<nutriente>` | float 0–1 o NULL | DERIVED | Percentil dentro de la categoría |
| `n_percentiles_validos` | entero | DERIVED | Cuántos percentiles del núcleo tienen dato |
| `d2` | float 0–100 o NULL | DERIVED | Subpuntaje de procesamiento |
| `universo_puntuable` | bool | DERIVED | Al menos cuatro percentiles válidos y procesamiento calculable |

`category_stats_*.parquet` es una tabla por categoría. No entra en esta fila de producto.

La dimensión nutricional puntúa azúcares, sal, grasa saturada, fibra y proteína. Energía, grasa total y carbohidratos conservan percentil para la ficha.

## 4. Precio resuelto

Una observación ganadora por código: la real más reciente. Si no hay ninguna, el estado es no disponible. Medido en este archivo: 259 reales (239 Open Prices y 20 PROFECO) y 12 834 no disponibles. Cero sintéticos y cero imputados dentro del Parquet.

| Columna | Tipo | Valores |
| --- | --- | --- |
| `price` | texto numérico o NULL | Monto real, o NULL. La ausencia no se guarda como 0 |
| `price_status` | texto | `REAL` o `UNAVAILABLE` |
| `price_source` | texto o NULL | `open_prices`, `qqp_profeco` o NULL |
| `price_source_url` | texto o NULL | URL de la observación ganadora |
| `price_retrieved_at` | texto ISO o NULL | Momento en que se materializó |
| `price_match_method` | texto o NULL | `exact_gtin` o `text_reviewed` |
| `price_match_confidence` | float 0–1 o NULL | Solo PROFECO. NULL en el cruce exacto por código |

`price_source` es el proveedor. `price_status` es la procedencia. El precio no puntúa. El de PROFECO se llama precio de referencia.

Al responder la ficha, los 12 834 no disponibles con código de barras salen como `SYNTHETIC`. Ese estado vive en el contrato HTTP, no en esta columna.

## 5. Calidad de información

Mide si la ficha tiene dato y si ese dato es físicamente consistente. No mide si el producto es más saludable. No puntúa. No imputa.

El puntaje es el promedio simple de siete componentes en el intervalo de 0 a 1:

| Componente | Entrada | 1 si… | 0 si… |
| --- | --- | --- | --- |
| `nutrition` | `n_percentiles_validos` | fracción n/8 | n nulo |
| `ingredients` | `ingredients_text` | hay texto | vacío |
| `category` | `categoria_referencia` | hay categoría de referencia | NULL |
| `nova` | `nova_group` | hay grupo NOVA | NULL |
| `additives` | `additives_n` | hay número, incluido 0 | NULL |
| `labels` | `labels_tags` | hay etiquetas | vacío |
| `consistency` | banderas de rango | ningún flag de rango o de macros | alguno activo |

| Columna | Tipo | Significado |
| --- | --- | --- |
| `data_quality_score` | float 0–1 | Promedio de los siete componentes |
| `data_quality_level` | texto | `insuficiente` por debajo de 0,25; `baja` por debajo de 0,50; `media` por debajo de 0,75; `alta` desde 0,75 |
| `data_quality_detalle` | texto | Componentes, por ejemplo `nutrition:0.5000;ingredients:1` |

`completeness` y `data_quality_errors_tags` de Open Food Facts siguen en el bloque real.

## 6. Tabla de observaciones

Columnas: `code`, `field`, `value`, `status`, `source`, `source_url`, `retrieved_at`, `snapshot_id`, `method`, `confidence`, `quality_flag`.

`value` es texto. La ficha resuelve con la observación real más reciente. Un valor imputado o sintético no se antepone a uno real. La implementación está en `nutrimatch.engine.observations`.
