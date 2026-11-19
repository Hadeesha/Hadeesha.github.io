# Simple, illustrative project figures in the style of the existing BioRender-like
# schematics: pale rounded panels, navy headings, flat pastel organs/cells, black chevrons.
import os
OUT = os.path.dirname(os.path.abspath(__file__))

W, H = 1200, 430
NAVY = "#1c2f4b"; SLATE = "#3b4a5a"; INK = "#1c2b33"
PANEL = "#e9eff7"; PANEL_STROKE = "#7a889e"
BRAIN = "#c9d9ef"; BRAIN_STROKE = "#6f86a8"; BRAIN_LINE = "#93a9c8"
RED = "#e06c6c"; RED_DARK = "#b84a4a"; TEAL = "#3fa796"; TEAL_DARK = "#2e7f72"
TUMOUR = "#e89aa2"; IMMUNE = "#b58ad6"; GLIAL = "#8fb3e0"; VASC = "#6cc1b3"
VESSEL = "#f0b4b4"; VESSEL_STROKE = "#c97a7a"; RBC = "#d9534f"
LUNG = "#f3c6c9"; LUNG_STROKE = "#c87b84"; HEART = "#f2b8b8"; HEART_STROKE = "#c0646a"
TILE = "#fbf3f4"; TILE_STROKE = "#c9a9ad"

FONT = ("font-family=\"Inter, 'Helvetica Neue', Arial, sans-serif\"")


def text(x, y, s, size=17, weight=400, fill=SLATE, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" {FONT}>{s}</text>')


def panel(x, y, w, h, title):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{PANEL}" stroke="{PANEL_STROKE}" stroke-width="1.6"/>'
            + text(x + w / 2, y + 40, title, 23, 700, NAVY, "middle"))


def chevron(x, y, s=16):
    return f'<path d="M{x},{y - s} L{x + s * 1.1},{y} L{x},{y + s} Z" fill="{INK}"/>'


def brain(x, y, scale=1.0, tumours=(), glow=False):
    """Side-view brain, ~200x160 at scale 1. tumours: list of (kind, cx, cy, r) in local coords."""
    g = [f'<g transform="translate({x},{y}) scale({scale})">']
    g.append(f'<rect x="108" y="118" width="22" height="36" rx="9" fill="#b9cbe6" stroke="{BRAIN_STROKE}" stroke-width="2"/>')
    g.append(f'<ellipse cx="152" cy="120" rx="30" ry="17" fill="#b9cbe6" stroke="{BRAIN_STROKE}" stroke-width="2"/>')
    g.append('<path d="M128,116 q10,4 20,0 M134,126 q12,5 24,-1" fill="none" stroke="%s" stroke-width="2"/>' % BRAIN_LINE)
    g.append(f'<path d="M20,80 C15,40 55,8 100,13 C142,16 178,34 182,70 C186,100 160,120 126,120 L96,122 C80,122 68,118 58,112 C34,108 22,98 20,80 Z" '
             f'fill="{BRAIN}" stroke="{BRAIN_STROKE}" stroke-width="2.2"/>')
    # gyri
    g.append(f'<path d="M48,60 C60,40 85,38 100,50 M70,90 C85,70 110,70 125,85 M100,30 C120,24 150,36 160,58 M40,95 C55,90 70,100 80,112 M120,50 C140,45 160,60 170,80" '
             f'fill="none" stroke="{BRAIN_LINE}" stroke-width="2.2" stroke-linecap="round"/>')
    for kind, cx, cy, r in tumours:
        fill, dark = (RED, RED_DARK) if kind == "glioma" else (TEAL, TEAL_DARK)
        if glow:
            g.append(f'<circle cx="{cx}" cy="{cy}" r="{r + 8}" fill="{fill}" opacity="0.25"/>')
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{dark}" stroke-width="1.5"/>')
        for dx, dy in ((-r * .4, -r * .3), (r * .35, -r * .1), (-r * .1, r * .4), (r * .3, r * .45)):
            g.append(f'<circle cx="{cx + dx}" cy="{cy + dy}" r="{r * .16}" fill="{dark}" opacity="0.8"/>')
    g.append('</g>')
    return "".join(g)


