"""Construye el Parquet de identidad homologada (nombre y marca) — paso 3 del plan de trabajo.

Ver `docs/diagnostico_calidad_datos.md` (sección H, paso 3) y las decisiones A28/A33/A37/A38 de
`AGENTS.md`. Lee el snapshot México ya construido y escribe un Parquet **nuevo**, sin tocar el
crudo (A2):

    datos/procesados/off_mexico_20260919.parquet   (crudo, NO se modifica)
        -> datos/procesados/identidad_homologada_20260919.parquet   (DERIVED, nuevo)

Columnas del resultado, una fila por `code` (A34):

    code
    product_name_original            REAL, tal cual vino en `product_name` (puede ser None)
    product_name_field_source        product_name | generic_name | abbreviated_product_name | None
    product_name_flag_respaldo_usado True si field_source no es "product_name"
    product_name_flag_placeholder_removido  True si se descartó un "Cargando…" en el camino
    product_name_homologated         DERIVED: normalizado cosméticamente, o None
    product_name_status              DERIVED | UNAVAILABLE (A33)
    brand_original                   REAL, tal cual vino en `brands` (puede ser None)
    brand_homologated                DERIVED: llave de coincidencia (minúsculas, sin acento)
    brand_status                     DERIVED | UNAVAILABLE (A33)
    snapshot_id
    generated_at

Uso:
    uv run python scripts/homologar_identidad.py
    uv run python scripts/homologar_identidad.py --fecha 20260919
"""

from __future__ import annotations

import argparse
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from nutrimatch.engine.identity_homologation import homologar_marca, resolver_nombre_homologado

REPO_ROOT = Path(__file__).resolve().parents[1]


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def _es_nulo(valor: Any) -> bool:
    """None o NaN de pandas (B13, AGENTS.md): un valor ausente nunca es cero ni cadena vacía."""
    if valor is None:
        return True
    return isinstance(valor, float) and math.isnan(valor)


