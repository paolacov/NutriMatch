# NutriMatch — documentación técnica

El mapa de carpetas, la clasificación de datos y los pasos de instalación están en [`mapa_proyecto.md`](mapa_proyecto.md), [`datos.md`](datos.md) y [`reproducibilidad.md`](reproducibilidad.md). Este archivo sigue siendo el recorrido técnico del sistema en producción.

Desarrollé NutriMatch como sistema de apoyo a la decisión de compra de alimentos empacados en México. El cálculo es determinista y la explicación forma parte del resultado. Este documento describe el flujo que queda en producción: datos, motor, API, interfaz y despliegue.

> NutriMatch no emite diagnósticos médicos. Compara productos frente a un perfil declarado y explica el resultado. No valora estados de salud, no prescribe dietas y no interpreta síntomas.

## 1. Flujo de una consulta

1. La persona completa el perfil en Angular: dieta, alergias, etiquetas valoradas y el orden de tres prioridades.
2. Busca por nombre, escribe un código, lo escanea con la cámara, o abre el catálogo.
3. Angular llama a FastAPI con rutas relativas (`/search`, `/products/{code}`, `/ranking`, `/cart/summary`, `/ai/ask`).
4. FastAPI carga el catálogo desde `datos/procesados/dataset_referencia_20261002.parquet` y aplica el motor.
5. La respuesta trae la banda, los subpuntajes, la cobertura, la procedencia de cada dato y, si no hay precio de mercado, el fallback de demostración.
6. La corrida de ranking y el historial se escriben en SQLite. El perfil, el carrito y la comparación de la sesión viven en el navegador.

La API serializa los contratos de `src/nutrimatch/schemas/`. No vuelve a inventar las fórmulas: la dimensión nutricional y las preferencias se resuelven en la petición; el procesamiento ya está materializado en el Parquet.

## 2. Catálogo operativo

Archivo: `datos/procesados/dataset_referencia_20261002.parquet`.

| Indicador | Valor medido |
| --- | --- |
| Filas | 13 093 |
| Columnas | 273 |
| Universo de partida (país México) | 16 851 |
| Tras excluir no alimentos | 16 848 (se excluyen 3) |
| Tras integridad mínima | 13 111 (se excluyen 3 737) |
| Tras identidad de nombre | 13 093 (se excluyen 18) |
| Universo puntuable | 5 864 |
| Calidad alta | 6 102 |
| Calidad media | 1 511 |
| Calidad baja | 1 274 |
| Calidad insuficiente | 4 206 |
| Precios reales | 259 |
| Open Prices (`exact_gtin`) | 239 |
| PROFECO (`text_reviewed`) | 20 |
| Sin observación de precio | 12 834 |
| Precios `SYNTHETIC` dentro del Parquet | 0 |

El archivo comprimido del export del 29 de septiembre de 2026 tiene el mismo SHA-256 que el del 19 de septiembre. La reducción de 16 851 a 13 093 la producen los tres candados de `scripts/ingesta_off.py`.

El metadato de tabla está en `datos/procesados/dataset_referencia_20261002_metadata.json`. El diccionario de columnas está en [`diccionario_dataset_referencia.md`](diccionario_dataset_referencia.md).

`src/nutrimatch/core/config.py` resuelve la ruta así:

- `REFERENCIA_FILENAME` vale `dataset_referencia_20261002.parquet` si el entorno no dice otra cosa.
- `SNAPSHOT_ID` vale `off_csv_20260929`.
- El directorio de procesados es `datos/procesados`, relativo a la raíz del repositorio.

## 3. Procedencia

Cada valor enriquecido lleva un estado: `REAL`, `DERIVED`, `IMPUTED`, `SYNTHETIC` o `UNAVAILABLE`.

El export de Open Food Facts es real por construcción. Los subpuntajes, los percentiles, la homologación del nombre, la corrección de escala de la sal y la cobertura son derivados. El catálogo operativo no contiene valores imputados. El precio de demostración es sintético y solo existe en la respuesta HTTP, cuando `price_status` es `UNAVAILABLE` y hay código de barras. Lo calcula `precio_demostracion_mxn` en `src/nutrimatch/engine/demo_price.py`: un entero entre 12 y 180, estable para el mismo código. La ficha lo etiqueta como dato de demostración. El ranking lo ignora.

La tabla `datos/procesados/observaciones_20260926.parquet` guarda lo que no viene del export: nombres recuperados en la ficha viva y precios. Varias filas por código y campo son válidas. La resolución elige la observación real más reciente. Si no hay ninguna, el estado es no disponible.

## 4. Motor

El paquete `nutrimatch.engine` concentra el cálculo. Los criterios completos están en [`../AGENTS.md`](../AGENTS.md). En resumen:

**Base.** Todo nutriente se evalúa por 100 g o 100 mL. Un ausente permanece NULL. Un valor físicamente imposible se marca y deja de entrar a los percentiles.

