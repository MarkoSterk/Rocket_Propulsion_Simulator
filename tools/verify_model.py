"""Computational verification of the internal-ballistics model.

    uv run python tools/verify_model.py [output_dir] [path/to/SRM_2023.xls(x)]

Checks (results are printed and written to ``verification.json``):

1. quasi-steady pressure: simulated p_c against Eq. (7), for a constant-Kn
   end burner and along the whole burn of the circular-canal grain A
   (for KNDX and KNSB this also exercises the transitions between the
   pressure ranges of the burn-rate law);
2. time-step convergence: h = tau/2 ... tau/32;
3. grid convergence of the distance-transform geometry: 401, 801, 1601 points;
4. comparison with the example BATES motor of R. Nakka's SRM 2023 spreadsheet;
5. nozzle at low chamber pressure: share of the impulse delivered with a
   separated nozzle flow, and sea-level against vacuum specific impulse for
   the one-grain / BATES comparison of the article.

The optional SRM file is only used to overlay SRM's p(t) and F(t) curves in
``verification_srm2023.png``; the reference numbers below were read from the
unmodified example case of SRM_2023.xls (Data and Kn, Pressure and
Performance sheets).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from srmsim import (Chamber, CircularCoreGrain, CoreMapGrain, CrossGrain, EndBurnerGrain, Motor,  # noqa: E402
                    MoonGrain, Nozzle, Propellant, SegmentedGrain, StarGrain, moon_core, size_throat)
from srmsim.propellant import G0  # noqa: E402

mm = 1e-3
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "verification")
SRM_FILE = sys.argv[2] if len(sys.argv) > 2 else None
os.makedirs(OUT, exist_ok=True)

D, L, FREE, EPS, P_TARGET = 46 * mm, 300 * mm, 10 * mm, 6.0, 4.0e6
PROPS = {n: Propellant.load(n) for n in ("KNSU", "KNDX", "KNSB")}
_trapz = getattr(np, "trapezoid", None) or np.trapz
results = {}


def nozzle(dt, eps=EPS, half_angle=15.0, eff=0.90, sep=0.4):
    return Nozzle(dt, dt * math.sqrt(eps), half_angle, eff, sep)


def motor(grain, prop, dt, **kw):
    return Motor(prop, grain, nozzle(dt, **kw), Chamber(D, grain.length + FREE))


def rel(a, b):
    return (a - b) / b


def eq7(m, kn, gas_fill=False):
    """Eq. (7) solved with the piecewise law; optionally with the gas-fill term (1 - rho_g/rho_p)."""
    pr = m.propellant
    cs = pr.cstar(m.cstar_efficiency)
    p = 3e6
    for _ in range(500):
        rr = pr.range_for(p)
        f = 1.0 - (p / (m.R * m.T)) / pr.density if gas_fill else 1.0
        pn = (kn * pr.density * f * rr.a * cs) ** (1.0 / (1.0 - rr.n))
        if abs(pn - p) < 0.01:
            break
        p = 0.5 * (p + pn)
    return pn


def check_equilibrium():
    out = {}
    g = EndBurnerGrain(D, L)
    dt = size_throat(lambda d: motor(g, PROPS["KNSU"], d), P_TARGET, 0.5e-3, 40e-3, tol=2e-6)
    for name, pr in PROPS.items():
        m = motor(g, pr, dt)
        r = m.simulate()
        mid = (r.t > 0.2 * r.t_burnout) & (r.t < 0.8 * r.t_burnout)
        kn = m.kn(0.0)
        p_sim = float(np.median(r.p[mid]))
        out[f"end burner {name}"] = {
            "Kn": round(kn, 2), "p_sim_MPa": round(p_sim / 1e6, 4),
            "p_eq7_MPa": round(eq7(m, kn) / 1e6, 4),
            "p_eq7_gasfill_MPa": round(eq7(m, kn, True) / 1e6, 4),
            "dev_eq7_gasfill_pct": round(100 * rel(p_sim, eq7(m, kn, True)), 3)}
    g = CircularCoreGrain(D, 16 * mm, L)
    dt = size_throat(lambda d: motor(g, PROPS["KNSU"], d), P_TARGET, 0.5e-3, 40e-3, tol=2e-6)
    for name, pr in PROPS.items():
        m = motor(g, pr, dt)
        r = m.simulate()
        sel = (r.t > 0.1 * r.t_burnout) & (r.t < 0.95 * r.t_burnout)
        dev = [rel(p, eq7(m, m.kn(w), True)) for p, w in zip(r.p[sel], r.w[sel])]
        out[f"circular canal A {name}"] = {"max_abs_dev_pct": round(100 * float(np.max(np.abs(dev))), 3),
                                           "mean_dev_pct": round(100 * float(np.mean(dev)), 3)}
    return out


def metrics(r):
    return {"p_max_MPa": r.peak_pressure / 1e6, "I_Ns": r.total_impulse, "t_b_s": r.burn_time,
            "Isp_s": r.specific_impulse, "F_max_N": r.peak_thrust}


def check_time_step():
    out = {}
    g = CircularCoreGrain(D, 16 * mm, L)
    dt = size_throat(lambda d: motor(g, PROPS["KNSU"], d), P_TARGET, 0.5e-3, 40e-3, tol=2e-6)
    for name in ("KNSU", "KNDX"):
        m = motor(g, PROPS[name], dt)
        tau = m.time_constant()
        fr = [0.5, 0.25, 0.125, 0.0625, 0.03125]
        res = {f: metrics(m.simulate(dt=1.0, tau_fraction=f, max_points=10 ** 7)) for f in fr}
        ref = res[fr[-1]]
        out[name] = {"tau0_ms": round(tau * 1e3, 3), "steps": {
            f"tau/{round(1 / f)} (h={f * tau * 1e3:.3f} ms)": {k: f"{100 * rel(v, ref[k]):+.4f} %"
                                                            for k, v in res[f].items()} for f in fr[:-1]}}
    return out


def check_grid():
    out = {}
    makers = {
        "B star": lambda n: StarGrain(D, L, 7, 8 * mm, 26 * mm, n),
        "C cross": lambda n: CrossGrain(D, L, 4, 4 * mm, 30 * mm, n),
        "D moon": lambda n: MoonGrain(D, L, 18 * mm, 12 * mm, n),
        "A circular (numeric)": lambda n: CoreMapGrain(D, L, moon_core(16 * mm, 0.0), resolution=n),
    }
    exact = CircularCoreGrain(D, 16 * mm, L)
    for key, mk in makers.items():
        grains = {n: mk(n) for n in (401, 801, 1601)}
        ref = exact if key.startswith("A") else grains[1601]
        dt = size_throat(lambda d: motor(grains[801], PROPS["KNSU"], d), P_TARGET, 0.5e-3, 40e-3, tol=2e-6)
        sims = {n: metrics(motor(g, PROPS["KNSU"], dt).simulate()) for n, g in grains.items()}
        if key.startswith("A"):
            sims["exact"] = metrics(motor(exact, PROPS["KNSU"], dt).simulate())
        refm = sims["exact"] if key.startswith("A") else sims[1601]
        row = {}
        for n, g in grains.items():
            ww = np.linspace(0.02 * ref.web, 0.98 * min(ref.web, g.web), 200)
            a_ref = np.array([ref.burning_area(w) for w in ww])
            a_g = np.array([g.burning_area(w) for w in ww])
            dab = float(np.max(np.abs(a_g - a_ref)) / a_ref.max())
            row[str(n)] = {"web_mm": round(g.web / mm, 3), "max_dAb_over_Abmax_pct": round(100 * dab, 3),
                           **{k: f"{100 * rel(v, refm[k]):+.3f} %" for k, v in sims[n].items()}}
        out[key] = {"reference": "analytic" if key.startswith("A") else "1601", "throat_mm": round(dt / mm, 3),
                    "grids": row}
    return out


SRM2023_EXAMPLE = {
    "description": "SRM_2023.xls example: KNDX, 4 BATES segments 115 mm, D 69 mm, d 20 mm, all faces "
                   "except the outer surface burning; chamber 75 x 470 mm; throat 221.47 mm2; "
                   "expansion ratio 8; combustion efficiency 0.95 (T = 0.95 T0); nozzle efficiency 0.85; "
                   "p_a = 0.101 MPa; erosive burning off",
    "grain_mass_kg": 2.8124, "p_max_MPa_abs": 6.4047, "t_burnout_s": 1.9422, "t_thrust_s": 2.0253,
    "F_max_N": 1968.1, "F_avg_N": 1728.9, "I_Ns": 3501.5, "Isp_s": 126.96,
}


def srm_motor():
    pr = PROPS["KNDX"]
    seg = CircularCoreGrain(69 * mm, 20 * mm, 115 * mm)
    g = SegmentedGrain(seg, 4, "both")
    dt = math.sqrt(4 * 221.472755889953e-6 / math.pi)
    noz = Nozzle(dt, dt * math.sqrt(8.0), 0.0, 0.85, 0.4)
    return Motor(pr, g, noz, Chamber(75 * mm, 470 * mm), cstar_efficiency=math.sqrt(0.95),
                 ambient_pressure=0.101e6)


def check_srm():
    m = srm_motor()
    r = m.simulate()
    ref = SRM2023_EXAMPLE
    ours = {"grain_mass_kg": r.propellant_mass, "p_max_MPa_abs": r.peak_pressure / 1e6,
            "t_burnout_s": r.t_burnout, "F_max_N": r.peak_thrust, "I_Ns": r.total_impulse,
            "Isp_s": r.total_impulse / (r.propellant_mass * 9.806)}
    out = {"case": ref["description"], "rows": {
        k: {"SRM 2023": ref[k], "this model": round(v, 4), "diff": f"{100 * rel(v, ref[k]):+.2f} %"}
        for k, v in ours.items()}}
    if SRM_FILE:
        try:
            out["overlay"] = overlay_srm(r, SRM_FILE)
        except Exception as e:  # noqa: BLE001
            out["overlay"] = f"not drawn: {e}"
    return out


def overlay_srm(r, path):
    import openpyxl
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if path.lower().endswith(".xls"):
        raise ValueError("convert the .xls file to .xlsx first (e.g. with LibreOffice)")
    wb = openpyxl.load_workbook(path, data_only=True)
    ps, pf = wb["Pressure"], wb["Performance"]
    t, p = [], []
    for row in range(28, 911):
        tv, pv = ps[f"Q{row}"].value, ps[f"AB{row}"].value
        if isinstance(tv, (int, float)) and isinstance(pv, (int, float)):
            t.append(tv); p.append(pv)
    tf, F = [], []
    for row in range(28, 911):
        tv, fv = pf[f"L{row}"].value, pf[f"J{row}"].value
        if isinstance(tv, (int, float)) and isinstance(fv, (int, float)):
            tf.append(tv); F.append(fv)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.5, 2.8))
    a1.plot(r.t, r.p / 1e6, label="this model"); a1.plot(t, p, "--", label="SRM 2023")
    a2.plot(r.t, r.F, label="this model"); a2.plot(tf, F, "--", label="SRM 2023")
    a1.set_xlabel("t [s]"); a1.set_ylabel("p_c [MPa, abs]"); a2.set_xlabel("t [s]"); a2.set_ylabel("F [N]")
    a1.legend(frameon=False); a1.grid(alpha=.3); a2.grid(alpha=.3)
    fig.tight_layout(); fn = os.path.join(OUT, "verification_srm2023.png"); fig.savefig(fn, dpi=200)
    plt.close(fig)
    return fn


def impulse_split(m, r):
    """Impulse and propellant burnt with a separated nozzle flow, and the vacuum impulse."""
    pr, noz = m.propellant, m.nozzle
    sep = np.array([noz.is_separated(p, m.p_a, pr.gamma_exhaust) if p > m.p_a else False for p in r.p])
    I = r.total_impulse
    I_sep = float(_trapz(np.where(sep, r.F, 0.0), r.t))
    mdot_gen = pr.density * r.Ab * r.r
    m_sep = float(_trapz(np.where(sep, mdot_gen, 0.0), r.t))
    k = noz.efficiency * noz.divergence_factor
    vac = Nozzle(noz.throat_diameter, noz.exit_diameter, noz.divergence_half_angle, noz.efficiency, 0.0)
    F_vac = np.array([k * vac.thrust_coefficient(p, 0.0, pr.gamma_exhaust) * p * noz.throat_area
                      for p in r.p])
    I_vac = float(_trapz(F_vac, r.t))
    return {"Isp_s": r.specific_impulse, "Isp_vac_s": I_vac / (r.propellant_mass * G0),
            "share_I_separated_pct": 100 * I_sep / I, "share_mass_separated_pct": 100 * m_sep / r.propellant_mass}


def check_low_pressure():
    out = {}
    pr = PROPS["KNSU"]
    noz = nozzle(10 * mm)
    ge = pr.gamma_exhaust
    from srmsim.nozzle import exit_pressure_ratio
    pe_pc = exit_pressure_ratio(EPS, ge)
    p_onset = 0.4 * 101325.0 / pe_pc
    out["nozzle eps=6 KNSU"] = {
        "gamma_e": ge, "pe_over_pc": round(pe_pc, 5),
        "separation_below_MPa": round(p_onset / 1e6, 3),
        "pc_where_unseparated_CF_would_be_0_MPa": None,
        "CF": {f"{pc / 1e6:g} MPa": round(noz.thrust_coefficient(pc, 101325.0, ge), 4)
               for pc in (6e6, 4e6, 2e6, 1e6, 0.5e6, 0.3e6, 0.2e6)},
        "CF_no_separation": {f"{pc / 1e6:g} MPa": round(nozzle(10 * mm, sep=0.0).thrust_coefficient(
            pc, 101325.0, ge), 4) for pc in (4e6, 2e6, 1e6, 0.5e6, 0.3e6, 0.2e6)},
        "CF_vacuum": round(noz.thrust_coefficient(4e6, 0.0, ge), 4),
        "momentum_term": round(noz.thrust_coefficient(4e6, 4e6 * pe_pc, ge), 4),
    }
    nosep = nozzle(10 * mm, sep=0.0)
    from scipy.optimize import brentq
    out["nozzle eps=6 KNSU"]["pc_where_unseparated_CF_would_be_0_MPa"] = round(
        brentq(lambda pc: nosep.thrust_coefficient(pc, 101325.0, ge), 0.12e6, 2e6) / 1e6, 3)
    cases = {
        "1 x 300 mm (canal)": CircularCoreGrain(D, 16 * mm, L),
        "3 x 100 mm (BATES)": SegmentedGrain(CircularCoreGrain(D, 16 * mm, L / 3), 3, "both"),
        "4 x 75 mm (BATES)": SegmentedGrain(CircularCoreGrain(D, 16 * mm, L / 4), 4, "both"),
    }
    rows = {}
    for lab, g in cases.items():
        dt = size_throat(lambda d: motor(g, pr, d), P_TARGET, 0.5e-3, 40e-3, tol=2e-6)
        m = motor(g, pr, dt)
        r = m.simulate()
        row = impulse_split(m, r)
        r_nosep = motor(g, pr, dt, sep=0.0).simulate()
        row["Isp_without_separation_model_s"] = r_nosep.specific_impulse
        row["throat_mm"] = dt / mm
        rows[lab] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items() if v is not None}
    base = rows["1 x 300 mm (canal)"]
    for lab, row in rows.items():
        row["gain_sea_level_pct"] = round(100 * rel(row["Isp_s"], base["Isp_s"]), 2)
        row["gain_vacuum_pct"] = round(100 * rel(row["Isp_vac_s"], base["Isp_vac_s"]), 2)
    out["one grain vs BATES (KNSU)"] = rows
    return out


if __name__ == "__main__":
    results["1_equilibrium_pressure"] = check_equilibrium()
    results["2_time_step"] = check_time_step()
    results["3_grid"] = check_grid()
    results["4_srm2023"] = check_srm()
    results["5_low_pressure_nozzle"] = check_low_pressure()
    with open(os.path.join(OUT, "verification.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=float)
    print(json.dumps(results, indent=1, ensure_ascii=False, default=float))
