# Makefile de NutriMatch.
# Los targets marcados como pendientes solo imprimen un aviso: el script todavía no existe.
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
	@echo "  ingest-qqp   Descarga y procesa los precios de PROFECO QQP    [pendiente]"
	@echo "  homologar-identidad  Homologa nombre y marca (DERIVED, sin tocar el crudo)"
	@echo "  piloto-precios       Materializa precios REALES de Open Prices (A35/A40)"
	@echo "  piloto-qqp           Fase A: genera candidatos QQP por texto para revisión manual (A35/A41)"
	@echo "  materializar-qqp     Fase B: materializa el CSV QQP ya revisado a mano (A35/A41, requiere CSV=ruta)"
	@echo "  eda          Rutas de los notebooks de EDA (02 y 08)"
	@echo "  api          Lanza FastAPI (catálogo de referencia, puerto 8000)"
	@echo "  ui           Lanza Angular (habla con FastAPI en :8000)"
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

# Homologa nombre (A28 + placeholders de captura) y marca (plegado de acentos, A38) en un
# Parquet nuevo. No modifica off_mexico_*.parquet (A2).
homologar-identidad: ## Homologa nombre y marca (DERIVED, sin tocar el crudo)
	uv run python scripts/homologar_identidad.py

# Descarga los precios en MXN de Open Prices y cruza por product_code (GTIN) con el universo
# México. El precio no puntúa (A5); no toca ningún Parquet existente.
piloto-precios: ## Materializa precios REALES de Open Prices por GTIN (A35/A40)
	uv run python scripts/piloto_precios_open_prices.py

# Fase A (A35/A41): genera candidatos de match por texto contra QQP y escribe un CSV pequeño
# para revisión manual. Nunca materializa un precio por sí solo.
piloto-qqp: ## Fase A: candidatos QQP por texto para revisión manual (A35/A41)
	uv run python scripts/piloto_precios_qqp.py

# Fase B (A35/A41): solo corre sobre un CSV ya revisado a mano (columna 'revisado' llena).
# Uso: make materializar-qqp CSV=datos/procesados/piloto_qqp_candidatos_20260926.csv
materializar-qqp: ## Fase B: materializa el CSV QQP ya revisado (requiere CSV=ruta)
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
