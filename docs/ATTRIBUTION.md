# Atribución de fuentes de datos

NutriMatch no genera datos de producto ni de precios: los toma de dos fuentes externas. Este
documento recoge sus licencias, las obligaciones que imponen y cómo citarlas.

---

## Open Food Facts

Base de datos colaborativa y abierta de productos alimentarios.

### Licencias

Open Food Facts distribuye su contenido bajo **tres licencias distintas** según el tipo de material:

| Material | Licencia |
| --- | --- |
| La **base de datos** (su estructura y su selección de contenidos) | **Open Database License (ODbL)** |
| Los **contenidos individuales** de cada registro | **Database Contents License (DbCL)** |
| Las **imágenes de producto** | **Creative Commons Attribution ShareAlike (CC BY-SA)** |

### Qué obliga la ODbL, en la práctica

La ODbL impone dos obligaciones que afectan directamente al diseño de NutriMatch:

1. **Atribuir.** Hay que reconocer a Open Food Facts como fuente de los datos.
2. **Compartir en las mismas condiciones (share-alike).** Cualquier **base derivada** que se
   distribuya debe publicarse bajo ODbL. El Parquet del universo México que genera el script de
   ingesta **es una base derivada**: si se distribuye, va bajo ODbL.

De la primera obligación se sigue una consecuencia concreta: **la atribución debe ser visible también
en la interfaz de Streamlit**, no solo en este archivo. No basta con mencionar la fuente en el
repositorio si la persona que usa la aplicación nunca llega a verla. La atribución en la UI es un
requisito de la licencia, no una cortesía.

Las imágenes de producto, al estar bajo CC BY-SA, requieren atribución y share-alike por separado si
se reutilizan.

---

## PROFECO, "Quién es Quién en los Precios"

Programa de monitoreo de precios de la Procuraduría Federal del Consumidor.

- **Naturaleza**: **datos abiertos oficiales del Gobierno de México**.
- **Publicación**: `datos.profeco.gob.mx`.

### Cómo se presentan los precios

Los precios de QQP se presentan **siempre como "precio de referencia"** y **nunca como "precio
estimado"**.

La distinción no es cosmética. Un precio de QQP es un precio **real**, observado por PROFECO en un
establecimiento concreto y en una fecha concreta. Llamarlo "estimado" sugeriría que NutriMatch lo
calculó o lo proyectó, lo cual sería falso y trasladaría al proyecto una responsabilidad que no le
corresponde. Además, el cruce con los productos de Open Food Facts es **por texto** (marca +
presentación + producto), porque QQP no publica código de barras: motivo adicional para no presentar
la cifra como una estimación propia.

---

## Formato de cita en APA

Sustituir los marcadores `[FECHA DE CONSULTA]` y `[FECHA DEL SNAPSHOT]` por las fechas reales antes
de entregar cualquier documento. La fecha del snapshot de Open Food Facts queda registrada en la
variable `SNAPSHOT_DATE` del archivo `.env` durante la ingesta.

### Open Food Facts

> Open Food Facts. (`[AÑO DEL SNAPSHOT]`). *Open Food Facts database* \[Conjunto de datos].
> Recuperado el `[FECHA DE CONSULTA]` de https://world.openfoodfacts.org
>
> Snapshot utilizado: export CSV del `[FECHA DEL SNAPSHOT]`.

Se indica la fecha del snapshot porque Open Food Facts **regenera sus exports a diario**: sin esa
fecha la cita no identifica una versión concreta de los datos y el análisis no sería reproducible.

### PROFECO, "Quién es Quién en los Precios"

> Procuraduría Federal del Consumidor. (`[AÑO DE PUBLICACIÓN]`). *Quién es Quién en los Precios*
> \[Conjunto de datos]. Gobierno de México. Recuperado el `[FECHA DE CONSULTA]` de
> https://datos.profeco.gob.mx
