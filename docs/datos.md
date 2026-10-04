# Datos

Dataset que utiliza actualmente la aplicación: `datos/procesados/dataset_referencia_20261002.parquet`.

Fuente de verdad recomendada para reproducibilidad: `datos/procesados/dataset_referencia_20261002.parquet`.

La API lo abre en `Catalog.from_referencia()` (`src/nutrimatch/services/catalog.py`), con la ruta de `Settings.referencia_parquet()`. El 3 de octubre de 2026 el archivo local tenía SHA-256 `a621d471a2f47aa09ba481408d95a7a808fe84bd2fa7205c56fa050e1c66045b`, 13 093 filas, 273 columnas y 5 864 filas con `universo_puntuable`. Esa huella es la de `dataset_referencia_20261002_metadata.json`.

## Comparación

| Pregunta | Respuesta |
| --- | --- |
| Documentado en README, AGENTS y `config.py` | `dataset_referencia_20261002.parquet` |
| Configurado en `.env` (`REFERENCIA_FILENAME`) | El mismo nombre |
| Resuelto por `get_settings().referencia_parquet()` | `datos/procesados/dataset_referencia_20261002.parquet` |
| Presente en disco | Sí, junto con cortes del 26, 27 y 29 de septiembre de 2026 |
| Qué admite `.gitignore` en un alta nueva | El operativo y su metadato. Los demás Parquet de `datos/procesados/` quedan ignorados |

Los scripts de construcción no son la aplicación. Siguen citando cortes previos:

| Script o prueba | Archivo que nombra | Clase |
| --- | --- | --- |
| La API (`Catalog.from_referencia`) | `dataset_referencia_20261002.parquet` | A. Lo usa la aplicación |
| `scripts/cerrar_dataset_operativo.py` | Lee el corte del 29 y escribe el del 2 de octubre | B. Construcción |
| `scripts/construir_dataset_referencia.py` | Default de salida `dataset_referencia_20260929.parquet` | B. Construcción |
| `scripts/confirmar_ranking_v1.py` y `tests/test_confirmar_ranking_v1.py` | `dataset_referencia_20260926.parquet`. La prueba se omite si el archivo no está | B. Validación |
| `scripts/auditar_cobertura_funcional.py` y `tests/test_catalog_referencia_api.py` | `dataset_referencia_20260927.parquet`. La prueba de API exige que el archivo exista | B. Validación |
| Módulo de cierre funcional que fija `referencia_filename` en el corte del 27 | El mismo Parquet del 27. Si falta, la prueba no arranca | B. Validación |
| `tests/test_dataset_operativo.py` | Compara `20261002` con `20260929`. Si falta el del 29, esa comparación se omite | B. Validación |
| `tests/test_golden_set.py` | `matriz_nut_100g_20260919.parquet` y `off_mexico_20260919.parquet`. Se omite si faltan | B. Validación |
| `tests/test_ranking_snapshot.py` | `off_mexico_20260929.parquet` y `matriz_nut_100g_20260929.parquet`. Se omite si faltan | B. Validación |

Esa diferencia es de linaje, no del proceso que atiende HTTP. Esta auditoría no cambió ningún archivo de datos.

## Qué es fuente de verdad

El Parquet operativo es la fuente de verdad del catálogo que ve la persona. El export CSV comprimido es la fuente de verdad del corte de Open Food Facts, y no entra a Git por tamaño. SQLite no es fuente de verdad: es uso local.

## Clasificación de `datos/`

Tamaños medidos en el árbol local. Ningún Parquet de `procesados/` supera 11 MB. El export sí: cada copia pesa alrededor de 1,2 GB.

### `datos/snapshots/`

