"""Pruebas del cliente de QQP (`nutrimatch.providers.qqp_api`).

Usan `httpx.MockTransport`: ninguna prueba de este archivo llama a una red real. La forma exacta
del JSON simulado replica la respuesta real de `datastore_search` verificada en vivo el
2026-09-26 (ver docstring del módulo bajo prueba).
"""

from __future__ import annotations

import json

import httpx

from nutrimatch.providers.qqp_api import buscar_por_categoria, buscar_texto


def _registro(id_: int, marca: str, producto: str, presentacion: str, precio: float = 25.0) -> dict:
    return {
        "_id": id_,
        "producto": producto,
        "presentacion": presentacion,
        "marca": marca,
        "categoria": "Café",
        "catalogo": "Básicos",
        "precio": precio,
        "fecha_registro": "2026-07-15",
        "cadena_comercial": "Walmart",
        "giro": "Supermercado",
        "nombre_comercial": "Walmart Constituyentes",
        "direccion": "Av. Constituyentes 123",
        "estado": "Querétaro",
        "municipio": "Corregidora",
        "latitud": 20.53,
        "longitud": -100.43,
    }


def _resultado(records: list[dict], total: int) -> dict:
    return {"help": "...", "success": True, "result": {"records": records, "total": total}}


def _cliente_con_respuestas(respuestas: list[httpx.Response]) -> httpx.Client:
    cola = list(respuestas)

    def handler(request: httpx.Request) -> httpx.Response:
        if not cola:
            raise AssertionError("Se pidieron más páginas de las configuradas en la prueba")
        return cola.pop(0)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_una_sola_pagina(tmp_path):
    registros = [_registro(1, "Nescafé. Clásico", "Café Soluble", "Frasco 120 Gr.")]
    cuerpo = _resultado(registros, total=1)
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    filas = buscar_por_categoria(
        "resource-x",
        "Café",
        cliente=cliente,
        directorio_cache=tmp_path,
        usar_cache=False,
    )

    assert len(filas) == 1
    assert filas[0]["marca"] == "Nescafé. Clásico"
    assert filas[0]["producto"] == "Café Soluble"


def test_pagina_hasta_agotar_total_o_limite_filas(tmp_path):
    pagina1 = _resultado(
        [_registro(1, "Marca A", "Producto 1", "Presentación 1"),
         _registro(2, "Marca B", "Producto 2", "Presentación 2")],
        total=3,
    )
    pagina2 = _resultado([_registro(3, "Marca C", "Producto 3", "Presentación 3")], total=3)
    cliente = _cliente_con_respuestas(
        [httpx.Response(200, json=pagina1), httpx.Response(200, json=pagina2)]
    )

    filas = buscar_por_categoria(
        "resource-x",
        "Café",
        cliente=cliente,
        limite_filas=300,
        directorio_cache=tmp_path,
        usar_cache=False,
        intervalo_entre_paginas_segundos=0.0,
    )

    assert [f["marca"] for f in filas] == ["Marca A", "Marca B", "Marca C"]


def test_respeta_limite_filas_sin_pedir_paginas_de_mas(tmp_path):
    # Categoría con 300 filas disponibles, pero limite_filas=2: solo debe pedir una página de 2.
    pagina1 = _resultado(
        [_registro(1, "Marca A", "Producto 1", "Presentación 1"),
         _registro(2, "Marca B", "Producto 2", "Presentación 2")],
        total=300,
    )
    cliente = _cliente_con_respuestas([httpx.Response(200, json=pagina1)])

    filas = buscar_por_categoria(
        "resource-x",
        "Café",
        cliente=cliente,
        limite_filas=2,
        directorio_cache=tmp_path,
        usar_cache=False,
    )

    assert len(filas) == 2


def test_cache_evita_repetir_la_peticion(tmp_path):
    cuerpo = _resultado([_registro(1, "Nescafé. Clásico", "Café Soluble", "Frasco 120 Gr.")], total=1)
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    primera = buscar_por_categoria(
        "resource-x", "Café", cliente=cliente, directorio_cache=tmp_path, usar_cache=True
    )
    assert len(primera) == 1

    # Segunda llamada con un cliente sin respuestas configuradas: si el código pidiera de nuevo,
    # el handler lanzaría AssertionError.
    cliente_vacio = _cliente_con_respuestas([])
    segunda = buscar_por_categoria(
        "resource-x", "Café", cliente=cliente_vacio, directorio_cache=tmp_path, usar_cache=True
    )
    assert len(segunda) == 1
    assert segunda[0]["marca"] == "Nescafé. Clásico"


def test_cache_persiste_como_json_legible(tmp_path):
    cuerpo = _resultado([_registro(1, "Nescafé. Clásico", "Café Soluble", "Frasco 120 Gr.")], total=1)
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    buscar_por_categoria(
        "resource-x", "Café", cliente=cliente, directorio_cache=tmp_path, usar_cache=True
    )

    rutas = list(tmp_path.glob("resource-x_Café_*.json"))
    assert len(rutas) == 1
    contenido = json.loads(rutas[0].read_text(encoding="utf-8"))
    assert contenido["total"] == 1
    assert contenido["records"][0]["marca"] == "Nescafé. Clásico"


def test_filtro_por_categoria_va_en_los_parametros(tmp_path):
    capturado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["params"] = dict(request.url.params)
        capturado["user_agent"] = request.headers.get("user-agent")
        return httpx.Response(200, json=_resultado([], total=0))

    cliente = httpx.Client(transport=httpx.MockTransport(handler))

    buscar_por_categoria(
        "resource-x", "Café", cliente=cliente, directorio_cache=tmp_path, usar_cache=False
    )

    assert json.loads(capturado["params"]["filters"]) == {"categoria": "Café"}
    assert capturado["params"]["resource_id"] == "resource-x"
    # Ver docstring del módulo: este proveedor exige un UA de navegador, a diferencia de OFF y
    # Open Prices, que aceptan un UA identificable.
    assert "Chrome" in capturado["user_agent"]


def test_buscar_texto_una_sola_pagina(tmp_path):
    registros = [_registro(1, "Nescafé. Clásico", "Café Soluble", "Frasco 120 Gr.")]
    cuerpo = _resultado(registros, total=1)
    cliente = _cliente_con_respuestas([httpx.Response(200, json=cuerpo)])

    filas = buscar_texto(
        "resource-x",
        "nescafe",
        cliente=cliente,
        directorio_cache=tmp_path,
        usar_cache=False,
    )

    assert len(filas) == 1
    assert filas[0]["marca"] == "Nescafé. Clásico"


def test_buscar_texto_envia_q_en_los_parametros(tmp_path):
    capturado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["params"] = dict(request.url.params)
        return httpx.Response(200, json=_resultado([], total=0))

    cliente = httpx.Client(transport=httpx.MockTransport(handler))

    buscar_texto(
        "resource-x", "leche", cliente=cliente, directorio_cache=tmp_path, usar_cache=False
    )

    assert capturado["params"]["q"] == "leche"
    assert capturado["params"]["resource_id"] == "resource-x"