def tissue(x, y, size=130, cells=True, vessel=True, pixels=False, focus=None):
    """Tissue tile with a vessel and coloured cells; optional pixel grid and focus cell with dashed ring."""
    g = [f'<g transform="translate({x},{y})">']
    g.append(f'<rect x="0" y="0" width="{size}" height="{size}" rx="14" fill="{TILE}" stroke="{TILE_STROKE}" stroke-width="1.6"/>')
    if pixels:
        cols = ("#f6d9c9", "#f1c4ad", "#e9a98b", "#d8b4e3", "#c99bd9", "#f8e6dc", "#f4cfc0", "#e2c3ea")
        n = 6; s = (size - 16) / n
        import random; random.seed(7)
        for i in range(n):
            for j in range(n):
                g.append(f'<rect x="{8 + i * s}" y="{8 + j * s}" width="{s}" height="{s}" fill="{random.choice(cols)}" opacity="0.85"/>')
        g.append(f'<rect x="8" y="8" width="{size - 16}" height="{size - 16}" rx="8" fill="none" stroke="{TILE_STROKE}" stroke-width="1"/>')
    if vessel:
        g.append(f'<rect x="12" y="{size / 2 - 11}" width="{size - 24}" height="22" rx="11" fill="{VESSEL}" stroke="{VESSEL_STROKE}" stroke-width="1.5"/>')
        for k in range(3):
            g.append(f'<ellipse cx="{30 + k * (size - 60) / 2}" cy="{size / 2}" rx="8" ry="5.5" fill="{RBC}"/>')
    if cells:
        pts = [(28, 26, TUMOUR), (62, 20, TUMOUR), (98, 30, IMMUNE), (40, 44, GLIAL), (108, 48, TUMOUR),
               (26, 96, IMMUNE), (56, 108, GLIAL), (90, 100, TUMOUR), (112, 84, VASC), (70, 88, IMMUNE)]
        for cx, cy, c in pts:
            cx = cx * size / 130; cy = cy * size / 130
            g.append(f'<circle cx="{cx}" cy="{cy}" r="{7.5 * size / 130}" fill="{c}" stroke="#ffffff" stroke-width="1.5"/>')
            g.append(f'<circle cx="{cx}" cy="{cy}" r="{3 * size / 130}" fill="#ffffff" opacity="0.6"/>')
    if focus:
        cx, cy = focus
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{size * .3}" fill="none" stroke="{INK}" stroke-width="2" stroke-dasharray="6 5"/>')
        g.append(f'<circle cx="{cx}" cy="{cy}" r="12" fill="{GLIAL}" stroke="{INK}" stroke-width="2.5"/>')
        g.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="#ffffff" opacity="0.7"/>')
    g.append('</g>')
    return "".join(g)


def legend(x, y, items, size=16, gap=24):
    g = []
    for i, (c, label) in enumerate(items):
        yy = y + i * gap
        g.append(f'<circle cx="{x}" cy="{yy - 5}" r="6.5" fill="{c}"/>')
        g.append(text(x + 14, yy, label, size, 500, SLATE))
    return "".join(g)


def legend_row(x, y, items, size=16, step=92):
    g = []
    for i, (c, label) in enumerate(items):
        xx = x + i * step
        g.append(f'<circle cx="{xx}" cy="{y - 5}" r="6.5" fill="{c}"/>')
        g.append(text(xx + 13, y, label, size, 500, SLATE))
    return "".join(g)


def people(x, y, scale=1.0):
    """Clinician and patient outline icon, like the current 'long-term goal' panel."""
    g = [f'<g transform="translate({x},{y}) scale({scale})" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">']
    g.append('<circle cx="40" cy="26" r="18"/><path d="M8,96 C8,66 24,56 40,56 C56,56 72,66 72,96"/>')
    g.append('<circle cx="98" cy="34" r="15"/><path d="M72,96 C74,74 84,64 98,64 C112,64 124,74 126,96"/>')
    g.append('</g>')
    return "".join(g)


