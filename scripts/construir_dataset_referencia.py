"""Construye el dataset analítico de referencia — paso 9 del plan de trabajo (decisión A43).

Ver `docs/diagnostico_calidad_datos.md` (sección H, paso 9; diseño en sección F) y las
decisiones A2/A33/A34/A38/A39/A40/A41/A43 de `AGENTS.md`. Une, por `code` (A34, llave única de
análisis), las piezas ya materializadas por pasos anteriores en dos Parquets nuevos:

    off_mexico_20260919.parquet                    (REAL, 211 columnas, SIN TOCAR)
      + identidad_homologada_20260919.parquet      (DERIVED, A38)
      + matriz_nut_100g_20260919.parquet           (DERIVED, A18/A21/A23/A27)
      + tabla de observaciones resuelta:
          experimento_recuperacion_nombres_20260919.parquet (REAL, A39, solo hits)
          precios_open_prices_20260926.parquet              (REAL, A40)
          precios_qqp_20260926.parquet                       (REAL, A41)
    -> datos/procesados/observaciones_<fecha>.parquet        (nuevo: tabla de observaciones, F.2)
    -> datos/procesados/dataset_referencia_<fecha>.parquet   (nuevo: dataset de referencia)
    -> datos/procesados/dataset_referencia_<fecha>_metadata.json  (nuevo: metadato de tabla)

Ningún Parquet existente se modifica. El resultado tiene siempre **una fila por `code`** del
universo México (16.851, A34), sin importar si alguna de las fuentes de observación no cubre
ese código: la ausencia se resuelve explícitamente como `UNAVAILABLE`, nunca como `NULL` mudo
ni como cero (A2).

**Explícitamente fuera de este paso** (es el paso 10, no este): no se toca
`src/nutrimatch/engine/*_score.py` ni `services/catalog.py`/`services/ranking.py`. Este
Parquet es un artefacto nuevo para consulta y evaluación, no un reemplazo de lo que el motor de
scoring consume hoy.

Uso:
    uv run python scripts/construir_dataset_referencia.py
    uv run python scripts/construir_dataset_referencia.py --fecha-off 20260919 \\
        --fecha-open-prices 20260926 --fecha-qqp 20260926
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nutrimatch.engine.observations import (
    construir_observaciones_nombre_recuperado,
    construir_observaciones_precio,
    resolver_observaciones,
)

PROCESADOS = REPO_ROOT / "datos" / "procesados"


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def _es_nulo(valor: Any) -> bool:
    """None, NaN o `pd.NA` de pandas (B13, `AGENTS.md`; ver docstring gemelo en
    `nutrimatch.engine.observations._es_nulo`)."""
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return bool(pd.isna(valor))


def _leer_parquet(ruta: Path, columnas: str = "*") -> pd.DataFrame:
    if not ruta.exists():
        log(f"ERROR: no existe {ruta}.")
        raise FileNotFoundError(ruta)
    con = duckdb.connect()
    return con.execute(f"SELECT {columnas} FROM read_parquet('{ruta.as_posix()}')").df()


def construir_tabla_observaciones(
    experimento: pd.DataFrame, precios_open_prices: pd.DataFrame, precios_qqp: pd.DataFrame
) -> pd.DataFrame:
    """Consolida las tres fuentes de observaciones externas en el esquema único de F.2."""
    partes = [
        construir_observaciones_nombre_recuperado(experimento),
        construir_observaciones_precio(precios_open_prices),
        construir_observaciones_precio(precios_qqp),
    ]
    return pd.concat(partes, ignore_index=True)


def _pivotear_precio(resueltas: pd.DataFrame) -> pd.DataFrame:
    """De la tabla de observaciones ya resuelta, extrae una fila por `code` con las columnas
    `price_*` para el dataset de referencia. `code` sin ninguna observación de precio no
    aparece aquí — el LEFT JOIN posterior contra el universo completo, más un relleno
    explícito, es quien convierte esa ausencia en `UNAVAILABLE` (A2: nunca NULL mudo)."""
    precio = resueltas[resueltas["field"] == "price"].copy()
    if precio.empty:
        return pd.DataFrame(
            columns=[
                "code",
                "price",
                "price_status",
                "price_source",
                "price_source_url",
                "price_retrieved_at",
                "price_match_method",
                "price_match_confidence",
            ]
        )
    return precio.rename(
        columns={
            "value": "price",
            "status": "price_status",
            "source": "price_source",
            "source_url": "price_source_url",
            "retrieved_at": "price_retrieved_at",
            "method": "price_match_method",
            "confidence": "price_match_confidence",
        }
    )[
        [
            "code",
            "price",
            "price_status",
            "price_source",
            "price_source_url",
            "price_retrieved_at",
            "price_match_method",
            "price_match_confidence",
        ]
    ]


def _pivotear_nombre_recuperado(resueltas: pd.DataFrame) -> pd.DataFrame:
    """Igual que `_pivotear_precio`, para las observaciones de `product_name` recuperadas por
    API (A39). Solo existen para códigos con un hit REAL (nunca UNAVAILABLE: A39 no genera una
    observación cuando no encuentra nada nuevo, ver docstring de
    `construir_observaciones_nombre_recuperado`)."""
    nombre = resueltas[resueltas["field"] == "product_name"].copy()
    if nombre.empty:
        return pd.DataFrame(columns=["code", "nombre_recuperado_api", "nombre_recuperado_api_source"])
    return nombre.rename(columns={"value": "nombre_recuperado_api", "source": "nombre_recuperado_api_source"})[
        ["code", "nombre_recuperado_api", "nombre_recuperado_api_source"]
    ]


# Columnas de identidad que viajan al catálogo. `brand_homologated` es llave de
# coincidencia (A38), no el texto que se muestra: `brands` no se pisa.
COLUMNAS_IDENTIDAD_VISIBLES: tuple[str, ...] = (
    "product_name_homologated",
    "product_name_status",
    "product_name_field_source",
    "product_name_flag_respaldo_usado",
    "product_name_flag_placeholder_removido",
    "product_name_original",
    "brand_original",
    "brand_homologated",
    "brand_status",
)


def _texto_visible(valor: Any) -> str | None:
    """Texto utilizable, o None. No trata el nombre real ``NAN`` como ausente."""
    if _es_nulo(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def aplicar_nombre_visible(resultado: pd.DataFrame) -> pd.DataFrame:
    """`product_name` = nombre homologado si existe; si no, el crudo del propio catálogo.

    Conserva el crudo en `product_name_crudo`. No inventa un nombre cuando ambos faltan (A2).
    """
    if "product_name_homologated" not in resultado.columns:
        return resultado
    salida = resultado.copy()
    previos = (
        salida["product_name_crudo"].tolist()
        if "product_name_crudo" in salida.columns
        else [None] * len(salida)
    )
    crudos: list[str | None] = []
    visibles: list[str | None] = []
    for previo, nombre, homologado in zip(
        previos,
        salida["product_name"].tolist(),
        salida["product_name_homologated"].tolist(),
        strict=True,
    ):
        base = _texto_visible(previo) or _texto_visible(nombre)
        crudos.append(base)
        visibles.append(_texto_visible(homologado) or base)
    salida["product_name_crudo"] = crudos
    salida["product_name"] = visibles
    return salida


def sql_nombres_homologados(
    ruta_catalogo: Path,
    ruta_identidad: Path,
    columnas_catalogo: set[str],
) -> str:
    """LEFT JOIN por GTIN. El nombre que consume la API queda en `product_name`."""
    excluir = ["product_name"]
    if "product_name_crudo" in columnas_catalogo:
        excluir.append("product_name_crudo")
    excluir.extend(col for col in COLUMNAS_IDENTIDAD_VISIBLES if col in columnas_catalogo)
    excluir_sql = ", ".join(f'"{col}"' for col in excluir)
    crudo_expr = (
        "COALESCE(catalogo.product_name_crudo, catalogo.product_name)"
        if "product_name_crudo" in columnas_catalogo
        else "catalogo.product_name"
    )
    columnas_identidad = ", ".join(f'"{col}"' for col in COLUMNAS_IDENTIDAD_VISIBLES)
    seleccion_identidad = ",\n      ".join(
        f'identidad."{col}"' for col in COLUMNAS_IDENTIDAD_VISIBLES
    )
    catalogo = ruta_catalogo.as_posix()
    identidad = ruta_identidad.as_posix()
    return f"""
    SELECT
      catalogo.* EXCLUDE ({excluir_sql}),
      {crudo_expr} AS product_name_crudo,
      COALESCE(
        NULLIF(TRIM(CAST(identidad.product_name_homologated AS VARCHAR)), ''),
        {crudo_expr}
      ) AS product_name,
      {seleccion_identidad}
    FROM (
      SELECT * REPLACE (CAST(code AS VARCHAR) AS code)
      FROM read_parquet('{catalogo}')
    ) catalogo
    LEFT JOIN (
      SELECT CAST(code AS VARCHAR) AS code, {columnas_identidad}
      FROM read_parquet('{identidad}')
    ) identidad
      ON catalogo.code = identidad.code
    """


def aplicar_nombres_homologados(
    ruta_catalogo: Path,
    ruta_identidad: Path,
    ruta_salida: Path,
) -> None:
    """Escribe el catálogo con `product_name` ya resuelto. No modifica el crudo ni la identidad."""
    if not ruta_catalogo.exists():
        raise FileNotFoundError(ruta_catalogo)
    if not ruta_identidad.exists():
        raise FileNotFoundError(ruta_identidad)
    con = duckdb.connect()
    columnas = set(
        con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{ruta_catalogo.as_posix()}')"
        ).df()["column_name"]
    )
    sql = sql_nombres_homologados(ruta_catalogo, ruta_identidad, columnas)
    n_entrada = con.execute(
        f"SELECT count(*) FROM read_parquet('{ruta_catalogo.as_posix()}')"
    ).fetchone()[0]
    destino = ruta_salida
    if ruta_salida.resolve() == ruta_catalogo.resolve():
        destino = ruta_salida.with_suffix(".parquet.tmp")
    con.execute(f"COPY ({sql}) TO '{destino.as_posix()}' (FORMAT PARQUET)")
    verificacion = con.execute(
        f"SELECT count(*) AS n, count(DISTINCT code) AS codes FROM read_parquet('{destino.as_posix()}')"
    ).fetchone()
    if verificacion is None or verificacion[0] != n_entrada or verificacion[1] != n_entrada:
        destino.unlink(missing_ok=True)
        raise RuntimeError(
            f"El JOIN cambió el universo: entrada={n_entrada}, salida={verificacion}"
        )
    if destino != ruta_salida:
        destino.replace(ruta_salida)
    log(f"Nombres homologados aplicados: {n_entrada:,} filas → {ruta_salida.name}")


def _asegurar_sin_colision_de_columnas(izquierda: pd.DataFrame, derecha: pd.DataFrame, nombre_izq: str, nombre_der: str) -> None:
    """Falla ruidosamente si dos fuentes a unir comparten un nombre de columna fuera de `code`.

    Un merge de pandas con columnas repetidas les pone sufijo `_x`/`_y` en silencio en vez de
    fallar — así es exactamente como se descubrió que `matriz_nut_100g` traía copias de
    `nova_group`/`additives_n` idénticas a las de `off_mexico` (2026-09-26): habría renombrado
    2 de las 211 columnas de OFF sin avisar, violando "SIN TOCAR" (A2). Mejor detenerse aquí y
    obligar a decidir explícitamente (dropear el duplicado o renombrarlo) que dejar que pandas
    decida en silencio.
    """
    colisión = (set(izquierda.columns) & set(derecha.columns)) - {"code"}
    if colisión:
        raise ValueError(
            f"Colisión de columnas entre {nombre_izq!r} y {nombre_der!r}: {sorted(colisión)}. "
            "Decide explícitamente si dropear o renombrar antes de unir (ver B15/A43 en AGENTS.md)."
        )


def construir_dataset_referencia(
    off: pd.DataFrame,
    identidad: pd.DataFrame,
    matriz: pd.DataFrame,
    observaciones_resueltas: pd.DataFrame,
) -> pd.DataFrame:
    """Ensambla el dataset de referencia: una fila por `code`, LEFT JOIN encadenado sobre la
    base de `off` (211 columnas REAL, sin tocar) — así el resultado siempre tiene exactamente
    `len(off)` filas, sin importar la cobertura de las demás fuentes."""
    n_off = len(off)

    identidad_sin_duplicar = identidad.drop(columns=["snapshot_id", "generated_at"], errors="ignore")
    # `nova_group`/`additives_n` de la matriz son un passthrough exacto de las columnas crudas
    # de OFF (verificado 2026-09-26: 0 filas distintas en las 16.851 del universo) — se
    # descartan aquí para que las 211 columnas de `off` no se renombren por colisión de
    # nombre al hacer el merge (pandas les habría puesto sufijo `_x`/`_y` en silencio, lo que
    # violaría "SIN TOCAR" las columnas de OFF).
    matriz_sin_duplicar = matriz.drop(columns=["snapshot_id", "nova_group", "additives_n"], errors="ignore")

    _asegurar_sin_colision_de_columnas(off, identidad_sin_duplicar, "off_mexico", "identidad_homologada")
    resultado = off.merge(identidad_sin_duplicar, on="code", how="left", validate="one_to_one")

    _asegurar_sin_colision_de_columnas(resultado, matriz_sin_duplicar, "off_mexico+identidad", "matriz_nut_100g")
    resultado = resultado.merge(matriz_sin_duplicar, on="code", how="left", validate="one_to_one")

    precio = _pivotear_precio(observaciones_resueltas)
    resultado = resultado.merge(precio, on="code", how="left", validate="one_to_one")
    # Ausencia de observación de precio -> UNAVAILABLE explícito, nunca NULL mudo (A2).
    resultado["price_status"] = resultado["price_status"].fillna("UNAVAILABLE")

    nombre_api = _pivotear_nombre_recuperado(observaciones_resueltas)
    resultado = resultado.merge(nombre_api, on="code", how="left", validate="one_to_one")

    # Override A39 sobre A38: una observación REAL de nombre por API gana sobre el resultado de
    # la homologación DERIVED del mismo registro (F.2: nunca un status peor por delante de uno
    # mejor). En la práctica hoy los 6 hits caen exactamente en los códigos que ya estaban
    # UNAVAILABLE tras homologar (verificado 2026-09-26), pero la regla se aplica de forma
    # general cuando una observación REAL trae nombre para un código que ya tenía uno
    # DERIVED.
    tiene_recuperado = ~resultado["nombre_recuperado_api"].apply(_es_nulo)
    resultado["product_name_source"] = "off_export"
    resultado.loc[tiene_recuperado, "product_name_homologated"] = resultado.loc[
        tiene_recuperado, "nombre_recuperado_api"
    ]
    resultado.loc[tiene_recuperado, "product_name_status"] = "REAL"
    resultado.loc[tiene_recuperado, "product_name_source"] = resultado.loc[
        tiene_recuperado, "nombre_recuperado_api_source"
    ]
    resultado = resultado.drop(columns=["nombre_recuperado_api", "nombre_recuperado_api_source"])
    resultado = aplicar_nombre_visible(resultado)

    assert len(resultado) == n_off, (
        f"El dataset de referencia debe tener una fila por code de off_mexico ({n_off}), "
        f"obtuvo {len(resultado)}."
    )
    assert resultado["code"].nunique() == n_off, "code duplicado tras los joins: revisar validate='one_to_one'."

    return resultado


def escribir_metadata(
    ruta_metadata: Path,
    *,
    fecha_off: str,
    fecha_identidad: str,
    fecha_matriz: str,
    fecha_experimento: str,
    fecha_open_prices: str,
    fecha_qqp: str,
    n_filas: int,
    n_columnas: int,
) -> None:
    """Metadato de tabla (F.2, punto 1): no se clona un `*_status` por columna de las 211
    columnas de OFF (son REAL por construcción); basta con listar aquí las fuentes y sus
    identificadores de versión. Mismo patrón que `_metadata.json` del snapshot crudo."""
    metadata = {
        "dataset_id": f"dataset_referencia_{time.strftime('%Y%m%d')}",
        "generated_at": datetime.now(UTC).isoformat(),
        "n_filas": n_filas,
        "n_columnas": n_columnas,
        "fuentes": {
            "off_mexico": f"off_csv_{fecha_off}",
            "identidad_homologada": f"identidad_homologada_{fecha_identidad}.parquet",
            "matriz_nut_100g": f"matriz_nut_100g_{fecha_matriz}.parquet",
            "experimento_recuperacion_nombres": f"experimento_recuperacion_nombres_{fecha_experimento}.parquet",
            "precios_open_prices": f"precios_open_prices_{fecha_open_prices}.parquet",
            "precios_qqp": f"precios_qqp_{fecha_qqp}.parquet",
        },
        "nota": (
            "Las 211 columnas del export de OFF son REAL por construcción (A33); ver "
            f"datos/snapshots/off_csv_{fecha_off}/_metadata.json para su procedencia completa. "
            "No se clona un status por columna para ese bloque; el diccionario de datos "
            "(docs/diccionario_dataset_referencia.md) documenta explícitamente cada columna "
            "añadida (identidad, matriz de nutrición, precio)."
        ),
        "fuera_de_alcance": (
            "No se tocó off_mexico_*.parquet ni el motor de scoring "
            "(src/nutrimatch/engine/*_score.py, services/catalog.py, services/ranking.py) — "
            "eso es el paso 10, explícitamente fuera de este paso (A43)."
        ),
    }
    ruta_metadata.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def reportar(resultado: pd.DataFrame, observaciones: pd.DataFrame) -> None:
    n = len(resultado)
    log(f"Filas: {n:,} (una por code, A34)")
    log(f"Columnas: {len(resultado.columns)}")
    log(f"Observaciones totales en la tabla consolidada: {len(observaciones):,}")
    for campo in ("product_name", "price"):
        n_obs = (observaciones["field"] == campo).sum()
        log(f"  field={campo}: {n_obs:,} observaciones")
    log(f"price_status=REAL: {(resultado['price_status'] == 'REAL').sum():,} de {n:,}")
    log(f"price_status=UNAVAILABLE: {(resultado['price_status'] == 'UNAVAILABLE').sum():,} de {n:,}")
    log(f"product_name_source=openfoodfacts_api_producto: {(resultado['product_name_source'] != 'off_export').sum():,}")
    log(f"universo_puntuable=True: {resultado['universo_puntuable'].sum():,} de {n:,}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aplicar-nombres",
        action="store_true",
        help="Solo cruza un catálogo ya materializado con la identidad homologada (LEFT JOIN por code)",
    )
    parser.add_argument(
        "--catalogo",
        default="datos/procesados/dataset_referencia_20260929.parquet",
        help="Parquet de catálogo que recibe el nombre visible",
    )
    parser.add_argument(
        "--identidad",
        default="datos/procesados/identidad_homologada_20260919.parquet",
        help="Parquet de identidad homologada (una fila por GTIN)",
    )
    parser.add_argument("--fecha-off", default="20260919")
    parser.add_argument("--fecha-identidad", default="20260919")
    parser.add_argument("--fecha-matriz", default="20260919")
    parser.add_argument("--fecha-experimento", default="20260919")
    parser.add_argument("--fecha-open-prices", default="20260926")
    parser.add_argument("--fecha-qqp", default="20260926")
    args = parser.parse_args()

    if args.aplicar_nombres:
        ruta_catalogo = Path(args.catalogo)
        if not ruta_catalogo.is_absolute():
            ruta_catalogo = REPO_ROOT / ruta_catalogo
        ruta_identidad = Path(args.identidad)
        if not ruta_identidad.is_absolute():
            ruta_identidad = REPO_ROOT / ruta_identidad
        log(f"LEFT JOIN {ruta_catalogo.name} × {ruta_identidad.name} por code")
        aplicar_nombres_homologados(ruta_catalogo, ruta_identidad, ruta_catalogo)
        log("Crudo intacto: off_mexico_*.parquet no se modificó")
        return 0

    ruta_off = PROCESADOS / f"off_mexico_{args.fecha_off}.parquet"
    ruta_identidad = PROCESADOS / f"identidad_homologada_{args.fecha_identidad}.parquet"
    ruta_matriz = PROCESADOS / f"matriz_nut_100g_{args.fecha_matriz}.parquet"
    ruta_experimento = PROCESADOS / f"experimento_recuperacion_nombres_{args.fecha_experimento}.parquet"
    ruta_open_prices = PROCESADOS / f"precios_open_prices_{args.fecha_open_prices}.parquet"
    ruta_qqp = PROCESADOS / f"precios_qqp_{args.fecha_qqp}.parquet"

    log("Leyendo fuentes...")
    try:
        off = _leer_parquet(ruta_off)
        identidad = _leer_parquet(ruta_identidad)
        matriz = _leer_parquet(ruta_matriz)
        experimento = _leer_parquet(ruta_experimento)
        precios_open_prices = _leer_parquet(ruta_open_prices)
        precios_qqp = _leer_parquet(ruta_qqp)
    except FileNotFoundError:
        return 1

    log("Construyendo tabla de observaciones (F.2)...")
    observaciones = construir_tabla_observaciones(experimento, precios_open_prices, precios_qqp)
    observaciones_resueltas = resolver_observaciones(observaciones)

    log("Construyendo dataset de referencia (joins encadenados por code)...")
    resultado = construir_dataset_referencia(off, identidad, matriz, observaciones_resueltas)

    log("")
    reportar(resultado, observaciones)

    fecha_salida = time.strftime("%Y%m%d")
    ruta_observaciones_out = PROCESADOS / f"observaciones_{fecha_salida}.parquet"
    ruta_dataset_out = PROCESADOS / f"dataset_referencia_{fecha_salida}.parquet"
    ruta_metadata_out = PROCESADOS / f"dataset_referencia_{fecha_salida}_metadata.json"

    observaciones.to_parquet(ruta_observaciones_out, index=False)
    resultado.to_parquet(ruta_dataset_out, index=False)
    escribir_metadata(
        ruta_metadata_out,
        fecha_off=args.fecha_off,
        fecha_identidad=args.fecha_identidad,
        fecha_matriz=args.fecha_matriz,
        fecha_experimento=args.fecha_experimento,
        fecha_open_prices=args.fecha_open_prices,
        fecha_qqp=args.fecha_qqp,
        n_filas=len(resultado),
        n_columnas=len(resultado.columns),
    )

    log("")
    log(f"Escrito: {ruta_observaciones_out.relative_to(REPO_ROOT)} ({ruta_observaciones_out.stat().st_size:,} bytes)")
    log(f"Escrito: {ruta_dataset_out.relative_to(REPO_ROOT)} ({ruta_dataset_out.stat().st_size:,} bytes)")
    log(f"Escrito: {ruta_metadata_out.relative_to(REPO_ROOT)}")
    log(f"Crudo intacto: {ruta_off.relative_to(REPO_ROOT)} (no se modificó)")
    log("No se tocó el motor de scoring (services/*, engine/*_score.py) — eso es el paso 10.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
