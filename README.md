# NutriMatch

Desarrollé NutriMatch para apoyar la decisión de compra de alimentos empacados en México con un resultado explicable y auditable.

> **Aviso.** NutriMatch no emite diagnósticos médicos. Compara productos empacados frente a un perfil que declara la propia persona y explica el porqué de cada resultado. No valora estados de salud, no prescribe dietas y no interpreta síntomas.

## Qué hace el sistema

La persona declara dieta, alergias, etiquetas que valora y el orden de tres prioridades. Busca un producto por nombre o por código de barras y recibe un ranking personalizado. Cada resultado muestra cuánto aportó cada dimensión, qué nutrientes pesaron, en qué percentil queda el producto dentro de su categoría y en qué estado están los datos.

El cálculo es determinista. Con los mismos datos de entrada, el motor devuelve siempre el mismo resultado. La capa de lenguaje es opcional y se limita a interpretar la pregunta y a narrar hechos que el motor ya calculó. Sin clave de API, la aplicación responde con plantillas deterministas.

## Catálogo operativo

La aplicación utiliza `datos/procesados/dataset_referencia_20261002.parquet`. Es la fuente de verdad del catálogo. La API lo abre en `Catalog.from_referencia()`. Ningún corte anterior lo sustituye.

| Indicador | Valor |
| --- | --- |
| Productos consolidados | 13 093 |
| Universo de partida, filtrado por país México | 16 851 |
| Calidad de información alta | 6 102 |
| Calidad de información insuficiente | 4 206 |
| Calidad de información media | 1 511 |
| Calidad de información baja | 1 274 |
| Universo puntuable | 5 864 |
| Precios reales | 259 |
| Open Prices, cruce exacto por código de barras | 239 |
| PROFECO Quién es Quién en los Precios, coincidencia de texto revisada | 20 |
| Resto del catálogo, sin observación de precio | 12 834 |

Los 13 093 productos salen del mismo export de Open Food Facts que las 16 851 filas con país México. Integré tres candados de ingesta, en este orden:

1. **No alimento.** Excluye 3 registros. Quedan 16 848.
2. **Integridad mínima.** Exige ingredientes, grupo NOVA o algún macronutriente mayor que cero. Excluye 3 737. Quedan 13 111.
3. **Identidad de nombre.** Excluye 18 registros sin un nombre utilizable. Quedan 13 093.

El universo puntuable reúne 5 864 productos bajo el umbral de inclusión técnica de al menos 4 percentiles válidos de los 8 nutrientes del núcleo y un subpuntaje de procesamiento calculable. El resto del catálogo sigue siendo buscable y consultable. Si la cobertura de las prioridades activas queda por debajo de la mitad del peso declarado, el producto se muestra en la banda de información insuficiente, separado del ranking.

El Parquet guarda 259 precios reales. Los 12 834 productos sin observación quedan con precio nulo y procedencia no disponible. Al responder la ficha, la API aplica un fallback dinámico de tipo `SYNTHETIC`: un monto de demostración derivado del código de barras, marcado como tal. Ese monto no entra al ranking ni se escribe en el dataset.

La variable de entorno `REFERENCIA_FILENAME` apunta a `dataset_referencia_20261002.parquet`. El mismo valor es el predeterminado de `src/nutrimatch/core/config.py`.

## Fuentes

- **Open Food Facts** aporta nutrientes, ingredientes, grupo NOVA, etiquetas y sellos frontales.
- **Open Prices** aporta precios en pesos mexicanos cruzados por el mismo código de barras.
- **PROFECO, Quién es Quién en los Precios,** aporta el precio de referencia de presentaciones cuya coincidencia de texto revisé. Ese precio informa. No puntúa y no filtra.

Las licencias y la cita están en [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md).

Para comprobar que el archivo local es el catálogo operativo:

```bash
shasum -a 256 datos/procesados/dataset_referencia_20261002.parquet
```

