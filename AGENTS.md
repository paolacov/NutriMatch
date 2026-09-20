# Convenciones de NutriMatch

Documento de referencia del proyecto. Recoge las decisiones ya cerradas y las trampas verificadas de
las fuentes de datos. Si una decisión aparece aquí, ya está tomada: no se rediscute sin motivo
nuevo. Si algo aparece marcado como PENDIENTE o BLOQUEANTE, es una decisión que falta cerrar.

---

## Sección A. Decisiones metodológicas cerradas

### A1. Restricciones duras antes del ranking, y fuera de él

Las restricciones duras se aplican **antes** de puntuar y **no** forman parte del score.

- **Alergias: filtro fail-safe.** Ante la duda, el producto se excluye. Un dato ambiguo o ausente
  sobre un alérgeno declarado nunca se interpreta a favor del producto.
- **Dieta: tres estados**, no dos. Compatible, incompatible y **"no verificable"**. El tercer estado
  es obligatorio: los ingredientes de OFF no siempre permiten afirmar que un producto cumple una
  dieta, y afirmarlo sin evidencia sería inventar.
- **El país NO filtra.** El mercado se fija en la ingesta: el snapshot ya es México por
  construcción. No hay filtro de país en tiempo de consulta porque no hay nada que filtrar.

### A2. Datos faltantes: nunca imputar cero

Un cero es una afirmación nutricional ("este producto no tiene azúcar"). Un dato ausente no es esa
afirmación. Por tanto:

- **Sin dato = NULL + bandera explícita.** Jamás cero.
- **Regla de cobertura `cov`:**

  ```
  cov = (suma de los pesos de las dimensiones que SÍ tienen dato) / (suma de los pesos totales)
  ```

- Si `cov < 0.5`, el producto **no entra al ranking**: va a la banda **"información
  insuficiente"**, que se muestra separada. Comparar un producto con la mitad de sus datos ausentes
  contra uno completo produciría un orden falso.

### A3. Normalización por 100 g o 100 mL

El score y el ranking se calculan **siempre** sobre base 100 g (sólidos) o 100 mL (líquidos), la
misma base en que OFF publica los nutrientes.

Las **porciones se difieren a las alertas**, donde son informativas y opcionales. **Jamás se inventa
una porción**: si el producto no declara `serving_size`, no hay cálculo por porción.

### A4. Sin doble conteo: un constructo, una sola dimensión

Cada constructo se puntúa **una vez y en un solo lugar**.

- **NOVA sí puntúa** (es la dimensión D2): mide grado de procesamiento, información que los
  nutrientes no contienen.
- **Nutri-Score NO puntúa.** Se deriva de los mismos nutrientes que ya puntúa D1; incluirlo sería
  contar dos veces lo mismo. Se usa solo como **referencia mostrada** y como **parity-check** en la
  evaluación.

### A5. Precio: referencia informativa, no puntúa

PROFECO QQP aporta un **"precio de referencia"**.

- El cruce con el producto es **por texto** (marca + presentación + producto), porque **QQP no
  publica código de barras**. No hay clave común con OFF.
- El precio **no puntúa y no filtra**. Al ser un cruce difuso, meterlo en el score contaminaría un
  cálculo determinista con una coincidencia probabilística.
- **Prohibido el término "precio estimado".** Siempre "precio de referencia": el dato es un precio
  real observado por PROFECO en un establecimiento y una fecha, no una estimación nuestra.

### A6. Pesos del usuario: perfil base + orden de prioridades

La usuaria declara un **perfil base** y **ordena tres prioridades**. Ese orden se convierte
internamente en **pesos normalizados que suman 1**.

**Sin controles numéricos directos.** Nadie debería tener que decidir si la nutrición vale 0,45 o
0,50. Ordenar tres prioridades sí es una decisión humana razonable.

### A7. Score de compatibilidad: tres dimensiones ponderadas

Score aditivo de tres dimensiones, cada una en escala 0–100:

| Dim | Qué mide | Cómo se calcula |
| --- | --- | --- |
| **D1** | Nutrición | Nutrientes **con signo según el objetivo** (un nutriente puede ser deseable o indeseable según la meta declarada), evaluados **por percentil dentro de la categoría de referencia** |
| **D2** | Procesamiento | Grupo **NOVA 1–4** mapeado linealmente a **100–0** |
| **D3** | Preferencias | **Porcentaje de etiquetas valoradas** por la usuaria que el producto presenta |

