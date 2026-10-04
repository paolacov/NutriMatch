# Makefile de NutriMatch.
#
# El entorno se gestiona con uv. La versión del intérprete la fija .python-version (3.12.13,
# la misma que el runtime de Google Colab), así que aquí no se nombra ningún python del sistema.
# Requisito previo: tener uv instalado (curl -LsSf https://astral.sh/uv/install.sh | sh).

.DEFAULT_GOAL := help
.PHONY: help setup ingest-off ingest-qqp homologar-identidad piloto-precios piloto-qqp materializar-qqp eda ui ui-angular api test lint

help: ## Lista los targets disponibles
	@echo "Targets de NutriMatch:"
	@echo "  setup        Crea .venv con uv e instala el paquete en modo editable (extra dev)"
	@echo "  ingest-off   Descarga y procesa el export de Open Food Facts (1,28 GB)"
	@echo "  ingest-qqp   Indica cómo reconstruir los precios de referencia de PROFECO"
	@echo "  homologar-identidad  Homologa nombre y marca (DERIVED, sin tocar el crudo)"
	@echo "  piloto-precios       Materializa precios reales de Open Prices por código de barras"
	@echo "  piloto-qqp           Genera candidatos PROFECO por texto, en CSV"
	@echo "  materializar-qqp     Escribe el Parquet de PROFECO desde el CSV revisado (CSV=ruta)"
	@echo "  eda          Rutas de los notebooks de EDA (02 y 08)"
	@echo "  api          Lanza FastAPI (catálogo de referencia, puerto 8000)"
	@echo "  ui           Lanza Angular (habla con FastAPI en :8000)"
	@echo "  test         Ejecuta las pruebas con pytest"
	@echo "  lint         Revisa el estilo con ruff"

# uv python install (sin argumentos) descarga el intérprete que pide .python-version si falta.
# El extra llm queda fuera de setup: la capa de lenguaje funciona con plantillas
# si no se instala. Para activarla: uv pip install -e ".[dev,llm]".
setup: ## Crea .venv con uv e instala el paquete en modo editable con el extra dev
	uv python install
	uv venv
	uv pip install -e ".[dev]"

# Descarga el export diario de OFF (~1,28 GB), inspecciona su esquema real, filtra México
# con DuckDB y reconcilia el conteo contra el count medido en la API.
ingest-off: ## Construye el snapshot México desde el export de Open Food Facts
	uv run python scripts/ingesta_off.py

ingest-qqp: ## Precios PROFECO ya integrados en el dataset operativo
	@echo "Los 20 precios de referencia PROFECO están en dataset_referencia_20261002.parquet."
	@echo "Para reconstruir su Parquet: make materializar-qqp CSV=datos/procesados/piloto_qqp_candidatos_20260926.csv"

# Homologa nombre (respaldo entre columnas del mismo registro y placeholder de captura)
# y marca (plegado de acentos) en un Parquet nuevo. No modifica off_mexico_*.parquet.
homologar-identidad: ## Homologa nombre y marca (DERIVED, sin tocar el crudo)
	uv run python scripts/homologar_identidad.py

# Descarga los precios en MXN de Open Prices y cruza por product_code (GTIN) con el universo
# México. El precio no entra al ranking. No toca el Parquet del catálogo.
piloto-precios: ## Materializa precios reales de Open Prices por código de barras
	uv run python scripts/piloto_precios_open_prices.py

# Genera candidatos de coincidencia por texto contra PROFECO y escribe un CSV.
# No materializa un precio por sí solo.
piloto-qqp: ## Candidatos PROFECO por texto, en CSV
	uv run python scripts/piloto_precios_qqp.py

# Solo corre sobre un CSV con la columna 'revisado' llena.
# Uso: make materializar-qqp CSV=datos/procesados/piloto_qqp_candidatos_20260926.csv
materializar-qqp: ## Escribe el Parquet de PROFECO desde el CSV revisado (requiere CSV=ruta)
	uv run python scripts/materializar_precios_qqp.py --csv $(CSV)

eda: ## Documenta los notebooks de EDA (no lanza Jupyter)
	@echo "Re-EDA de identidad (2026-09-26): notebooks/08_re_eda_identidad.ipynb"
	@echo "EDA original del universo México: notebooks/02_eda_universo_mexico.ipynb"
	@echo "CSV de este corte: datos/procesados/re_eda_20260926/"

api: ## Lanza FastAPI sobre el dataset de referencia
	uv run uvicorn nutrimatch.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000

ui: ## Lanza Angular (necesita `make api` en otra terminal)
	cd frontend && npm start

ui-angular: ui ## Alias de `ui`

test: ## Ejecuta la batería de pruebas
	uv run pytest

lint: ## Revisa el estilo del código
	uv run ruff check .
