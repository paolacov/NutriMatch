"""Confirma el ranking v1 sobre el dataset de referencia — paso 10 (decisión A44).

Reproduce las cifras ya publicadas de cobertura (G.1, A22, A27, A31) leyendo
`dataset_referencia_*.parquet`, no `off_mexico` + `matriz` por separado. Si alguna cifra no
cuadra, el script falla: eso sería un join roto del paso 9, no un motivo para cambiar D1/D2/D3.

No imputa, no baja `cov`, no mete precio en el score, no toca `engine/*_score.py` ni
`services/ranking.py` (G.4; A5; A2). El precio se reporta solo como cobertura informativa.

Uso:
    uv run python scripts/confirmar_ranking_v1.py
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from evaluacion.coverage_diagnostic import diagnosticar_cobertura
from nutrimatch.engine.nutrition_score import (
    NUTRIENTES_D1_SIGNO,
    calcular_subpuntaje_d1,
)
from nutrimatch.engine.preference_score import calcular_d3
from nutrimatch.engine.user_weights import convertir_prioridades_a_pesos

# Cifras ya publicadas (G.1 / A22 / A27 / A31 / A43). El script debe reproducirlas exactas.
N_UNIVERSO = 16_851
N_D1_CALCULABLE = 7_040
N_D2_CALCULABLE = 6_781
N_UNIVERSO_PUNTUABLE = 5_864
N_PRICE_REAL = 263
N_INSUFICIENTE = {"Ana": 9_517, "Caro": 10_974}

PERFILES = {
    "Ana": {
        "etiquetas_valoradas": ["en:organic", "en:no-gluten"],
        "orden_prioridades": ["D1", "D3", "D2"],
    },
    "Beto": {
        "etiquetas_valoradas": ["en:fair-trade"],
        "orden_prioridades": ["D2", "D1", "D3"],
    },
    "Caro": {
        "etiquetas_valoradas": [],
        "orden_prioridades": ["D3", "D1", "D2"],
    },
}


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def _es_nulo(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return bool(pd.isna(valor))


def percentiles_d1_de_fila(fila: pd.Series) -> dict[str, float | None]:
    """Lee los 5 percentiles con signo de una fila del dataset de referencia."""
    return {
        nutriente: None if _es_nulo(fila.get(f"percentil_{nutriente}")) else float(fila[f"percentil_{nutriente}"])
        for nutriente in NUTRIENTES_D1_SIGNO
    }


def d1_es_calculable(fila: pd.Series) -> bool:
    d1, _ = calcular_subpuntaje_d1(percentiles_d1_de_fila(fila))
    return d1 is not None


def d2_es_calculable(fila: pd.Series) -> bool:
    return not _es_nulo(fila.get("d2"))


def medir_g1(df: pd.DataFrame) -> dict[str, int]:
    """Cobertura agnóstica del usuario (G.1 / A22 / A27) + precio informativo (A5, no puntúa)."""
    n_d1 = int(df.apply(d1_es_calculable, axis=1).sum())
    n_d2 = int(df.apply(d2_es_calculable, axis=1).sum())
    n_puntuable = int(df["universo_puntuable"].sum())
    n_price_real = int((df["price_status"] == "REAL").sum()) if "price_status" in df.columns else 0
    return {
        "n_total": len(df),
        "n_d1_calculable": n_d1,
        "n_d2_calculable": n_d2,
        "n_universo_puntuable": n_puntuable,
        "n_price_real": n_price_real,
    }


def disponibilidad_para_perfil(df: pd.DataFrame, etiquetas_valoradas: list[str]) -> pd.DataFrame:
    """Una fila por producto con D1/D2/D3 disponibles para ese perfil (A19, A31)."""
    return pd.DataFrame(
        {
            "D1": df.apply(d1_es_calculable, axis=1),
            "D2": df.apply(d2_es_calculable, axis=1),
            "D3": df["labels_tags"].apply(lambda tags: calcular_d3(tags, etiquetas_valoradas) is not None),
        }
    )


def medir_a31(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Banda `cov < 0.5` y causa dominante, mismos perfiles que el notebook 04."""
    reportes: dict[str, dict[str, Any]] = {}
    for nombre, perfil in PERFILES.items():
        pesos = convertir_prioridades_a_pesos(perfil["orden_prioridades"])
        disponibilidad = disponibilidad_para_perfil(df, perfil["etiquetas_valoradas"])
        reporte = diagnosticar_cobertura(disponibilidad, pesos)
        desglose = reporte["desglose_por_combinacion_faltante"]
        dominante = desglose.iloc[0]["dimensiones_faltantes"] if not desglose.empty else None
        reportes[nombre] = {
            "n_informacion_insuficiente": reporte["n_informacion_insuficiente"],
            "porcentaje_informacion_insuficiente": round(reporte["porcentaje_informacion_insuficiente"], 1),
            "causa_dominante": dominante,
        }
    return reportes