El score final es la suma ponderada por los pesos de A6. Cada dimensión conserva su **subpuntaje**
visible.

### A8. Evaluación

Tres mecanismos:

1. **Golden set interno**: casos con resultado esperado, revisados a mano.
2. **Parity-check con Nutri-Score**: se comprueba que el orden de D1 correlacione razonablemente con
   Nutri-Score. Divergencias grandes son señal de error, no de mérito.
3. **Diagnóstico de cobertura**: cuántos productos caen en la banda "información insuficiente" y por
   qué dimensión.

### A9. Etiquetado frontal mexicano: informa, no puntúa

Los sellos de advertencia (`es:exceso-*`, NOM-051) se muestran y **generan alertas**, pero **no
puntúan**. Derivan de los mismos nutrientes de D1 (ver A4).

### A10. La explicación del porqué es la protagonista de la interfaz

No es un apéndice del resultado: es el producto. Cada resultado muestra:

- Subpuntaje por dimensión.
- Contribución de cada nutriente.
- Percentil dentro de la categoría.
- Peso aplicado.
- **Estado de los datos** (qué había, qué faltaba, qué se marcó con bandera).

### A11. Historial y lista de compras alimentan el `event_log`

Las decisiones y la lista de compras se registran en el `event_log`. **No puntúan**: son trazas de
uso, no evidencia nutricional.

### A12. Módulo carrito

Dos vistas más un resumen agregado:

- Vista **Plato del Bien Comer**.
- Vista **por categorías**.

Reglas de agregación, explícitas para que el número sea interpretable:

- **Promedio por 100 g** como método por defecto.
- **Ponderado por gramos solo si TODOS los productos tienen `quantity`.** Si falta uno, no se
  pondera.
- **Siempre con bandera de método y de cobertura**: quien lee el número sabe cómo se obtuvo.
- **Porcentajes por grupo con denominador = número de productos** (no gramos).
- Producto **sin categoría mapeable** va al bucket **"no clasificado"**, visible. No se fuerza.
- **Sin juicios médicos** en ningún resumen.

### A13. Capa LLM opcional

Tres roles, con `tools.py` como registro delgado sobre `engine/`:

- **planner**: traduce lenguaje natural a JSON validado. No calcula; elige qué operación
  determinista invocar.
- **critic**: auditor **determinista** (no es un LLM juzgando a otro LLM). Verifica que cada
  afirmación del texto esté respaldada por un hecho calculado.
- **narrate**: redacta la explicación en markdown.

Requisitos: **grounding obligatorio** sobre hechos calculados, **parsing JSON validado**,
**anonimización del identificador de usuario** antes de cualquier llamada, **caché** de respuestas y
**fallback determinista por plantillas**. Sin clave de API, todo funciona.

### A14. Arquitectura

El motor vive en el paquete `nutrimatch`, **reutilizado tal cual** por notebooks y UI. **Streamlit**
es la interfaz del MVP. **FastAPI y Angular quedan documentados como línea futura** en
[`docs/linea_futura.md`](docs/linea_futura.md), fuera del alcance.

---

## Sección B. Trampas verificadas en vivo el 2026-09-19

Todo lo de esta sección son **mediciones reales hechas el 2026-09-19**, no supuestos. Se citan con
su fecha porque los datos de OFF se regeneran a diario y los counts cambian.

### B1. Staging vs producción: la confusión que invalidó las primeras cifras

`world.openfoodfacts.net` es el entorno de **STAGING**: requiere **auth básica (off/off)** y
contiene una copia **PARCIAL** de la base. **NUNCA usarlo para construir el snapshot.** Producción es
`world.openfoodfacts.org`.

### B2. Counts de México (medidos el 2026-09-19)

| Consulta | Producción (`.org`) | Staging (`.net`) |
| --- | --- | --- |
| México, total | **17.741** | 11.995 |
| `states_tags=nutrition-facts-completed` | **13.633** | — |
| `states_tags=ingredients-completed` | **7.783** | — |

