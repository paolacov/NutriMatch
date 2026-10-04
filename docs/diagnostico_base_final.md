# Base final del catálogo

La base que sirve la aplicación es `datos/procesados/dataset_referencia_20261002.parquet`.

| Pieza | Archivo | Papel |
| --- | --- | --- |
| Catálogo operativo | `dataset_referencia_20261002.parquet` | 13 093 productos. Lo lee la API |
| Metadato | `dataset_referencia_20261002_metadata.json` | Candados, precios y huella SHA-256 |
| Observaciones | `observaciones_20260926.parquet` | Nombres de ficha viva y precios, varias filas por código |
| Precios Open Prices | `precios_open_prices_20260926.parquet` | Observaciones reales por código de barras |
| Precios PROFECO | `precios_qqp_20260926.parquet` | Precios de referencia con coincidencia revisada |
| Universo de país | `off_mexico_20260929.parquet` | Insumo de la ingesta. La API no lo sirve |
| Matriz nutricional | `matriz_nut_100g_20260929.parquet` | Percentiles y procesamiento ya calculados |
| Identidad | `identidad_homologada_20260919.parquet` | Nombres y marcas homologados |

Conteos del archivo operativo, leídos del Parquet:

- 5 864 productos en el universo puntuable.
- 259 precios reales: 239 de Open Prices y 20 de PROFECO.
- 12 834 sin observación de precio. El fallback `SYNTHETIC` se calcula en la respuesta y no está almacenado.
- Calidad de información: alta 6 102, insuficiente 4 206, media 1 511, baja 1 274.

Los cortes anteriores del dataset de referencia permanecen en `datos/procesados/` como material de la construcción. La configuración `REFERENCIA_FILENAME` apunta al archivo del 2 de octubre de 2026.
