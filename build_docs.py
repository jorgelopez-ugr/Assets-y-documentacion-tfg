#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte la bóveda Obsidian del TFG (docs/docs-tfg, ficheros .md) a un sitio
HTML estático en docs/, con el tema unificado (assets/estilo.css).

- Resuelve los wikilinks [[Nota]] / [[Nota|alias]] / [[Nota#sección]] a enlaces
  reales entre los .html generados (por nombre de fichero, como hace Obsidian).
  Los [[...]] que viven dentro de bloques de código NO se tocan.
- Convierte los callouts de Obsidian (> [!warning] ...) a tarjetas con estilo.
- Genera docs/index.html: un menú agrupado por carpeta de la bóveda.

Reejecutable: borra y reconstruye docs/*.html en cada pasada.
"""
import html
import os
import re
import shutil
import unicodedata
import xml.etree.ElementTree as etree

import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.preprocessors import Preprocessor

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = "/home/jorge/Escritorio/tfg/version-final/TFG-evaluacion-de-caminos-forestales/docs/docs-tfg"
OUT = os.path.join(HERE, "docs")

# Ficheros/carpetas de la bóveda que NO se publican.
EXCLUDE_NAMES = {"PERSONAL-NOTES.md"}
EXCLUDE_DIRS = {".obsidian"}

# Orden y etiquetas de las secciones del índice (por carpeta de la bóveda).
FOLDER_META = [
    ("",                   "Visión general",
     "Arquitectura del sistema, el motor del tick, la evaluación de caminos y los conceptos clave."),
    ("motor",              "Motor C++",
     "Pipeline de simulación, organización en cuadrantes y el protocolo de comandos del motor."),
    ("motor/clases",       "Motor — clases",
     "Cada operación del tick como una clase: advección, presión, buoyancy, reacción…"),
    ("api",                "API (FastAPI)",
     "La API como orquestador entre Godot y el motor C++."),
    ("mvps",               "MVPs e hitos",
     "El diario de desarrollo: cada MVP, las fases de optimización y los recopilatorios."),
    ("tools",              "Tooling de datos",
     "build_world y la derivación de combustible por especie desde los datos."),
    ("logs",               "Logging",
     "El sistema de logs del proyecto y su rotación."),
    ("resultados",         "Resultados",
     "Benchmarks reproducibles y validación del cortafuegos."),
    ("errores-afrontados", "Errores afrontados",
     "Bugs reales encontrados durante el desarrollo y cómo se resolvieron."),
    ("referencias",        "Referencias",
     "Material externo de apoyo (matemáticas de propagación, etc.)."),
]

# Documento destacado del índice (la nota raíz de la bóveda).
FEATURED = "Inicio"

CALLOUT_ICONS = {
    "info": "ℹ", "note": "✎", "warning": "⚠", "danger": "⛔",
    "tip": "★", "success": "✓", "question": "?", "example": "≣",
    "quote": "❝", "abstract": "≣", "todo": "☐", "bug": "🐞",
    "failure": "✗", "important": "❗",
}
CALLOUT_TITLES = {
    "info": "Info", "note": "Nota", "warning": "Aviso", "danger": "Peligro",
    "tip": "Consejo", "success": "Hecho", "question": "Pregunta",
    "example": "Ejemplo", "quote": "Cita", "abstract": "Resumen",
    "todo": "Pendiente", "bug": "Bug", "failure": "Fallo", "important": "Importante",
}


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "doc"


# ── Wikilinks ────────────────────────────────────────────────────────────────
class WikiLinkProcessor(InlineProcessor):
    def __init__(self, pattern, md, link_map):
        super().__init__(pattern, md)
        self.link_map = link_map

    def handleMatch(self, m, data):
        raw = m.group(1).replace("\\|", "|")
        if "|" in raw:
            left, alias = raw.split("|", 1)
            alias = alias.strip()
        else:
            left, alias = raw, None
        target = left.split("#", 1)[0].strip()
        if alias is None:
            alias = left.strip().replace("#", " › ")
        slug = self.link_map.get(target) or self.link_map.get(target.lower())
        if slug:
            el = etree.Element("a")
            el.set("href", slug)
        else:
            el = etree.Element("span")
            el.set("class", "wikilink-missing")
            el.set("title", "nota no publicada: " + target)
        el.text = alias
        return el, m.start(0), m.end(0)


# ── Callouts de Obsidian ──────────────────────────────────────────────────────
class CalloutPreprocessor(Preprocessor):
    RE = re.compile(r"^>\s*\[!(\w+)\]([+-]?)\s*(.*)$")

    def __init__(self, md, inner_factory):
        super().__init__(md)
        self.inner_factory = inner_factory

    def run(self, lines):
        out, i, n = [], 0, len(lines)
        while i < n:
            m = self.RE.match(lines[i])
            if not m:
                out.append(lines[i]); i += 1; continue
            ctype = m.group(1).lower()
            title = m.group(3).strip()
            body, i = [], i + 1
            while i < n and lines[i].lstrip().startswith(">"):
                body.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            inner_html = self.inner_factory().convert("\n".join(body))
            icon = CALLOUT_ICONS.get(ctype, "ℹ")
            disp = title or CALLOUT_TITLES.get(ctype, ctype.capitalize())
            full = (
                f'<div class="callout callout-{ctype}">'
                f'<div class="callout-title"><span class="callout-icon">{icon}</span> '
                f"{html.escape(disp)}</div>"
                f'<div class="callout-body">{inner_html}</div></div>'
            )
            out.extend(["", self.md.htmlStash.store(full), ""])
        return out


class ObsidianExtension(Extension):
    def __init__(self, link_map, with_callouts=True):
        super().__init__()
        self.link_map = link_map
        self.with_callouts = with_callouts

    def extendMarkdown(self, md):
        # Prioridad 185: por debajo de los code spans (`backtick`, 190) para no
        # tocar wikilinks dentro de código, pero por encima del procesador de
        # escapes (`escape`, 180) para ver el pipe escapado «\|» literal.
        md.inlinePatterns.register(
            WikiLinkProcessor(r"\[\[([^\]]+?)\]\]", md, self.link_map), "wikilink", 185)
        if self.with_callouts:
            md.preprocessors.register(
                CalloutPreprocessor(md, lambda: build_md(self.link_map, False)),
                "obsidian_callout", 30)


def build_md(link_map, with_callouts=True):
    return markdown.Markdown(
        extensions=["fenced_code", "tables", "sane_lists", "attr_list", "toc",
                    ObsidianExtension(link_map, with_callouts)],
        output_format="html5",
    )


# ── Frontmatter y título ──────────────────────────────────────────────────────
FM_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
COMMENT_RE = re.compile(r"%%.*?%%", re.DOTALL)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def strip_and_title(text, fallback):
    text = FM_RE.sub("", text, count=1)
    text = COMMENT_RE.sub("", text)
    m = H1_RE.search(text)
    if m:
        title = m.group(1).strip()
        # quitamos solo el primer H1 para no duplicarlo con el <h1> de la cabecera
        text = text[:m.start()] + text[m.end():]
    else:
        title = fallback
    return text.strip("\n"), title


# ── Plantillas ────────────────────────────────────────────────────────────────
def topnav(prefix, active):
    items = [
        ("inicio", "Inicio", prefix + "index.html"),
        ("docs", "Documentación", prefix + "docs/index.html"),
        ("lab", "Laboratorio", prefix + "testing-lab/docs/index.html"),
        ("galeria", "Galería", prefix + "galeria/index.html"),
    ]
    links = "".join(
        '<a href="{}"{}>{}</a>'.format(
            href, ' class="active"' if key == active else "", label)
        for key, label, href in items
    )
    return (
        f'<nav class="topnav"><a class="brand" href="{prefix}index.html">'
        f"TFG · <b>caminos forestales</b></a>"
        f'<div class="links">{links}</div></nav>'
    )


PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Documentación TFG</title>
<link rel="stylesheet" href="../assets/estilo.css">
</head>
<body>
{nav}
<div class="wrap">
  <header class="hero">
    <p class="kicker"><a href="index.html">Documentación</a> · {folder}</p>
    <h1>{title}</h1>
  </header>
  <article class="doc">
{body}
  </article>
  <footer class="pie">
    <a href="index.html">← Índice de la documentación</a> ·
    <a href="../index.html">Inicio</a>
    <span style="float:right">Generado desde la bóveda Obsidian del TFG.</span>
  </footer>
</div>
</body>
</html>
"""


def main():
    # 1) Recolectar ficheros y construir el mapa nombre→slug.html
    docs = []  # (basename, folder_rel, slug, abspath)
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in files:
            if not fn.endswith(".md") or fn in EXCLUDE_NAMES:
                continue
            base = fn[:-3]
            folder_rel = os.path.relpath(root, VAULT)
            folder_rel = "" if folder_rel == "." else folder_rel.replace(os.sep, "/")
            docs.append((base, folder_rel, slugify(base) + ".html", os.path.join(root, fn)))

    link_map = {base: slug for base, _, slug, _ in docs}

    # 2) Limpiar y regenerar docs/
    if os.path.isdir(OUT):
        for f in os.listdir(OUT):
            if f.endswith(".html"):
                os.remove(os.path.join(OUT, f))
    os.makedirs(OUT, exist_ok=True)

    folder_label = {fr: lbl for fr, lbl, _ in FOLDER_META}
    titles = {}  # base -> title
    md = build_md(link_map, with_callouts=True)

    for base, folder_rel, slug, path in docs:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        body_md, title = strip_and_title(raw, base)
        titles[base] = title
        md.reset()
        body_html = md.convert(body_md)
        lbl = folder_label.get(folder_rel, folder_rel or "Visión general")
        page = PAGE.format(title=html.escape(title), folder=html.escape(lbl),
                           body=body_html, nav=topnav("../", "docs"))
        with open(os.path.join(OUT, slug), "w", encoding="utf-8") as fh:
            fh.write(page)

    # 3) Índice agrupado por carpeta
    by_folder = {}
    for base, folder_rel, slug, _ in docs:
        by_folder.setdefault(folder_rel, []).append((titles[base], slug, base))

    seen = set()
    sections_html = []
    ordered = FOLDER_META + [(fr, fr or "Otros", "") for fr in sorted(by_folder) ]
    for folder_rel, label, lead in ordered:
        if folder_rel in seen or folder_rel not in by_folder:
            continue
        seen.add(folder_rel)
        entries = sorted(by_folder[folder_rel], key=lambda e: e[0].lower())
        cards = []
        featured_html = ""
        for title, slug, base in entries:
            if base == FEATURED:
                featured_html = (
                    f'<a class="featured" href="{slug}"><span class="ico">▸</span>'
                    f'<span><span class="t">{html.escape(title)}</span><br>'
                    f'<span class="d">Empieza aquí: el mapa de toda la documentación.</span></span>'
                    f'<span class="arrow">→</span></a>'
                )
                continue
            cards.append(f'<a class="doc-card" href="{slug}"><span class="t">'
                         f'{html.escape(title)}</span></a>')
        lead_html = f'<p class="lead">{html.escape(lead)}</p>' if lead else ""
        grid = f'<div class="doc-grid">{"".join(cards)}</div>' if cards else ""
        sections_html.append(
            f'<section class="doc-section"><h2>{html.escape(label)}</h2>'
            f"{lead_html}{featured_html}{grid}</section>"
        )

    total = len(docs)
    index = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Documentación · TFG caminos forestales</title>
<link rel="stylesheet" href="../assets/estilo.css">
</head>
<body>
{topnav("../", "docs")}
<div class="wrap">
  <header class="hero">
    <p class="kicker">TFG · caminos forestales</p>
    <h1>Documentación técnica</h1>
    <p class="sub">La bóveda de notas del proyecto, pasada a web: arquitectura, motor C++,
      API, los MVPs del desarrollo, los errores afrontados y los resultados.
      {total} documentos.</p>
  </header>
  {"".join(sections_html)}
  <footer class="pie">
    <a href="../index.html">← Inicio</a> ·
    <a href="../testing-lab/docs/index.html">Laboratorio de simulación</a> ·
    <a href="../galeria/index.html">Galería</a>
    <span style="float:right">Generado desde la bóveda Obsidian del TFG.</span>
  </footer>
</div>
</body>
</html>
"""
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index)

    print(f"OK · {total} documentos → {OUT}")
    print(f"   mapa de wikilinks: {len(link_map)} notas")


if __name__ == "__main__":
    main()