Las cifras previas de **9.681** y **6.469** venían de **staging** y quedan **descartadas**. No
usarlas en la memoria del proyecto.

### B3. El `HTTP 401` no era límite de tasa

El `HTTP 401` que se observaba era la **autenticación de staging**, no un rate limit. Diagnosticarlo
mal costó tiempo; conviene recordarlo.

### B4. Límites de tasa oficiales de OFF

- **10 peticiones/minuto** para `search`.
- **15 peticiones/minuto** para consultas de producto.
- Además, un **límite global anti-crawl** que responde **`HTTP 503` con independencia de la IP**.

Ese 503 apareció **3 veces en 9 peticiones**, incluso espaciando las peticiones **de 7 a 12
segundos**. Es decir: respetar el límite por minuto **no garantiza** que no aparezca.

### B5. Por eso el snapshot se construye desde el export, no paginando la API

La documentación de OFF **pide explícitamente** descargar los exports en CSV o JSONL si se necesitan
**más de unos cientos de productos**. El snapshot se construye **desde el export**. La **API queda
reservada al escaneo de un producto individual**.

### B6. Tamaños de los exports (medidos el 2026-09-19)

| Formato | Tamaño |
| --- | --- |
| **CSV comprimido** | **1,28 GB** ← **elegido** |
| Parquet (Hugging Face) | 7,89 GB |
| JSONL comprimido | 13,0 GB |
| Volcado MongoDB | 15,8 GB |

Se **regeneran a diario**, lo que da una **fecha de snapshot exacta y citable**. Se eligió el CSV
comprimido por ser un orden de magnitud más pequeño que las alternativas.

### B7. User-Agent obligatorio

OFF **exige un `User-Agent` identificable en todas las peticiones**. Se configura en
`OFF_USER_AGENT` con el formato `NombreApp/Version (email de contacto)`.

### B8. Versión de API: v2 para buscar

La **API v2 es la única con búsqueda estructurada**. **v3 no tiene búsqueda.**

### B9. PENDIENTE de confirmar al leer el esquema del export

Falta confirmar, leyendo la cabecera real del export, si existen las columnas:

- `main_category`
- `allergens_en`
- Las **imágenes de nutrición e ingredientes**.

Una prueba con **solo 2 productos no fue concluyente**, porque **OFF omite los campos vacíos** en la
respuesta: la ausencia de una columna en una muestra pequeña no prueba que la columna no exista.

### B10. BLOQUEANTE para D1: política de "categoría de referencia"

Falta definir **la política de categoría de referencia para los percentiles**. El problema:
`categories_tags` de OFF es **multietiqueta y jerárquica**, y un producto pertenece a **varias
categorías a la vez**. Sin una regla que elija una sola categoría de comparación, el percentil de D1
no está definido.

También falta fijar un **tamaño mínimo de categoría**: un percentil calculado sobre 3 productos no
es informativo.

**Esto bloquea D1.** Es la decisión más urgente del proyecto.

---

## Sección C. Convenciones de código

- **Idiomas separados por función.** Identificadores de código y nombres de tablas y columnas en
  **inglés con `snake_case`**. Documentación, comentarios y textos de interfaz en **español**.
- **Nombre unificado `ranking_run`**, nunca `scoring_run`. Un solo nombre para el concepto, en
  código, en base de datos y en documentación.
- **Los faltantes son NULL + bandera, nunca cero** (ver A2). Aplica en el dominio, en la base y en
  los esquemas.
- **Trazabilidad obligatoria**: todo dato lleva `snapshot_id` o `version`. Un resultado debe poder
 atribuirse a la versión exacta de los datos y del motor que lo produjeron.
- **Entorno con uv y Python 3.12.13, la versión de Google Colab.** El entorno se gestiona con **uv**
 y `.python-version` fija **3.12.13**, que es la versión exacta del runtime de Colab (2026.07). El
 motivo: el paquete `nutrimatch` se reutiliza tal cual en los notebooks (ver A14), y un intérprete
 distinto en local y en Colab abre la puerta a que el mismo código dé resultados distintos según
 dónde se ejecute. `pyproject.toml` conserva `requires-python = ">=3.11"` como suelo de
 compatibilidad del paquete: fija el mínimo, no el intérprete. `.python-version` **se versiona**.
