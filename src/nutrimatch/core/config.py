"""Configuración del proceso: rutas locales leídas de `.env` (pydantic-settings).

No carga secretos hacia logs. Las variables de OFF (`OFF_USER_AGENT`, etc.) se ignoran aquí:
este corte de la app lee el snapshot local y no llama a la API.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SNAPSHOT_ID_POR_DEFECTO = "off_csv_20260919"


def project_root() -> Path:
    """Raíz del repositorio: `src/nutrimatch/core/config.py` → tres niveles arriba."""
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Rutas de persistencia y del snapshot procesado.

    `NUTRIMATCH_DB_PATH` ya está en `.env.example`. Las rutas de Parquet tienen valor por
    defecto relativo a la raíz del repo para que `make api` y pytest hallen el dataset de
    referencia en `datos/procesados/` sin configuración extra.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nutrimatch_db_path: Path = Path("nutrimatch.db")
    snapshot_id: str = SNAPSHOT_ID_POR_DEFECTO
    processed_data_dir: Path = Path("datos/procesados")
    referencia_filename: str = "dataset_referencia_20260927.parquet"
    ranking_top_n: int = 25

    def db_path(self) -> Path:
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
    return Settings()
