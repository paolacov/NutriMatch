"""Ingesta del export CSV de Open Food Facts y construccion del universo Mexico.

Por que el export y no la API: Open Food Facts limita `search` a 10 peticiones
por minuto, aplica un limite global anti-crawl que responde HTTP 503 y pide
explicitamente en su documentacion descargar los exports cuando se necesitan
mas de unos cientos de productos. El universo Mexico son ~17.700 productos.

El proceso tiene cuatro fases y se detiene en cuanto una falla:

  1. Descarga    el CSV comprimido y registra su procedencia (Last-Modified,
                 ETag, Content-Length y SHA-256) para que el snapshot sea
                 citable y verificable.
  2. Esquema     lee la cabecera real, detecta el separador y reporta que
                 columnas necesarias estan presentes y cuales faltan.
  3. Filtrado    recorre el archivo comprimido con DuckDB sin descomprimirlo a
                 disco y escribe en Parquet solo las filas de Mexico.
  4. Reconcilia  compara el numero de filas con el count medido en la API para
                 detectar un criterio de filtrado mal planteado.

Uso:
    python scripts/ingesta_off.py                # proceso completo
    python scripts/ingesta_off.py --skip-download  # reutiliza un .gz ya bajado
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import httpx

EXPORT_URL = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
USER_AGENT = "NutriMatch/0.1-dev (MVP academico; contacto: paola.nutrimatch@proton.me)"

# Count medido en la API de produccion el 2026-09-19 con
# countries_tags_en=mexico. Sirve de contraste, no de verdad absoluta: el
# export se regenera a diario y una deriva pequena es esperable.
API_MEXICO_COUNT = 17_741
API_COUNT_FECHA = "2026-09-19"
TOLERANCIA_RECONCILIACION = 0.10

REPO_ROOT = Path(__file__).resolve().parents[1]

# Columnas que el MVP necesita, agrupadas por bloque del inventario de datos.
# La fase 2 reporta cuales existen realmente en el export; no se asume ninguna.
COLUMNAS_REQUERIDAS = {
    "identidad": [
        "code",
        "product_name",
        "brands",
        "quantity",
        "categories_tags",
        "countries_tags",
        "image_url",
        "url",
    ],
    "nutricion_100g": [
        "energy-kcal_100g",
        "energy_100g",
        "fat_100g",
        "saturated-fat_100g",
        "carbohydrates_100g",
        "sugars_100g",
        "fiber_100g",
        "proteins_100g",
        "salt_100g",
        "sodium_100g",
    ],
    "ingredientes": [
        "ingredients_text",
        "ingredients_tags",
        # El export no trae allergens_tags (solo existe en la API) y su columna
        # allergens_en esta VACIA en el 100% de las filas, verificado el
        # 2026-09-19. La unica fuente util es "allergens", que ya viene
        # taxonomizada con el prefijo del idioma ("en:milk,en:gluten,...").
        "allergens",
        # traces = menciones "puede contener": imprescindibles para el filtro
        # fail-safe de alergias de la decision 1.
        "traces",
        "traces_tags",
        # Fuente del filtro de dieta (vegano / vegetariano) y de su tercer
        # estado "no verificable".
        "ingredients_analysis_tags",
        "additives_tags",
        "nova_group",
        "labels_tags",
    ],
    "referencia_no_puntuada": [
        "nutriscore_grade",
        "nutriscore_score",
    ],
    "diferibles": [
        "serving_size",
        "completeness",
        "created_t",
        "last_modified_t",
        "states_tags",
    ],
    # Eran el checkpoint B9 de AGENTS.md: una prueba con 2 productos en la API
    # no fue concluyente porque OFF omite los campos vacios. El export confirma
    # que las cuatro existen, mas main_category_en ya taxonomizada.
    "confirmadas_b9": [
        "main_category",
        "main_category_en",
        "image_nutrition_url",
        "image_ingredients_url",
        # Existe pero llega vacia en el 100% de las filas de Mexico: se ingesta
        # para dejar constancia, no se usa.
        "allergens_en",
    ],
    # Candidatas utiles descubiertas al leer el esquema real. No son criticas:
    # se ingestan para evaluar su cobertura en el EDA.
    "candidatas_eda": [
        "food_groups_tags",
        "nutrient_levels_tags",
        "data_quality_errors_tags",
        "popularity_tags",
    ],
}

# Candidatas para localizar el mercado, en orden de preferencia. La primera que
# exista en el export decide el criterio de filtrado.
COLUMNAS_PAIS = [
    ("countries_tags", "en:mexico"),
    ("countries_en", "mexico"),
    ("countries", "mexico"),
]


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def formato_bytes(n: int) -> str:
    unidades = ["B", "KB", "MB", "GB"]
    valor = float(n)
    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.2f} {unidad}"
        valor /= 1024
    return f"{valor:.2f} GB"


# --------------------------------------------------------------------------
# Fase 1: descarga con registro de procedencia
# --------------------------------------------------------------------------


def descargar_export(destino: Path, skip: bool) -> dict:
    """Descarga el CSV comprimido y devuelve sus metadatos de procedencia."""
    if skip and destino.exists():
        log(f"Fase 1 omitida: se reutiliza {destino.name} ({formato_bytes(destino.stat().st_size)})")
        return {
            "url": EXPORT_URL,
            "reutilizado": True,
            "bytes": destino.stat().st_size,
            "sha256": _sha256(destino),
        }

    libre = shutil.disk_usage(destino.parent).free
    log(f"Fase 1: descargando el export. Espacio libre en disco: {formato_bytes(libre)}")

    parcial = destino.with_suffix(destino.suffix + ".parcial")
    sha = hashlib.sha256()
    descargados = 0
    inicio = time.monotonic()

    with httpx.stream(
        "GET",
        EXPORT_URL,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, read=300.0),
    ) as respuesta:
        respuesta.raise_for_status()
        cabeceras = respuesta.headers
        total = int(cabeceras.get("Content-Length", 0))
        if total and total < 100_000_000:
            raise RuntimeError(
                f"El servidor anuncia solo {formato_bytes(total)}; se esperaba mas de 1 GB. "
                "Posible pagina de error en lugar del export."
            )
        log(f"  Tamano anunciado: {formato_bytes(total) if total else 'desconocido'}")

        with parcial.open("wb") as salida:
            siguiente_aviso = 5
            for bloque in respuesta.iter_bytes(chunk_size=1024 * 1024):
                salida.write(bloque)
                sha.update(bloque)
                descargados += len(bloque)
                if total:
                    pct = descargados * 100 / total
                    if pct >= siguiente_aviso:
                        transcurrido = time.monotonic() - inicio
                        velocidad = descargados / transcurrido if transcurrido else 0
                        log(
                            f"  {pct:5.1f}%  {formato_bytes(descargados)}"
                            f"  ({formato_bytes(int(velocidad))}/s)"
                        )
                        siguiente_aviso = int(pct) + 5

    if total and descargados != total:
        parcial.unlink(missing_ok=True)
        raise RuntimeError(
            f"Descarga incompleta: {descargados} bytes recibidos de {total} anunciados."
        )

    parcial.replace(destino)
    duracion = time.monotonic() - inicio
    log(f"  Descarga completa en {duracion:.0f} s: {formato_bytes(descargados)}")

    return {
        "url": EXPORT_URL,
        "reutilizado": False,
        "bytes": descargados,
        "sha256": sha.hexdigest(),
        "last_modified": cabeceras.get("Last-Modified"),
        "etag": cabeceras.get("ETag"),
        "content_length": cabeceras.get("Content-Length"),
        "descargado_en": datetime.now(UTC).isoformat(),
        "segundos": round(duracion, 1),
    }


def _sha256(ruta: Path) -> str:
    sha = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            sha.update(bloque)
    return sha.hexdigest()


# --------------------------------------------------------------------------
# Fase 2: esquema real del export
# --------------------------------------------------------------------------


def inspeccionar_esquema(ruta: Path) -> dict:
    """Lee la cabecera real y contrasta las columnas contra las que necesitamos."""
    log("Fase 2: leyendo la cabecera real del export")
    with gzip.open(ruta, "rt", encoding="utf-8", errors="replace") as fh:
        cabecera = fh.readline().rstrip("\r\n")

    separador = "\t" if cabecera.count("\t") >= cabecera.count(",") else ","
    columnas = cabecera.split(separador)
    presentes = set(columnas)
    log(f"  Separador detectado: {'tabulacion' if separador == chr(9) else 'coma'}")
    log(f"  Columnas en el export: {len(columnas)}")

    informe: dict[str, dict[str, list[str]]] = {}
    faltan_criticas: list[str] = []
    for bloque, esperadas in COLUMNAS_REQUERIDAS.items():
        hay = [c for c in esperadas if c in presentes]
        faltan = [c for c in esperadas if c not in presentes]
        informe[bloque] = {"presentes": hay, "faltan": faltan}
        estado = "completo" if not faltan else f"faltan {len(faltan)}"
        log(f"  {bloque:24s} {len(hay):2d}/{len(esperadas):2d}  ({estado})")
        if faltan:
            log(f"      sin encontrar: {', '.join(faltan)}")
        if faltan and bloque in {"identidad", "nutricion_100g", "ingredientes"}:
            faltan_criticas.extend(faltan)

    columna_pais = None
    valor_pais = None
    for candidata, valor in COLUMNAS_PAIS:
        if candidata in presentes:
            columna_pais, valor_pais = candidata, valor
            break
    if columna_pais is None:
        raise RuntimeError(
            "El export no trae ninguna columna de pais conocida "
            f"({', '.join(c for c, _ in COLUMNAS_PAIS)}). No se puede filtrar Mexico."
        )
    log(f"  Columna de pais elegida: {columna_pais} (se busca '{valor_pais}')")

    if faltan_criticas:
        raise RuntimeError(
            "Faltan columnas criticas en el export: "
            f"{', '.join(sorted(set(faltan_criticas)))}. "
            "Revisa el esquema antes de continuar en lugar de generar un snapshot mutilado."
        )

    return {
        "separador": "tab" if separador == "\t" else "coma",
        "separador_literal": separador,
        "n_columnas": len(columnas),
        "columnas": columnas,
        "cobertura_requeridas": informe,
        "columna_pais": columna_pais,
        "valor_pais": valor_pais,
    }


# --------------------------------------------------------------------------
# Fase 3: filtrado del universo Mexico
# --------------------------------------------------------------------------


def filtrar_mexico(ruta_gz: Path, esquema: dict, destino_parquet: Path) -> dict:
    """Filtra Mexico con DuckDB en streaming y escribe el resultado en Parquet."""
    log("Fase 3: filtrando el universo Mexico con DuckDB (sin descomprimir a disco)")
    inicio = time.monotonic()

    con = duckdb.connect()
    con.execute("PRAGMA enable_progress_bar=false")

    # all_varchar: el export mezcla texto libre y numeros sucios en las mismas
    # columnas; la conversion de tipos se hace despues, de forma auditada.
    # quote/escape vacios: OFF no entrecomilla y hay comillas sueltas en los
    # textos de ingredientes.
    # store_rejects: las filas malformadas se registran en vez de perderse en
    # silencio, para poder auditarlas.
    # DuckDB no admite parametros preparados dentro de CREATE VIEW ni en las
    # opciones de read_csv, asi que los literales van embebidos. La ruta y el
    # separador no vienen del exterior, pero se escapan igualmente.
    ruta_sql = str(ruta_gz).replace("'", "''")
    delim_sql = esquema["separador_literal"].replace("'", "''")
    lector = (
        f"read_csv("
        f"  '{ruta_sql}',"
        f"  delim='{delim_sql}',"
        f"  header=true,"
        f"  quote='',"
        f"  escape='',"
        f"  all_varchar=true,"
        f"  null_padding=true,"
        f"  store_rejects=true"
        f")"
    )

    columna = esquema["columna_pais"]
    valor = esquema["valor_pais"]
    condicion = f'"{columna}" IS NOT NULL AND contains(lower("{columna}"), \'{valor}\')'

    con.execute(
        f"CREATE OR REPLACE TEMP VIEW off_mexico AS SELECT * FROM {lector} WHERE {condicion}"
    )
    con.execute(
        f"COPY off_mexico TO '{destino_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )

    filas = con.execute(
        f"SELECT count(*) FROM read_parquet('{destino_parquet}')"
    ).fetchone()[0]
    codigos_unicos = con.execute(
        f"SELECT count(DISTINCT code) FROM read_parquet('{destino_parquet}')"
    ).fetchone()[0]

    try:
        rechazos = con.execute("SELECT count(*) FROM reject_errors").fetchone()[0]
    except duckdb.Error:
        rechazos = 0

    con.close()
    duracion = time.monotonic() - inicio
    tamano = destino_parquet.stat().st_size

    log(f"  Filas de Mexico: {filas:,}")
    log(f"  Codigos unicos:  {codigos_unicos:,} (duplicados: {filas - codigos_unicos:,})")
    log(f"  Filas rechazadas por malformacion: {rechazos:,}")
    log(f"  Parquet escrito: {destino_parquet.name} ({formato_bytes(tamano)}) en {duracion:.0f} s")

    return {
        "filas": filas,
        "codigos_unicos": codigos_unicos,
        "duplicados": filas - codigos_unicos,
        "filas_rechazadas": rechazos,
        "bytes_parquet": tamano,
        "segundos": round(duracion, 1),
        "condicion_filtrado": condicion,
    }


# --------------------------------------------------------------------------
# Fase 4: reconciliacion contra el count de la API
# --------------------------------------------------------------------------


def reconciliar(filas: int) -> dict:
    log("Fase 4: reconciliando contra el count medido en la API")
    delta = filas - API_MEXICO_COUNT
    desviacion = abs(delta) / API_MEXICO_COUNT
    dentro = desviacion <= TOLERANCIA_RECONCILIACION

    log(f"  Export:  {filas:,} filas")
    log(f"  API ({API_COUNT_FECHA}): {API_MEXICO_COUNT:,} productos")
    log(f"  Diferencia: {delta:+,} ({desviacion:.1%})")

    if dentro:
        log("  Reconciliacion OK: la diferencia esta dentro de la tolerancia.")
    else:
        log(
            "  ATENCION: la diferencia supera la tolerancia del "
            f"{TOLERANCIA_RECONCILIACION:.0%}. El criterio de filtrado del export "
            "podria no ser equivalente al countries_tags_en=mexico de la API. "
            "Revisalo antes de usar este snapshot en el EDA."
        )

    return {
        "filas_export": filas,
        "count_api": API_MEXICO_COUNT,
        "fecha_count_api": API_COUNT_FECHA,
        "delta": delta,
        "desviacion_relativa": round(desviacion, 4),
        "dentro_de_tolerancia": dentro,
        "tolerancia": TOLERANCIA_RECONCILIACION,
    }


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="reutiliza el .gz ya descargado en lugar de bajarlo de nuevo",
    )
    parser.add_argument(
        "--fecha",
        default=datetime.now(UTC).astimezone().strftime("%Y%m%d"),
        help="etiqueta de fecha del snapshot (por defecto, hoy)",
    )
    args = parser.parse_args()

    dir_snapshot = REPO_ROOT / "datos" / "snapshots" / f"off_csv_{args.fecha}"
    dir_snapshot.mkdir(parents=True, exist_ok=True)
    ruta_gz = dir_snapshot / "en.openfoodfacts.org.products.csv.gz"

    dir_procesados = REPO_ROOT / "datos" / "procesados"
    dir_procesados.mkdir(parents=True, exist_ok=True)
    ruta_parquet = dir_procesados / f"off_mexico_{args.fecha}.parquet"

    try:
        procedencia = descargar_export(ruta_gz, args.skip_download)
        esquema = inspeccionar_esquema(ruta_gz)
        filtrado = filtrar_mexico(ruta_gz, esquema, ruta_parquet)
        conciliacion = reconciliar(filtrado["filas"])
    except Exception as error:  # noqa: BLE001 - el script reporta y se detiene
        log(f"ERROR: {error}")
        return 1

    metadatos = {
        "snapshot_id": f"off_csv_{args.fecha}",
        "generado_en": datetime.now(UTC).isoformat(),
        "fuente": "Open Food Facts, export CSV diario",
        "licencia": "ODbL (base) / DbCL (contenidos) / CC-BY-SA (imagenes)",
        "user_agent": USER_AGENT,
        "duckdb": duckdb.__version__,
        "procedencia": procedencia,
        "esquema": esquema,
        "filtrado": filtrado,
        "reconciliacion": conciliacion,
        "parquet": str(ruta_parquet.relative_to(REPO_ROOT)),
    }
    ruta_meta = dir_snapshot / "_metadata.json"
    ruta_meta.write_text(json.dumps(metadatos, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Metadatos escritos en {ruta_meta.relative_to(REPO_ROOT)}")

    return 0 if conciliacion["dentro_de_tolerancia"] else 2


if __name__ == "__main__":
    sys.exit(main())
