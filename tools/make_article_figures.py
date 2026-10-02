"""Reproduce all figures and tables of the article (Dianoia manuscript).

    uv run python tools/make_article_figures.py  [output_dir]

Figures are written as PNG (300 dpi); a JSON file with the numbers used in the
tables is written alongside.
"""
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyArrowPatch
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from srmsim import (Propellant, CircularCoreGrain, StarGrain, CrossGrain, MoonGrain,
                    EndBurnerGrain, CoreMapGrain, SegmentedGrain, Nozzle, Motor, Chamber, size_throat)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
LS = ["-", "--", "-.", ":", (0, (5, 1, 1, 1, 1, 1))]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#dcdad3"
plt.rcParams.update({
    "font.family": "Liberation Serif", "mathtext.fontset": "stix", "font.size": 10,
    "axes.labelsize": 10, "axes.titlesize": 10, "legend.fontsize": 9, "xtick.labelsize": 9,
    "ytick.labelsize": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "lines.linewidth": 1.8, "legend.frameon": False,
    "savefig.dpi": 300, "savefig.bbox": "tight", "figure.dpi": 100,
})


def comma(x, _pos=None):
    s = f"{x:g}"
    return s.replace(".", ",")


def comma_axes(*axes):
    for ax in axes:
        ax.xaxis.set_major_formatter(FuncFormatter(comma))
        ax.yaxis.set_major_formatter(FuncFormatter(comma))


mm = 1e-3
KNDX, KNSU, KNSB = (Propellant.load(n) for n in ("KNDX", "KNSU", "KNSB"))
PROPS = (KNSU, KNDX, KNSB)
REF = KNSU
numbers = {}

def fig_burnrate():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
    for i, pr in enumerate(PROPS):
        pp = np.logspace(np.log10(pr.p_valid[0]), np.log10(pr.p_valid[1]), 800)
        a1.plot(pp / 1e6, [pr.burn_rate(x) * 1e3 for x in pp], color=C[i], ls=LS[i], label=pr.name)
    for rr in KNDX.ranges[1:]:
        a1.axvline(rr.p_min / 1e6, color=C[PROPS.index(KNDX)], lw=1.1, ls=(0, (4, 2.5)), alpha=0.95, zorder=1)
    a1.set_xscale("log"); a1.set_yscale("log")
    a1.set_xlabel("$p$ [MPa]"); a1.set_ylabel("$r$ [mm/s]")
    a1.set_xticks([0.1, 0.2, 0.5, 1, 2, 5, 10]); a1.set_yticks([2, 3, 5, 7, 10, 15, 20])
    a1.set_ylim(1.8, 20)
    comma_axes(a1); a1.minorticks_off()
    a1.legend(loc="lower right"); a1.set_title("(a)", loc="left")
    kn = np.linspace(50, 420, 300)
    for i, pr in enumerate(PROPS):
        cs = pr.cstar(0.975)
        ps = []
        for k in kn:
            p = 2e6
            for _ in range(300):
                rr = pr.range_for(p)
                pn = (k * pr.density * rr.a * cs) ** (1 / (1 - rr.n))
                if abs(pn - p) < 1: break
                p = 0.5 * (p + pn)
            ps.append(p / 1e6 if p <= pr.p_valid[1] * 1.001 else np.nan)
        a2.plot(kn, ps, color=C[i], ls=LS[i], label=pr.name)
    a2.set_xlabel("$K_n = A_\\mathrm{b}/A_\\mathrm{t}$"); a2.set_ylabel("$p_\\mathrm{c,eq}$ [MPa]")
    a2.set_ylim(0, 10); comma_axes(a2); a2.set_title("(b)", loc="left")
    a2.legend(loc="upper left")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig2_burnrate.png")); plt.close(fig)


