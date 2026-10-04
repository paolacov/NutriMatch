# Cierre funcional del sistema

El cierre funcional comprobó el recorrido de punta a punta: Angular llama a FastAPI, FastAPI lee el catálogo de referencia y el servicio de ranking aplica el motor sin cambiar sus fórmulas.

La API vigente carga `dataset_referencia_20261002.parquet` (13 093 productos). El perfil, el carrito y la comparación viven en el navegador. Los perfiles de evaluación que usa `scripts/confirmar_ranking_v1.py` sirven para reproducir conteos; no son una tabla de usuarios de la interfaz.

Recorrido validado:

```
Angular (frontend/)
  → GET /search | GET /products/{code} | POST /ranking | POST /ranking/explain
  → POST /cart/summary | POST /ai/ask
  → FastAPI (nutrimatch.api)
  → Catalog.from_referencia()
  → RankingService
```

El subpuntaje de procesamiento está en el Parquet. La dimensión nutricional, las preferencias, la cobertura y el resultado final se resuelven en la petición. La calidad de información está en el archivo y no entra al puntaje.

El ranking es un motor determinista de reglas, evidencia disponible y cobertura. El catálogo no contiene un desenlace observado de recomendación con el que entrenar y evaluar un modelo supervisado. Esa es la forma del sistema: cada resultado se calcula y se puede explicar con las tres dimensiones, los percentiles y el estado de los datos.

Las pruebas de este cierre viven en `tests/test_cierre_mvp.py` y en la batería de regresión del repositorio.
