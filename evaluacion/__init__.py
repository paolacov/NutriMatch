"""Evaluación del motor de scoring (decisión A8, AGENTS.md): tres mecanismos independientes.

- ``golden_set``: casos con resultado esperado, revisados a mano, sobre productos reales del
  snapshot. Ver `AGENTS.md` para el criterio de selección de los casos.
- ``parity_check``: correlación entre el orden de D1 y Nutri-Score. Divergencias grandes son
  señal de error en el motor, no de mérito (D1 y Nutri-Score no tienen por qué coincidir
  exactamente: puntúan nutrientes distintos y con metodologías distintas).
- ``coverage_diagnostic``: cuántos productos caen en la banda "información insuficiente" y por
  qué dimensión, para un perfil de usuario dado.

Vive fuera de `src/nutrimatch` a propósito: es instrumentación para verificar el motor, no lógica
de producto que la UI necesite importar. Se instala en editable junto al paquete `nutrimatch`
(ver `pyproject.toml`) para que notebooks y pruebas puedan importarlo sin manipular `sys.path`.
"""