def fig_schematic():
    fig, ax = plt.subplots(figsize=(6.3, 2.5))
    ax.set_aspect("equal"); ax.axis("off")
    Rc, L, t = 23, 300, 3
    rc, inh = 8, 3
    x0 = 4
    ax.add_patch(Rectangle((0, -Rc - t), L + 14, t, color="#8a8984"))
    ax.add_patch(Rectangle((0, Rc), L + 14, t, color="#8a8984"))
    ax.add_patch(Rectangle((-8, -Rc - t), 8, 2 * (Rc + t), color="#8a8984"))
    for sgn in (1, -1):
        y = rc if sgn > 0 else -Rc
        ax.add_patch(Rectangle((x0, y), L, Rc - rc, color="#e9c46a", ec="#b08a2e", lw=0.6))
        ax.add_patch(Rectangle((x0 - inh, y), inh, Rc - rc, color="#5b5a55"))
        ax.add_patch(Rectangle((x0 + L, y), inh, Rc - rc, color="#5b5a55"))
    xs = L + 14
    xt = xs + 16
    rt, re = 7, 17
    top = [(xs, Rc + t), (xs, Rc), (xt - 4, rt), (xt, rt), (xt + 38, re), (xt + 38, re + 5),
           (xt, rt + 6), (xs + 6, Rc + t)]
    ax.add_patch(Polygon(top, color="#4f4e4a"))
    ax.add_patch(Polygon([(px, -py) for px, py in top], color="#4f4e4a"))
    ax.add_patch(Rectangle((-6, -2), 10, 4, color=C[7]))
    ax.add_patch(FancyArrowPatch((90, 0), (xt + 60, 0), arrowstyle="-|>", mutation_scale=12, color=C[0], lw=1.4))
    ax.plot([xt, xt], [-rt, rt], color=C[1], lw=1.0, ls="--")
    ax.plot([xt + 38, xt + 38], [-re, re], color=C[1], lw=1.0, ls="--")
    kw = dict(fontsize=9, color=INK)
    arr = dict(arrowstyle="-", color=INK2, lw=.6)
    ax.annotate("ohišje", (170, Rc + 1.5), (170, Rc + 16), ha="center", arrowprops=arr, **kw)
    ax.annotate("pogonsko zrno, dolžina $L$", (70, 16), (60, Rc + 16), ha="center", arrowprops=arr, **kw)
    ax.annotate("zaščitena čelna ploskev", (x0 + L + 1.5, 15), (265, Rc + 16), ha="center", arrowprops=arr, **kw)
    ax.annotate("kanal", (230, 3), (230, -Rc - 16), ha="center", arrowprops=arr, **kw)
    ax.annotate("vžigalnik", (-1, -2), (5, -Rc - 16), ha="center", arrowprops=arr, **kw)
    ax.annotate("šoba", (xt + 20, -re + 2), (xt + 20, -Rc - 16), ha="center", arrowprops=arr, **kw)
    ax.text(xt, rt + 12, "$A_\\mathrm{t}$", ha="center", **kw)
    ax.text(xt + 38, re + 9, "$A_\\mathrm{e}$", ha="center", **kw)
    ax.text(40, 0, "$p_\\mathrm{c},\\ T_\\mathrm{c}$", fontsize=9, color=INK, va="center")
    ax.text(xt + 64, -3, "$v_\\mathrm{e},\\ p_\\mathrm{e}$", fontsize=10, color=INK, va="center")
    ax.set_xlim(-12, xt + 90); ax.set_ylim(-Rc - 22, Rc + 22)
    fig.savefig(os.path.join(OUT, "fig1_schematic.png")); plt.close(fig)


D, L = 46 * mm, 300 * mm
FREE = 10 * mm
EPS = 6.0
P_TARGET = 4.0e6

def nozzle_for(dt):
    return Nozzle(dt, dt * math.sqrt(EPS), 15.0, 0.90)


GEOMS = {
    "A": ("krožni kanal", lambda: CircularCoreGrain(D, 16 * mm, L)),
    "B": ("7-kraki zvezdasti kanal", lambda: StarGrain(D, L, 7, 8 * mm, 26 * mm, 801)),
    "C": ("križni kanal", lambda: CrossGrain(D, L, 4, 4 * mm, 30 * mm, 801)),
    "D": ("izmaknjen krožni kanal", lambda: MoonGrain(D, L, 18 * mm, 12 * mm, 801)),
    "E": ("čelni gorilnik", lambda: EndBurnerGrain(D, L)),
}


def motor(grain, prop, dt):
    return Motor(prop, grain, nozzle_for(dt), Chamber(D, L + FREE))


def study():
    out = {}
    for key, (label, gfun) in GEOMS.items():
        g = gfun()
        dt = size_throat(lambda d: motor(g, REF, d), P_TARGET, 0.5e-3, 40e-3, tol=2e-6)
        runs = {}
        for pr in PROPS:
            m = motor(g, pr, dt)
            runs[pr.name] = (m, m.simulate(dt=1e-3))
        out[key] = (label, g, dt, runs)
    return out


