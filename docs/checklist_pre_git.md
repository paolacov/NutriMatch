# Checklist previo a Git

Marcas de la auditoría del 3 de octubre de 2026. Una casilla en OK se apoya en una comprobación hecha sobre este árbol. REVISAR significa que el código o la configuración están en su sitio y falta un paso humano o una prueba que esta auditoría no cerró. PENDIENTE es un hueco que hay que resolver antes de publicar.

El repositorio Git ya está inicializado en `main`. No hace falta `git init`. No hay remoto. Esta auditoría no ejecutó `git add` ni `git push`.

## Lista

- [OK] Proyecto ejecuta en pruebas. `pytest` del entorno `.venv`: 338 passed, 1 skipped, 47,68 s. La prueba omitida es el smoke en vivo de OpenAI (`tests/test_ai_ask_openai_live.py`), que llama al servicio real y no se usó como evidencia.
- [REVISAR] Backend en un proceso largo. `make api` está definido y las pruebas de API pasan, incluidas las que abren el Parquet operativo. No se dejó `uvicorn` escuchando ni se llamó a `curl http://127.0.0.1:8000/meta` en esta pasada.
- [REVISAR] Frontend en el navegador. `frontend/node_modules/.bin/ng build --configuration development` terminó bien (salida en `frontend/dist`, luego borrada; esa carpeta está ignorada). No se abrió `http://127.0.0.1:4200` ni se recorrieron las pantallas. `npm test` (Karma) no se ejecutó.
- [OK] API responde dentro de pytest. `tests/test_api.py` y `tests/test_dataset_operativo.py::test_api_operativa_emite_real_y_demostracion` forman parte de los 338 passed.
- [OK] Dataset correcto identificado. `get_settings().referencia_parquet()` apunta a `datos/procesados/dataset_referencia_20261002.parquet`. SHA-256 `a621d471a2f47aa09ba481408d95a7a808fe84bd2fa7205c56fa050e1c66045b`, 13 093 filas, 273 columnas, 5 864 puntuables. Coincide con el metadato y con `.env`.
- [OK] Dependencias documentadas. Python `3.12.13` en `.python-version` y en el `.venv`. FastAPI `0.141.1`, uvicorn `0.53.0`, pydantic `2.13.5`, pandas `3.0.6` y DuckDB `1.5.5` en `uv.lock`. Angular `^20.3.0` en `frontend/package.json`. Node observado `v24.21.0`, dentro del rango `^20.19.0 || ^22.12.0 || >=24.0.0` del lock. uv observado `0.12.17`, no pinneado en el repo.
- [OK] `.env.example` creado y actualizado. Nombres de variables, sin claves. Incluye `PROCESSED_DATA_DIR` comentada.
- [OK] Secretos fuera del repositorio. `.env` está en `.gitignore`, no está en el índice y no aparece en el historial. El archivo local sí tiene `OPENAI_API_KEY` con valor. No se copió aquí.
- [OK] `.gitignore` revisado. Ignora `.env`, entornos, cachés, SQLite, `node_modules`, `frontend/dist`, `frontend/.angular`, logs, el gzip de snapshots, la caché, las figuras, las capturas `prueba-codigo*.png` y el PDF generado. El Parquet operativo no queda ignorado (`git check-ignore` sale 1).
- [OK] Datos clasificados. Ver [`datos.md`](datos.md).
- [OK] SQLite clasificado. Estado de uso, regenerable al arrancar la API, fuera de Git. El perfil de la interfaz está en el navegador.
- [OK] Documentación actualizada. README, mapa, datos, decisiones, reproducibilidad, atribución y este checklist.
- [OK] Arquitectura documentada. [`mapa_proyecto.md`](mapa_proyecto.md), sección B, contrastada con `create_app` y `Catalog.from_referencia`.
- [OK] Engine documentado. Sección F del mapa, sin cambiar fórmulas. Criterios de origen en `AGENTS.md`.
- [OK] Endpoints documentados. Los 13 de `src/nutrimatch/api/app.py`.
- [OK] Frontend documentado. Rutas de `app.routes.ts` y llamadas de `product.repository.ts`.
- [OK] Pruebas de Python revisadas. 338 passed. Huecos: no hay prueba de extremo a extremo en el navegador; las specs de Angular cubren consultas, formato, onboarding y el plato, no cada pantalla; el smoke de OpenAI en vivo no se ejecutó contra el servicio.
- [OK] Archivos temporales identificados. Clasificación A/B/C/D en el mapa. No se borró código de producto. Se borró solo `frontend/dist` generado por la compilación de esta auditoría.
- [REVISAR] Licencias. OFF (ODbL, DbCL, CC BY-SA) está en `docs/ATTRIBUTION.md`. PROFECO: `AGENTS.md` afirma CC-BY 4.0 y el texto no está en el repo. Open Prices no tiene un identificador de licencia propio copiado. USDA no es fuente. Ilustraciones de Nuti: sin aviso de terceros.
- [OK] README reproducible. Instalación, ejecución, dataset, huella, motor, pantallas y qué queda fuera de Git.
- [REVISAR] Proyecto listo para el commit que lo publique. Falta añadir el Parquet operativo y el código que hoy está sin seguimiento (frontend, `api/`, docs, pruebas nuevas). El remoto no existe. No subir `.env`.

## Qué no se marcó OK a propósito

- Recorrido manual de Inicio, búsqueda, ficha, carrito y alternativas en el navegador.
- `make api` dejado en marcha.
- Llamada real a OpenAI.
- `npm test`.
- Confirmación externa de la licencia de PROFECO y de Open Prices.
