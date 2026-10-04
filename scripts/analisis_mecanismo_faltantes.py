"""Mecanismo de faltantes (MCAR/MAR/MNAR) en CORE8, categoría y variables afines — paso 7.

Ver `docs/diagnostico_calidad_datos.md` (sección H, fila 7, y tabla E.1) y la decisión A42 de
`AGENTS.md`. Mide, sobre el snapshot real, si la ausencia de cada variable depende de otra
variable **observada** (presencia de `ingredients_text`/`ingredients_tags`, y el score
`completeness` que ya calcula OFF) — la prueba operativa de "no es MCAR, es consistente con
MAR condicionado a X" que pide el paso 8. El script mide la ausencia y no imputa.

No imputa nada: solo mide y reporta (A2, A36 siguen vigentes). No escribe ningún Parquet nuevo;
el resumen se guarda como CSV legible en `datos/procesados/re_eda_20260926/`, mismo patrón que
el resto de esa carpeta (paso 1, notebook 08).

Uso:
    python scripts/analisis_mecanismo_faltantes.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

CORE8 = (
    "energy-kcal_100g",
    "fat_100g",
    "saturated-fat_100g",
    "carbohydrates_100g",
    "sugars_100g",
    "proteins_100g",
    "salt_100g",
    "fiber_100g",
)


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def _es_nulo_texto(serie: pd.Series) -> pd.Series:
    """Cubre `None`, `NaN` y la cadena literal `'nan'` (trampa B13: texto ausente vía DuckDB)."""
    return serie.isna() | (serie.astype(str).str.strip().str.lower().isin(["", "nan"]))


def cargar_columnas(ruta_off: Path) -> pd.DataFrame:
    con = duckdb.connect()
    columnas_core8 = ", ".join(f'"{c}"' for c in CORE8)
    otras = (
        "categories_tags",
        "ingredients_text",
        "ingredients_tags",
        "ingredients_analysis_tags",
        "allergens",
        "traces",
        "labels_tags",
        "nova_group",
        "completeness",
        "brands",
    )
    columnas = f"{columnas_core8}, {', '.join(otras)}"
    df = con.execute(
        f"SELECT {columnas} FROM read_parquet('{ruta_off.as_posix()}')"
    ).df()
    # `completeness` llega como VARCHAR (mismo patrón que `nutriscore_score`, B14): convertir
    # explícitamente antes de cualquier comparación numérica.
    df["completeness_num"] = pd.to_numeric(df["completeness"], errors="coerce")
    return df


def medir_variable(nombre: str, ausente: pd.Series, sin_ingredientes: pd.Series, completeness: pd.Series) -> dict:
    pct_faltante = ausente.mean()
    p_falta_sin_ing = ausente[sin_ingredientes].mean()
    p_falta_con_ing = ausente[~sin_ingredientes].mean()
    razon = p_falta_sin_ing / max(p_falta_con_ing, 1e-9)
    comp_si_falta = completeness[ausente].mean()
    comp_si_tiene = completeness[~ausente].mean()
    return {
        "variable": nombre,
        "pct_faltante": round(pct_faltante * 100, 1),
        "p_falta_sin_ingredientes": round(p_falta_sin_ing * 100, 1),
        "p_falta_con_ingredientes": round(p_falta_con_ing * 100, 1),
        "razon_sin_vs_con_ingredientes": round(razon, 2),
        "completeness_si_falta": round(comp_si_falta, 3),
        "completeness_si_tiene": round(comp_si_tiene, 3),
    }


def construir_resumen(df: pd.DataFrame) -> pd.DataFrame:
    sin_ingredientes = _es_nulo_texto(df["ingredients_text"]) & _es_nulo_texto(df["ingredients_tags"])
    completeness = df["completeness_num"]

    filas = []
    for nut in CORE8:
        filas.append(medir_variable(nut, df[nut].isna(), sin_ingredientes, completeness))

    filas.append(
        medir_variable("categories_tags", _es_nulo_texto(df["categories_tags"]), sin_ingredientes, completeness)
    )
    filas.append(medir_variable("nova_group", df["nova_group"].isna(), sin_ingredientes, completeness))
    filas.append(
        medir_variable(
            "ingredients_analysis_tags (dieta)",
            _es_nulo_texto(df["ingredients_analysis_tags"]),
            sin_ingredientes,
            completeness,
        )
    )
    filas.append(
        medir_variable(
            "allergens+traces (ambos vacíos)",
            _es_nulo_texto(df["allergens"]) & _es_nulo_texto(df["traces"]),
            sin_ingredientes,
            completeness,
        )
    )
    filas.append(medir_variable("labels_tags (sellos)", _es_nulo_texto(df["labels_tags"]), sin_ingredientes, completeness))

    return pd.DataFrame(filas)


def reportar(resumen: pd.DataFrame, n_faltantes_core8: pd.Series, correlacion: float) -> None:
    log("Resumen por variable (% faltante, y su relación con tener o no ingredientes):")
    for _, fila in resumen.iterrows():
        log(
            f"  {fila['variable']}: {fila['pct_faltante']}% faltante | "
            f"P(falta|sin ingredientes)={fila['p_falta_sin_ingredientes']}% | "
            f"P(falta|con ingredientes)={fila['p_falta_con_ingredientes']}% | "
            f"razón={fila['razon_sin_vs_con_ingredientes']}x | "
            f"completeness si falta={fila['completeness_si_falta']} si tiene={fila['completeness_si_tiene']}"
        )
    log("")
    log("Distribución de cuántos de los 8 CORE8 le faltan a cada producto (patrón 'todo o nada'):")
    for n, conteo in n_faltantes_core8.value_counts().sort_index().items():
        log(f"  {n} faltantes: {conteo} productos")
    log(f"Correlación completeness vs. nº de CORE8 faltantes: {correlacion:.3f}")


def main() -> int:
    ruta_off = REPO_ROOT / "datos" / "procesados" / "off_mexico_20260919.parquet"
    ruta_salida = REPO_ROOT / "datos" / "procesados" / "re_eda_20260926" / "mecanismo_faltantes.csv"

    if not ruta_off.exists():
        log(f"ERROR: no existe {ruta_off}. Corre `make ingest-off` primero.")
        return 1

    log(f"Leyendo: {ruta_off.relative_to(REPO_ROOT)}")
    df = cargar_columnas(ruta_off)
    log(f"Universo: {len(df):,} productos")
    log("")

    resumen = construir_resumen(df)
    n_faltantes_core8 = df[list(CORE8)].isna().sum(axis=1)
    correlacion = df["completeness_num"].corr(n_faltantes_core8)

    reportar(resumen, n_faltantes_core8, correlacion)

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    resumen.to_csv(ruta_salida, index=False, encoding="utf-8")
    log("")
    log(f"Escrito: {ruta_salida.relative_to(REPO_ROOT)}")
    log(
        "No se imputó nada (A2/A36 siguen vigentes): este script solo mide el mecanismo de "
        "faltantes, no rellena ningún valor."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