| Conjunto | Origen | Propósito | Tamaño | ¿Ejecutar la app? | ¿Regenerable? | ¿Sensible? | Git |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `off_csv_20260919/en.openfoodfacts.org.products.csv.gz` | Open Food Facts, export CSV | Insumo de `scripts/ingesta_off.py` | ~1,2 GB | No | Sí, volviendo a descargar. El SHA-256 del gzip coincide con el del 29 | Datos públicos de producto | Fuera. Ya ignorado |
| `off_csv_20260929/en.openfoodfacts.org.products.csv.gz` | El mismo archivo que el del 19 (`mismo_gzip` en el metadato) | Cita del snapshot `off_csv_20260929` | ~1,2 GB | No | Sí, con `OFF_CSV_EXPORT_URL`. El export diario cambia: este SHA fija el corte | Datos públicos | Fuera |
| `*/_metadata.json` | Escrito por la ingesta | URL, fecha, SHA-256, esquema | Kilobytes | No | Se reescribe al ingerir | No | Dentro. El `.gitignore` lo reincorpora |

`datos/precios_qqp/` está vacía y queda fuera de Git. El ZIP de PROFECO no está en el árbol. `AGENTS.md` lo cita en unos 186 MB. Para reconstruir los 20 precios ya integrados haría falta volver a obtener el portal y el CSV revisado.

### `datos/cache/`

Caché local de Open Food Facts, Open Prices, PROFECO y un spike de lenguaje (~11 MB). Acelera una re-ejecución. No es fuente de verdad. Fuera de Git. Regenerable al volver a llamar a las APIs. Puede contener respuestas de esas APIs; no es un almacén de claves.

### `datos/procesados/` — catálogo y linaje

| Archivo | Origen | Propósito | Tamaño | ¿Para ejecutar? | ¿Regenerable? | Git |
| --- | --- | --- | --- | --- | --- | --- |
| `dataset_referencia_20261002.parquet` | Cierre sobre el corte del 29 más precios y calidad | Catálogo de la API | 8,8 MB | Sí. Clase A | Sí, con `scripts/cerrar_dataset_operativo.py` si existe el del 29 | Dentro. El `.gitignore` lo admite |
| `dataset_referencia_20261002_metadata.json` | El mismo cierre | Huella y conteos | 4 KB | Verifica el archivo. Clase A | Sí, con el script | Dentro |
| `dataset_referencia_20260929.parquet` | Construcción previa, 13 093 filas | Origen de percentiles, D2 y `universo_puntuable` | 8,9 MB | No. Clase B | Cadena de scripts y una comparación que se omite si falta | Fuera de un alta nueva |
| `dataset_referencia_20260927.parquet` | Corte de 16 851 | Regresión de `tests/test_catalog_referencia_api.py` y del cierre funcional | 9,5 MB | No. Clase B | Esas pruebas lo exigen | Fuera de un alta nueva. Un commit anterior ya lo sigue; Git no lo suelta solo con `.gitignore` |
| `dataset_referencia_20260926.parquet` | Corte previo a la calidad de información | `confirmar_ranking_v1.py` | 10 MB | No. Clase B | La prueba se omite si falta | Fuera de un alta nueva |
| `off_mexico_20260919.parquet` | Ingesta filtrada a México | Universo crudo y conjunto de oro | ~5 MB | No. Clase B | `tests/test_golden_set.py` se omite si falta | Fuera de un alta nueva. Un commit anterior ya lo sigue |
| `off_mexico_20260929.parquet` | Ingesta del mismo export | Insumo de la ingesta citada por el snapshot de la API | ~5 MB | No. Clase B | `tests/test_ranking_snapshot.py` se omite si falta | Fuera de un alta nueva |
| `matriz_nut_100g_20260919.parquet` | Transformación nutricional | Percentiles del conjunto de oro | < 1 MB | No. Clase B | Junto con `off_mexico_20260919` | Fuera de un alta nueva. Un commit anterior ya lo sigue |
| `matriz_nut_100g_20260929.parquet` | Transformación nutricional | Percentiles del corte del 29 | < 1 MB | No. Clase B | `tests/test_ranking_snapshot.py` | Fuera de un alta nueva |
| `category_stats_20260919.parquet` y `category_stats_20260929.parquet` | Estadísticas de categoría | Apoyo del análisis | 56 KB | No. Clase C | Ninguna prueba de la aplicación los abre | Fuera de un alta nueva. El de 20260919 ya está en un commit anterior |
| `identidad_homologada_20260919.parquet` | `scripts/homologar_identidad.py` | Nombres y marcas derivados | 768 KB | No. Clase B | El script de construcción | Fuera de un alta nueva |
| `observaciones_20260926.parquet` | Precios y nombres recuperados | Observaciones que el cierre une | 16 KB | No. Clase B | `scripts/cerrar_dataset_operativo.py` | Fuera de un alta nueva |
| `precios_open_prices_20260926.parquet` | Open Prices, MXN, cruce por código | 239 precios antes de unirlos | 24 KB | No. Clase B | `make piloto-precios` y la construcción | Fuera de un alta nueva |
| `precios_qqp_20260926.parquet` | PROFECO, texto revisado | 20 precios de referencia | 16 KB | No. Clase B | `make materializar-qqp` y la construcción | Fuera de un alta nueva |
| `experimento_recuperacion_nombres_20260919.parquet` | Consulta a la ficha viva de OFF | Nombres recuperados, sin sobrescribir el export | 16 KB | No. Clase B | `scripts/experimento_recuperacion_nombres.py` | Fuera de un alta nueva |
| CSV y JSON de auditoría en la raíz de `procesados/` | Scripts de diagnóstico | Conteos y candidatos PROFECO | < 30 KB | No | Los scripts que los escriben | Dentro. Antes el `.gitignore` los dejaba fuera |
| `re_eda_20260926/*.csv` | Notebook 08 | Resúmenes citables | 104 KB el directorio | No | El notebook | Dentro |
| `figuras_universo_operativo_20261002/*.png` | `scripts/figuras_universo_operativo.py` | Figuras del análisis | 492 KB | No | El script | Fuera. Son salida |

