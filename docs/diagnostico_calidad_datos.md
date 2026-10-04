# Calidad de los datos

Medí la calidad del universo de México de Open Food Facts y, a partir de esa medición, cerré el catálogo operativo `dataset_referencia_20261002.parquet` (13 093 productos). Este documento resume los hallazgos que quedaron incorporados al sistema.

## Universo

El export filtrado por país México contiene 16 851 productos, con códigos únicos. Tres candados de ingesta producen el catálogo que sirve la API:

| Candado | Filas que permanecen | Excluidas |
| --- | --- | --- |
| País México | 16 851 | — |
| No alimento | 16 848 | 3 |
| Integridad mínima (ingredientes, NOVA o algún macro mayor que cero) | 13 111 | 3 737 |
| Identidad de nombre | 13 093 | 18 |

El archivo comprimido del 29 de septiembre de 2026 es el mismo que el del 19 de septiembre. La reducción no viene de un export nuevo.

## Ausencias

La ausencia de nutrientes del núcleo, de categoría, de NOVA, de dieta, de alérgenos y de sellos acompaña a los registros con ingredientes vacíos y con menor completitud. El patrón es de registro: o están los ocho nutrientes del núcleo, o faltan casi todos. Por eso un ausente permanece NULL. Rellenarlo inventaría un hecho nutricional o, en alérgenos, un hecho de seguridad.

## Identidad

La unidad es el código de barras. El nombre visible sale del propio registro (`product_name`, `generic_name`, `abbreviated_product_name`). El placeholder «Cargando…» se trata como vacío. La marca de cruce se pliega a minúsculas sin acentos y no se muestra. Un lote contra la ficha viva recuperó nombres reales adicionales; en el catálogo operativo quedan 5 con fuente `openfoodfacts_api_producto`. Esas observaciones no sobrescriben el export.

## Precio

El precio de mercado es real o está ausente.

- Open Prices, filtro `currency=MXN`, cruce exacto por código: 239 precios en el catálogo operativo. El filtro por país de la ubicación no existe en esa API y se ignora en silencio.
- PROFECO no publica código de barras. El esquema real trae producto, presentación, marca compuesta, precio, fecha y establecimiento. Integré 20 precios cuya coincidencia de texto quedó revisada. Se muestran como precio de referencia, con el método y la confianza visibles.
- 12 834 productos quedan sin observación. El Parquet guarda NULL. La ficha, al responder, emite un fallback de tipo `SYNTHETIC`.

El portal de PROFECO responde HTTP 403 a un agente que no parece un navegador. El cliente de ese proveedor, y solo ese, envía un agente de navegador.

## Procedencia

Los estados son `REAL`, `DERIVED`, `IMPUTED`, `SYNTHETIC` y `UNAVAILABLE`. El Parquet operativo usa real, derivado y no disponible. Lo que no viene del export vive en `datos/procesados/observaciones_20260926.parquet`. Si hay varias observaciones, gana la real más reciente.

La calidad de información (alta 6 102, media 1 511, baja 1 274, insuficiente 4 206) mide disponibilidad y coherencia física. No entra al puntaje.

## Motor

El universo puntuable del catálogo operativo tiene 5 864 productos: al menos cuatro percentiles válidos del núcleo y procesamiento calculable. Las fórmulas del ranking permanecen las descritas en [`../AGENTS.md`](../AGENTS.md). El precio no puntúa.
