# Mapa del proyecto NutriMatch

Auditoría del árbol tal como está el 3 de octubre de 2026. No cambia el motor, el dataset ni las tecnologías.

## A. Resumen

NutriMatch apoya la decisión de compra de alimentos empacados en México. La persona declara preferencias. El motor ordena productos con tres dimensiones reproducibles y explica el resultado. Nuti informa, NutriMatch organiza y la persona decide.

El cálculo vive en el paquete `nutrimatch`. La API es FastAPI. La interfaz es Angular. El catálogo es un Parquet. El historial de uso es SQLite y se puede borrar.

NutriMatch no utiliza aprendizaje supervisado porque el catálogo no contiene un target observado que permita entrenar y evaluar de manera científicamente válida un modelo de recomendación.

## B. Arquitectura

El flujo que el código ejecuta es este:

```text
Open Food Facts (export CSV)  +  Open Prices  +  PROFECO Quién es Quién en los Precios
        ↓
scripts/ingesta_off.py y scripts de identidad, nutrición, observaciones y precios
        ↓
datos/procesados/dataset_referencia_20261002.parquet
        ↓
nutrimatch.engine  (D1 en la petición; D2 ya está en el Parquet; D3 en la petición)
        ↓
nutrimatch.services  (catálogo, ficha, ranking, carrito, alternativas)
        ↓
FastAPI  nutrimatch.api.app
        ↓
Angular  frontend/  (proxy local hacia el puerto 8000)
        ↓
persona
```

`nutrimatch.ai` se cruza solo en `POST /ai/ask`. Lee hechos ya calculados. Si no hay clave, usa plantillas.

Comprobado en código:

- `create_app()` llama a `Catalog.from_referencia()` si no recibe un catálogo de prueba.
- `Settings.referencia_filename` vale `dataset_referencia_20261002.parquet` si el entorno no dice otra cosa.
- En esta máquina `.env` repite ese nombre y `get_settings()` resuelve la ruta a `datos/procesados/dataset_referencia_20261002.parquet`.
- Angular no calcula D1, D2 ni D3. `frontend/src/app/core/data/product.repository.ts` llama a la API.
- `Catalog.from_parquet()` (matriz + snapshot crudo) sigue en el código para pruebas y linaje. La aplicación HTTP no lo usa: usa `from_referencia()`.

## C. Estructura de carpetas

| Ruta | Qué es | ¿Hace falta para ejecutar? | Git |
| --- | --- | --- | --- |
| `src/nutrimatch/engine/` | Motor determinístico | Sí | Dentro |
| `src/nutrimatch/services/` | Catálogo, ficha, ranking, carrito | Sí | Dentro |
| `src/nutrimatch/api/` | FastAPI | Sí | Dentro |
| `src/nutrimatch/schemas/` | Contratos pydantic | Sí | Dentro |
| `src/nutrimatch/core/` | Settings, errores | Sí | Dentro |
| `src/nutrimatch/db/` | SQLite de uso | Sí, el código. El archivo `.db` no | Código dentro; `nutrimatch.db` fuera |
| `src/nutrimatch/ai/` | Lenguaje opcional | El código sí. La clave no | Dentro |
| `src/nutrimatch/agents/` | Nota de los tres roles. La implementación está en `ai/` | No aporta cálculo | Dentro |
| `src/nutrimatch/providers/` | Clientes de OFF, Open Prices y PROFECO | Solo para ingesta y fichas vivas | Dentro |
| `src/nutrimatch/domain/` | Modelos de dominio | Lo usa el paquete | Dentro |
| `src/nutrimatch/eda/` | Figuras del análisis | No | Dentro |
| `frontend/` | Angular | Sí | Dentro, sin `node_modules`, `.angular` ni `dist` |
| `api/` | Entrada de Vercel (`index.py`, `requirements.txt`) | Solo en Vercel | Dentro |
| `scripts/` | Ingesta y cierre del dataset | No, para levantar la app ya cerrada | Dentro |
| `notebooks/` | Análisis. 02, 03, 04, 05 y 08 | No | Dentro |
| `tests/` | pytest | No para ejecutar | Dentro |
| `evaluacion/` | Conjunto de oro, parity-check, cobertura | Lo importan pruebas y notebooks | Dentro |
| `docs/` | Documentación | No para ejecutar | Markdown dentro. El PDF generado queda fuera |
| `datos/procesados/*.parquet` | Catálogo y linaje | El operativo, sí | Dentro. Ver [`datos.md`](datos.md) |
| `datos/snapshots/*.csv.gz` | Export crudo | No | Fuera |
| `datos/cache/` | Caché de APIs | No | Fuera |
| `ui/` | Solo `.gitkeep` | No | El marcador puede quedarse. No es la interfaz |
| Raíz | `pyproject.toml`, `uv.lock`, `Makefile`, `vercel.json`, `.env.example`, `LICENSE` | Sí, salvo Vercel | Dentro |
| `.env` | Secretos y rutas locales | En la máquina, sí. En Git, no | Fuera |
| `prueba-codigo*.png` | Capturas locales de códigos de barras | No | Fuera |

