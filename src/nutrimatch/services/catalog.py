"""Carga del universo México desde Parquet y precálculo de D1 (agnóstico del usuario)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from nutrimatch.core.config import Settings, get_settings
from nutrimatch.core.errors import CatalogNotFoundError, ProductNotFoundError
from nutrimatch.engine.constants import CORE8_NUTRIENTES
from nutrimatch.engine.nutrition_score import calcular_subpuntaje_d1
from nutrimatch.engine.product_naming import resolver_nombre_producto

COLUMNAS_CRUDO: tuple[str, ...] = (
    "code",
    "product_name",
    "generic_name",
    "abbreviated_product_name",
    "labels_tags",
    "allergens",
    "traces",
    "ingredients_analysis_tags",
)


def _es_nulo(valor: Any) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def _percentiles_de_fila(fila: pd.Series) -> dict[str, float | None]:
    return {
        nutriente: None if _es_nulo(fila.get(f"percentil_{nutriente}")) else float(fila[f"percentil_{nutriente}"])
        for nutriente in CORE8_NUTRIENTES
    }


@dataclass
class Catalog:
    """Universo buscable (A19) con D1 ya calculado. D2 viene de `matriz_nut_100g` (paso 6)."""

    df: pd.DataFrame
    snapshot_id: str

    def n_puntuable(self) -> int:
        if "universo_puntuable" not in self.df.columns:
            return 0
        return int(self.df["universo_puntuable"].fillna(False).astype(bool).sum())

    @classmethod
    def from_parquet(cls, settings: Settings | None = None) -> Catalog:
        settings = settings or get_settings()
        matriz_path = settings.matriz_parquet()
        snapshot_path = settings.snapshot_parquet()
        if not matriz_path.exists() or not snapshot_path.exists():
            raise CatalogNotFoundError(
                f"Faltan Parquet del snapshot {settings.snapshot_id}: "
                f"{matriz_path} y/o {snapshot_path}"
            )
        return cls._from_paths(matriz_path, snapshot_path, settings.snapshot_id)

    @classmethod
    def from_dataframes(
        cls,
        matriz: pd.DataFrame,
        crudo: pd.DataFrame,
        snapshot_id: str,
    ) -> Catalog:
        """Construye un catálogo sintético (pruebas) con el mismo merge y D1 que producción."""
        df = _ensamblar(matriz, crudo)
        return cls(df=df, snapshot_id=snapshot_id)

    @classmethod
    def from_referencia(cls, settings: Settings | None = None) -> Catalog:
        """Carga el dataset analítico de referencia (A43) y calcula D1. No toca el crudo."""
        settings = settings or get_settings()
        ruta = settings.referencia_parquet()
        if not ruta.exists():
            raise CatalogNotFoundError(f"Falta el dataset de referencia: {ruta}")
        df = duckdb.execute(f"SELECT * FROM '{ruta.as_posix()}'").df()
        return cls.from_referencia_frame(df, settings.snapshot_id)

    @classmethod
    def from_referencia_frame(cls, df: pd.DataFrame, snapshot_id: str) -> Catalog:
        """Igual que `from_referencia`, sobre un DataFrame ya cargado (pruebas)."""
        return cls(df=_preparar_referencia(df), snapshot_id=snapshot_id)

    @classmethod
    def _from_paths(cls, matriz_path: Path, snapshot_path: Path, snapshot_id: str) -> Catalog:
        columnas = ", ".join(COLUMNAS_CRUDO)
        matriz = duckdb.execute(f"SELECT * FROM '{matriz_path.as_posix()}'").df()
        crudo = duckdb.execute(
            f"SELECT {columnas} FROM '{snapshot_path.as_posix()}'"
        ).df()
        return cls(df=_ensamblar(matriz, crudo), snapshot_id=snapshot_id)

    def get_row(self, code: str) -> pd.Series:
        coincidencias = self.df.loc[self.df["code"] == code]
        if coincidencias.empty:
            raise ProductNotFoundError(f"code no está en el catálogo: {code}")
        return coincidencias.iloc[0]


def _ensamblar(matriz: pd.DataFrame, crudo: pd.DataFrame) -> pd.DataFrame:
    df = matriz.merge(crudo, on="code", how="left", validate="one_to_one")
    if "product_name" in df.columns:
        df = df.rename(columns={"product_name": "product_name_bruto"})
    nombres = df.apply(
        lambda r: resolver_nombre_producto(
            r.get("product_name_bruto"), r.get("generic_name"), r.get("abbreviated_product_name")
        ),
        axis=1,
    )
    df["product_name"] = nombres.apply(lambda t: t[0])
    df["product_name_flag_respaldo_usado"] = nombres.apply(lambda t: t[1])

    d1_pares = df.apply(
        lambda r: calcular_subpuntaje_d1(_percentiles_de_fila(r)),
        axis=1,
    )
    df["d1"] = d1_pares.apply(lambda t: t[0])
    return df


def _preparar_referencia(crudo: pd.DataFrame) -> pd.DataFrame:
    """Alinea el Parquet de referencia al `df` que espera `RankingService` + la ficha."""
    df = crudo.copy()
    df["code"] = df["code"].astype(str)
    if "product_name_homologated" in df.columns:
        homologado = [_texto_o_none(v) for v in df["product_name_homologated"].tolist()]
        df["product_name"] = homologado
    d1_pares = df.apply(lambda r: calcular_subpuntaje_d1(_percentiles_de_fila(r)), axis=1)
    df["d1"] = d1_pares.apply(lambda t: t[0])
    return df


def _texto_o_none(valor: Any) -> str | None:
    if _es_nulo(valor):
        return None
    texto = str(valor).strip()
    return texto or None
