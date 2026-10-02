"""Server-side Matplotlib charts returned to the browser as SVG."""
from __future__ import annotations

import io
from collections.abc import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from srmsim import Motor, SimulationResult

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
DASH = ["-", "--", "-.", ":", (0, (5, 1, 1, 1))]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#dcdad3"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "lines.linewidth": 2.0, "legend.frameon": False,
    "svg.fonttype": "none", "font.family": "sans-serif",
})

Runs = Iterable[tuple[str, SimulationResult]]


def _svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    text = buf.getvalue()
    return text[text.index("<svg"):]


def time_plot(runs: Runs, key: str, ylabel: str, order: list[str], scale: float = 1.0) -> str:
    runs = list(runs)
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    for name, res in runs:
        i = order.index(name) if name in order else 0
        ax.plot(res.t, getattr(res, key) * scale, color=SERIES[i % 8], ls=DASH[i % 5], label=name)
    ax.set_xlabel("$t$ [s]")
    ax.set_ylabel(ylabel)
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    if len(runs) > 1:
        ax.legend(loc="best")
    return _svg(fig)


def kn_plot(motor: Motor) -> str:
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ww = np.linspace(0, motor.web * 0.9995, 300)
    ax.plot(ww * 1e3, [motor.kn(x) for x in ww], color=SERIES[0])
    ax.set_xlabel("burnt web $w$ [mm]")
    ax.set_ylabel("$K_n = A_\\mathrm{b}/A_\\mathrm{t}$")
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    return _svg(fig)
