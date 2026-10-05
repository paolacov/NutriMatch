"""Única capa de persistencia: SQLite en modo WAL, reservada al estado mutable y regenerable
(perfil, `event_log`, carrito, `ranking_run`, caché de proveedor y de LLM). NO es la fuente de
verdad analítica: esa es el Parquet derivado del snapshot de Open Food Facts.
"""

from nutrimatch.db.connection import connect, init_db

__all__ = ["connect", "init_db"]