La huella esperada es `a621d471a2f47aa09ba481408d95a7a808fe84bd2fa7205c56fa050e1c66045b` (13 093 filas, 273 columnas). Está repetida en `datos/procesados/dataset_referencia_20261002_metadata.json`.

En el mismo directorio hay Parquet de septiembre. La aplicación no los abre. Algunos scripts de construcción y algunas pruebas sí. El detalle está en [`docs/datos.md`](docs/datos.md). `.gitignore` admite el archivo del 2 de octubre y su metadato, y deja fuera del alta nueva a los demás Parquet de `datos/procesados/`.

## Arquitectura

| Pieza | Elección | Función |
| --- | --- | --- |
| Lógica | Paquete `nutrimatch` | Un solo motor para los cuadernos de análisis y para la API |
| Interfaz | Angular (`frontend/`) | Explica el porqué de cada resultado y habla con FastAPI |
| API | FastAPI (`nutrimatch.api`) | Serializa los contratos de `schemas/` y no recalcula las tres dimensiones por su cuenta |
| Análisis | DuckDB sobre Parquet | Consulta el snapshot sin un servidor de base de datos |
| Estado de uso | SQLite en modo WAL | Historial y corridas de ranking, regenerables |
| Validación | pydantic v2 | Contratos explícitos de entrada y salida |

Organicé los datos en tres niveles:

1. **Export crudo de Open Food Facts.** Se descarga el CSV comprimido del día y permanece intacto. La fecha de descarga identifica la versión citada.
2. **Parquet derivado.** Universo de México, ya filtrado, con identidad, nutrición, precio resuelto y calidad de información. El análisis y la API leen de aquí.
3. **SQLite.** Perfil de servidor, historial, corridas de ranking y caché. Se puede borrar y reconstruir. El perfil activo, el carrito y la comparación de la interfaz viven en el navegador.

## Instalación

