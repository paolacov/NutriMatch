# Línea futura

> **Nada de este documento forma parte del MVP.** Se registra aquí para dejar constancia de que la
> arquitectura fue considerada y descartada de forma deliberada, no por desconocimiento. El MVP es
> el paquete `nutrimatch` más una interfaz Streamlit.

## Por qué se descarta del MVP

La **rúbrica académica exige una interfaz en Streamlit o Gradio**, así que construir un frontend
Angular y un backend HTTP no sumaría puntos y sí restaría tiempo al motor, que es donde está el
aporte real del proyecto.

Descartarlo no cierra la puerta. **El motor vive en el paquete `nutrimatch`**, con la lógica de
scoring, filtrado, comparación y carrito completamente separada de la interfaz. Streamlit importa ese
paquete igual que lo haría FastAPI. Por eso **migrar a FastAPI más adelante no requeriría reescribir
la lógica**: bastaría con escribir la capa de endpoints y la serialización, porque los esquemas
pydantic v2 de `schemas/` ya son el contrato de entrada y salida. La decisión de no hacerlo ahora es
de alcance, no de arquitectura.

---

## Backend: FastAPI con uvicorn

Aproximadamente **8 endpoints**, uno por operación determinista ya existente en `engine/`:

| Endpoint | Responsabilidad |
| --- | --- |
| `search` | Búsqueda de productos en el universo México |
| `ranking` | Ranking personalizado contra el perfil |
| `compare` | Comparación directa entre productos |
| `cart` | Carrito y sus vistas agregadas |
| `alerts` | Alertas (sellos frontales, alérgenos, porciones) |
| `price` | Precio de referencia de PROFECO QQP |
| `chat` | Entrada en lenguaje natural hacia la capa LLM opcional |
| `meta` | Metadatos del snapshot, versión del motor y atribución |

## Frontend: Angular 22 con Tailwind v4

Interfaz web propia, en sustitución de Streamlit, con control total sobre el diseño de la explicación
del porqué (que es la protagonista de la interfaz).

## Despliegue: docker-compose con nginx

Composición de contenedores para backend, frontend y nginx como proxy inverso y servidor de los
archivos estáticos.

## Autenticación: JWT

Tokens JWT para sesiones de usuario. El MVP no tiene autenticación: el perfil es local y la
persistencia es un SQLite en la máquina de la usuaria.

## Páginas de BI y administración

- **BI**: tableros de uso, distribución de scores y cobertura de datos por categoría.
- **Administración**: gestión de snapshots, revisión de cruces de precio dudosos y control de la
  caché de proveedor y de LLM.
