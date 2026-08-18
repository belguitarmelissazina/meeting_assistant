"""Generation des schemas et couvertures — charte Yele Consulting.

Deux briques :
  - `cover(...)`   : page de garde grenat (croix + semis de points) -> PNG
  - `Diagram(...)` : diagrammes boites/fleches -> PNG

Les diagrammes utilisent un repere en unites arbitraires (0..100 en x,
0..H en y, origine en bas a gauche). Toutes les tailles sont exprimees
dans ce repere, ce qui rend les schemas independants du DPI.

Usage :
    from yele_schemas import Diagram, cover, PALETTE
    d = Diagram(width=100, height=48)
    d.group(2, 2, 96, 20, "Couche presentation")
    d.box(6, 6, 20, 10, "App.js", ["Shell + layout"], "grenat")
    d.arrow((16, 6), (16, -2))
    d.save("schema.png")
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle, Ellipse

DPI = 220

# ── Palette (alignee sur yele_style) ────────────────────────────────────────
PALETTE = {
    "grenat":     ("#B2544F", "#FFFFFF"),
    "grenat_f":   ("#8E403C", "#FFFFFF"),
    "violet":     ("#6B4E9B", "#FFFFFF"),
    "vert":       ("#1F6F5C", "#FFFFFF"),
    "vert_f":     ("#14503F", "#FFFFFF"),
    "bleu":       ("#2F5D8A", "#FFFFFF"),
    "orange":     ("#B5651D", "#FFFFFF"),
    "gris":       ("#5F5F5F", "#FFFFFF"),
    "gris_c":     ("#E9E9E9", "#333333"),
    "rose":       ("#F8EBEA", "#8E403C"),
    "blanc":      ("#FFFFFF", "#333333"),
}

GROUP_FILL = {
    "grenat": "#FCF3F2", "violet": "#F4F0FA", "vert": "#EEF6F3",
    "bleu": "#EFF4F9", "gris": "#F4F4F4", "orange": "#FBF3EA",
}

# ⚠ NE PAS remettre Calibri ici. Sous matplotlib/FreeType, la fonte Calibri
# cesse de rendre ses glyphes en dessous d'environ 7 pt : seule la ligature
# « ti » survit, le reste du texte disparaît silencieusement (constaté sur
# tous les sous-titres de boîtes). Segoe UI, Arial, Verdana et DejaVu Sans
# n'ont pas ce défaut. Le corps du Word reste en Calibri, où le problème
# n'existe pas — il est propre au moteur de rendu de matplotlib.
FONT = ["Segoe UI", "DejaVu Sans"]
plt.rcParams["font.family"] = FONT
plt.rcParams["font.sans-serif"] = FONT


# ─────────────────────────────────────────────────────────────────────────────
#   Couverture de partie
# ─────────────────────────────────────────────────────────────────────────────
def cover(titre: str, sous_titre: str, out: str | Path,
          bg: str = "#B2544F") -> str:
    """Page de garde : fond grenat, croix fine en haut a gauche,
    semis de points en bas a droite, titre centre bas."""
    W, H = 9.52, 12.32          # ratio de la reference (~A4 dans les marges)
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 129)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 100, 129, color=bg, zorder=0))

    # Croix fine (deux traits qui se croisent), coin haut-gauche
    ax.plot([9, 47], [122, 93], color="white", lw=0.9, zorder=2,
            solid_capstyle="round")
    ax.plot([9, 47], [93, 122], color="white", lw=0.9, zorder=2,
            solid_capstyle="round")
    # Prolongement long de la diagonale descendante, jusqu'au centre bas-droit
    ax.plot([28, 62], [107, 81], color="white", lw=0.7, alpha=0.85, zorder=2)

    # Semis de points elliptiques, coin bas-droit
    import random
    random.seed(7)
    cx, cy, R = 80, 22, 17
    for _ in range(230):
        a = random.uniform(0, 2 * math.pi)
        r = R * math.sqrt(random.uniform(0, 1))
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        ang = math.degrees(math.atan2(y - cy, x - cx)) + 90
        ax.add_patch(Ellipse((x, y), 0.9, 2.2, angle=ang,
                             color="white", alpha=0.16, zorder=1))

    ax.text(50, 55, titre, ha="center", va="center", color="white",
            fontsize=30, fontweight="bold", zorder=3)
    ax.text(50, 45, sous_titre, ha="center", va="center", color="white",
            fontsize=30, fontweight="bold", zorder=3)

    out = str(out)
    fig.savefig(out, dpi=DPI, facecolor=bg)
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────────
#   Diagrammes
# ─────────────────────────────────────────────────────────────────────────────
class Diagram:
    """Diagramme boites / fleches en unites arbitraires."""

    # Largeur utile du document = 16 cm = 6.30 pouces. En calant la figure sur
    # cette largeur, une police de 7 pt dans le schema reste une police de 7 pt
    # dans le Word — sinon l'image est reduite a l'insertion et le texte devient
    # illisible.
    SCALE = 6.30 / 100.0

    def __init__(self, width: float = 100, height: float = 50,
                 scale: float | None = None, bg: str = "#FFFFFF"):
        scale = self.SCALE if scale is None else scale
        self.scale = scale
        # Unites du repere par point typographique — sert a empiler le texte
        # sans chevauchement, quelle que soit l'echelle du schema.
        self.u_pt = 1.0 / (72.0 * scale)
        self.W, self.H = width, height
        self.fig = plt.figure(figsize=(width * scale, height * scale), dpi=DPI)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, width)
        self.ax.set_ylim(0, height)
        self.ax.axis("off")
        self.bg = bg
        self.ax.add_patch(plt.Rectangle((0, 0), width, height, color=bg, zorder=0))

    # ── Primitives ──────────────────────────────────────────────────────────
    def group(self, x, y, w, h, title=None, color="grenat", z=1):
        """Cadre de regroupement : fond tres clair + liseré colore + titre."""
        edge = PALETTE[color][0]
        self.ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
            linewidth=1.1, edgecolor=edge, facecolor=GROUP_FILL.get(color, "#F6F6F6"),
            zorder=z))
        if title:
            self.ax.text(x + w / 2, y + h - 2.4, title, ha="center", va="center",
                         color=edge, fontsize=8.5, fontweight="bold", zorder=z + 1)
        return self

    def box(self, x, y, w, h, title, lines=None, color="grenat",
            title_size=7.6, line_size=6.2, z=3):
        """Boite arrondie : titre gras + lignes secondaires."""
        fill, fg = PALETTE[color]
        self.ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
            linewidth=0, facecolor=fill, zorder=z))
        lines = lines or []
        cx = x + w / 2
        if not lines:
            self.ax.text(cx, y + h / 2, title, ha="center", va="center",
                         color=fg, fontsize=title_size, fontweight="bold",
                         zorder=z + 1)
            return self

        # Empilement centre : hauteur reelle de chaque ligne, en unites du
        # repere, pour que titre et sous-titres ne se chevauchent jamais.
        th = title_size * 1.32 * self.u_pt
        lh = line_size * 1.42 * self.u_pt
        total = th + len(lines) * lh
        top = y + h / 2 + total / 2
        self.ax.text(cx, top - th / 2, title, ha="center", va="center",
                     color=fg, fontsize=title_size, fontweight="bold",
                     zorder=z + 1)
        for i, ln in enumerate(lines):
            self.ax.text(cx, top - th - lh * (i + 0.5), ln, ha="center",
                         va="center", color=fg, fontsize=line_size,
                         alpha=0.93, zorder=z + 1)
        return self

    def path(self, points, color="#8A8A8A", lw=1.1, arrow=True, dashed=False,
             z=4):
        """Polyligne (liste de points) avec pointe de fleche sur le dernier
        segment. Remplace les enchainements d'`arrow` sans tete, qui laissaient
        des segments orphelins."""
        ls = (0, (3, 2)) if dashed else "solid"
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        if arrow and len(points) >= 2:
            self.ax.plot(xs[:-1], ys[:-1], color=color, lw=lw, zorder=z,
                         linestyle=ls, solid_capstyle="round")
            self.arrow(points[-2], points[-1], color=color, lw=lw,
                       dashed=dashed, z=z)
        else:
            self.ax.plot(xs, ys, color=color, lw=lw, zorder=z, linestyle=ls,
                         solid_capstyle="round")
        return self

    def label(self, x, y, txt, size=6.4, color="#5A5A5A", ha="center",
              va="center", weight="normal", style="normal", z=5):
        self.ax.text(x, y, txt, ha=ha, va=va, color=color, fontsize=size,
                     fontweight=weight, style=style, zorder=z)
        return self

    def arrow(self, p0, p1, color="#8A8A8A", lw=1.1, style="-|>",
              dashed=False, label=None, label_dx=0, label_dy=0,
              label_size=6.0, rad=0.0, z=4):
        self.ax.add_patch(FancyArrowPatch(
            p0, p1, arrowstyle=style, mutation_scale=9, linewidth=lw,
            color=color, zorder=z,
            linestyle=(0, (3, 2)) if dashed else "solid",
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=0, shrinkB=0))
        if label:
            mx, my = (p0[0] + p1[0]) / 2 + label_dx, (p0[1] + p1[1]) / 2 + label_dy
            self.label(mx, my, label, size=label_size)
        return self

    def elbow(self, p0, p1, color="#8A8A8A", lw=1.1, via="h", label=None,
              label_size=6.0, z=4):
        """Fleche en L : `via='h'` part horizontalement, `'v'` verticalement."""
        mid = (p1[0], p0[1]) if via == "h" else (p0[0], p1[1])
        self.ax.plot([p0[0], mid[0]], [p0[1], mid[1]], color=color, lw=lw, zorder=z)
        self.arrow(mid, p1, color=color, lw=lw, z=z)
        if label:
            self.label((p0[0] + mid[0]) / 2, p0[1] + 1.6, label, size=label_size)
        return self

    def brace_note(self, x, y, txt, color="#8E403C", size=6.4):
        self.label(x, y, txt, size=size, color=color, style="italic")
        return self

    def save(self, out: str | Path) -> str:
        out = str(out)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(out, dpi=DPI, facecolor=self.bg)
        plt.close(self.fig)
        return out