def heart(x, y, scale=1.0, outline=False):
    fill = "none" if outline else HEART
    stroke = INK if outline else HEART_STROKE
    g = [f'<g transform="translate({x},{y}) scale({scale})">']
    # aortic arch drawn as an outlined tube (thick stroke with a lighter core)
    g.append(f'<path d="M54,36 C52,14 70,6 86,16" fill="none" stroke="{stroke}" stroke-width="13" stroke-linecap="round"/>')
    g.append(f'<path d="M54,36 C52,14 70,6 86,16" fill="none" stroke="{PANEL if outline else fill}" stroke-width="7" stroke-linecap="round"/>')
    g.append(f'<path d="M60,44 C46,22 14,26 12,54 C10,82 34,108 60,128 C86,108 110,82 108,54 C106,26 74,22 60,44 Z" fill="{fill}" stroke="{stroke}" stroke-width="3" stroke-linejoin="round"/>')
    g.append(f'<path d="M56,58 C48,72 50,90 62,106" fill="none" stroke="{stroke}" stroke-width="2.5" stroke-linecap="round" opacity="0.8"/>')
    g.append('</g>')
    return "".join(g)


def brain_outline(x, y, scale=1.0):
    g = [f'<g transform="translate({x},{y}) scale({scale})" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">']
    g.append('<rect x="108" y="118" width="22" height="36" rx="9"/><ellipse cx="152" cy="120" rx="30" ry="17"/>')
    g.append('<path d="M20,80 C15,40 55,8 100,13 C142,16 178,34 182,70 C186,100 160,120 126,120 L96,122 C80,122 68,118 58,112 C34,108 22,98 20,80 Z"/>')
    g.append('<path d="M48,60 C60,40 85,38 100,50 M70,90 C85,70 110,70 125,85 M100,30 C120,24 150,36 160,58 M40,95 C55,90 70,100 80,112 M120,50 C140,45 160,60 170,80" stroke-width="2.4"/>')
    g.append('</g>')
    return "".join(g)


def lung(x, y, scale=1.0):
    g = [f'<g transform="translate({x},{y}) scale({scale})">']
    g.append(f'<rect x="56" y="0" width="18" height="46" rx="8" fill="{LUNG}" stroke="{LUNG_STROKE}" stroke-width="2.4"/>')
    g.append(f'<path d="M65,40 L38,66 M65,40 L92,66" fill="none" stroke="{LUNG_STROKE}" stroke-width="5" stroke-linecap="round"/>')
    g.append(f'<path d="M56,54 C40,46 10,66 6,106 C2,146 22,170 50,166 C62,164 64,150 62,130 L60,70 C60,60 58,56 56,54 Z" fill="{LUNG}" stroke="{LUNG_STROKE}" stroke-width="2.4"/>')
    g.append(f'<path d="M74,54 C90,46 120,66 124,106 C128,146 108,170 80,166 C68,164 66,150 68,130 L70,70 C70,60 72,56 74,54 Z" fill="{LUNG}" stroke="{LUNG_STROKE}" stroke-width="2.4"/>')
    g.append(f'<path d="M38,90 C30,100 28,120 34,140 M92,90 C100,100 102,120 96,140" fill="none" stroke="{LUNG_STROKE}" stroke-width="2" opacity="0.7"/>')
    g.append('</g>')
    return "".join(g)


def clipboard(x, y, scale=1.0):
    g = [f'<g transform="translate({x},{y}) scale({scale})" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">']
    g.append('<rect x="0" y="12" width="92" height="116" rx="10" fill="#ffffff"/><rect x="28" y="2" width="36" height="20" rx="6" fill="#ffffff"/>')
    for i, yy in enumerate((48, 72, 96)):
        g.append(f'<path d="M16,{yy} l6,6 l12,-13" stroke="{TEAL_DARK}"/><path d="M44,{yy} h30"/>')
    g.append('</g>')
    return "".join(g)