## D. Datos

Fuentes:

- Open Food Facts: nutrientes, ingredientes, NOVA, etiquetas, sellos, imágenes de producto.
- Open Prices: 239 precios en MXN por código de barras.
- PROFECO: 20 precios de referencia por texto revisado.

Archivo que sirve la aplicación: `datos/procesados/dataset_referencia_20261002.parquet`.

Huella SHA-256: `a621d471a2f47aa09ba481408d95a7a808fe84bd2fa7205c56fa050e1c66045b`.

La tabla archivo por archivo está en [`datos.md`](datos.md).

SQLite (`nutrimatch.db`) guarda corridas y eventos. Se crea solo. No se versiona.

## E. Backend

FastAPI 0.141.1 en el lock. Entrada: `nutrimatch.api.app:create_app`.

| Método | Ruta | Servicio | Qué devuelve |
| --- | --- | --- | --- |
| GET | `/meta` | `Catalog` | `snapshot_id`, versión, productos y universo puntuable |
| GET | `/search?q=&limit=` | `filtrar_por_query` | Hasta 40 fichas por defecto, tope 100 |
| GET | `/products?codes=` | catálogo | Fichas de los códigos pedidos |
| GET | `/products/{code}` | `detalle_desde_fila` | Ficha. 404 si el código no está |
| GET | `/catalog/categories` | `catalog_browse` | Categorías del catálogo completo |
| GET | `/catalog/products` | `paginar_catalogo` | Página filtrada por texto y categoría. No recorta por universo puntuable |
| POST | `/ranking` | `RankingService.rank` | Bandas y, de paso, guarda la corrida y un evento |
| POST | `/ranking/explain` | `RankingService.explain` | Un producto con explicación |
| POST | `/ranking/alternatives` | `RankingService.alternatives` | Hasta 5 productos del mismo grupo, banda de ranking |
| POST | `/cart/summary` | `resumir_codes` | Plato del Bien Comer y categorías |
| GET | `/events` | `EventLogRepository` | Historial |
| POST | `/events` | `EventLogRepository` | Alta de un evento |
| POST | `/ai/ask` | `nutrimatch.ai.service.preguntar` | Texto de lenguaje o plantilla |

Configuración: `src/nutrimatch/core/config.py`. Lee `.env` de la raíz. No imprime la clave.

Esquemas: `src/nutrimatch/schemas/` (`product`, `ranking`, `catalog`, `cart`, `profile`, `event`).

## F. Engine

Entrada: una fila del catálogo y un perfil (`priority_order`, dieta, alergias, etiquetas valoradas).

Filtros, en este orden, una sola banda por producto (`asignar_banda`):

1. Excluido. Alergia no apta o dieta incompatible. No se lista. Solo se cuenta.
2. No verificable. Alergia o dieta sin evidencia suficiente. No se mezcla con apto.
3. Información insuficiente. Cobertura menor que 0,5. El resultado queda vacío.
4. Ranking. El resto, de mayor a menor resultado.

Calidad física: valores fuera de rango dejan de aportar a percentiles. El dato crudo sigue en la ficha. La sal se corrige solo cuando su razón con el sodio del mismo producto es aproximadamente 2,5 y el valor dividido entre 1 000 cae en rango. Si no, permanece fuera de rango.

