# Documentación web del TFG — caminos forestales

Sitio estático que reúne **toda la documentación** del TFG *«Generación de caminos
forestales para la reducción de riesgos en incendios y accesibilidad en parques
nacionales»* en un solo lugar, pensado como material de apoyo para la defensa.

Una **landing** (`index.html`) enlaza con tres bloques bajo un mismo tema oscuro
y responsive:

| Bloque | Ruta | Qué es |
|---|---|---|
| **Documentación técnica** | `docs/` | La bóveda de notas Obsidian del proyecto, convertida a HTML. |
| **Laboratorio de simulación** | `testing-lab/docs/` | Cada operación del motor C++ aislada y demostrada con gráficos. |
| **Galería** | `galeria/` | Capturas del desarrollo, resultados de experimentos y figuras de la memoria. |

## Estructura

```
index.html               landing con el menú a los tres bloques
assets/estilo.css        hoja de estilos unificada (tema oscuro, responsive)
docs/                    Obsidian → HTML (índice + un .html por nota)
testing-lab/docs/        páginas del testing-lab (con la nav inyectada)
testing-lab/out/         imágenes que usan esas páginas
galeria/                 index.html + las imágenes (sin el .mp4 ni las refs sin fuente)
.nojekyll                desactiva el procesado Jekyll de GitHub Pages
```

## Cómo se regenera

Las tres partes se reconstruyen con scripts de Python (requieren `markdown` y
`beautifulsoup4`). Leen las fuentes originales que viven **fuera** de este repo
(la bóveda Obsidian y la galería de `presentacion/`):

```bash
python3 build_docs.py      # bóveda Obsidian  → docs/*.html  (+ índice)
python3 build_gallery.py   # presentacion/    → galeria/      (filtra mp4 y refs sin fuente)
python3 inject_topnav.py   # añade la barra de navegación a las páginas del testing-lab
```

`build_docs.py` resuelve los wikilinks `[[Nota]]` entre páginas, convierte los
callouts de Obsidian (`> [!warning]`) y excluye `PERSONAL-NOTES.md`. Los enlaces
`[[…]]` que viven dentro de bloques de código se dejan intactos.

## Publicar en GitHub Pages

1. `git push` de este repo a GitHub.
2. En GitHub: **Settings → Pages**.
3. En **Build and deployment → Source**, elige **Deploy from a branch**.
4. **Branch**: `main` (o la rama que uses) y carpeta **`/ (root)`**. Guarda.
5. A los ~1–2 min el sitio queda en
   `https://jorgelopez-ugr.github.io/Assets-y-documentacion-tfg/`.

El `.nojekyll` ya está incluido para que Pages sirva todos los ficheros tal cual.
