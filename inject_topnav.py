#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inyecta la barra de navegación unificada en las páginas (copiadas) del
testing-lab, para que se integren con el resto del sitio. No toca el
testing-lab original: solo la copia que vive en este repo.

- Añade las reglas .topnav a testing-lab/docs/estilo.css (que ya define las
  mismas variables de color), una sola vez.
- Inserta el <nav class="topnav"> justo tras <body> en cada .html.
Reejecutable (idempotente).
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, "testing-lab", "docs")

TOPNAV_CSS = """
/* ── Barra de navegación del sitio (añadida por inject_topnav.py) ────────── */
.topnav {
  position: sticky; top: 0; z-index: 100;
  display: flex; align-items: center; gap: 1.2rem;
  padding: .65rem clamp(1rem, 4vw, 2.2rem);
  background: rgba(13, 17, 23, .86); backdrop-filter: blur(9px);
  border-bottom: 1px solid var(--linea);
}
.topnav .brand { font-family: var(--mono); font-weight: 700; font-size: .9rem;
  color: var(--titulo); text-decoration: none; white-space: nowrap; }
.topnav .brand b { color: var(--acento); }
.topnav .links { display: flex; gap: .25rem; margin-left: auto; flex-wrap: wrap; }
.topnav .links a { color: var(--tinta-soft); text-decoration: none; font-size: .9rem;
  padding: .35rem .8rem; border-radius: 7px; transition: background .15s, color .15s; }
.topnav .links a:hover { color: var(--titulo); background: var(--papel-2); text-decoration: none; }
.topnav .links a.active { color: var(--acento); background: rgba(88, 176, 236, .12); }
@media (max-width: 680px) {
  .topnav { gap: .6rem; padding: .55rem .9rem; }
  .topnav .brand { font-size: .8rem; }
  .topnav .links a { padding: .3rem .55rem; font-size: .82rem; }
}
"""

PREFIX = "../../"
NAV_ITEMS = [("inicio", "Inicio", "index.html"),
             ("docs", "Documentación", "docs/index.html"),
             ("lab", "Laboratorio", "testing-lab/docs/index.html"),
             ("galeria", "Galería", "galeria/index.html")]


def nav_html():
    links = "".join(
        '<a href="{}{}"{}>{}</a>'.format(
            PREFIX, href, ' class="active"' if key == "lab" else "", label)
        for key, label, href in NAV_ITEMS)
    return ('<nav class="topnav"><a class="brand" href="{p}index.html">'
            'TFG · <b>caminos forestales</b></a>'
            '<div class="links">{l}</div></nav>'.format(p=PREFIX, l=links))


def main():
    css_path = os.path.join(LAB, "estilo.css")
    css = open(css_path, encoding="utf-8").read()
    if ".topnav" not in css:
        with open(css_path, "w", encoding="utf-8") as fh:
            fh.write(css + "\n" + TOPNAV_CSS)
        print("estilo.css: reglas .topnav añadidas")
    else:
        print("estilo.css: ya tenía .topnav (sin cambios)")

    nav = nav_html()
    n = 0
    for fn in os.listdir(LAB):
        if not fn.endswith(".html"):
            continue
        p = os.path.join(LAB, fn)
        txt = open(p, encoding="utf-8").read()
        if 'class="topnav"' in txt:
            continue
        new = re.sub(r"(<body>)", r"\1\n" + nav.replace("\\", "\\\\"), txt, count=1)
        if new != txt:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(new)
            n += 1
    print(f"nav inyectada en {n} páginas del testing-lab")


if __name__ == "__main__":
    main()
