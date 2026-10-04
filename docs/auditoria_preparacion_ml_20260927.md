# Criterio del motor determinista

El ranking de NutriMatch es un cálculo reproducible de tres dimensiones: nutrición por percentil en la categoría de referencia, procesamiento por grupo NOVA y número de aditivos, y preferencias por etiquetas valoradas.

Lo construí así porque el catálogo observa productos, nutrientes e ingredientes. No observa un desenlace de «esta recomendación fue la correcta» con el que entrenar y evaluar un modelo supervisado de forma válida. Inventar ese desenlace cambiaría el significado del orden.

Por la misma razón, los nutrientes ausentes, los alérgenos ausentes, el grupo NOVA ausente y el precio ausente permanecen ausentes. La banda de información insuficiente y el estado no verificable cubren esos casos. El precio de demostración que la ficha emite como `SYNTHETIC` no entra al orden.

La evaluación del motor es el conjunto de oro, el contraste con Nutri-Score y el diagnóstico de cobertura, descritos en [`../AGENTS.md`](../AGENTS.md).