def fig_geometry(res):
    keys = list(res)
    fig = plt.figure(figsize=(6.6, 4.1))
    gs = fig.add_gridspec(2, 5, height_ratios=[1.0, 1.7], hspace=0.12, wspace=0.08)
    th = np.linspace(0, 2 * np.pi, 400)
    R = D / 2 / mm
    for i, k in enumerate(keys):
        ax = fig.add_subplot(gs[0, i]); ax.set_aspect("equal"); ax.axis("off")
        g = res[k][1]
        ax.fill(R * np.cos(th), R * np.sin(th), color="#e9c46a", lw=0)
        ax.plot((R + 1.2) * np.cos(th), (R + 1.2) * np.sin(th), color="#8a8984", lw=2.4)
        if isinstance(g, CoreMapGrain):
            X, Y, dist, core, inside = g.field()
            ax.contourf(X / mm, Y / mm, np.where(core, 1.0, np.nan), levels=[0.5, 1.5], colors=["white"])
            ax.contour(X / mm, Y / mm, np.where(inside, dist, np.nan) / mm, levels=np.arange(3, 30, 3),
                       colors=[INK2], linewidths=0.5)
        elif isinstance(g, CircularCoreGrain):
            r0 = g.core_diameter / 2 / mm
            ax.fill(r0 * np.cos(th), r0 * np.sin(th), color="white")
            for ww in np.arange(3, 15, 3):
                ax.plot((r0 + ww) * np.cos(th), (r0 + ww) * np.sin(th), color=INK2, lw=0.5)
        else:
            ax.text(0, 0, "gori\nzadnja\nčelna\nploskev", ha="center", va="center", fontsize=7.5, color=INK)
        ax.set_title(k, fontsize=10, color=INK)
        ax.set_xlim(-R - 3, R + 3); ax.set_ylim(-R - 3, R + 3)
    ax = fig.add_subplot(gs[1, :])
    for i, k in enumerate(keys):
        g = res[k][1]
        ww = np.linspace(0, g.web * 0.9995, 400)
        ab = np.array([g.burning_area(x) for x in ww])
        ax.plot(ww / g.web, ab / ab[0], color=C[i], ls=LS[i], label=f"{k}: {res[k][0]}")
    ax.set_xlabel("delež izgorele debeline $w/w_\\mathrm{max}$")
    ax.set_ylabel("$A_\\mathrm{b}(w)/A_\\mathrm{b}(0)$")
    ax.set_xlim(0, 1); ax.set_ylim(0, 3.2); comma_axes(ax)
    ax.legend(loc="upper left", fontsize=8.5)
    fig.savefig(os.path.join(OUT, "fig3_geometry.png")); plt.close(fig)


