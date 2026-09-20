"""Motor determinista de scoring y las operaciones que lo acompañan.

Score aditivo de tres dimensiones (D1 nutrición, D2 procesamiento NOVA, D3 preferencias) con
subpuntajes, percentiles calculados dentro de la categoría de referencia, regla de cobertura `cov`
y banda de "información insuficiente". Incluye las operaciones deterministas de filtro, ranking,
comparación, alertas y carrito. Es la única capa autorizada a calcular.
"""