El entorno se gestiona con **[uv](https://docs.astral.sh/uv/)**. El archivo `.python-version` fija **Python 3.12.13**, la misma versión del runtime de Google Colab, para que el paquete se comporte igual en local y en los cuadernos. `pyproject.toml` mantiene `requires-python = ">=3.11"` como suelo de compatibilidad del paquete.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

make setup
cp .env.example .env
```

`make setup` descarga el intérprete, crea `.venv` e instala el paquete en modo editable con las herramientas de desarrollo. La dependencia de lenguaje es opcional:

```bash
uv pip install -e ".[dev,llm]"
```

En `.env`, el correo de `OFF_USER_AGENT` identifica las peticiones a Open Food Facts. `OPENAI_API_KEY` puede quedar vacía.

## Ejecución local

```bash
make api     # FastAPI en http://127.0.0.1:8000
make ui      # Angular en http://127.0.0.1:4200
make test    # pytest
make lint    # ruff
make help
```

Los targets usan `uv run`. La primera carga del catálogo precalcula la dimensión nutricional y puede tardar unos segundos. Cada corrida de ranking y el historial se guardan en `nutrimatch.db`, que no se versiona.

En local, Angular y FastAPI viven en orígenes distintos. El proxy de `frontend/proxy.conf.json` reenvía las rutas de la API al puerto 8000, y FastAPI autoriza `http://localhost:4200` y `http://127.0.0.1:4200`.

## Despliegue en Vercel

`vercel.json`, en la raíz, publica los dos procesos bajo el mismo dominio:

- La interfaz estática sale de `ng build` (`frontend/dist/frontend/browser`).
- FastAPI entra por `api/index.py`, que carga el mismo catálogo operativo.
- Las rutas de la API (`/meta`, `/search`, `/products`, `/catalog`, `/ranking`, `/cart`, `/events`, `/ai`) llegan a Python.
- El resto de las rutas llega a `index.html`, para que el enrutador de Angular resuelva la pantalla.

Como la interfaz y la API comparten dominio, el navegador trata las llamadas como mismo origen y no dispara un conflicto de CORS. Además, la API acepta los dominios `https://*.vercel.app` y los orígenes extra de `CORS_ALLOW_ORIGINS`, para el desarrollo local y las vistas previas.

El historial SQLite de la función se escribe en `/tmp`, porque el disco de la función es de solo lectura fuera de esa carpeta. El catálogo no depende de esa base.

Variables útiles en el proyecto de Vercel:

```bash
REFERENCIA_FILENAME=dataset_referencia_20261002.parquet
SNAPSHOT_ID=off_csv_20260929
OFF_USER_AGENT=NutriMatch/0.1.0 (tu-correo@ejemplo.com)
OPENAI_API_KEY=
```

`REFERENCIA_FILENAME` ya tiene ese valor en el código. Hace falta repetirla en el panel solo si se quiere señalar otro archivo.

## Mapa del repositorio

```
src/nutrimatch/       paquete instalable
  agents/             nota de los tres roles de lenguaje; la implementación está en ai/
  ai/                 capa de lenguaje opcional (POST /ai/ask)
  core/               configuración, registro y errores
  db/                 SQLite del historial
  domain/             modelos de dominio
  engine/             motor determinista
  providers/          Open Food Facts, Open Prices y PROFECO
  schemas/            contratos pydantic
  services/           catálogo, ficha, ranking y carrito
datos/
  snapshots/          export crudo (no se versiona el archivo grande)
  procesados/         Parquet operativo y tablas de apoyo
  cache/              caché local de APIs (no se versiona)
docs/                 atribución, diccionario y documentación técnica
notebooks/            análisis del universo, la transformación y la evaluación
frontend/             aplicación Angular
scripts/              ingesta, identidad, precios y cierre del dataset
api/                  entrada de FastAPI en Vercel
tests/                pruebas del motor, de la API y de la interfaz de datos
evaluacion/           conjunto de oro, parity-check y diagnóstico de cobertura
```

## Análisis

El análisis quedó registrado en este orden:

1. Ingesta del export, en `scripts/ingesta_off.py`.
2. Exploración del universo México, en `notebooks/02_eda_universo_mexico.ipynb`.
3. Transformación y saneamiento, en `notebooks/03_transformacion_score.ipynb`.
4. Modelo de recomendación, en `notebooks/04_modelo_recomendacion.ipynb`.
5. Evaluación, en `notebooks/05_evaluacion.ipynb`.
6. Precios reales de Open Prices y de PROFECO, en `scripts/piloto_precios_open_prices.py` y `scripts/materializar_precios_qqp.py`.
7. Interfaz Angular, API y capa de lenguaje en `nutrimatch.ai`.
8. Identidad de nombres y marcas, en `notebooks/08_re_eda_identidad.ipynb`.

Los criterios metodológicos están en [`AGENTS.md`](AGENTS.md). El detalle técnico está en [`docs/NutriMatch_Documentacion_Tecnica_Completa.md`](docs/NutriMatch_Documentacion_Tecnica_Completa.md). El diccionario de columnas está en [`docs/diccionario_dataset_referencia.md`](docs/diccionario_dataset_referencia.md).

## Motor, en una página

La persona ordena tres prioridades. Ese orden se convierte en pesos 0,50 / 0,33 / 0,17.

| Dimensión | Qué mide |
| --- | --- |
| D1 Nutrición | Azúcares, sal y grasa saturada (menos es mejor); fibra y proteína (más es mejor). Percentil dentro de la categoría de referencia. |
| D2 Procesamiento | Grupo NOVA en bandas de 25 puntos, afinado por el número de aditivos. |
| D3 Preferencias | Porcentaje de etiquetas valoradas que el producto presenta. |

El resultado es el promedio ponderado de las dimensiones que sí tienen dato. Si la cobertura queda por debajo de 0,5, el producto va a la banda de información insuficiente y el resultado queda vacío. Un dato ausente no se trata como cero. Alergia no apta o dieta incompatible excluyen el producto del listado. Alergia o dieta no verificable tienen su propia banda.

NutriMatch no utiliza aprendizaje supervisado porque el catálogo no contiene un target observado que permita entrenar y evaluar de manera científicamente válida un modelo de recomendación.

El detalle está en [`docs/mapa_proyecto.md`](docs/mapa_proyecto.md) y en [`AGENTS.md`](AGENTS.md).

## Qué hace cada pantalla

| Pantalla | Ruta | Qué muestra |
| --- | --- | --- |
| Inicio | `/` | Presentación de Nuti y escaneo de código |
| Preferencias | `/onboarding` y panel de perfil | Nombre, prioridades, dieta y alergias |
| Buscar | `/buscar` | Nombre o código de barras |
| Catálogo | `/catalogo` | Exploración por categoría, sin filtrar el universo puntuable |
| Para ti | `/recomendaciones` | Ranking del perfil |
| Ficha | `/producto/:code` | Nutrientes, bandas, procedencia y alternativas |
| Comparar | `/comparar` | Productos elegidos lado a lado |
| Carrito | `/carrito` | Plato del Bien Comer, categorías y alternativas |
| Alertas | `/alertas` | Sellos y porción, cuando el producto declara `serving_size` |
| Recetas | `/recetas` | Ideas a partir del carrito, con la capa de lenguaje |
| Historial | `/historial` | Eventos de uso guardados en SQLite |

Nuti informa. NutriMatch organiza. La persona decide.

## OpenAI, opcional

`POST /ai/ask` vive en `nutrimatch.ai`. Traduce la pregunta, redacta y comprueba que el texto cite hechos ya calculados. El modelo por defecto es `gpt-4o-mini`. Si `OPENAI_API_KEY` está vacía, o si el paquete `openai` no está instalado, la respuesta sale de plantillas deterministas. El lenguaje no calcula el ranking ni modifica D1, D2 o D3.

```bash
uv pip install -e ".[dev,llm]"
```

## Límites conocidos

- El catálogo es un corte de Open Food Facts, no el anaquel en tiempo real.
- La cobertura de alérgenos es baja. «Sin dato» se muestra como no verificable.
- 12 834 productos no tienen precio de mercado. La ficha puede mostrar un monto de demostración marcado `SYNTHETIC`. Ese monto no entra al orden ni se guarda en el Parquet.
- El precio informa. No puntúa y no filtra.
- Nutri-Score y los sellos frontales se muestran. Quedan fuera del puntaje.
- No hay diagnóstico médico.

## Qué queda fuera de Git

Secretos (`.env`), el entorno virtual, `node_modules`, la base `nutrimatch.db`, la caché de APIs y el export comprimido de Open Food Facts (1,28 GB en `datos/snapshots/`). El Parquet operativo sí entra: pesa 8,8 MB. La clasificación completa está en [`docs/datos.md`](docs/datos.md).

## Documentos

| Documento | Para qué |
| --- | --- |
| [`docs/mapa_proyecto.md`](docs/mapa_proyecto.md) | Mapa del sistema y estado para Git |
| [`docs/reproducibilidad.md`](docs/reproducibilidad.md) | Instalación y ejecución |
| [`docs/datos.md`](docs/datos.md) | Cada archivo de `datos/` |
| [`docs/decisiones.md`](docs/decisiones.md) | Decisiones que el código aplica |
| [`docs/checklist_pre_git.md`](docs/checklist_pre_git.md) | Lista previa a publicar el repositorio |
| [`AGENTS.md`](AGENTS.md) | Criterios ya aplicados del motor |
| [`docs/diccionario_dataset_referencia.md`](docs/diccionario_dataset_referencia.md) | Columnas del catálogo |

## Licencia

El código se publica con todos los derechos reservados; ver [`LICENSE`](LICENSE). Los datos de terceros se rigen por sus propias licencias; ver [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md).
