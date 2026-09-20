# NutriMatch

Apoyo a la decisión de compra de alimentos en México, explicable y auditable.

> **Aviso importante: NutriMatch no emite diagnósticos médicos.** No sustituye la consulta con
> personal de salud ni con profesionales de la nutrición. El sistema compara productos empacados
> frente a un perfil declarado por la propia usuaria y explica el porqué de cada resultado; no
> valora estados de salud, no prescribe dietas y no interpreta síntomas.

## Qué es y para quién

NutriMatch es un MVP académico. La persona declara un perfil (dieta, alergias, objetivo, orden de
prioridades y presupuesto), busca un producto por nombre o escanea su código de barras, y recibe un
**ranking personalizado con explicación detallada**: cuánto aportó cada dimensión, qué nutrientes
pesaron, en qué percentil queda el producto dentro de su categoría y en qué estado están los datos.

Está pensado para quien compra en México y quiere entender por qué un producto le conviene más que
otro, sin tener que interpretar una tabla nutrimental por su cuenta.

Dos ideas ordenan todo el diseño:

1. **El cálculo es determinista y explicable.** El motor de scoring es aritmética reproducible. Con
   los mismos datos de entrada devuelve siempre el mismo resultado.
2. **El LLM es opcional y nunca calcula.** Solo interpreta lo que pide la usuaria en lenguaje
   natural y narra los hechos que ya calculó el motor. Sin clave de API, la aplicación funciona
   igual con plantillas deterministas.

## Fuentes de datos

- **Open Food Facts (OFF)** para los datos de producto: nutrientes, ingredientes, grupo NOVA,
  etiquetas y sellos frontales.
- **PROFECO "Quién es Quién en los Precios" (QQP)** para el **precio de referencia**. El precio es
  informativo: no puntúa ni filtra.

Las licencias y la forma de citar ambas fuentes están en [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md).

## Stack del MVP

| Pieza | Elección | Por qué |
| --- | --- | --- |
| Lógica | Paquete `nutrimatch` instalable (src-layout) | Un solo motor compartido entre notebooks y UI, sin código duplicado |
| Interfaz | Streamlit | Requisito de la rúbrica académica y suficiente para el MVP |
| Análisis | DuckDB sobre Parquet | Consulta un snapshot de millones de filas sin servidor de base de datos |
| Estado | SQLite en modo WAL | Solo estado mutable y regenerable |
| Validación | pydantic v2 | Contratos explícitos de entrada y salida |

## Jerarquía de datos en tres niveles

Distinguir estos tres niveles es la decisión de arquitectura más importante del proyecto:

1. **Export crudo de OFF: inmutable y citable.** Se descarga el CSV comprimido del día y no se
   modifica nunca. Es el origen, y como OFF regenera los exports a diario, la fecha de descarga da
   una cita exacta.
2. **Parquet derivado: fuente de verdad analítica.** Del export se deriva el universo México, ya
   filtrado y normalizado. Es reproducible: se puede regenerar desde el crudo con el script de
   ingesta. Todo el análisis y el scoring leen de aquí.
3. **SQLite: mutable y desechable.** Perfil, `event_log`, carrito, `ranking_run`, caché de
   proveedor y de LLM. Se puede borrar y reconstruir; no contiene nada que no sea regenerable.

## Instalación

