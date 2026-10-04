"""Precio de demostración determinista a partir del GTIN.

No es una observación de mercado. El Parquet operativo guarda REAL o UNAVAILABLE.
La ficha convierte UNAVAILABLE en SYNTHETIC solo al responder, con esta función,
para que Angular no invente el monto. El ranking no la usa.
"""

from __future__ import annotations

NOTA_PRECIO_DEMOSTRACION = "Dato simulado para demostración"
FUENTE_PRECIO_DEMOSTRACION = "demo"


def precio_demostracion_mxn(code: str) -> int:
    """Entero entre 12 y 180. Misma cuenta que el antiguo hash del cliente.

    El desplazamiento ``>>> 0`` de JavaScript es un uint32. Con dígitos de un
    GTIN el producto ``hash * 31`` cabe en un entero exacto de JS, así que
    enmascarar a 32 bits reproduce el mismo resultado.
    """
    acumulado = 0
    for caracter in code:
        acumulado = (acumulado * 31 + ord(caracter)) & 0xFFFFFFFF
    return 12 + (acumulado % 169)
