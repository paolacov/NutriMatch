# Reproducibilidad

Estas versiones salen de los archivos del repositorio y de la máquina en la que se revisó el árbol el 3 de octubre de 2026. No son estimaciones.

## Requisitos

| Pieza | Versión en el proyecto | Dónde está |
| --- | --- | --- |
| Sistema | El desarrollo local está en macOS. El código no fija un sistema operativo. | — |
| Python del paquete | `>=3.11` | `pyproject.toml` |
| Python fijado para uv y Colab | `3.12.13` | `.python-version` |
| Intérprete del `.venv` local | `3.12.13` | verificado con `.venv/bin/python` |
| uv | El `Makefile` exige uv. En esta máquina: `0.12.17` | no está pinneado en el repo |
| Node | Los paquetes de Angular 20 en `frontend/package-lock.json` piden `^20.19.0 \|\| ^22.12.0 \|\| >=24.0.0` | `package-lock.json` |
| Node en esta máquina | `v24.21.0` | `node -v` |
| npm en esta máquina | `11.19.0` | `npm -v` |
| Angular | `^20.3.0`; CLI de desarrollo `@angular/cli` `^20.3.37` | `frontend/package.json` |
| FastAPI pinneado por el lock | `0.141.1` | `uv.lock` |
| Uvicorn pinneado | `0.53.0` | `uv.lock` |
| Pydantic pinneado | `2.13.5` | `uv.lock` |
| pandas pinneado | `3.0.6` | `uv.lock` |
| DuckDB pinneado | `1.5.5` | `uv.lock` |

`requirements.txt` y `api/requirements.txt` listan las dependencias de la función de Vercel sin pin de parche. El lock de uv es la referencia de versiones del entorno local.

La dependencia `openai` es opcional (`[llm]`). Matplotlib, seaborn y plotly están en `pyproject.toml` para el análisis. La lista de Vercel no los incluye.

## Dataset que tiene que existir antes de arrancar

Archivo: `datos/procesados/dataset_referencia_20261002.parquet`.

1. Nombre exacto: `dataset_referencia_20261002.parquet`.
2. Carpeta: `datos/procesados/`, en la raíz del repositorio.
3. Cómo obtenerlo: forma parte de los Parquet de `datos/procesados/` que el `.gitignore` deja entrar al repositorio. Al clonar, el archivo viaja con el código si el commit lo incluye. En este árbol, antes de ese commit, el archivo ya está en disco y su SHA-256 coincide con el metadato.
4. El export CSV de Open Food Facts no hace falta para ejecutar la aplicación. Hace falta para reconstruir el universo desde cero (`make ingest-off`).
5. Verificación:

```bash
shasum -a 256 datos/procesados/dataset_referencia_20261002.parquet
```

Huella esperada:

```text
a621d471a2f47aa09ba481408d95a7a808fe84bd2fa7205c56fa050e1c66045b
```

Conteo esperado: 13 093 filas, 273 columnas, 5 864 con `universo_puntuable`. El metadato está en `datos/procesados/dataset_referencia_20261002_metadata.json`.

`REFERENCIA_FILENAME` en `.env` y el default de `config.py` apuntan a ese nombre. Si el archivo no está, `Catalog.from_referencia()` lanza `CatalogNotFoundError` al crear la aplicación.

Ese Parquet es el que utiliza la aplicación. Los cortes de septiembre que están en el mismo directorio no lo sustituyen. La aplicación no los abre. Los scripts y las pruebas que sí los nombran están en [`datos.md`](datos.md).

## Instalación del backend

Requisito previo: [uv](https://docs.astral.sh/uv/).

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
make setup
cp .env.example .env
```

`make setup` ejecuta `uv python install`, `uv venv` y `uv pip install -e ".[dev]"`.

Lenguaje opcional:

```bash
uv pip install -e ".[dev,llm]"
```

## Instalación del frontend

```bash
cd frontend
npm install
```

`package-lock.json` fija el árbol de npm. En esta máquina `frontend/node_modules` ya existe.

## Ejecución

Dos terminales, desde la raíz del repositorio.

```bash
make api
```

Eso es `uv run uvicorn nutrimatch.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000`.

```bash
make ui
```

Eso es `cd frontend && npm start`. Angular usa `frontend/proxy.conf.json` y reenvía `/meta`, `/search`, `/products`, `/catalog`, `/ranking`, `/cart`, `/events` y `/ai` a `http://127.0.0.1:8000`.

Abrir `http://127.0.0.1:4200`.

Comprobación de la API, con el backend ya en marcha:

```bash
curl -s http://127.0.0.1:8000/meta
```

La primera carga del catálogo calcula D1 en memoria y puede tardar unos segundos. La respuesta debe traer `n_products` 13093.

## Otros targets del Makefile

| Target | Qué hace |
| --- | --- |
| `make help` | Lista los targets |
| `make test` | `uv run pytest` |
| `make lint` | `uv run ruff check .` |
| `make ingest-off` | Descarga el export de Open Food Facts y construye el snapshot de México |
| `make ingest-qqp` | Imprime cómo reconstruir el Parquet de PROFECO. No descarga |
| `make homologar-identidad` | `scripts/homologar_identidad.py` |
| `make piloto-precios` | Precios de Open Prices |
| `make piloto-qqp` | Candidatos PROFECO en CSV |
| `make materializar-qqp CSV=ruta` | Escribe el Parquet de PROFECO desde un CSV revisado |
| `make eda` | Imprime las rutas de los notebooks 02 y 08. No abre Jupyter |
| `make ui-angular` | Alias de `make ui` |

Pruebas del frontend, si hay Chrome para Karma:

```bash
cd frontend && npm test
```

Esa batería no se ejecutó en esta auditoría.

## SQLite

No hay un paso manual. Al arrancar FastAPI, `init_db` crea las tablas en `nutrimatch.db` (o en la ruta de `NUTRIMATCH_DB_PATH`). Borrar ese archivo y volver a levantar la API lo regenera vacío. El perfil de la interfaz sigue en el navegador.

## Variables

La plantilla es `.env.example`. El archivo real `.env` no se versiona. La descripción de cada variable está en [`mapa_proyecto.md`](mapa_proyecto.md), sección I.

## Reconstruir el catálogo

Ejecutar la aplicación no requiere este camino. El orden de construcción que dejó el repositorio es:

1. `make ingest-off` sobre el export CSV.
2. Homologación, matriz nutricional, observaciones y precios, con los scripts de `scripts/`.
3. `scripts/construir_dataset_referencia.py` arma un dataset de referencia.
4. `scripts/cerrar_dataset_operativo.py` lee `dataset_referencia_20260929.parquet` y escribe `dataset_referencia_20261002.parquet`.

Ejecutar la aplicación usa el Parquet del 2 de octubre. Reconstruir ese archivo con `scripts/cerrar_dataset_operativo.py` pide además `dataset_referencia_20260929.parquet` y `observaciones_20260926.parquet`, que están en el disco de trabajo y no entran en un alta nueva.
