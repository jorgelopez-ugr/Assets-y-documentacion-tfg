#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenera la galería de imágenes del TFG en galeria/, partiendo de la galería ya
curada en presentacion/index.html (que tiene las citas escritas a mano).

Filtros aplicados a petición:
  - Se descarta el vídeo .mp4 (pesado, no aporta a la docu).
  - Se descartan las imágenes de internet SIN referencia (citas «pendiente»).
  - Se conservan las imágenes propias (experimentos, capturas) y las externas
    que SÍ tienen fuente; el trabajo propio se muestra primero.

Copia solo las imágenes supervivientes a galeria/ (sin el prefijo «galeria/»,
para no anidar galeria/galeria) y emite galeria/index.html con el tema unificado.
"""
import html
import os
import shutil

from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
PRES = "/home/jorge/Escritorio/tfg/presentacion"
SRC_HTML = os.path.join(PRES, "index.html")
GAL = os.path.join(HERE, "galeria")

# Orden de las secciones: primero el trabajo propio, luego las referencias.
GROUP_ORDER = [
    "Capturas de pantalla",
    "Laboratorio de simulación",
    "Laboratorio — diapositivas",
    "Memoria — figuras finales",
    "Terrenos / DEM",
    "Arquitectura",
    "Esquemas e ideas",
    "Notas para la presentación",
    "Depuración de alineación",
    "Logos y plantilla",
    # ── referencias / material externo (al final) ──
    "Referencias hiperespectral / especies",
    "Estado del arte (figuras)",
    "Referencias externas / competencia",
]

# Imágenes a excluir por nombre de fichero (boilerplate que no es del proyecto).
EXCLUDE_BASENAMES = {"logo.png"}  # logo de la plantilla LaTeX, no aporta a la galería


def topnav():
    items = [("inicio", "Inicio", "../index.html"),
             ("docs", "Documentación", "../docs/index.html"),
             ("lab", "Laboratorio", "../testing-lab/docs/index.html"),
             ("galeria", "Galería", "index.html")]
    links = "".join(
        '<a href="{}"{}>{}</a>'.format(h, ' class="active"' if k == "galeria" else "", l)
        for k, l, h in items)
    return ('<nav class="topnav"><a class="brand" href="../index.html">'
            'TFG · <b>caminos forestales</b></a>'
            f'<div class="links">{links}</div></nav>')


def main():
    with open(SRC_HTML, encoding="utf-8") as fh:
        soup = BeautifulSoup(fh.read(), "html.parser")

    # limpiar galeria/ (subcarpetas de imágenes + index), preservar nada más
    if os.path.isdir(GAL):
        for entry in os.listdir(GAL):
            p = os.path.join(GAL, entry)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(GAL, exist_ok=True)

    groups = {}          # nombre grupo -> lista de cards (dict)
    kept = dropped = 0

    for section in soup.select("section.group"):
        gname = section.find("h2").get_text().strip()
        # el <h2> trae un <span class=count>; nos quedamos solo con el nombre
        gname = section.find("h2").contents[0].strip() if section.find("h2").contents else gname
        for card in section.select(".card"):
            video = card.find("video")
            img = card.find("img")
            if video is not None or img is None:      # descartar vídeo / mp4
                dropped += 1
                continue
            cite_el = card.select_one(".card-cite")
            is_pendiente = cite_el is not None and "pendiente" in (cite_el.get("class") or [])
            if is_pendiente:                          # descartar internet sin referencia
                dropped += 1
                continue
            src = img.get("src", "")
            if os.path.basename(src) in EXCLUDE_BASENAMES:   # boilerplate excluido
                dropped += 1
                continue
            new_src = src[len("galeria/"):] if src.startswith("galeria/") else src
            name_el = card.select_one(".card-name")
            name = name_el.get_text().strip() if name_el else os.path.basename(src)
            cite = cite_el.get_text().strip() if cite_el else ""
            propia = "propia" in (card.get("class") or [])

            # copiar el fichero superviviente
            srcpath = os.path.join(PRES, src)
            dstpath = os.path.join(GAL, new_src)
            os.makedirs(os.path.dirname(dstpath) or GAL, exist_ok=True)
            if os.path.isfile(srcpath):
                shutil.copy2(srcpath, dstpath)
                kept += 1
            else:
                print("  AVISO: falta", srcpath)
                continue

            groups.setdefault(gname, []).append(
                {"src": new_src, "name": name, "cite": cite, "propia": propia})

    # ── emitir HTML ──
    ordered = [g for g in GROUP_ORDER if g in groups]
    ordered += [g for g in groups if g not in ordered]

    sections_html = []
    for g in ordered:
        cards = groups[g]
        cards_html = []
        for c in cards:
            klass = "card propia" if c["propia"] else "card"
            cite_html = (f'<div class="card-cite">{html.escape(c["cite"])}</div>'
                         if c["cite"] else "")
            cards_html.append(
                f'<div class="{klass}" data-name="{html.escape(c["name"].lower())}" '
                f'onclick="open_lb(this)">'
                f'<img loading="lazy" src="{html.escape(c["src"])}" alt="">'
                f'<div class="card-info"><div class="card-name">{html.escape(c["name"])}</div>'
                f"{cite_html}</div></div>")
        sections_html.append(
            f'<section class="group"><h2>{html.escape(g)} '
            f'<span class="count">{len(cards)}</span></h2>'
            f'<div class="gallery">{"".join(cards_html)}</div></section>')

    total = kept
    page = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Galería · TFG caminos forestales</title>
<link rel="stylesheet" href="../assets/estilo.css">
<style>
  .gal-wrap {{ max-width: 1280px; margin: 0 auto; padding: 0 1.6rem 5rem; }}
  .toolbar {{ position: sticky; top: 52px; z-index: 40; background: rgba(13,17,23,.9);
              backdrop-filter: blur(6px); padding: .9rem 0 1rem; display: flex; gap: 1.2rem;
              align-items: center; justify-content: center; flex-wrap: wrap; }}
  #search {{ width: min(420px, 80vw); padding: .55rem .9rem; border-radius: 8px;
             border: 1px solid var(--linea); background: var(--papel); color: var(--tinta);
             font-size: .92rem; }}
  .legend {{ display: flex; gap: 1.2rem; font-size: .72rem; color: var(--tinta-soft); }}
  .legend span {{ display: flex; align-items: center; gap: .4rem; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  .dot.prop {{ background: var(--ok); }} .dot.ref {{ background: var(--aviso); }}
  .group {{ margin-top: 2.2rem; }}
  .group h2 {{ font-size: 1.1rem; color: var(--titulo); border-bottom: 1px solid var(--linea);
               padding-bottom: .4rem; margin-bottom: 1rem; }}
  .count {{ color: var(--tinta-soft); font-size: .8rem; font-weight: normal; }}
  .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 1.2rem; }}
  .card {{ background: var(--papel); border: 1px solid var(--linea); border-radius: 10px;
           overflow: hidden; cursor: pointer; transition: transform .15s, box-shadow .15s, border-color .15s;
           display: flex; flex-direction: column; }}
  .card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,.5); border-color: var(--acento); }}
  .card img {{ width: 100%; height: 170px; object-fit: cover; display: block; background: #0a0e14; }}
  .card.propia img {{ object-fit: contain; }}
  .card-info {{ padding: .55rem .7rem .7rem; display: flex; flex-direction: column; gap: .3rem; flex: 1; }}
  .card-name {{ font-size: .72rem; color: var(--tinta); word-break: break-all; }}
  .card-cite {{ font-size: .68rem; color: var(--tinta-soft); font-style: italic; word-break: break-all;
                border-left: 2px solid var(--linea); padding-left: .5rem; }}
  .card.propia .card-cite {{ color: #57d39a99; border-left-color: #57d39a44; }}
  .hidden {{ display: none !important; }}
  #lightbox {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,.94); z-index: 200;
               align-items: center; justify-content: center; flex-direction: column; gap: .7rem; padding: 2rem; }}
  #lightbox.active {{ display: flex; }}
  #lightbox img {{ max-width: 92vw; max-height: 82vh; object-fit: contain; border-radius: 6px; }}
  #lightbox-name {{ color: var(--tinta-soft); font-size: .8rem; }}
  #lightbox-cite {{ font-size: .78rem; color: var(--tinta-soft); font-style: italic; max-width: 80ch; text-align: center; }}
  #lightbox-close {{ position: fixed; top: 1rem; right: 1.5rem; font-size: 2rem; cursor: pointer; color: #ccc; }}
  #lightbox-close:hover {{ color: #fff; }}
</style>
</head>
<body>
{topnav()}
<div class="gal-wrap">
  <header class="hero" style="margin:2.4rem 0 .5rem;">
    <p class="kicker">TFG · caminos forestales</p>
    <h1>Galería</h1>
    <p class="sub">Capturas del desarrollo día a día, resultados de los experimentos del
      laboratorio, figuras de la memoria y material de referencia. {total} imágenes · clic para ampliar.</p>
  </header>

  <div class="toolbar">
    <input id="search" type="text" placeholder="Filtrar por nombre o ruta…" oninput="filtrar(this.value)">
    <div class="legend">
      <span><div class="dot prop"></div> imagen propia</span>
      <span><div class="dot ref"></div> con fuente</span>
    </div>
  </div>

  {"".join(sections_html)}

  <footer class="pie">
    <a href="../index.html">← Inicio</a> ·
    <a href="../docs/index.html">Documentación</a> ·
    <a href="../testing-lab/docs/index.html">Laboratorio</a>
  </footer>
</div>

<div id="lightbox" onclick="close_lb()">
  <span id="lightbox-close">&times;</span>
  <img id="lightbox-img" src="" alt="">
  <div id="lightbox-name"></div>
  <div id="lightbox-cite"></div>
</div>

<script>
  function open_lb(card) {{
    const img = card.querySelector('img');
    if (!img) return;
    document.getElementById('lightbox-img').src = img.src;
    document.getElementById('lightbox-name').textContent = card.querySelector('.card-name').textContent;
    const citeEl = card.querySelector('.card-cite');
    document.getElementById('lightbox-cite').textContent = citeEl ? citeEl.textContent : '';
    document.getElementById('lightbox').classList.add('active');
  }}
  function close_lb() {{ document.getElementById('lightbox').classList.remove('active'); }}
  document.addEventListener('keydown', e => {{ if (e.key === 'Escape') close_lb(); }});
  function filtrar(q) {{
    q = q.trim().toLowerCase();
    document.querySelectorAll('.group').forEach(g => {{
      let vis = 0;
      g.querySelectorAll('.card').forEach(c => {{
        const txt = (c.dataset.name || '') + ' ' +
                    (c.querySelector('.card-cite')?.textContent || '').toLowerCase();
        const ok = !q || txt.includes(q);
        c.classList.toggle('hidden', !ok);
        if (ok) vis++;
      }});
      g.classList.toggle('hidden', vis === 0);
    }});
  }}
</script>
</body>
</html>
"""
    with open(os.path.join(GAL, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"OK · galería: {kept} imágenes conservadas, {dropped} descartadas (mp4 + sin fuente)")
    print(f"   secciones: {', '.join(ordered)}")


if __name__ == "__main__":
    main()