Universo puntuable: `d2` presente y al menos 4 de 8 percentiles del núcleo. En el operativo son 5 864 de 13 093. Es una marca previa al perfil. Un producto fuera de ese universo sigue siendo buscable. Puede recibir resultado si la cobertura del perfil alcanza 0,5 con las dimensiones que sí tiene.

D1. Cinco nutrientes: azúcares, sal y grasa saturada con signo negativo; fibra y proteína con signo positivo. Promedio de los que tienen percentil. Energía, grasa total y carbohidratos se muestran y no entran. Categoría de referencia: etiqueta más específica de `categories_tags` con al menos 30 productos; si no, se sube un nivel. Cada percentil pide al menos 5 productos con dato en esa categoría.

D2. NOVA 1 en 75–100, NOVA 2 en 50–75, NOVA 3 en 25–50, NOVA 4 en 0–25. Los aditivos empujan hacia el piso de la banda, hasta el percentil 95 de aditivos del grupo 4. Si faltan aditivos, se resta media banda (12,5) y el producto queda al centro. Sin NOVA, D2 es NULL. D2 ya está en el Parquet.

D3. Porcentaje de etiquetas valoradas presentes en `labels_tags`. Si la persona no eligió etiquetas, o si el producto no trae etiquetas, D3 es NULL.

Pesos. El orden de tres prioridades reparte 3, 2 y 1 y se normaliza: 0,50 / 0,33 / 0,17.

Resultado. Suma de peso por subpuntaje, dividida entre la suma de los pesos disponibles. La dimensión ausente no vale cero.

Cobertura. Peso con dato dividido entre peso total. Umbral 0,5.

Calidad de información (`data_quality_level`): promedio de siete componentes de disponibilidad (nutrición, ingredientes, categoría, NOVA, aditivos, etiquetas, coherencia). Insuficiente por debajo de 0,25, baja por debajo de 0,50, media por debajo de 0,75, alta en adelante. No entra al resultado.

Nutri-Score se muestra como contraste. Los sellos mexicanos se muestran y alimentan alertas. El precio se muestra. Los tres quedan fuera del resultado.

## G. Frontend

Angular 20, Tailwind 4, rutas en `frontend/src/app/app.routes.ts`. Salvo `/onboarding`, las pantallas pasan por `requireOnboarding`.

| Pantalla | Ruta | Entrada | Qué hace | Datos | Endpoint |
| --- | --- | --- | --- | --- | --- |
| Inicio | `/` | Cámara o navegación | Presenta a Nuti y permite escanear | Código leído | La ficha siguiente usa `/products/{code}` |
| Preferencias | `/onboarding` y panel | Nombre, metas, orden de focos, dieta y alergias | Guarda el perfil en el navegador. El precio se puede considerar y el propio texto dice que no cambia el ranking | `localStorage` | El perfil viaja en el cuerpo de `/ranking` y `/ai/ask` |
| Buscar | `/buscar` | Texto o código | Lista coincidencias | Catálogo operativo | `GET /search` |
| Catálogo | `/catalogo` | Categoría y texto | Hojea el catálogo completo | Categorías del Parquet | `GET /catalog/categories`, `GET /catalog/products` |
| Para ti | `/recomendaciones` | Perfil | Ranking personalizado | Perfil + catálogo | `POST /ranking` |
| Ficha | `/producto/:code` | Código | Nutrientes, bandas, procedencia, precio y alternativas | Fila del Parquet | `GET /products/{code}`, `POST /ranking/explain`, `POST /ranking/alternatives` |
| Comparar | `/comparar` | Códigos elegidos en el navegador | Contraste lado a lado | Fichas | `GET /products?codes=` |
| Carrito | `/carrito` | Códigos del carrito local | Resumen por Plato del Bien Comer y por categoría. Alternativas por producto | Códigos | `POST /cart/summary`, `POST /ranking/alternatives` |
| Alertas | `/alertas` | Carrito | Sellos y porción cuando hay `serving_size`. Alternativas | Fichas del carrito | `GET /products`, alternativas |
| Recetas | `/recetas` | Carrito y perfil | Ideas de preparación | Hechos del carrito | `POST /ai/ask` |
| Historial | `/historial` | — | Lista eventos de uso | SQLite | `GET /events` |

