"""Infraestructura transversal: configuración y errores."""

from nutrimatch.core.config import Settings, get_settings, project_root
from nutrimatch.core.errors import CatalogNotFoundError, NutriMatchError, ProductNotFoundError

__all__ = [
    "CatalogNotFoundError",
    "NutriMatchError",
    "ProductNotFoundError",
    "Settings",
    "get_settings",
    "project_root",
]