Ninguno de estos archivos es un secreto de aplicación. Son datos públicos de alimentos y precios, más derivados calculados. El Parquet operativo no guarda la clave de OpenAI.

## Estrategia para lo que no cabe en Git

El export CSV no debe subirse. GitHub rechaza archivos por encima de 100 MB y advierte desde 50 MB. Cada gzip está en torno a 1,2 GB.

Para reproducir solo la aplicación, el clon necesita `dataset_referencia_20261002.parquet` en `datos/procesados/`. No necesita el gzip.

Para reconstruir el universo:

1. Conseguir el export de Open Food Facts. La URL de trabajo está en `OFF_CSV_EXPORT_URL` (`.env.example`). El archivo del corte citado tiene SHA-256 de gzip `f72687ee8bc6522054fe69dbfda6b91902c16af1ec2e043cde27bc6c29ad8176`. El export público de hoy puede ser otro archivo: Open Food Facts lo regenera a diario.
2. Colocarlo donde lo espera `scripts/ingesta_off.py` (`datos/snapshots/`).
3. Correr `make ingest-off` y el resto de la cadena descrita en [`reproducibilidad.md`](reproducibilidad.md).

El gzip permanece fuera del repositorio. Para ejecutar la aplicación basta el Parquet operativo.

## SQLite

Archivo local: `nutrimatch.db` en la raíz, con `nutrimatch.db-wal` y `nutrimatch.db-shm`.

Tablas creadas por `src/nutrimatch/db/schema.py`:

- `user_profile`: un perfil JSON de servidor.
- `ranking_run` y `ranking_run_item`: cada corrida que atiende `POST /ranking`.
- `event_log`: eventos de uso (`GET` y `POST /events`).

Contiene estado mutable de uso. En una máquina de desarrollo puede incluir búsquedas y perfiles de prueba. No es el catálogo. Se regenera vacío al arrancar la API si el archivo no existe. Queda fuera de Git. En Vercel la ruta efectiva es `/tmp/nutrimatch.db` porque el disco de la función es de solo lectura fuera de `/tmp`.

El perfil, el carrito y la comparación que ve la persona están en `localStorage` del navegador (`nutrimatch.profile.v2` y las tiendas de `frontend/src/app/core/data/`).