La navegación principal también incluye Comparar, Alertas, Recetas e Historial. El dock móvil incluye el carrito.

Explorar alternativas, en `RankingService.alternatives` y en el componente `cart-alternatives`:

- El producto inicial es el de la ficha, el del carrito o el de la alerta.
- El grupo es `categoria_referencia`.
- Se puntúan los demás productos de ese grupo con el perfil actual y el mismo motor.
- Entran los de la banda de ranking. Se muestran cinco, con el total disponible.
- Se ven nombre, marca, precio con su tipo de procedencia, resultado y banda.
- La persona abre la ficha o sustituye el producto en el carrito.
- Si no hay categoría, o si nadie más entra al ranking, la pantalla lo dice y el carrito no cambia.

## H. Integraciones externas

| Integración | Dónde | Variable | Si falta |
| --- | --- | --- | --- |
| Open Food Facts, export | `scripts/ingesta_off.py` | `OFF_CSV_EXPORT_URL`, `OFF_USER_AGENT` | La app sigue con el Parquet ya cerrado |
| Open Food Facts, ficha viva | `providers/off_product_api.py` | `OFF_USER_AGENT`, `OFF_BASE_URL` | La ficha del catálogo no depende de esa llamada |
| Open Prices | `providers/open_prices_api.py` | User-Agent de OFF | Los 239 precios ya están en el Parquet |
| PROFECO | `providers/qqp_api.py` | User-Agent de navegador, solo para ese portal | Los 20 precios ya están en el Parquet |
| OpenAI | `nutrimatch.ai.client` | `OPENAI_API_KEY`, opcional `OPENAI_MODEL` | Plantillas deterministas |
| Vercel | `vercel.json`, `api/index.py` | Las mismas variables en el panel | El despliegue es aparte de la ejecución local |

USDA FoodData Central no es una fuente. Ver [`ATTRIBUTION.md`](ATTRIBUTION.md).

## I. Reproducibilidad

Pasos exactos, versiones y comprobación del Parquet: [`reproducibilidad.md`](reproducibilidad.md).

Variables de `.env.example`:

| Variable | Uso | Obligación |
| --- | --- | --- |
| `OFF_USER_AGENT` | Identifica las peticiones a Open Food Facts | Necesaria si se llama a OFF. Hay un ejemplo con correo ficticio |
| `OFF_BASE_URL` | Producción `https://world.openfoodfacts.org` | Tiene default en la plantilla |
| `OFF_CSV_EXPORT_URL` | Export diario | Solo para reingestar |
| `SNAPSHOT_DATE` | La escribe la ingesta | Opcional hasta ingerir |
| `NUTRIMATCH_DB_PATH` | Ruta de SQLite. Default `nutrimatch.db` | Opcional |
| `REFERENCIA_FILENAME` | Nombre del Parquet. Default el operativo | Opcional si el archivo tiene el nombre default |
| `SNAPSHOT_ID` | `off_csv_20260929` | Opcional; el default del código es ese |
| `PROCESSED_DATA_DIR` | Carpeta de Parquet. Default `datos/procesados` | Opcional. Comentada en la plantilla |
| `CORS_ALLOW_ORIGINS` | Orígenes extra, separados por comas | Opcional. Localhost:4200 ya está en el código |
| `OPENAI_API_KEY` | Lenguaje | Opcional. Vacía activa las plantillas |
| `OPENAI_MODEL` | Default `gpt-4o-mini` | Opcional |

El número de resultados lo fija `top_n` en el cuerpo de `POST /ranking`. El esquema trae 25 por defecto. `Settings` no tiene un campo que lo sustituya: `ranking_top_n` estaba definido y el servicio no lo leía, así que se quitó de la configuración.

## J. Git

El repositorio Git ya existe, rama `main`, sin remoto. `.env` no está en el índice ni en el historial.

Dentro:

