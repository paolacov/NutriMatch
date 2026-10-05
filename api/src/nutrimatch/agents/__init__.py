"""Roles de la capa de lenguaje.

Este paquete no ejecuta el ranking. Documenta los tres papeles que implementa
``nutrimatch.ai`` y que la API expone en ``POST /ai/ask``:

1. Planner. Traduce la pregunta a una operación ya definida. No calcula.
2. Critic. Comprueba, con reglas deterministas, que el texto cite hechos ya calculados.
3. Narrate. Redacta la explicación.

El motor de compatibilidad permanece en ``nutrimatch.engine``. Esta capa no
calcula nutrición, procesamiento, preferencias ni precio.
"""
