"""Jerarquía mínima de errores del paquete."""

from __future__ import annotations


class NutriMatchError(Exception):
    """Error de dominio o de orquestación (no de la fuente externa)."""


class CatalogNotFoundError(NutriMatchError):
    """No están los Parquet del universo México en la ruta configurada."""


class ProductNotFoundError(NutriMatchError):
    """El `code` pedido no está en el catálogo cargado."""
