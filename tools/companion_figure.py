"""Figure 1 of the companion paper, drawn from runs_mp/results.json (no number is typed here).

Two panels, one per model. For each memory condition, two bars: sessions (of 50) in which the reply acted on the
targeted false inference, for recall questions and for task questions.

  python tools/companion_figure.py      -> report/generated/companion_fig1.png

Colors are slots 1 and 2 of the validated categorical palette (blue #2a78d6, orange #eb6834); every bar carries its
value, and the same numbers are in Appendix B as a table.
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "runs_mp", "results.json"), encoding="utf-8"))
CONDS = [("A", "No\nmemory"), ("B", "Naive\nmemory"), ("C", "Labels"), ("C_gate", "Labels\n+ gate"), ("C_hold", "Labels\n+ hold")]
SERIES = [("recall", "Recall question", "#2a78d6"), ("task", "Task question", "#eb6834")]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def cell(tag, cond, kind):
    b = next(x for x in R[tag]["t1"]["by_kind"] if x["condition"] == cond and x["kind"] == kind)
    return b["action"], b["judged"]


plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.45), sharey=True)
for ax, (tag, name) in zip(axes, (("gemma431bit", "gemma-4-31b-it"), ("deepseekv4fl", "deepseek-v4-flash"))):
    width = 0.36
    for k, (kind, label, color) in enumerate(SERIES):
        xs = [i + (k - 0.5) * (width + 0.03) for i in range(len(CONDS))]
        vals = [cell(tag, c, kind) for c, _ in CONDS]
        ax.bar(xs, [100.0 * a / n for a, n in vals], width=width, color=color, label=label, linewidth=0, zorder=3)
        for x, (a, n) in zip(xs, vals):
            ax.text(x, 100.0 * a / n + 2.0, f"{a}/{n}", ha="center", va="bottom", fontsize=6.8, color=INK, zorder=4)
    ax.set_xticks(range(len(CONDS))); ax.set_xticklabels([lab for _, lab in CONDS], fontsize=7, color=INK)
    ax.set_ylim(0, 100); ax.set_yticks([0, 25, 50, 75, 100])
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0); ax.set_axisbelow(True)
    for side in ("top", "right", "left"): ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED); ax.tick_params(axis="both", length=0, colors=MUTED)
    ax.set_title(name, fontsize=8.5, color=INK, loc="left", pad=6)
axes[0].set_ylabel("Sessions where the reply acted\non the false memory (%)", fontsize=7.5, color=INK)
axes[1].legend(loc="upper right", frameon=False, fontsize=7.5, handlelength=1.2, borderaxespad=0.2)
fig.tight_layout(w_pad=1.2)
out = os.path.join(ROOT, "report", "generated"); os.makedirs(out, exist_ok=True)
fig.savefig(os.path.join(out, "companion_fig1.png"), dpi=220, facecolor="white")
print("wrote", os.path.join(out, "companion_fig1.png"))
