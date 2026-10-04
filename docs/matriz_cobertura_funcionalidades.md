# Cobertura funcional

Estado del sistema sobre el catálogo operativo `dataset_referencia_20261002.parquet`.

| Comprobación | Resultado |
| --- | --- |
| Filas | 13 093 |
| Universo puntuable | 5 864 |
| Precio real | 259 (239 Open Prices y 20 PROFECO) |
| Precio `SYNTHETIC` dentro del Parquet | 0 |
| Precio no disponible dentro del Parquet | 12 834 |
| Calidad alta / insuficiente / media / baja | 6 102 / 4 206 / 1 511 / 1 274 |

El CSV `datos/procesados/matriz_cobertura_funcionalidades_20260927.csv` corresponde a una lectura anterior, sobre el corte de 16 851 filas. La API ya no carga ese corte.

## Funciones en operación

| Función | Dónde vive | Dato que usa |
| --- | --- | --- |
| Búsqueda | `GET /search` y la pantalla Buscar | Nombre resuelto y código, sobre los 13 093 |
| Ficha | `GET /products/{code}` | Nutrientes, ingredientes, sellos, procedencia y precio |
| Ranking explicable | `POST /ranking` y `POST /ranking/explain` | Perfil, cobertura y las tres dimensiones |
| Catálogo | `GET /catalog/categories` y `GET /catalog/products` | Categoría de referencia y nombre |
| Carrito | `POST /cart/summary` y la pantalla Carrito | Promedio por 100 g, con el método declarado |
| Comparación | Estado del navegador | Fichas ya cargadas |
| Historial | `GET /events` y `POST /events` | Registro de uso. No puntúa |
| Alertas | Pantalla Alertas | Sellos y porción declarada |
| Recetas y preguntas | `POST /ai/ask` y la pantalla Recetas | Hechos del motor. Sin clave, plantillas |
| Precio de demostración | Respuesta de la ficha | Fallback `SYNTHETIC` para los 12 834 sin observación |

Alergia y dieta se expresan en tres estados: apto, no apto y no verificable. La banda de información insuficiente separa a los productos cuya cobertura queda por debajo de 0,5.
