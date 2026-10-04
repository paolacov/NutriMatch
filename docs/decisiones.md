# Decisiones de NutriMatch

Estas son las decisiones que el código aplica. Los criterios medidos del motor están en [`../AGENTS.md`](../AGENTS.md).

## Interfaz: Angular

La interfaz es Angular 20 en `frontend/`. Habla con FastAPI por HTTP. El perfil, el carrito y la comparación de la sesión viven en el navegador (`localStorage`). La carpeta `ui/` solo contiene un `.gitkeep`. La interfaz es `frontend/`.

## API: FastAPI

La API es FastAPI (`nutrimatch.api.app`). En local escucha en `127.0.0.1:8000`. En Vercel entra por `api/index.py` y `vercel.json` la publica en el mismo dominio que Angular.

## Parquet como fuente de verdad del catálogo

El catálogo que abre la aplicación es `datos/procesados/dataset_referencia_20261002.parquet`. Lo eligen `REFERENCIA_FILENAME` y el valor por defecto de `src/nutrimatch/core/config.py`. `Catalog.from_referencia()` es el cargador de la API.

Los Parquet anteriores y las tablas intermedias (`off_mexico_*`, `matriz_nut_100g_*`) documentan la construcción y alimentan scripts o pruebas. Con el nombre configurado, la API abre el archivo del 2 de octubre de 2026.

## SQLite como estado mutable

`nutrimatch.db` guarda perfil de servidor, corridas de ranking y el registro de eventos. Se crea al arrancar la API con `init_db`. Se puede borrar. En Vercel se escribe en `/tmp/nutrimatch.db`. El perfil que usa la interfaz está en el navegador.

## Ranking determinístico

D1, D2 y D3 se calculan con reglas fijas. Los mismos datos y el mismo perfil producen el mismo resultado. Los pesos salen del orden de tres prioridades: 0,50 / 0,33 / 0,17.

## Sin aprendizaje supervisado

NutriMatch no utiliza aprendizaje supervisado porque el catálogo no contiene un target observado que permita entrenar y evaluar de manera científicamente válida un modelo de recomendación.

La evaluación del motor es el conjunto de oro (`evaluacion/golden_set.py`), el contraste con Nutri-Score y el diagnóstico de cobertura.

## Datos faltantes

Un faltante es NULL con bandera. No se imputan nutrientes, alérgenos, grupo NOVA ni precio de mercado para completar el ranking. Un cero nutricional es un hecho declarado. La cobertura por debajo de 0,5 manda el producto a información insuficiente, separado del orden. El estado `IMPUTED` existe en la taxonomía de procedencia y el catálogo operativo no lo usa.

## OpenAI solo para el lenguaje

`nutrimatch.ai` atiende `POST /ai/ask`. Planifica la operación, redacta y un critic determinista comprueba que el texto cite hechos ya calculados. Sin `OPENAI_API_KEY`, o si la llamada falla, responden plantillas en `nutrimatch.ai.baseline`. El modelo por defecto es `gpt-4o-mini`.

El lenguaje redacta la explicación. El ranking lo calcula `nutrimatch.engine`. D1, D2 y D3 permanecen en el motor.

## Precios reales y monto de demostración

Open Prices (cruce exacto por código, 239 precios) y PROFECO Quién es Quién en los Precios (20 coincidencias de texto revisadas) son precios reales dentro del Parquet. El resto queda `UNAVAILABLE`. Al armar la ficha, si no hay observación, la API puede emitir un entero de demostración entre 12 y 180 pesos, determinista a partir del código, con procedencia `SYNTHETIC`. Ese monto no se escribe en el Parquet y no entra al ranking ni a los filtros. No hay un precio de mercado imputado.

## Explorar alternativas

`RankingService.alternatives` toma la `categoria_referencia` del producto, aplica el mismo ranking del perfil y devuelve hasta cinco productos de la banda de ranking. La interfaz lo muestra en la ficha, el carrito y las alertas. La persona puede abrir la ficha o sustituir el producto en el carrito.

El orden apoya la decisión según las preferencias declaradas.
