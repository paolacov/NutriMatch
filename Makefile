# Makefile de NutriMatch.
# Los targets marcados como pendientes solo imprimen un aviso: el script todavía no existe.
#
# El entorno se gestiona con uv. La versión del intérprete la fija .python-version (3.12.13,
# la misma que el runtime de Google Colab), así que aquí no se nombra ningún python del sistema.
# Requisito previo: tener uv instalado (curl -LsSf https://astral.sh/uv/install.sh | sh).

.DEFAULT_GOAL := help
.PHONY: help setup ingest-off ingest-qqp eda ui test lint

help: ## Lista los targets disponibles
	@echo "Targets de NutriMatch:"
	@echo "  setup        Crea .venv con uv e instala el paquete en modo editable (extra dev)"
	@echo "  ingest-off   Descarga y procesa el export de Open Food Facts (1,28 GB)"
	@echo "  ingest-qqp   Descarga y procesa los precios de PROFECO QQP    [pendiente]"
	@echo "  eda          Análisis exploratorio del universo México        [pendiente]"
	@echo "  ui           Lanza la interfaz Streamlit"
	@echo "  test         Ejecuta las pruebas con pytest"
	@echo "  lint         Revisa el estilo con ruff"

# uv python install (sin argumentos) descarga el intérprete que pide .python-version si falta.
# El extra llm queda fuera a propósito: la capa LLM es opcional y todavía no se necesita.
setup: ## Crea .venv con uv e instala el paquete en modo editable con el extra dev
	uv python install
	uv venv
	uv pip install -e ".[dev]"

# Descarga el export diario de OFF (~1,28 GB), inspecciona su esquema real, filtra México
# con DuckDB y reconcilia el conteo contra el count medido en la API.
ingest-off: ## Construye el snapshot México desde el export de Open Food Facts
	uv run python scripts/ingesta_off.py

ingest-qqp: ## Pendiente: ingesta de los precios de referencia de PROFECO QQP
	@echo "pendiente de implementar: ingesta de PROFECO QQP"

eda: ## Pendiente: análisis exploratorio (notebook 02_eda_universo_mexico)
	@echo "pendiente de implementar: análisis exploratorio del universo México"

ui: ## Lanza la interfaz Streamlit del MVP
	uv run streamlit run ui/app.py

test: ## Ejecuta la batería de pruebas
	uv run pytest

lint: ## Revisa el estilo del código
	uv run ruff check .