**Nutrición.** Cinco nutrientes con signo fijo: azúcares, sal y grasa saturada hacia abajo; fibra y proteína hacia arriba. El percentil se calcula dentro de la categoría de referencia. Esa categoría es la etiqueta más específica que alcance al menos 30 productos; si no alcanza, se sube un nivel en la jerarquía del propio producto. Cada nutriente exige al menos cinco pares con dato válido. Energía, grasa total y carbohidratos se muestran y no puntúan.

**Procesamiento.** El grupo NOVA define una banda de 25 puntos. El número de aditivos mueve el subpuntaje hacia el piso de esa banda. Si el número de aditivos falta, el ajuste deja el producto en el centro de su banda. Sin NOVA, la dimensión queda vacía.

**Preferencias.** Porcentaje de etiquetas valoradas por la persona que el producto presenta.

**Pesos.** El orden de las tres prioridades se traduce en 0,50, 0,33 y 0,17. El resultado final promedia solo las dimensiones con dato. Por debajo de una cobertura de 0,5, el resultado es NULL y el producto sale del ranking.

**Universo puntuable.** Al menos cuatro percentiles válidos del núcleo de ocho nutrientes y procesamiento calculable. Son 5 864 productos. El resto se puede buscar y abrir en ficha.

**Bandas, en orden exclusivo.** Excluido por alergia no apta o dieta incompatible; no verificable; información insuficiente; ranking.

**Carrito.** Promedio por 100 g. Ponderación por gramos solo si todos los productos declaran cantidad. Porcentajes por grupo con denominador igual al número de productos. Sin categoría mapeable, el producto queda en «no clasificado».

## 5. Precios

Integré dos fuentes reales y un fallback de respuesta.

Open Prices se consulta en `nutrimatch.providers.open_prices_api` con `currency=MXN` y se cruza por el código de barras. PROFECO se consulta en `nutrimatch.providers.qqp_api` contra el datastore público. Su portal responde 403 a un agente que no parece un navegador; el cliente de este proveedor envía un agente de navegador. El precio de PROFECO que entra al catálogo pasó por revisión de la coincidencia de texto. Se muestra como precio de referencia, con método `text_reviewed` y la confianza del cruce. No es un precio estimado por el sistema.

`scripts/cerrar_dataset_operativo.py` arma el Parquet de producción a partir del corte del 29 de septiembre, de la tabla de observaciones y de los indicadores de calidad. Rechaza el archivo si encuentra un precio sintético materializado.

## 6. Capa de lenguaje

El código vigente está en `src/nutrimatch/ai/` y responde en `POST /ai/ask`.

- El planner traduce la pregunta a una operación ya definida.
- El critic es determinista: contrasta el texto con hechos calculados.
- La narración redacta esos hechos.
- Sin `OPENAI_API_KEY` no hay llamada de red. La respuesta sale de plantillas.
- El identificador de la persona no viaja a un proveedor externo.

El paquete `src/nutrimatch/agents/` solo documenta esos tres roles. No calcula nutrición, procesamiento, preferencias ni precio.

## 7. API

`src/nutrimatch/api/app.py` construye la aplicación con `create_app`. Rutas:

| Método | Ruta | Uso |
| --- | --- | --- |
| GET | `/meta` | Snapshot, versión del motor y conteos |
| GET | `/search` | Búsqueda por texto |
| GET | `/products` | Varias fichas por códigos |
| GET | `/products/{code}` | Ficha |
| GET | `/catalog/categories` | Categorías navegables |
| GET | `/catalog/products` | Página del catálogo |
| POST | `/ranking` | Ranking del perfil |
| POST | `/ranking/explain` | Explicación de un producto |
| POST | `/cart/summary` | Resumen del carrito |
| GET, POST | `/events` | Historial |
| POST | `/ai/ask` | Pregunta en lenguaje natural |

En local, el middleware de CORS autoriza `http://localhost:4200` y `http://127.0.0.1:4200`. También autoriza `https://*.vercel.app` y los orígenes de `CORS_ALLOW_ORIGINS`. Los métodos permitidos son GET, POST, HEAD y OPTIONS. No se habilitan credenciales de cookie, porque el perfil de la interfaz no viaja en una sesión de servidor.

## 8. Interfaz

Angular 20, en `frontend/`. Rutas de pantalla: inicio, onboarding, buscar, catálogo, producto, recomendaciones, comparar, carrito, alertas, recetas e historial. Esas rutas están en español y no coinciden con las rutas inglesas de la API, así que el enrutador de Vercel puede separarlas sin ambigüedad.

El desarrollo usa `frontend/proxy.conf.json` hacia el puerto 8000. La build de producción deja archivos estáticos en `frontend/dist/frontend/browser`.

### Cámara y código de barras

El inicio monta `app-barcode-scan`, en `frontend/src/app/shared/barcode-scan/barcode-scan.ts`. La misma pieza aparece en `/buscar?modo=escanear`. La cámara y la lectura ocurren en el navegador. El servidor solo recibe el código ya leído, por `GET /products/{code}`.