- Código, pruebas, notebooks, documentación Markdown, `uv.lock`, `package-lock.json`, `.env.example`.
- `datos/procesados/dataset_referencia_20261002.parquet` y `dataset_referencia_20261002_metadata.json`.
- CSV de `datos/procesados/re_eda_20260926/`.
- Metadatos `datos/snapshots/*/_metadata.json`.

Fuera:

- `.env` y cualquier clave.
- `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`.
- `frontend/node_modules/`, `frontend/.angular/`, `frontend/dist/`.
- `nutrimatch.db` y sus archivos WAL.
- `datos/cache/`, `datos/precios_qqp/`, los gzip de `datos/snapshots/`.
- Figuras PNG generadas.
- `prueba-codigo*.png`.
- `docs/NutriMatch_Documentacion_Tecnica_Completa.pdf` (sale de `scripts/render_documentacion_pdf.py`).

El operativo todavía no está en el último commit. Hay que añadirlo en el commit que publique el árbol, junto con el frontend y `api/`, que también están sin seguimiento. Esta auditoría no hizo `git add` ni `git push`.

## K. Limitaciones

- Corte estático de Open Food Facts, no el anaquel del día.
- Alérgenos con poca cobertura: sin dato es no verificable, y así se muestra.
- 12 834 productos sin precio de mercado. El monto `SYNTHETIC` es demostración en la respuesta de la ficha.
- El precio, Nutri-Score y los sellos no puntúan.
- La mayoría de los productos con NOVA en México caen en el grupo 4. D2 afina con aditivos dentro de la banda y no promete separar el catálogo en cuatro grupos equilibrados.
- No hay modelo supervisado ni desenlace observado de «esta compra fue la correcta».
- Las pruebas de Python pasaron en esta auditoría: 338 passed, 1 skipped (el smoke en vivo de OpenAI). Angular compiló con `ng build --configuration development`. No se recorrió el navegador ni se dejó la API en un puerto.
- `scripts/` y algunas pruebas siguen abriendo cortes de septiembre. La API no.

## L. Estado final

Listo para documentar y para preparar el commit, con observaciones.

Listo:

- El motor, la API y Angular están en el árbol y coinciden con esta descripción.
- El dataset que abre la aplicación está identificado, presente y con la huella del metadato.
- `.env.example` no contiene claves. `.env` está ignorado.
- `.gitignore` deja fuera secretos, cachés, SQLite y el export de 1,2 GB, y deja entrar el Parquet operativo.

Pendiente antes de publicar:

- Incluir en el commit el Parquet operativo y el código que hoy figura como no seguido (frontend, `api/`, pruebas nuevas, docs).
- El remoto no existe.
- Revisar el resultado de pytest en el checklist.
- Confirmar en el portal de PROFECO el texto CC-BY 4.0 que ya cita `AGENTS.md`.

## Limpieza, sin borrar

| Elemento | Clase | Motivo |
| --- | --- | --- |
| `src/`, `frontend/src`, `tests/`, `evaluacion/`, `api/` | A conservar | Código vigente |
| Notebooks 02, 03, 04, 05 y 08 | A conservar | Análisis. No arrancan la app. El README los cita |
| `scripts/` | A conservar | Reconstruyen el catálogo. No son código muerto |
| `src/nutrimatch/agents/` | A conservar | Documenta los roles que implementa `ai/` |
| `ui/.gitkeep` | A conservar | Marcador. La interfaz es `frontend/` |
| Markdown de `docs/` y `AGENTS.md` | A conservar | Criterios y auditoría |
| PDF técnico | C ignorar en Git | Generado. Comando en `scripts/render_documentacion_pdf.py` |
| Figuras PNG | C ignorar | Salida de `scripts/figuras_universo_operativo.py` |
| `prueba-codigo*.png` | C ignorar | Capturas locales de prueba manual |
| `.env`, `.venv`, `node_modules`, cachés, `nutrimatch.db`, gzip, `datos/cache` | C ignorar | Secretos, entornos o insumos enormes |
| `.cursorignore` vacío | C ignorar en Git | Archivo vacío |
| `ranking_top_n` en `Settings` | Eliminado de la configuración | El servicio no lo leía. El tope es `top_n` del request |
