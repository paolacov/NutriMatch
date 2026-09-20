"""Modelos de dominio (producto, usuario, carrito) independientes de la persistencia y de la UI.

Regla invariable: un dato faltante se representa como NULL más una bandera explícita, NUNCA como
cero.
"""
