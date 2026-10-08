"""Aperçu du reporting (docs/apercu.png) en attendant le dashboard Power BI.

Rejoue sql/controles.sql sur les CSV de data/ et trace trois vues :
écarts par contrôle, état du parc par type, parc hors garantie par type.
"""
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
BG, FG, MUTED, GRID, ACCENT = "#111111", "#ededed", "#8a8a8a", "#2a2a2a", "#c4f24e"

con = duckdb.connect()
con.execute((ROOT / "sql" / "controles.sql").read_text(encoding="utf-8"))
synthese = con.sql("SELECT controle, nb_ecarts FROM synthese_controles ORDER BY nb_ecarts").fetchall()
etat = con.sql("""
    SELECT type,
           count(*) FILTER (statut = 'attribué') AS attribue,
           count(*) FILTER (statut = 'en stock') AS stock,
           count(*) FILTER (statut = 'réformé') AS reforme
    FROM equipements GROUP BY type ORDER BY count(*)
""").fetchall()
renouv = dict(con.sql("SELECT type, count(*) FROM a_renouveler GROUP BY type").fetchall())
n_eq = con.sql("SELECT count(*) FROM equipements").fetchone()[0]
n_mvt = con.sql("SELECT count(*) FROM mouvements").fetchone()[0]
n_ecarts = sum(n for _, n in synthese)

plt.rcParams.update({"font.family": "Segoe UI", "text.color": FG, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": FG, "axes.edgecolor": GRID})
fig = plt.figure(figsize=(16, 9), facecolor=BG)
fig.text(0.04, 0.92, "ParcIT", fontsize=34, fontweight="bold", color=FG)
fig.text(0.04, 0.875, "Qualité des données d'un parc informatique · contrôles SQL (DuckDB)",
         fontsize=15, color=MUTED)

kpis = [(f"{n_eq:,}".replace(",", " "), "équipements"),
        (f"{n_mvt:,}".replace(",", " "), "mouvements"),
        (str(n_ecarts), "écarts détectés"),
        (f"{sum(renouv.values()):,}".replace(",", " "), "hors garantie")]
for i, (val, lab) in enumerate(kpis):
    x = 0.04 + i * 0.235
    fig.text(x, 0.74, val, fontsize=40, fontweight="bold", color=ACCENT if i == 2 else FG)
    fig.text(x, 0.70, lab, fontsize=14, color=MUTED)


def style(ax, title):
    ax.set_facecolor(BG)
    ax.set_title(title, loc="left", fontsize=15, color=FG, pad=14)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=12)
    ax.tick_params(axis="x", labelsize=11)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


# Écarts par contrôle
ax = fig.add_axes([0.17, 0.08, 0.2, 0.5])
style(ax, "Écarts par contrôle")
labels = [c.replace("Attribué à un collaborateur parti", "Attribué à un parti")
          .replace("Champs obligatoires manquants", "Champs manquants")
          .replace("Doublons de n° de série", "Doublons n° série") for c, _ in synthese]
vals = [n for _, n in synthese]
ax.barh(labels, vals, color=ACCENT, height=0.6)
for y, v in enumerate(vals):
    ax.text(v + 1.5, y, str(v), va="center", fontsize=12, color=FG)

# État du parc par type
ax = fig.add_axes([0.5, 0.08, 0.2, 0.5])
style(ax, "État du parc par type")
types = [t for t, *_ in etat]
left = [0] * len(etat)
for idx, (lab, col) in enumerate([("attribué", FG), ("en stock", "#6b6b6b"), ("réformé", "#3a3a3a")]):
    v = [row[idx + 1] for row in etat]
    ax.barh(types, v, left=left, color=col, height=0.6, label=lab)
    left = [a + b for a, b in zip(left, v)]
ax.legend(frameon=False, loc="lower right", fontsize=11, labelcolor=MUTED)

# Hors garantie par type
ax = fig.add_axes([0.79, 0.08, 0.17, 0.5])
style(ax, "Hors garantie, encore en service")
ax.barh(types, [renouv.get(t, 0) for t in types], color="#6b6b6b", height=0.6)
ax.set_yticklabels([])

out = ROOT / "docs" / "apercu.png"
out.parent.mkdir(exist_ok=True)
fig.savefig(out, dpi=110, facecolor=BG)
print(out)