def construir_resumen(g1: dict[str, int], a31: dict[str, dict[str, Any]]) -> pd.DataFrame:
    filas = [
        {"grupo": "G1", "metrica": "n_total", "valor": g1["n_total"], "esperado": N_UNIVERSO},
        {"grupo": "G1", "metrica": "n_d1_calculable", "valor": g1["n_d1_calculable"], "esperado": N_D1_CALCULABLE},
        {"grupo": "G1", "metrica": "n_d2_calculable", "valor": g1["n_d2_calculable"], "esperado": N_D2_CALCULABLE},
        {
            "grupo": "G1",
            "metrica": "n_universo_puntuable",
            "valor": g1["n_universo_puntuable"],
            "esperado": N_UNIVERSO_PUNTUABLE,
        },
        {"grupo": "A5", "metrica": "n_price_real", "valor": g1["n_price_real"], "esperado": N_PRICE_REAL},
    ]
    for nombre, esperado in N_INSUFICIENTE.items():
        filas.append(
            {
                "grupo": "A31",
                "metrica": f"n_insuficiente_{nombre}",
                "valor": a31[nombre]["n_informacion_insuficiente"],
                "esperado": esperado,
            }
        )
        filas.append(
            {
                "grupo": "A31",
                "metrica": f"causa_dominante_{nombre}",
                "valor": a31[nombre]["causa_dominante"],
                "esperado": "D1+D2+D3",
            }
        )
    resumen = pd.DataFrame(filas)
    resumen["ok"] = resumen["valor"] == resumen["esperado"]
    return resumen


def main() -> int:
    ruta = REPO_ROOT / "datos" / "procesados" / "dataset_referencia_20260926.parquet"
    ruta_salida = REPO_ROOT / "datos" / "procesados" / "re_eda_20260926" / "confirmacion_ranking_v1.csv"

    if not ruta.exists():
        log(f"ERROR: no existe {ruta}. Corre `scripts/construir_dataset_referencia.py` primero.")
        return 1

    log(f"Leyendo: {ruta.relative_to(REPO_ROOT)}")
    df = duckdb.execute(f"SELECT * FROM read_parquet('{ruta.as_posix()}')").df()
    log(f"Filas: {len(df):,}")

    g1 = medir_g1(df)
    log(
        f"G.1: D1={g1['n_d1_calculable']:,}  D2={g1['n_d2_calculable']:,}  "
        f"universo_puntuable={g1['n_universo_puntuable']:,}  price_REAL={g1['n_price_real']:,} (no puntúa, A5)"
    )

    a31 = medir_a31(df)
    for nombre, reporte in a31.items():
        log(
            f"A31 {nombre}: insuficientes={reporte['n_informacion_insuficiente']:,} "
            f"({reporte['porcentaje_informacion_insuficiente']}%)  "
            f"causa dominante={reporte['causa_dominante']}"
        )

    resumen = construir_resumen(g1, a31)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    resumen.to_csv(ruta_salida, index=False, encoding="utf-8")
    log(f"Escrito: {ruta_salida.relative_to(REPO_ROOT)}")

    fallos = resumen[~resumen["ok"]]
    if not fallos.empty:
        log("ERROR: cifras que no reproducen las publicadas (G.1 / A31 / A43):")
        for _, fila in fallos.iterrows():
            log(f"  {fila['metrica']}: obtenido={fila['valor']} esperado={fila['esperado']}")
        return 1

    log("Todas las cifras reproducen. Ranking v1 confirmado (A44): no se cambian fórmulas.")
    log("No se tocó engine/*_score.py ni services/ranking.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
