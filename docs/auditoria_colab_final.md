# Auditoría de Colab

Fecha: 3 de octubre de 2026. No se modificó el notebook, el PDF, el motor ni el dataset.

# Resultado

NO EJECUTADO EN COLAB

El ZIP mínimo sí se instaló y el notebook sí se ejecutó en una copia limpia, en `/tmp/nm-colab-run`, desconectada del entorno de desarrollo. Esa corrida no es Google Colab. Sirve para comprobar que el paquete, el Parquet y las celdas cierran solos. Quien entregue el trabajo todavía tiene que subir el ZIP a Colab y seguir `docs/reproducibilidad_colab_final.md`.

# Entorno

| Pieza | Validación local del ZIP | Google Colab |
| --- | --- | --- |
| Python | 3.12.13, el de `.python-version` | No ejecutado. Hace falta 3.11 o posterior |
| Instalación | `uv pip install -e .` sobre el ZIP descomprimido. OpenAI no quedó instalado | El paso equivalente es `pip install -e /content/nutrimatch` |
| Ubicación | `/tmp/nm-colab-run`, raíz del ZIP | Debe quedar en `/content/nutrimatch` |
| Dataset | `datos/procesados/dataset_referencia_20261002.parquet` | El mismo archivo, dentro del ZIP |

`pip install -e .` alcanzó para importar `nutrimatch`, `evaluacion`, pandas, pyarrow y matplotlib. No falta una dependencia del notebook. No se añadió ninguna.

El ZIP preparado está en la raíz del proyecto: `nutrimatch-colab.zip` (7,4 MB, 96 archivos). Incluye `src/`, `evaluacion/`, el Parquet oficial, el notebook, `pyproject.toml` y `README.md`. No incluye `.git`, cachés, entornos, `node_modules`, SQLite ni `.env`.

# Resultados verificados

Obtenidos en la copia limpia, no en Colab. El notebook terminó 64 celdas sin error.

| Resultado | Esperado | Obtenido | Estado |
| --- | ---: | ---: | --- |
| Productos | 13 093 | 13 093 | Coincide |
| Columnas del Parquet | 273 | 273 | Coincide |
| Universo puntuable | 5 864 | 5 864 | Coincide |
| Porcentaje | 44,79 % | 44,79 | Coincide |
| Discrepancias regla y bandera | 0 | 0 | Coincide |
| Calidad alta | 6 102 | 6 102 | Coincide |
| Calidad media | 1 511 | 1 511 | Coincide |
| Calidad baja | 1 274 | 1 274 | Coincide |
| Calidad insuficiente | 4 206 | 4 206 | Coincide |
| Precios REAL | 259 | 259 | Coincide |
| Precios UNAVAILABLE | 12 834 | 12 834 | Coincide |
| IMPUTED | 0 | 0 | Coincide |
| SYNTHETIC en el Parquet | 0 | 0 | Coincide |
| Casos de oro | 13, de ellos 12 pasan | 13, de ellos 12 pasan | Coincide |
| Caso distinto | contrato de nombre de `5060323907641` | el mismo caso y el mismo motivo | Coincide |
| Spearman | −0,475683 | −0,475683 | Coincide |
| n de Spearman | 6 035 | 6 035 | Coincide |
| D1, letra A | 59,68 | 59,68 | Coincide |
| D1, letra B | 54,80 | 54,80 | Coincide |
| D1, letra C | 50,87 | 50,87 | Coincide |
| D1, letra D | 49,00 | 49,00 | Coincide |
| D1, letra E | 41,57 | 41,57 | Coincide |
| Regla experimental, nutrición primero | 665 | 665 | Coincide |
| Regla experimental, procesamiento primero | 640 | 640 | Coincide |
| SHA-256 | `a621d471…045b` | el mismo | Coincide |
| Dos pasadas | mismo orden | Scores, bandas y orden iguales, n = 113 | Coincide |

La instalación resolvió pandas 3.0.6, numpy 2.5.3 y matplotlib 3.11.2. Con esas versiones las cifras no se movieron. No hubo motivo para cambiar el cuaderno.

# Problemas encontrados

## P0

Ninguno. Con el directorio de trabajo en la raíz del ZIP, la instalación y la ejecución terminan.

## P1

- Google Colab no se abrió desde aquí. La pasada del profesor sigue pendiente, con la guía ya escrita.
- La primera celda del notebook solo mira el directorio de trabajo y su padre. En Colab ese directorio no es la raíz del proyecto hasta que se ejecuta `%cd /content/nutrimatch` en el mismo kernel. Sin esa celda inicial, «Ejecutar todo» no encuentra el Parquet. No se cambió el notebook: el paso quedó en la guía.
- Un comando de shell con `!` en Colab puede no heredar el `%cd`. La guía usa rutas absolutas para `unzip`, `test` y `pip install`.

## P2

- La salida ya guardada en el notebook muestra la ruta de una corrida anterior. Al ejecutarlo de nuevo, esa línea cambia. No hace falta editar el archivo.
- En la prueba local, `plt.show()` avisó porque el backend era Agg, no interactivo. Ese aviso lo introdujo la prueba, no el cuaderno. Colab muestra las figuras sin ese backend.

# Instrucciones finales

1. Toma `nutrimatch-colab.zip` de la raíz del proyecto.
2. En Colab, sube el notebook maestro y sube el ZIP a `/content/nutrimatch-colab.zip`.
3. Inserta al inicio la celda de la guía (`unzip`, `%cd /content/nutrimatch`, comprobación `RAIZ_OK`, `pip install -e /content/nutrimatch`) y ejecútala.
4. Ejecuta el resto de las celdas de arriba abajo.
5. Comprueba la huella SHA-256, 5 864 productos puntuables y Spearman −0,475683 con n = 6 035. Si esas tres salidas aparecen y no hay celdas en error, la corrida de Colab quedó hecha.

El notebook, el PDF, el motor y el dataset no se modificaron.