def fig_matrix(res, key, ylabel, scale, fname):
    fig, axs = plt.subplots(2, 3, figsize=(6.6, 4.4))
    axs = axs.ravel()
    for i, k in enumerate(res):
        ax = axs[i]
        label, g, dt, runs = res[k]
        for j, pr in enumerate(PROPS):
            r = runs[pr.name][1]
            ax.plot(r.t, getattr(r, key) * scale, color=C[j], ls=LS[j], lw=1.4, label=pr.name)
        ax.set_title(f"{k}: {label}", fontsize=9, loc="left")
        ax.set_ylim(bottom=0); ax.set_xlim(left=0)
        ax.tick_params(labelsize=8)
        if i % 3 == 0:
            ax.set_ylabel(ylabel)
        if i >= 2:
            ax.set_xlabel("$t$ [s]")
        comma_axes(ax)
    axs[5].axis("off")
    h, l = axs[0].get_legend_handles_labels()
    axs[5].legend(h, l, loc="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname)); plt.close(fig)


BATES = {
    "1 × 300 mm, gori le kanal": lambda: CircularCoreGrain(D, 16 * mm, L),
    "3 × 100 mm, kanal in obe čeli": lambda: SegmentedGrain(CircularCoreGrain(D, 16 * mm, L / 3), 3, "both"),
    "4 × 75 mm, kanal in obe čeli": lambda: SegmentedGrain(CircularCoreGrain(D, 16 * mm, L / 4), 4, "both"),
}


def bates_study():
    out = {}
    for label, gfun in BATES.items():
        g = gfun()
        dt = size_throat(lambda d: motor(g, REF, d), P_TARGET, 0.5e-3, 40e-3, tol=2e-6)
        m = motor(g, REF, dt)
        out[label] = (g, dt, m, m.simulate(dt=1e-3))
    return out


def _bates_sketch(ax, g, color):
    """Longitudinal section of the grain stack (radial scale exaggerated); burning surfaces in colour,
    inhibited faces dark grey."""
    R, r0 = D / 2 / mm, 8.0
    n = g.n if isinstance(g, SegmentedGrain) else 1
    Ls = (g.segment_length if isinstance(g, SegmentedGrain) else g.length) / mm
    both = isinstance(g, SegmentedGrain) and g.k == 2
    for sg in (1, -1):
        ax.add_patch(Rectangle((0, sg * R if sg > 0 else -R - 2.5), L / mm, 2.5, color="#8a8984", lw=0))
        for i in range(n):
            x = i * Ls
            y = r0 if sg > 0 else -R
            ax.add_patch(Rectangle((x, y), Ls, R - r0, color="#e9c46a", ec="white", lw=1.0))
            ax.plot([x, x + Ls], [sg * r0, sg * r0], color=color, lw=2.2, solid_capstyle="butt")
            for xe in (x, x + Ls):
                ax.plot([xe, xe], [sg * r0, sg * R], color=color if both else "#5b5a55", lw=2.2 if both else 1.8)
    ax.plot([-3, L / mm + 3], [0, 0], color=INK2, lw=0.6, ls=(0, (6, 3, 1, 3)))
    ax.set_xlim(-4, L / mm + 4); ax.set_ylim(-R - 4, R + 4); ax.axis("off")


def fig_bates(res):
    fig = plt.figure(figsize=(6.6, 3.9))
    gsp = fig.add_gridspec(2, 3, height_ratios=[0.30, 1.0], hspace=0.38, wspace=0.14)
    labels = list(res)
    for i, lab in enumerate(labels):
        ax = fig.add_subplot(gsp[0, i])
        _bates_sketch(ax, res[lab][0], C[i])
        ax.set_title(lab, fontsize=8.5, color=INK)
    sub = gsp[1, :].subgridspec(1, 2, wspace=0.32)
    a1, a2 = fig.add_subplot(sub[0, 0]), fig.add_subplot(sub[0, 1])
    for i, lab in enumerate(labels):
        g, dt, m, r = res[lab]
        ww = np.linspace(0, g.web * 0.9995, 400)
        a1.plot(ww / mm, [g.burning_area(x) / 1e-4 for x in ww], color=C[i], ls=LS[i], label=lab)
        a2.plot(r.t, r.p / 1e6, color=C[i], ls=LS[i], label=lab)
    a1.set_xlabel("izgorela debelina $w$ [mm]"); a1.set_ylabel("$A_\\mathrm{b}$ [cm²]")
    a1.set_xlim(0, 15.5); a1.set_ylim(0, 450); a1.set_title("(a)", loc="left")
    a2.set_xlabel("$t$ [s]"); a2.set_ylabel("$p_\\mathrm{c}$ [MPa]")
    a2.set_xlim(left=0); a2.set_ylim(0, 4.6); a2.set_title("(b)", loc="left")
    comma_axes(a1, a2)
    a1.legend(loc="lower right", fontsize=7.5)
    fig.savefig(os.path.join(OUT, "fig7_bates.png")); plt.close(fig)


def bates_numbers(res):
    out = {}
    for lab, (g, dt, m, r) in res.items():
        ww = np.linspace(0, g.web * 0.9995, 2000)
        ab = np.array([g.burning_area(x) for x in ww])
        bt = r.t <= r.t_burnout
        out[lab] = dict(**r.summary(), throat_mm=round(dt * 1e3, 2), web_mm=round(g.web * 1e3, 2),
                        Ab0_cm2=round(ab[0] / 1e-4, 1), Ab_max_cm2=round(ab.max() / 1e-4, 1),
                        Ab_end_cm2=round(ab[-1] / 1e-4, 1),
                        p_min_burn_MPa=round(float(r.p[bt & (r.t > 0.05 * r.t_burnout)].min()) / 1e6, 3),
                        tau_ms=round(m.time_constant() * 1e3, 2))
    return out


if __name__ == "__main__":
    fig_schematic()
    fig_burnrate()
    res = study()
    fig_geometry(res)
    fig_matrix(res, "p", "$p_\\mathrm{c}$ [MPa]", 1e-6, "fig4_pressure.png")
    fig_matrix(res, "F", "$F$ [N]", 1.0, "fig5_thrust.png")
    numbers["study"] = {}
    for k, (label, g, dt, runs) in res.items():
        numbers["study"][k] = {"label": label, "throat_mm": round(dt * 1e3, 2),
                               "exit_mm": round(dt * 1e3 * math.sqrt(EPS), 2),
                               "web_mm": round(g.web * 1e3, 2),
                               "runs": {n: dict(**r.summary(), warnings=r.warnings) for n, (m, r) in runs.items()}}
    mA = res["A"][3][REF.name][0]
    numbers["designA_tau_s"] = mA.time_constant()
    numbers["cstar"] = {p.name: p.cstar(0.975) for p in PROPS}
    bres = bates_study()
    fig_bates(bres)
    numbers["bates"] = bates_numbers(bres)
    with open(os.path.join(OUT, "numbers.json"), "w", encoding="utf-8") as f:
        json.dump(numbers, f, indent=2, ensure_ascii=False, default=float)
    print(json.dumps(numbers, indent=1, ensure_ascii=False, default=float))
