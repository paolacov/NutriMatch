# Atribución de fuentes de datos

NutriMatch no genera los datos de producto ni los precios de mercado. Los toma de fuentes externas. Este documento dice qué usa el código y qué licencia está registrada dentro del repositorio. El texto legal de cada licencia no está copiado aquí.

## Open Food Facts

Fuente de nutrientes, ingredientes, grupo NOVA, etiquetas, sellos e imágenes de producto. El catálogo operativo cita el snapshot `off_csv_20260929`. El export es el CSV comprimido cuyo SHA-256 coincide en las descargas del 19 y del 29 de septiembre de 2026.

El script `scripts/ingesta_off.py` y el metadato `datos/snapshots/off_csv_20260929/_metadata.json` registran esta cadena:

`ODbL (base) / DbCL (contenidos) / CC-BY-SA (imagenes)`

Esa cadena es el registro del proyecto. Los textos de la Open Database License, de la Database Contents License y de CC BY-SA no están en el repositorio. Confirmar el alcance de cada una es un punto de verificación documental en la ficha de Open Food Facts.

## Open Prices

239 precios en pesos mexicanos, método `exact_gtin`, unidos al catálogo operativo. El cliente está en `src/nutrimatch/providers/open_prices_api.py`. El comentario de `scripts/piloto_precios_open_prices.py` nombra ODbL. El texto de esa licencia no está en el repositorio. Es un punto de verificación documental en el proyecto Open Prices.

## PROFECO, Quién es Quién en los Precios

20 precios de referencia, método `text_reviewed`, unidos al catálogo operativo. El cliente está en `src/nutrimatch/providers/qqp_api.py`. `AGENTS.md` y ese cliente afirman la licencia CC-BY 4.0. El texto de la licencia no está en el repositorio. Es un punto de verificación documental en la ficha del conjunto en el portal de datos abiertos.

Esos 20 precios se presentan como precio de referencia de una presentación parecida. La coincidencia es de texto. El sistema no los calcula ni los proyecta.

## Lo que no es una fuente del catálogo

USDA FoodData Central no alimenta el catálogo. La única aparición de USDA en el código es la traducción de la etiqueta `en:usda-organic` a «Orgánico USDA» en `frontend/src/app/shared/sello-label.ts`.

Las ilustraciones de Nuti y los marcadores de categoría viven en `frontend/public/`. El repositorio no trae un aviso de banco de imágenes para esos archivos. La licencia del código está en [`LICENSE`](../LICENSE).

## Cita

### Open Food Facts

> Open Food Facts. (2026). *Open Food Facts database* [Conjunto de datos]. Recuperado el 2 de octubre de 2026 de https://world.openfoodfacts.org
>
> Snapshot utilizado: export CSV identificado como `off_csv_20260929` (el archivo comprimido coincide con el del 19 de septiembre de 2026).

Open Food Facts regenera sus exports a diario. La fecha del snapshot identifica la versión usada.

### Open Prices

> Open Food Facts. (2026). *Open Prices* [Conjunto de datos]. Recuperado el 2 de octubre de 2026 de https://prices.openfoodfacts.org

### PROFECO, Quién es Quién en los Precios

> Procuraduría Federal del Consumidor. (2026). *Quién es Quién en los Precios* [Conjunto de datos]. Gobierno de México. Recuperado el 2 de octubre de 2026 de https://datos.profeco.gob.mx
