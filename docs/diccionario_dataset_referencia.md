# Diccionario del dataset analítico de referencia

Artefacto vigente con calidad DERIVED: `datos/procesados/dataset_referencia_20260927.parquet` (16.851 filas, una por `code`; 270 columnas).
La API (`Catalog.from_referencia` → `Settings.referencia_filename`) lee este archivo desde el 2026-09-27. El ranking no cambió.
Predecesor intacto: `datos/procesados/dataset_referencia_20260926.parquet` (16.851 × 267). No se sobrescribe.
Metadato de tabla: `datos/procesados/dataset_referencia_20260927_metadata.json`.
Tabla de observaciones (varias filas por `code`/`field`): `datos/procesados/observaciones_20260926.parquet`.

Cierre: decisiones **A43** (tabla maestra) y materialización de calidad DERIVED (2026-09-27). El snapshot crudo `off_mexico_20260919.parquet` **no se modifica**.

---

## 1. Las 211 columnas del export de OFF

Todas las columnas de `off_mexico_20260919.parquet` llegan **bit a bit iguales** al original.

- **Status:** REAL por construcción (A33). No se clona un `*_status` por columna.
- **Fuente:** Open Food Facts, export CSV diario, snapshot `off_csv_20260919`.
- **Procedencia completa:** `datos/snapshots/off_csv_20260919/_metadata.json` (URL, bytes, sha256, lista de las 211 columnas).
- **Documentación de campo:** [wiki de Open Food Facts](https://wiki.openfoodfacts.org/Main_fields).

`nova_group` y `additives_n` viven solo en este bloque. `matriz_nut_100g` las traía como passthrough idéntico; se dropean al unir para no renombrar las de OFF con `_x`/`_y`.

---

## 2. Identidad (DERIVED, A28 / A38; override REAL A39)

| Columna | Tipo | Status | Fuente | Decisión |
| --- | --- | --- | --- | --- |
| `product_name_original` | texto | REAL del export (puede ser NULL) | `product_name` de OFF | A37, A38 |
| `product_name_field_source` | texto | DERIVED | `product_name` / `generic_name` / `abbreviated_product_name` / NULL | A28, A38 |
| `product_name_flag_respaldo_usado` | bool | DERIVED | True si el nombre no vino de `product_name` | A28 |
| `product_name_flag_placeholder_removido` | bool | DERIVED | True si se descartó el literal `"Cargando…"` | A38 |
| `product_name_homologated` | texto | DERIVED, o REAL si hay hit de API | Homologación interna, o API de producto OFF | A38, A39 |
| `product_name_status` | texto | `DERIVED` / `REAL` / `UNAVAILABLE` | Homologación o API | A33, A38, A39 |
| `product_name_source` | texto | `off_export` o `openfoodfacts_api_producto` | Quién ganó en la ficha | A39, A43 |
| `brand_original` | texto | REAL del export (puede ser NULL) | `brands` de OFF | A38 |
| `brand_homologated` | texto | DERIVED | Llave interna (minúsculas, acentos plegados); no es para mostrar | A38 |
| `brand_status` | texto | `DERIVED` / `UNAVAILABLE` | Homologación de marca | A38 |

Hoy hay 6 códigos con `product_name_source = openfoodfacts_api_producto` (hits del experimento A39). El resto usa el export.

---

## 3. Matriz nutricional (DERIVED, A18 / A21 / A23 / A27)

Patrón por nutriente CORE8 (`energy-kcal`, `fat`, `saturated-fat`, `carbohydrates`, `sugars`, `proteins`, `salt`, `fiber`), cada uno con tres columnas:

| Sufijo | Significado | Status |
| --- | --- | --- |
| `*_100g_bruto` | Valor crudo del export | REAL (copia trazable) |
| `*_100g_flag_fuera_de_rango` | True si el bruto está fuera de rango físico | DERIVED (A18) |
| `*_100g_saneado` | Valor usado para percentiles; NULL si flag | DERIVED; nunca un 0 inventado (A2) |

Columnas extra de la matriz:

| Columna | Tipo | Status | Decisión |
| --- | --- | --- | --- |
| `salt_100g_flag_correccion_escala_aplicada` | bool | DERIVED | A21 |
| `flag_suma_macros_excede_100` | bool | DERIVED | A18 |
| `categoria_referencia` | texto | DERIVED o NULL | A16 |
| `nivel_retroceso` | entero | DERIVED o NULL | A16 |
| `percentil_<nutriente>` | float 0–1 o NULL | DERIVED | A24, A27 |
| `n_percentiles_validos` | entero | DERIVED | A22 |
| `d2` | float 0–100 o NULL | DERIVED | A23 |
| `universo_puntuable` | bool | DERIVED | A22 |

`category_stats_20260919.parquet` **no** entra aquí: es por categoría, no por producto.

---

## 4. Precio resuelto (REAL o UNAVAILABLE, A5 / A35 / A36 / A40 / A41)

Una observación ganadora por `code` (regla F.2: REAL más reciente; si no hay, UNAVAILABLE). Medido el 2026-09-26: 263 `REAL` (242 Open Prices + 21 QQP únicos), 16.588 `UNAVAILABLE`. 0 códigos con las dos fuentes a la vez. No hay IMPUTED ni SYNTHETIC.

| Columna | Tipo | Status / valores | Decisión |
| --- | --- | --- | --- |
| `price` | texto (número como string, B14) o NULL | REAL o NULL; nunca 0 por ausencia | A2, A43 |
| `price_status` | texto | `REAL` / `UNAVAILABLE` | A33, A36 |
| `price_source` | texto o NULL | `open_prices` / `qqp_profeco` / NULL | A40, A41 |
| `price_source_url` | texto o NULL | URL de la observación ganadora | A33 |
| `price_retrieved_at` | texto ISO o NULL | Cuándo se materializó la observación | A33 |
| `price_match_method` | texto o NULL | `exact_gtin` (Open Prices) / `text_reviewed` (QQP) | A35, A40, A41 |
| `price_match_confidence` | float 0–1 o NULL | Solo QQP (`score/100`); NULL en EAN exacto | A41 |

El precio **no puntúa**. QQP se llama siempre "precio de referencia", nunca "estimado".

`price_source` es el **proveedor** (`open_prices` / `qqp_profeco` / NULL). `price_status` es la procedencia (`REAL` / `UNAVAILABLE`). No se sustituyen por `real|synthetic|missing`.

---

## 5. Calidad de información (DERIVED, 2026-09-27)

No miden si el producto es “más saludable”. Miden si la ficha tiene dato y si ese dato es físicamente consistente. **No puntúan.** No imputan. Un NULL de nutriente sigue NULL; un 0 real sigue 0.

Fórmula: promedio simple de 7 componentes en [0, 1], reutilizando columnas ya existentes.

| Componente | Entrada reutilizada | 1 si… | 0 si… |
| --- | --- | --- | --- |
| `nutrition` | `n_percentiles_validos` | fracción `n/8` | `n` nulo → 0 |
| `ingredients` | `ingredients_text` | hay texto | NULL / NaN / vacío |
| `category` | `categoria_referencia` | hay categoría A16 | NULL |
| `nova` | `nova_group` | hay grupo NOVA | NULL |
| `additives` | `additives_n` | hay número, **incluido 0** | NULL |
| `labels` | `labels_tags` | hay etiquetas | NULL |
| `consistency` | flags A18 | ningún flag de rango/macros | algún `*_flag_fuera_de_rango` o `flag_suma_macros_excede_100` |

`data_quality_score = (suma de los 7) / 7`. Siempre definido: la ausencia es un 0 en el componente, no un nutriente inventado.

| Columna | Tipo | Procedencia | Descripción | NULL | Uso |
| --- | --- | --- | --- | --- | --- |
| `data_quality_score` | float 0–1 | DERIVED | Promedio de las 7 dimensiones de disponibilidad/consistencia | no se anula; la ficha siempre se puede auditar | diagnóstico; no entra a D1/D2/D3/`cov` |
| `data_quality_level` | texto | DERIVED | `insuficiente` (&lt;0,25) / `baja` (&lt;0,50) / `media` (&lt;0,75) / `alta` (≥0,75) | no | diagnóstico |
| `data_quality_detalle` | texto | DERIVED | `nutrition:0.5000;ingredients:1;...` — componentes del score | no | explicación (A10), no duplica las columnas fuente |

`completeness` y `data_quality_errors_tags` de OFF siguen en el bloque REAL; no se copian aquí.

No hay SYNTHETIC ni IMPUTED en este Parquet.

---

## 6. Tabla de observaciones

Esquema F.2: `code`, `field`, `value`, `status`, `source`, `source_url`, `retrieved_at`, `snapshot_id`, `method`, `confidence`, `quality_flag`.

`value` es texto. Varias filas por `(code, field)` son válidas (42 códigos de Open Prices tienen más de un precio). La ficha resuelve con `resolver_observaciones` (REAL más reciente; nunca IMPUTED por delante de REAL).