def layer_tile(x, y, w, label, icon):
    g = [f'<rect x="{x}" y="{y}" width="{w}" height="52" rx="12" fill="#ffffff" stroke="{PANEL_STROKE}" stroke-width="1.4"/>']
    ix, iy = x + 14, y + 26
    if icon == "cells":
        for dx, dy, c in ((0, -8, TUMOUR), (14, 6, IMMUNE), (26, -6, GLIAL), (10, -14, VASC)):
            g.append(f'<circle cx="{ix + 8 + dx}" cy="{iy + dy}" r="6" fill="{c}" stroke="#fff" stroke-width="1.2"/>')
    elif icon == "lipids":
        for k in range(4):
            g.append(f'<circle cx="{ix + 6 + k * 9}" cy="{iy - 6}" r="4" fill="#c6a15b"/>')
            g.append(f'<path d="M{ix + 6 + k * 9},{iy - 2} v14" stroke="#c6a15b" stroke-width="2"/>')
    elif icon == "glycans":
        g.append(f'<path d="M{ix + 18},{iy + 12} v-10 M{ix + 18},{iy + 2} l-10,-8 M{ix + 18},{iy + 2} l10,-8 M{ix + 8},{iy - 6} l-6,-6 M{ix + 28},{iy - 6} l6,-6" fill="none" stroke="{TEAL_DARK}" stroke-width="2"/>')
        for px, py, c in ((ix + 18, iy + 12, "#3f6fb5"), (ix + 8, iy - 6, "#3fa796"), (ix + 28, iy - 6, "#3fa796"), (ix + 2, iy - 12, "#e0b23a"), (ix + 34, iy - 12, "#e0b23a")):
            g.append(f'<circle cx="{px}" cy="{py}" r="4" fill="{c}"/>')
    g.append(text(x + 58, y + 32, label, 17, 600, NAVY))
    return "".join(g)


def svg(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'{body}</svg>')


# ---------------------------------------------------------------- Figure 1: pediatric brain tumours
def fig_pediatric():
    b = []
    px, pw, py, ph = 20, 350, 20, 390
    b.append(panel(px, py, pw, ph, "Patient tumours"))
    b.append(brain(px + 70, py + 70, 1.05, tumours=[("glioma", 72, 58, 20), ("medullo", 152, 120, 13)]))
    b.append(legend_row(px + 52, py + ph - 52, [(RED, "Glioma"), (TEAL, "Medulloblastoma")], 16, 110))
    b.append(text(px + pw / 2, py + ph - 20, "Surgical tissue and clinical follow-up", 16, 400, SLATE, "middle"))
    b.append(chevron(px + pw + 18, py + ph / 2))

    px2, pw2 = 420, 360
    b.append(panel(px2, py, pw2, ph, "Spatial multi-omic imaging"))
    b.append(tissue(px2 + 40, py + 72, 150))
    b.append(text(px2 + 215, py + 110, "Transcripts, proteins,", 17, 500, NAVY))
    b.append(text(px2 + 215, py + 134, "lipids, metabolites", 17, 500, NAVY))
    b.append(text(px2 + 215, py + 158, "and glycans, mapped", 17, 500, NAVY))
    b.append(text(px2 + 215, py + 182, "cell by cell", 17, 500, NAVY))
    b.append(legend_row(px2 + 36, py + ph - 52, [(TUMOUR, "Tumour"), (IMMUNE, "Immune"), (GLIAL, "Glial"), (VASC, "Vascular")], 15, 82))
    b.append(text(px2 + pw2 / 2, py + ph - 20, "Single-cell resolution", 16, 400, SLATE, "middle"))
    b.append(chevron(px2 + pw2 + 18, py + ph / 2))

    px3, pw3 = 850, 330
    b.append(panel(px3, py, pw3, ph, "Informing patient care"))
    b.append(people(px3 + 100, py + 80, 1.15))
    b.append(text(px3 + pw3 / 2, py + 258, "How the microenvironment shapes", 16, 400, SLATE, "middle"))
    b.append(text(px3 + pw3 / 2, py + 282, "progression and treatment response,", 16, 400, SLATE, "middle"))
    b.append(text(px3 + pw3 / 2, py + 306, "to inform care and new therapies", 16, 400, SLATE, "middle"))
    return svg("".join(b))


