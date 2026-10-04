"""Entrada de FastAPI en Vercel.

Vercel carga la variable ``app`` de este módulo. El archivo vive en ``api/``
para que el runtime de Python lo publique como función, y ``vercel.json``
le reenvía las rutas de la API (``/meta``, ``/search``, ``/products``,
``/catalog``, ``/ranking``, ``/cart``, ``/events``, ``/ai``) conservando
la ruta original. Así los decoradores de ``nutrimatch.api.app`` coinciden
con lo que llama Angular.

``src/`` se añade al camino de importación porque el paquete no está
instalado dentro de la función: viaja junto al código por ``includeFiles``.
Al importar este módulo se abre el Parquet operativo
(``dataset_referencia_20261002.parquet``).
"""

from __future__ import annotations

import sys
from pathlib import Path

# api/index.py → raíz del repositorio → src/nutrimatch
_RAIZ = Path(__file__).resolve().parents[1]
_SRC = _RAIZ / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from nutrimatch.api.app import create_app

# La construcción carga el catálogo una vez por instancia de la función.
app = create_app()