El entorno se gestiona con **[uv](https://docs.astral.sh/uv/)**, el gestor de paquetes y de
intérpretes de Astral. uv se encarga de descargar el Python correcto, crear `.venv` y resolver las
dependencias, así que no hace falta ningún Python previo en la máquina más allá del del sistema.

### Por qué Python 3.12.13

El archivo `.python-version` fija **Python 3.12.13**, que es **exactamente la versión del runtime de
Google Colab** (runtime 2026.07). No es una preferencia estética: el paquete `nutrimatch` se
reutiliza tal cual desde los notebooks, y si el intérprete local y el de Colab divergen, el mismo
código puede comportarse distinto en cada sitio. Fijar la versión elimina esa clase de problema de
raíz.

`pyproject.toml` mantiene `requires-python = ">=3.11"` porque es el **suelo de compatibilidad** del
paquete; `.python-version` fija el **intérprete concreto del entorno local**. Son dos cosas
distintas y por eso no coinciden. `.python-version` **sí se versiona**.

### Puesta en marcha

```bash
# 1. Instalar uv (solo la primera vez; no pide contraseña de administrador)
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"        # o reinicia la terminal

# 2. Crear el entorno e instalar el paquete en modo editable con el extra dev
make setup

# 3. Copiar la plantilla de variables de entorno
cp .env.example .env
```

`make setup` equivale a estos tres pasos:

```bash
uv python install          # descarga el 3.12.13 que pide .python-version
uv venv                    # crea .venv con esa versión
uv pip install -e ".[dev]" # instala el paquete editable + pytest y ruff
```

El extra **`llm` no se instala** a propósito: la capa LLM es opcional y el sistema funciona sin ella
con plantillas deterministas. Cuando haga falta: `uv pip install -e ".[dev,llm]"`.

Después edita `.env` y pon tu correo en `OFF_USER_AGENT`: OFF exige un User-Agent identificable en
todas las peticiones. `OPENAI_API_KEY` puede quedarse vacía.

## Cómo correr

```bash
make ui             # interfaz Streamlit
make test           # pruebas con pytest
make lint           # estilo con ruff
make help           # lista todos los targets
```

Los targets del `Makefile` usan `uv run`, que resuelve el intérprete de `.venv` por sí solo: **no
hace falta activar el entorno**. Para ejecutar algo suelto, el mismo prefijo sirve:

```bash
uv run python -c "import nutrimatch; print(nutrimatch.__version__)"
```

Si prefieres activar el entorno a mano: `source .venv/bin/activate`.

Los targets `make ingest-off`, `make ingest-qqp` y `make eda` están declarados pero **todavía
avisan de que están pendientes de implementar**.

## Mapa de carpetas

```
src/nutrimatch/       paquete instalable: toda la lógica
  agents/             capa LLM opcional (planner, critic, narrate) + registro de herramientas
    prompts/          plantillas de prompt de los tres roles
  core/               configuración, logging, guard de conformidad, errores
  db/                 SQLite WAL: única capa de persistencia
    repositories/     acceso a datos con patrón repositorio
  domain/             modelos de dominio (producto, usuario, carrito)
  engine/             motor determinista de scoring y operaciones
  providers/          acceso a OFF y a PROFECO QQP, con caché y limitador
  schemas/            esquemas pydantic v2 de entrada y salida
  services/           orquestación: ingesta, universo México, ranking
datos/
  snapshots/          export crudo de OFF (no se versiona)
  precios_qqp/        ZIP de PROFECO QQP (no se versiona)
  procesados/         Parquet derivado del universo México
docs/                 atribución de datos y línea futura
notebooks/            notebooks de análisis
ui/                   aplicación Streamlit
scripts/              scripts de ingesta y mantenimiento
tests/                pruebas
  fixtures/           datos de prueba
evaluacion/           golden set, parity-check y diagnóstico de cobertura
```

## Notebooks previstos

**Ninguno existe todavía.** El orden planeado es:

1. `01_ingesta`
2. `02_eda_universo_mexico`
3. `03_transformacion_score`
4. `04_evaluacion`
5. `05_qqp_precios`
6. `06_app_y_llm`

## Convenciones

Las decisiones metodológicas cerradas, las trampas ya verificadas de las fuentes de datos y las
convenciones de código están en [`AGENTS.md`](AGENTS.md). Conviene leerlo antes de tocar el motor.

## Licencias

La licencia del **código está PENDIENTE de decidir**; ver [`LICENSE`](LICENSE). Los **datos** de
terceros se rigen por sus propias licencias: ver [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md).