# ---------------------------------------------------------------- Figure 2: brain–heart
def fig_brain_heart():
    b = []
    py, ph = 20, 390
    px, pw = 20, 350
    b.append(panel(px, py, pw, ph, "Childhood brain tumour"))
    b.append(brain(px + 70, py + 72, 1.05, tumours=[("glioma", 78, 62, 17)], glow=True))
    b.append(text(px + pw / 2, py + ph - 44, "Treated with surgery and therapy;", 16, 400, SLATE, "middle"))
    b.append(text(px + pw / 2, py + ph - 20, "most children survive", 16, 400, SLATE, "middle"))
    b.append(chevron(px + pw + 18, py + ph / 2))

    px2, pw2 = 420, 360
    b.append(panel(px2, py, pw2, ph, "Tissue and follow-up"))
    b.append(tissue(px2 + 36, py + 84, 140))
    b.append(clipboard(px2 + 228, py + 90, 1.0))
    b.append(text(px2 + 106, py + 258, "Spatial multi-omic", 16, 500, NAVY, "middle"))
    b.append(text(px2 + 106, py + 280, "imaging", 16, 500, NAVY, "middle"))
    b.append(text(px2 + 274, py + 258, "Years of clinical", 16, 500, NAVY, "middle"))
    b.append(text(px2 + 274, py + 280, "follow-up", 16, 500, NAVY, "middle"))
    b.append(text(px2 + pw2 / 2, py + ph - 20, "Does the tissue hold clues to later health?", 16, 400, SLATE, "middle"))
    b.append(chevron(px2 + pw2 + 18, py + ph / 2))

    px3, pw3 = 850, 330
    b.append(panel(px3, py, pw3, ph, "Brain and heart health"))
    b.append(brain_outline(px3 + 20, py + 90, 0.78))
    b.append(heart(px3 + 196, py + 104, 0.86, outline=True))
    b.append(text(px3 + 92, py + 258, "Cognition", 16, 500, NAVY, "middle"))
    b.append(text(px3 + 250, py + 258, "Cardiovascular health", 16, 500, NAVY, "middle"))
    b.append(text(px3 + pw3 / 2, py + ph - 44, "Identify children at risk and", 16, 400, SLATE, "middle"))
    b.append(text(px3 + pw3 / 2, py + ph - 20, "ways to protect them", 16, 400, SLATE, "middle"))
    return svg("".join(b))


# ---------------------------------------------------------------- Figure 3: lung development
def fig_lung():
    b = []
    py, ph = 20, 390
    px, pw = 20, 350
    b.append(panel(px, py, pw, ph, "The developing lung"))
    b.append(lung(px + 28, py + 150, 0.5))
    b.append(lung(px + 110, py + 118, 0.72))
    b.append(lung(px + 212, py + 84, 0.95))
    b.append(f'<path d="M{px + 40},{py + ph - 58} H{px + pw - 48}" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>')
    b.append(chevron(px + pw - 48, py + ph - 58, 8))
    b.append(text(px + pw / 2, py + ph - 20, "Maturation over time", 16, 400, SLATE, "middle"))
    b.append(chevron(px + pw + 18, py + ph / 2))

    px2, pw2 = 420, 360
    b.append(panel(px2, py, pw2, ph, "Molecular layers"))
    b.append(layer_tile(px2 + 30, py + 72, 300, "Transcripts and proteins", "cells"))
    b.append(layer_tile(px2 + 30, py + 140, 300, "Lipids and metabolites", "lipids"))
    b.append(layer_tile(px2 + 30, py + 208, 300, "Glycans", "glycans"))
    b.append(text(px2 + pw2 / 2, py + ph - 44, "Imaged on the same tissue, across", 16, 400, SLATE, "middle"))
    b.append(text(px2 + pw2 / 2, py + ph - 20, "airways, air sacs, stroma and vessels", 16, 400, SLATE, "middle"))
    b.append(chevron(px2 + pw2 + 18, py + ph / 2))

    px3, pw3 = 850, 330
    b.append(panel(px3, py, pw3, ph, "Molecular neighbourhoods"))
    b.append(tissue(px3 + 90, py + 76, 150, cells=False, vessel=False, pixels=True, focus=(75, 78)))
    b.append(text(px3 + pw3 / 2, py + ph - 44, "How the molecules around a cell", 16, 400, SLATE, "middle"))
    b.append(text(px3 + pw3 / 2, py + ph - 20, "are organized as the lung matures", 16, 400, SLATE, "middle"))
    return svg("".join(b))


if __name__ == "__main__":
    for name, fn in (("pediatric-brain-tumours", fig_pediatric), ("brain-heart", fig_brain_heart), ("lung-development", fig_lung)):
        with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
            f.write(fn())
        print("wrote", name + ".svg")
