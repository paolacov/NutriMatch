# Reproducir el notebook maestro en Google Colab

El cuaderno es `notebooks/06_notebook_maestro_nutrimatch.ipynb`. El único dataset que debe abrir es `datos/procesados/dataset_referencia_20261002.parquet`.

No hay un repositorio remoto. No se usa `git clone`.

El archivo para subir es `nutrimatch-colab.zip`, en la raíz del proyecto. Pesa 7,4 MB. La raíz del ZIP ya es la raíz del proyecto: al descomprimirlo aparecen `src/`, `evaluacion/`, `datos/procesados/dataset_referencia_20261002.parquet`, el notebook, `pyproject.toml` y `README.md`. No trae `.git`, entornos, `node_modules`, secretos ni el export grande de Open Food Facts.

Esta guía no se ejecutó dentro de Google Colab. El ZIP sí se instaló y el cuaderno sí se ejecutó en una copia limpia, fuera del entorno de desarrollo. Esa corrida no sustituye la de Colab. Los pasos de abajo son los que debe seguir quien lo abra allí.

## Qué tiene que quedar en PROJECT_ROOT

`PROJECT_ROOT` es la carpeta que contiene, al mismo tiempo:

- `pyproject.toml`
- `README.md`
- `src/nutrimatch/`
- `evaluacion/`
- `notebooks/06_notebook_maestro_nutrimatch.ipynb`
- `datos/procesados/dataset_referencia_20261002.parquet`

`README.md` hace falta para `pip install -e .`. El cuaderno no lo abre. Sin ese archivo, la instalación se detiene.

`pip install -e .` instala las dependencias del paquete, incluido lo que el cuaderno importa: pandas, pyarrow, matplotlib y el propio `nutrimatch`, más `evaluacion`. No instala OpenAI. El cuaderno no lo usa. No añadas SciPy, scikit-learn ni datos de Kaggle.

## Volver a generar el ZIP

Solo si el archivo de la raíz no está. Desde la raíz del proyecto:

```bash
zip -r nutrimatch-colab.zip \
  pyproject.toml \
  README.md \
  src \
  evaluacion \
  notebooks/06_notebook_maestro_nutrimatch.ipynb \
  datos/procesados/dataset_referencia_20261002.parquet \
  -x '*__pycache__*' '*.pyc' '*/.DS_Store'
```

## Pasos en Google Colab

El entorno de Colab tiene que ser Python 3.11 o posterior. El paquete declara `requires-python = ">=3.11"`. La validación local usó Python 3.12.13.

1. Entra a [https://colab.research.google.com](https://colab.research.google.com).
2. Sube el notebook: Archivo, Subir notebook, y elige `notebooks/06_notebook_maestro_nutrimatch.ipynb`. Puede salir del ZIP, descomprimido en tu máquina, o del proyecto.
3. En el panel de archivos de Colab, sube `nutrimatch-colab.zip` a `/content`. El nombre debe quedar `/content/nutrimatch-colab.zip`.
4. Inserta esta celda al inicio del notebook, antes de las que ya trae, y ejecútala una vez. Las rutas del shell van absolutas: en Colab, un comando con `!` no siempre hereda el directorio que cambió `%cd`.

```python
!unzip -q -o /content/nutrimatch-colab.zip -d /content/nutrimatch
%cd /content/nutrimatch
!test -f /content/nutrimatch/datos/procesados/dataset_referencia_20261002.parquet \
  && test -f /content/nutrimatch/pyproject.toml \
  && test -d /content/nutrimatch/src/nutrimatch \
  && test -d /content/nutrimatch/evaluacion \
  && echo RAIZ_OK
!pip install -e /content/nutrimatch
```

Tiene que imprimir `RAIZ_OK` y terminar la instalación sin error. `PROJECT_ROOT` queda en `/content/nutrimatch`.

5. Sin reiniciar el entorno, ejecuta el resto de las celdas de arriba abajo. Si aparece `ModuleNotFoundError`, reinicia el entorno y vuelve a ejecutar desde la celda del paso 4. No cambies el Parquet ni las comprobaciones.

La primera celda del cuaderno solo busca el dataset en el directorio de trabajo y en su padre. Por eso el `%cd` tiene que ocurrir en ese mismo kernel, antes de esas celdas. Si se abre el notebook y se ejecuta todo sin ese paso, no encuentra el archivo. No es una ruta escrita en el código.

La salida guardada en el archivo del notebook imprime una ruta de la máquina donde se ejecutó antes. Al correr en Colab, esa línea debe pasar a `/content/nutrimatch`.

## Cifras que deben aparecer

Si una comprobación no cuadra, la celda se detiene. No se sustituye el número obtenido por el esperado.

| Comprobación | Valor |
| --- | --- |
| Filas y columnas del Parquet | 13 093 × 273 |
| Códigos duplicados | 0 |
| SHA-256 | `a621d471a2f47aa09ba481408d95a7a808fe84bd2fa7205c56fa050e1c66045b` |
| Calidad alta, media, baja, insuficiente | 6 102, 1 511, 1 274, 4 206 |
| Precios REAL y UNAVAILABLE | 259 y 12 834 |
| Imputados y sintéticos en el Parquet | 0 y 0 |
| Universo puntuable | 5 864 (44,79 %), 0 desajustes con la regla |
| Regla | D2 presente y al menos 4 de 8 percentiles |
| Casos de oro | 13 presentes, 12 pasan |
| Caso que no pasa | `5060323907641`, por el contrato del nombre |
| Spearman | −0,475683, n = 6 035 |
| D1 promedio, letras A a E | 59,68; 54,80; 50,87; 49,00; 41,57 |
| Banda de ranking | 113 con nutrición primero, 114 con procesamiento primero |
| Regla experimental del cuaderno | 665 y 640 |
| Dos pasadas | mismos puntajes, mismas bandas, mismo orden |

La regla de 665 y 640 no es la banda de ranking de la aplicación.

La corrida sirvió si no hay celdas en error y aparecen juntas la huella SHA-256, el universo de 5 864 y la correlación −0,475683 con n = 6 035.