El permiso sale del clic en **Escanear**. Dentro de ese clic llamo a `navigator.mediaDevices.getUserMedia` con video y sin audio. `facingMode: environment` pide la cámara trasera del teléfono; en una computadora el navegador usa la cámara disponible. El gesto de la persona es lo que autoriza el permiso: la llamada tiene que nacer del clic, porque el navegador rechaza una petición de cámara que aparece sola.

El elemento `<video>` se crea cuando el permiso ya se concedió. Guardo el `MediaStream` en una señal y un `effect` se lo asigna a `srcObject` en cuanto el video existe en la página. Luego llama a `play()`. El video lleva `autoplay`, `muted` y `playsinline` para que el teléfono lo muestre dentro de la página. Al abrirse, la página se desplaza hasta el recuadro para que el visor y el campo del código queden por encima de la barra inferior.

La lectura usa `BarcodeDetector`, la API del propio navegador. La construyo al crear el componente con los formatos `ean_13`, `ean_8`, `upc_a`, `upc_e` y `code_128`. Un temporizador consulta el video cada 280 milisegundos, y solo cuando ya hay un cuadro (`readyState` de al menos 2). De cada lectura me quedo con el primer texto que, ya sin letras ni espacios, tiene entre 8 y 14 dígitos. Ese intervalo cubre EAN-8, UPC-A y EAN-13.

Con ese código consulto `ProductRepository.byCode`, que pide `GET /products/{code}`. Si el catálogo tiene el producto, detengo la cámara y abro `/producto/{code}`. Si no está, lo digo en la página y la lectura continúa. Una bandera evita lanzar dos consultas a la vez. Un contador de ciclo descarta los cuadros que llegan después de cerrar la cámara o de encontrar un código.

Si el navegador no tiene `getUserMedia`, o la persona niega el permiso, dejo el campo para escribir el código. El mismo campo está bajo el visor mientras la cámara está abierta. Si `BarcodeDetector` no existe o el constructor falla, la cámara se muestra y el código se escribe a mano: Chrome y el resto de navegadores Chromium leen las barras; un navegador sin esa API enseña el video y espera los dígitos.

**Cerrar cámara**, salir de la pantalla y destruir el componente llaman a `stop()` en cada pista del flujo. Así se apaga el indicador de cámara del navegador. La cámara solo se entrega en un contexto seguro: `https` o `localhost`.

## 9. Despliegue

`vercel.json` define dos construcciones:

1. `@vercel/static-build` sobre `frontend/package.json`. El script `vercel-build` instala las herramientas de compilación y ejecuta `ng build`. El directorio publicado es `dist/frontend/browser`.
2. `@vercel/python` sobre `api/index.py`. Ese módulo añade `src/` al camino de importación y expone `app = create_app()`.

Las peticiones a `/meta`, `/search`, `/products`, `/catalog`, `/ranking`, `/cart`, `/events` y `/ai` se entregan a FastAPI con la ruta original, para que los decoradores de la API coincidan. Cualquier otra ruta con archivo estático se sirve tal cual. El resto cae en `index.html`.

La función incluye `src/nutrimatch/**` y `datos/procesados/dataset_referencia_20261002.parquet`. Las dependencias de ejecución están en `requirements.txt`. Matplotlib, seaborn y plotly quedan fuera de esa lista: los usa el análisis, no la API.

En Vercel, `NUTRIMATCH_DB_PATH` del entorno local no se usa. `Settings.db_path()` detecta la variable `VERCEL` y escribe `nutrimatch.db` en `/tmp`.

## 10. Cómo reproduzco el catálogo

```bash
make setup
make ingest-off
make homologar-identidad
make piloto-precios
make materializar-qqp CSV=datos/procesados/piloto_qqp_candidatos_20260926.csv
uv run python scripts/construir_dataset_referencia.py
uv run python scripts/cerrar_dataset_operativo.py
```

`make api` y `make ui` levantan el sistema ya cerrado. `make test` ejecuta la batería de pytest del motor, de la API y de los contratos.

## 11. Evaluación

- Conjunto de oro de 13 códigos reales, en `evaluacion/` y `tests/test_golden_set.py`.
- Contraste de Spearman entre la dimensión nutricional y `nutriscore_score`, con umbral de sanidad −0,3.
- Diagnóstico de cobertura por combinación de dimensiones ausentes.

El ranking es un motor de reglas, evidencia disponible y cobertura. El catálogo no contiene un desenlace observado de «recomendación correcta» con el que entrenar y evaluar un modelo supervisado. Por eso el resultado se calcula y se explica con las tres dimensiones, no con un modelo entrenado.

## 12. Fuentes y cita

Open Food Facts (base ODbL, contenidos DbCL, imágenes CC BY-SA), Open Prices y PROFECO Quién es Quién en los Precios. La atribución visible también está en la interfaz. El formato de cita está en [`ATTRIBUTION.md`](ATTRIBUTION.md).
