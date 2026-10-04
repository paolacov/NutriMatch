"""Pruebas del cliente de Open Prices (`nutrimatch.providers.open_prices_api`).

Usan `httpx.MockTransport`: ninguna prueba de este archivo llama a una red real. La forma exacta
del JSON simulado aquí replica la respuesta real verificada en vivo el 2026-09-26 (ver docstring
del módulo bajo prueba), no una suposición.
"""

from __future__ import annotations

import json

import httpx

from nutrimatch.providers.open_prices_api import obtener_precios_por_moneda


def _item(id_: int, product_code: str, price: float = 25.0, country_code: str = "MX") -> dict:
    return {
        "id": id_,
        "price": price,
        "currency": "MXN",
        "date": "2024-06-10",
        "product_code": product_code,
        "location": {
            "osm_name": "Walmart Constituyentes",
            "osm_address_city": "Corregidora",
            "osm_address_country": "México",
            "osm_address_country_code": country_code,
            "osm_lat": 20.53,
            "osm_lon": -100.43,
        },
    }


def _pagina(items: list[dict], page: int, pages: int, total: int) -> dict:
    return {"items": items, "page": page, "pages": pages, "size": 100, "total": total}


def _cliente_con_respuestas(respuestas: list[httpx.Response]) -> httpx.Client:
    cola = list(respuestas)

    def handler(request: httpx.Request) -> httpx.Response:
        if not cola:
            raise AssertionError("Se pidieron más páginas de las configuradas en la prueba")
        return cola.pop(0)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_una_sola_pagina(tmp_path):
    cuerpo = _pagina([_item(1, "7501300801197")], page=1, pages=1, total=1)
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    resultados = obtener_precios_por_moneda(
        "MXN", cliente=cliente, directorio_cache=tmp_path, usar_cache=False
    )

    assert len(resultados) == 1
    fila = resultados[0]
    assert fila.product_code == "7501300801197"
    assert fila.price == 25.0
    assert fila.currency == "MXN"
    assert fila.retailer == "Walmart Constituyentes"
    assert fila.location_country_code == "MX"
    assert fila.source_url.endswith("/1")


def test_pagina_solicita_todas_las_paginas_reportadas(tmp_path):
    pagina1 = _pagina([_item(1, "0001"), _item(2, "0002")], page=1, pages=2, total=3)
    pagina2 = _pagina([_item(3, "0003")], page=2, pages=2, total=3)
    cliente = _cliente_con_respuestas(
        [httpx.Response(200, json=pagina1), httpx.Response(200, json=pagina2)]
    )

    resultados = obtener_precios_por_moneda(
        "MXN",
        cliente=cliente,
        directorio_cache=tmp_path,
        usar_cache=False,
        intervalo_entre_paginas_segundos=0.0,
    )

    assert [r.product_code for r in resultados] == ["0001", "0002", "0003"]


def test_cache_evita_repetir_la_peticion(tmp_path):
    cuerpo = _pagina([_item(1, "7501300801197")], page=1, pages=1, total=1)
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    primera = obtener_precios_por_moneda(
        "MXN", cliente=cliente, directorio_cache=tmp_path, usar_cache=True
    )
    assert len(primera) == 1

    # Segunda llamada con un cliente sin respuestas configuradas: si el código pidiera de nuevo,
    # el handler lanzaría AssertionError.
    cliente_vacio = _cliente_con_respuestas([])
    segunda = obtener_precios_por_moneda(
        "MXN", cliente=cliente_vacio, directorio_cache=tmp_path, usar_cache=True
    )
    assert len(segunda) == 1
    assert segunda[0].product_code == "7501300801197"


def test_cache_persiste_como_json_legible(tmp_path):
    cuerpo = _pagina([_item(1, "7501300801197")], page=1, pages=1, total=1)
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    obtener_precios_por_moneda(
        "MXN", cliente=cliente, directorio_cache=tmp_path, usar_cache=True
    )

    ruta = tmp_path / "MXN_pagina_1.json"
    assert ruta.exists()
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    assert contenido["total"] == 1
    assert contenido["items"][0]["product_code"] == "7501300801197"


def test_fila_sin_location_no_falla(tmp_path):
    item_sin_location = {
        "id": 9,
        "price": 10.0,
        "currency": "MXN",
        "date": None,
        "product_code": "0009",
        "location": None,
    }
    cuerpo = _pagina([item_sin_location], page=1, pages=1, total=1)
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    resultados = obtener_precios_por_moneda(
        "MXN", cliente=cliente, directorio_cache=tmp_path, usar_cache=False
    )

    assert len(resultados) == 1
    assert resultados[0].retailer is None
    assert resultados[0].location_country_code is None
