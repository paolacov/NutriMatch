"""Pruebas del cliente de la API de producto de OFF (`nutrimatch.providers.off_product_api`).

Usan `httpx.MockTransport`: ninguna prueba de este archivo llama a una red real. Verifican el
contrato de negocio (caché, backoff ante 503, distinción encontrado/no-encontrado), no el
comportamiento real de `world.openfoodfacts.org`.
"""

from __future__ import annotations

import json
import time

import httpx
import pytest

from nutrimatch.providers.off_product_api import LimitadorDeTasa, obtener_producto


def _cliente_con_respuestas(respuestas: list[httpx.Response]) -> httpx.Client:
    """Devuelve un `httpx.Client` que responde con `respuestas` en orden, una por llamada."""
    cola = list(respuestas)

    def handler(request: httpx.Request) -> httpx.Response:
        if not cola:
            raise AssertionError("Se pidieron más respuestas de las configuradas en la prueba")
        return cola.pop(0)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _limitador_sin_espera() -> LimitadorDeTasa:
    """Limitador con intervalo 0: las pruebas no deben tardar segundos reales."""
    return LimitadorDeTasa(intervalo_segundos=0.0)


def test_producto_encontrado_devuelve_nombres(tmp_path):
    cuerpo = {
        "status": 1,
        "product": {
            "product_name": "Totopos de maíz horneados con nopal",
            "generic_name": None,
            "abbreviated_product_name": None,
            "brands": "Marca X",
        },
    }
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    respuesta = obtener_producto(
        "7503028965717",
        cliente=cliente,
        limitador=_limitador_sin_espera(),
        directorio_cache=tmp_path,
        usar_cache=False,
    )

    assert respuesta.resultado == "encontrado"
    assert respuesta.product_name == "Totopos de maíz horneados con nopal"
    assert respuesta.brands == "Marca X"
    assert respuesta.desde_cache is False


def test_producto_no_encontrado_por_status_cero(tmp_path):
    cuerpo = {"status": 0, "product": {}}
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    respuesta = obtener_producto(
        "0000000000000",
        cliente=cliente,
        limitador=_limitador_sin_espera(),
        directorio_cache=tmp_path,
        usar_cache=False,
    )

    assert respuesta.resultado == "no_encontrado"
    assert respuesta.product_name is None


def test_producto_no_encontrado_por_http_404(tmp_path):
    cliente = _cliente_con_respuestas([httpx.Response(404, json={})])

    respuesta = obtener_producto(
        "0000000000000",
        cliente=cliente,
        limitador=_limitador_sin_espera(),
        directorio_cache=tmp_path,
        usar_cache=False,
    )

    assert respuesta.resultado == "no_encontrado"
    assert respuesta.http_status == 404


def test_503_se_reintenta_y_luego_se_resuelve(tmp_path, monkeypatch):
    # No dormir de verdad en la prueba: solo importa que SÍ hubo reintento, no cuánto duró.
    monkeypatch.setattr(time, "sleep", lambda _segundos: None)

    cuerpo_ok = {"status": 1, "product": {"product_name": "Producto recuperado"}}
    cliente = _cliente_con_respuestas(
        [httpx.Response(503, text="anti-crawl"), httpx.Response(200, json=cuerpo_ok)]
    )

    respuesta = obtener_producto(
        "1111111111111",
        cliente=cliente,
        limitador=_limitador_sin_espera(),
        directorio_cache=tmp_path,
        usar_cache=False,
    )

    assert respuesta.resultado == "encontrado"
    assert respuesta.product_name == "Producto recuperado"
    assert respuesta.intentos == 2


def test_503_persistente_se_rinde_tras_agotar_reintentos(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _segundos: None)

    # 1 intento inicial + 3 reintentos (MAX_REINTENTOS_ANTICRAWL) = 4 respuestas 503.
    cliente = _cliente_con_respuestas([httpx.Response(503, text="anti-crawl")] * 4)

    respuesta = obtener_producto(
        "2222222222222",
        cliente=cliente,
        limitador=_limitador_sin_espera(),
        directorio_cache=tmp_path,
        usar_cache=False,
    )

    assert respuesta.resultado == "error_anticrawl"
    assert respuesta.http_status == 503


def test_cache_evita_una_segunda_peticion_http(tmp_path):
    cuerpo = {"status": 1, "product": {"product_name": "Cacheado"}}
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    primera = obtener_producto(
        "3333333333333",
        cliente=cliente,
        limitador=_limitador_sin_espera(),
        directorio_cache=tmp_path,
        usar_cache=True,
    )
    assert primera.desde_cache is False
    assert primera.product_name == "Cacheado"

    # Un segundo cliente sin respuestas configuradas: si el código intentara pedir de nuevo,
    # `_cliente_con_respuestas` lanzaría AssertionError dentro del handler.
    cliente_vacio = _cliente_con_respuestas([])
    segunda = obtener_producto(
        "3333333333333",
        cliente=cliente_vacio,
        limitador=_limitador_sin_espera(),
        directorio_cache=tmp_path,
        usar_cache=True,
    )
    assert segunda.desde_cache is True
    assert segunda.product_name == "Cacheado"


def test_cache_persiste_como_json_legible(tmp_path):
    cuerpo = {"status": 1, "product": {"product_name": "Legible"}}
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    obtener_producto(
        "4444444444444",
        cliente=cliente,
        limitador=_limitador_sin_espera(),
        directorio_cache=tmp_path,
        usar_cache=True,
    )

    ruta = tmp_path / "4444444444444.json"
    assert ruta.exists()
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    assert contenido["http_status"] == 200
    assert contenido["cuerpo"]["product"]["product_name"] == "Legible"


def test_limitador_espacia_llamadas(monkeypatch):
    tiempos = iter([0.0, 0.1, 5.0])
    monkeypatch.setattr(time, "monotonic", lambda: next(tiempos))
    dormidos: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda segundos: dormidos.append(segundos))

    limitador = LimitadorDeTasa(intervalo_segundos=4.5)
    limitador.esperar_turno()  # primera llamada: no espera (no hay `_ultima_llamada` aún)
    limitador.esperar_turno()  # segunda: han pasado 0.1s de 4.5s -> debe dormir 4.4s

    assert dormidos == [pytest.approx(4.4)]
