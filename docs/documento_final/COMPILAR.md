# Compilar el PDF

El documento está en `docs/documento_final/`. El PDF ya generado es `main.pdf`.

Esta compilación se hizo con Tectonic 0.17, que trae XeTeX y BibTeX. No usa Biber. La bibliografía APA sale del estilo `apacite`.

Desde la carpeta del documento:

```bash
cd docs/documento_final
tectonic -X compile main.tex
```

El resultado es `main.pdf` en esa misma carpeta.

Si `tectonic` no está instalado, el binario oficial de la versión 0.17 se puede dejar en el PATH. La compilación descarga los paquetes que falten la primera vez, así que hace falta red.

Con TeX Live también compila, porque el archivo detecta el motor. En ese caso, desde `docs/documento_final`:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```
