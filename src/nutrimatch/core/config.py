"""Configuración del proceso.

Lee el archivo `.env` de la raíz del repositorio. Si una variable no está,
se usa el valor de aquí. El catálogo que carga la API es
``dataset_referencia_20261002.parquet``: 13 093 productos, con los tres
candados de ingesta ya aplicados.

Este módulo resuelve rutas. No imprime secretos. La clave de lenguaje viaja
en ``OPENAI_API_KEY`` y la lee la capa de lenguaje, no el motor.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Identificador del export de Open Food Facts del que sale el universo.
SNAPSHOT_ID_POR_DEFECTO = "off_csv_20260929"
# Nombre del Parquet operativo. La variable de entorno REFERENCIA_FILENAME
# puede sustituirlo; si no existe, la API usa este archivo.
REFERENCIA_FILENAME_POR_DEFECTO = "dataset_referencia_20261002.parquet"


def project_root() -> Path:
    """Raíz del repositorio: `src/nutrimatch/core/config.py` → tres niveles arriba."""
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Rutas del historial y del catálogo.

    ``referencia_filename`` es el archivo que abre ``Catalog.from_referencia``.
    El valor por defecto es el dataset operativo de 13 093 filas: nutrición del
    corte del 29 de septiembre de 2026, 259 precios reales y calidad de
    información. El crudo ``off_mexico_20260929.parquet`` alimenta la ingesta;
    la API no lo sirve.

    Las rutas relativas se resuelven desde la raíz del repositorio, tres niveles
    por encima de este archivo, para que ``make api`` y las pruebas encuentren
    ``datos/procesados/`` sin configuración extra.
    """

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nutrimatch_db_path: Path = Path("nutrimatch.db")
    snapshot_id: str = SNAPSHOT_ID_POR_DEFECTO
    processed_data_dir: Path = Path("datos/procesados")
    referencia_filename: str = REFERENCIA_FILENAME_POR_DEFECTO
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    def db_path(self) -> Path:
        """Ruta de SQLite para el historial y las corridas de ranking.

        Esa base solo guarda uso. El catálogo está en el Parquet. En local el
        archivo queda en la raíz del repositorio. En Vercel el disco de la
        función es de solo lectura fuera de ``/tmp``, así que el historial de
        esa instancia se escribe ahí.
        """
        if os.environ.get("VERCEL"):
            return Path("/tmp/nutrimatch.db")
        ruta = self.nutrimatch_db_path
        return ruta if ruta.is_absolute() else project_root() / ruta

    def processed_dir(self) -> Path:
        ruta = self.processed_data_dir
        return ruta if ruta.is_absolute() else project_root() / ruta

    def matriz_parquet(self) -> Path:
        return self.processed_dir() / f"matriz_nut_100g_{self.snapshot_date_suffix()}.parquet"

    def snapshot_parquet(self) -> Path:
        return self.processed_dir() / f"off_mexico_{self.snapshot_date_suffix()}.parquet"

    def referencia_parquet(self) -> Path:
        return self.processed_dir() / self.referencia_filename

    def snapshot_date_suffix(self) -> str:
        """`off_csv_20260919` → `20260919` (el id de snapshot del resto del proyecto)."""
        if "_" in self.snapshot_id:
            return self.snapshot_id.rsplit("_", 1)[-1]
        return self.snapshot_id


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(_env_file=project_root() / ".env")
