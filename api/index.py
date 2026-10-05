"""Entrada de FastAPI para Vercel."""

from __future__ import annotations

import sys
from pathlib import Path

# El servicio de Vercel tiene como raíz api/.
# El paquete NutriMatch vive dentro de api/src/.
_RAIZ = Path(__file__).resolve().parent
_SRC = _RAIZ / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from nutrimatch.api.app import create_app

app = create_app()
