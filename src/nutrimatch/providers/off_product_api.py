"""Cliente de la API de producto individual de Open Food Facts (`world.openfoodfacts.org`).

Consulta un `code` a la vez. El catálogo completo sale del export CSV
(`scripts/ingesta_off.py`). Esta API no se pagina para construir el snapshot.

Reglas de Open Food Facts, verificadas en vivo:

- 15 peticiones por minuto para la ficha de un producto. La búsqueda admite 10.
- Un límite anti-crawl responde HTTP 503 con independencia de la IP.
- Toda petición lleva un User-Agent identificable.
- Producción es `world.openfoodfacts.org`. `world.openfoodfacts.net` es staging
  (autenticación básica y copia parcial) y este módulo no lo usa.

Este módulo por eso:

1. Espacía las peticiones a un mínimo de `INTERVALO_MINIMO_SEGUNDOS` (4,5 s ⇒ ~13,3/min, por
   debajo de las 15/min permitidas, con margen para el reloj de OFF).
2. Reintenta con espera creciente ante `429` y `503`, y se detiene después de
   `MAX_REINTENTOS_ANTICRAWL` intentos. Un 503 repetido indica parar el lote.
3. Guarda cada respuesta en `datos/cache/off_producto_api/<code>.json`. Repetir un
   código no vuelve a pedir lo que ya está en caché. Esa caché no se versiona
   (ver `.gitignore`): acelera la reejecución y no es la fuente de verdad.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

# Mismo formato que scripts/ingesta_off.py: "NombreApp/Version (contacto)".
# Open Food Facts exige un agente identificable en cada petición.
USER_AGENT = "NutriMatch/0.1.0 (contacto: paola.nutrimatch@proton.me)"

# Producción. La ficha de un código conocido se lee en la API v2.
BASE_URL = "https://world.openfoodfacts.org/api/v2/product"

# Solo los campos que este experimento necesita: no se trae la ficha completa de cada producto.
CAMPOS_SOLICITADOS = "code,status,product_name,generic_name,abbreviated_product_name,brands"

# 60 / 15 = 4,0 s exactos; se añade margen porque B4 ya documentó 503 incluso espaciando de 7 a
# 12 s en un runs de solo 9 peticiones. No es una garantía, es la mejor política razonable.
INTERVALO_MINIMO_SEGUNDOS = 4.5

# Backoff ante 429/503: 15 s, 30 s, 60 s. Si el tercer intento también falla, se marca el
# código como error y se sigue con el siguiente: un límite anti-crawl persistente es una señal
# para el humano ("para el experimento"), no un problema que resolver a base de reintentos.
ESPERAS_REINTENTO_SEGUNDOS: tuple[float, ...] = (15.0, 30.0, 60.0)
MAX_REINTENTOS_ANTICRAWL = len(ESPERAS_REINTENTO_SEGUNDOS)

REPO_ROOT = Path(__file__).resolve().parents[3]
DIR_CACHE_POR_DEFECTO = REPO_ROOT / "datos" / "cache" / "off_producto_api"


@dataclass(frozen=True)
class RespuestaProductoOFF:
    """Resultado de consultar un `code` en la API de producto de OFF.

    `resultado` es uno de: `"encontrado"`, `"no_encontrado"` (OFF dice que el `code` no existe
    en su base viva), `"error_anticrawl"` (503/429 persistente tras agotar reintentos),
    `"error_otro"` (cualquier otro fallo HTTP o de red).
    """

    code: str
    resultado: str
    http_status: int | None
    product_name: str | None
    generic_name: str | None
    abbreviated_product_name: str | None
    brands: str | None
    desde_cache: bool
    intentos: int


class LimitadorDeTasa:
    """Espacia llamadas consecutivas al menos `intervalo_segundos` entre sí.

    Deliberadamente simple (un solo timestamp, un solo cliente): este experimento hace una
    petición a la vez, nunca en paralelo, así que no hace falta un limitador multihilo.
    """

    def __init__(self, intervalo_segundos: float) -> None:
        self._intervalo_segundos = intervalo_segundos
        self._ultima_llamada: float | None = None

    def esperar_turno(self) -> None:
        if self._ultima_llamada is not None:
            transcurrido = time.monotonic() - self._ultima_llamada
            faltante = self._intervalo_segundos - transcurrido
            if faltante > 0:
                time.sleep(faltante)
        self._ultima_llamada = time.monotonic()


def _ruta_cache(code: str, directorio_cache: Path) -> Path:
    return directorio_cache / f"{code}.json"


def _leer_cache(code: str, directorio_cache: Path) -> dict[str, Any] | None:
    ruta = _ruta_cache(code, directorio_cache)
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _escribir_cache(code: str, directorio_cache: Path, payload: dict[str, Any]) -> None:
    directorio_cache.mkdir(parents=True, exist_ok=True)
    _ruta_cache(code, directorio_cache).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _parsear_respuesta(code: str, http_status: int, cuerpo: dict[str, Any]) -> RespuestaProductoOFF:
    # La API v2 marca `status: 1` si encontró el producto, `0` si no. Confirmar por `status` en
    # vez de solo por el HTTP code: OFF puede responder 200 con `status: 0`.
    encontrado = bool(cuerpo.get("status")) and http_status == 200
    producto = cuerpo.get("product") or {}
    if not encontrado:
        return RespuestaProductoOFF(
            code=code,
            resultado="no_encontrado",
            http_status=http_status,
            product_name=None,
            generic_name=None,
            abbreviated_product_name=None,
            brands=None,
            desde_cache=False,
            intentos=0,
        )
    return RespuestaProductoOFF(
        code=code,
        resultado="encontrado",
        http_status=http_status,
        product_name=producto.get("product_name") or None,
        generic_name=producto.get("generic_name") or None,
        abbreviated_product_name=producto.get("abbreviated_product_name") or None,
        brands=producto.get("brands") or None,
        desde_cache=False,
        intentos=0,
    )


def obtener_producto(
    code: str,
    *,
    cliente: httpx.Client,
    limitador: LimitadorDeTasa,
    directorio_cache: Path = DIR_CACHE_POR_DEFECTO,
    usar_cache: bool = True,
) -> RespuestaProductoOFF:
    """Consulta un `code` en la API de producto de OFF, con caché, límite de tasa y reintentos.

    No lanza excepción ante 503/429: los agota con backoff y devuelve `error_anticrawl` para que
    el experimento pueda seguir con el resto de la muestra y reportar cuántos códigos quedaron
    sin resolver por esa causa, en vez de abortar todo el lote.
    """
    if usar_cache:
        cacheado = _leer_cache(code, directorio_cache)
        if cacheado is not None:
            respuesta = _parsear_respuesta(code, cacheado["http_status"], cacheado["cuerpo"])
            return RespuestaProductoOFF(
                **{**respuesta.__dict__, "desde_cache": True, "intentos": 0}
            )

    url = f"{BASE_URL}/{code}.json"
    intentos = 0
    while True:
        limitador.esperar_turno()
        intentos += 1
        try:
            resp = cliente.get(
                url,
                params={"fields": CAMPOS_SOLICITADOS},
                headers={"User-Agent": USER_AGENT},
                timeout=15.0,
            )
        except httpx.HTTPError:
            if intentos > MAX_REINTENTOS_ANTICRAWL:
                return RespuestaProductoOFF(
                    code=code,
                    resultado="error_otro",
                    http_status=None,
                    product_name=None,
                    generic_name=None,
                    abbreviated_product_name=None,
                    brands=None,
                    desde_cache=False,
                    intentos=intentos,
                )
            time.sleep(ESPERAS_REINTENTO_SEGUNDOS[intentos - 1])
            continue

        if resp.status_code in (429, 503):
            if intentos > MAX_REINTENTOS_ANTICRAWL:
                return RespuestaProductoOFF(
                    code=code,
                    resultado="error_anticrawl",
                    http_status=resp.status_code,
                    product_name=None,
                    generic_name=None,
                    abbreviated_product_name=None,
                    brands=None,
                    desde_cache=False,
                    intentos=intentos,
                )
            time.sleep(ESPERAS_REINTENTO_SEGUNDOS[intentos - 1])
            continue

        if resp.status_code == 404:
            respuesta = RespuestaProductoOFF(
                code=code,
                resultado="no_encontrado",
                http_status=404,
                product_name=None,
                generic_name=None,
                abbreviated_product_name=None,
                brands=None,
                desde_cache=False,
                intentos=intentos,
            )
            if usar_cache:
                _escribir_cache(code, directorio_cache, {"http_status": 404, "cuerpo": {}})
            return respuesta

        if resp.status_code != 200:
            return RespuestaProductoOFF(
                code=code,
                resultado="error_otro",
                http_status=resp.status_code,
                product_name=None,
                generic_name=None,
                abbreviated_product_name=None,
                brands=None,
                desde_cache=False,
                intentos=intentos,
            )

        cuerpo = resp.json()
        if usar_cache:
            _escribir_cache(code, directorio_cache, {"http_status": 200, "cuerpo": cuerpo})
        respuesta = _parsear_respuesta(code, 200, cuerpo)
        return RespuestaProductoOFF(**{**respuesta.__dict__, "intentos": intentos})
