"""Genera el catálogo de figuras del dataset operativo.

Escribe cinco PNG en ``datos/procesados/figuras_universo_operativo_20261002/``.
No modifica el Parquet ni recalcula el ranking.

Uso:
    python scripts/figuras_universo_operativo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nutrimatch.eda.figures import catalogo

ORIGEN = REPO_ROOT / "datos" / "procesados" / "dataset_referencia_20261002.parquet"
DESTINO = REPO_ROOT / "datos" / "procesados" / "figuras_universo_operativo_20261002"
DATASET_ID = "dataset_referencia_20261002"


def main() -> None:
    if not ORIGEN.exists():
        raise SystemExit(f"No se encontró el dataset operativo: {ORIGEN.name}")
    marco = duckdb.execute(f"SELECT * FROM '{ORIGEN.as_posix()}'").df()
    figuras = catalogo(marco, dataset_id=DATASET_ID)
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, figura in figuras.items():
        ruta = DESTINO / f"{nombre}.png"
        figura.savefig(ruta, dpi=160)
        print(f"{ruta.relative_to(REPO_ROOT)} ({ruta.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