def construir_identidad_homologada(crudo: pd.DataFrame, snapshot_id: str) -> pd.DataFrame:
    """Aplica la homologación fila a fila sobre las columnas de identidad del crudo.

    Deliberadamente NO usa `DataFrame.apply(..., result_type="expand")` ni `Series.map` para
    repartir la tupla resuelta en columnas: en pandas 3.x, construir una columna mixta de `str`
    y `None` a partir de esas operaciones infiere el nuevo dtype `str` nativo y silenciosamente
    convierte cada `None` en `float('nan')` (la misma trampa B13 de AGENTS.md, pero disparada por
    este código en vez de por la lectura del Parquet). Un chequeo `campo is not None` sobre esa
    columna ya coercionada marcaría TODAS las filas como "con dato". Se evita calculando cada
    fila con Python puro (sobre listas, no sobre una `Series` intermedia) y derivando
    `*_status`/`*_flag_*` con `_es_nulo` — que cubre `None` y `NaN` por igual — antes de que
    pandas tenga oportunidad de coercionar nada.
    """
    filas = zip(
        crudo["product_name"].tolist(),
        crudo["generic_name"].tolist(),
        crudo["abbreviated_product_name"].tolist(),
        crudo["brands"].tolist(),
        strict=True,
    )

    product_name_original: list[str | None] = []
    product_name_field_source: list[str | None] = []
    product_name_flag_respaldo_usado: list[bool] = []
    product_name_flag_placeholder_removido: list[bool] = []
    product_name_homologated: list[str | None] = []
    product_name_status: list[str] = []
    brand_original: list[str | None] = []
    brand_homologated: list[str | None] = []
    brand_status: list[str] = []

    for product_name, generic_name, abbreviated_product_name, brands in filas:
        product_name_original.append(None if _es_nulo(product_name) else str(product_name))

        nombre, campo, removio_placeholder = resolver_nombre_homologado(
            product_name, generic_name, abbreviated_product_name
        )
        product_name_field_source.append(campo)
        product_name_flag_respaldo_usado.append(not _es_nulo(campo) and campo != "product_name")
        product_name_flag_placeholder_removido.append(removio_placeholder)
        product_name_homologated.append(nombre)
        product_name_status.append("UNAVAILABLE" if _es_nulo(nombre) else "DERIVED")

        brand_original.append(None if _es_nulo(brands) else str(brands))
        marca = homologar_marca(brands)
        brand_homologated.append(marca)
        brand_status.append("UNAVAILABLE" if _es_nulo(marca) else "DERIVED")

    return pd.DataFrame(
        {
            "code": crudo["code"].tolist(),
            "product_name_original": product_name_original,
            "product_name_field_source": product_name_field_source,
            "product_name_flag_respaldo_usado": product_name_flag_respaldo_usado,
            "product_name_flag_placeholder_removido": product_name_flag_placeholder_removido,
            "product_name_homologated": product_name_homologated,
            "product_name_status": product_name_status,
            "brand_original": brand_original,
            "brand_homologated": brand_homologated,
            "brand_status": brand_status,
            "snapshot_id": snapshot_id,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    )


def reportar(resultado: pd.DataFrame, crudo: pd.DataFrame) -> None:
    # `resultado["*_status"]` y `resultado["*_flag_*"]` son str/bool "limpios" (se calcularon con
    # `_es_nulo` antes de ensamblar el DataFrame), así que sí es seguro compararlos con `==` aquí.
    # `resultado["*_homologated"]`/`brand_original` pueden venir NaN (no None) tras el ensamblado;
    # se cuentan por el status ya calculado, nunca por `.isna()` directo sobre esas columnas.
    n = len(resultado)
    sin_nombre_original = crudo["product_name"].isna().sum()
    sin_nombre_homologado = (resultado["product_name_status"] == "UNAVAILABLE").sum()
    respaldo = resultado["product_name_flag_respaldo_usado"].sum()
    placeholder = resultado["product_name_flag_placeholder_removido"].sum()
    recuperados_por_placeholder = (
        resultado["product_name_flag_placeholder_removido"] & (resultado["product_name_status"] == "DERIVED")
    ).sum()
    marcas_originales = crudo["brands"].dropna().str.lower().str.strip().nunique()
    marcas_homologadas = resultado.loc[resultado["brand_status"] == "DERIVED", "brand_homologated"].nunique()

    log(f"Productos: {n:,}")
    log(f"  product_name original vacío: {sin_nombre_original:,}")
    log(f"  sin ningún nombre tras homologar (UNAVAILABLE): {sin_nombre_homologado:,}")
    log(f"  usó respaldo (generic_name/abbreviated): {respaldo:,}")
    log(f"  placeholder 'Cargando…' descartado: {placeholder:,} (de los cuales recuperó nombre real: {recuperados_por_placeholder:,})")
    log(f"  marcas únicas antes de homologar (lower/trim): {marcas_originales:,}")
    log(f"  marcas únicas después de homologar (acento plegado): {marcas_homologadas:,}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fecha", default="20260919", help="fecha del snapshot (ej. 20260919)")
    args = parser.parse_args()

    snapshot_id = f"off_csv_{args.fecha}"
    ruta_crudo = REPO_ROOT / "datos" / "procesados" / f"off_mexico_{args.fecha}.parquet"
    ruta_salida = REPO_ROOT / "datos" / "procesados" / f"identidad_homologada_{args.fecha}.parquet"

    if not ruta_crudo.exists():
        log(f"ERROR: no existe {ruta_crudo}. Corre `make ingest-off` primero.")
        return 1

    log(f"Leyendo {ruta_crudo.relative_to(REPO_ROOT)}")
    con = duckdb.connect()
    crudo = con.execute(
        f"SELECT code, product_name, generic_name, abbreviated_product_name, brands "
        f"FROM '{ruta_crudo.as_posix()}'"
    ).df()

    log("Homologando nombre y marca (DERIVED, sin tocar el crudo)")
    resultado = construir_identidad_homologada(crudo, snapshot_id)

    reportar(resultado, crudo)

    resultado.to_parquet(ruta_salida, index=False)
    log(f"Escrito: {ruta_salida.relative_to(REPO_ROOT)} ({ruta_salida.stat().st_size:,} bytes)")
    log(f"Crudo intacto: {ruta_crudo.relative_to(REPO_ROOT)} (no se modificó)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
