"""Solid rocket motor model and time integration of the chamber pressure.

Governing equations (lumped-parameter, "0-D" internal ballistics)
-------------------------------------------------------------------
Mass balance of the combustion gas in the free chamber volume V(t)::

    d(rho_g V)/dt = rho_p A_b r - mdot_n,        dV/dt = A_b r

With the ideal gas law rho_g = p/(R T) and T = const. this gives::

    V/(R T) dp/dt = A_b r (rho_p - rho_g) - mdot_n(p)          (*)

    dw/dt = r(p) = a_i p^n_i        (piecewise Saint Robert law)

(*) is integrated together with the web equation until the grain is
consumed; the tail-off (A_b = 0) is then integrated until the chamber
pressure has decayed to ambient.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from .grains import Grain, grain_from_dict
from .nozzle import Nozzle
from .propellant import G0, Propellant

_trapz = getattr(np, "trapezoid", None) or np.trapz

MOTOR_CLASSES = [(c, 1.25 * 2 ** i) for i, c in enumerate("ABCDEFGHIJKLMNO")]


def motor_class(total_impulse: float) -> str:
    """Impulse-class letter (NFPA 1125 / NAR: each letter doubles the total impulse) in N s."""
    if total_impulse <= 2.5:
        return "A" if total_impulse > 1.25 else "1/2A or smaller"
    for letter, lower in MOTOR_CLASSES:
        if lower < total_impulse <= 2 * lower:
            return letter
    return ">O"


@dataclass
class Chamber:
    inner_diameter: float
    length: float

    @property
    def volume(self) -> float:
        return math.pi * 0.25 * self.inner_diameter ** 2 * self.length


@dataclass
class SimulationResult:
    t: np.ndarray
    p: np.ndarray
    F: np.ndarray
    w: np.ndarray
    Ab: np.ndarray
    Kn: np.ndarray
    mdot: np.ndarray
    r: np.ndarray
    p_ambient: float
    propellant_mass: float
    t_burnout: float
    warnings: list[str] = field(default_factory=list)

    @property
    def total_impulse(self) -> float:
        return float(_trapz(self.F, self.t))

    @property
    def peak_pressure(self) -> float:
        return float(self.p.max())

    @property
    def peak_thrust(self) -> float:
        return float(self.F.max())

    @property
    def specific_impulse(self) -> float:
        return self.total_impulse / (self.propellant_mass * G0)

    @property
    def burn_time(self) -> float:
        """Action time: thrust above 10 % of peak thrust."""
        idx = np.where(self.F >= 0.1 * self.F.max())[0]
        return float(self.t[idx[-1]] - self.t[idx[0]]) if len(idx) else 0.0

    @property
    def average_thrust(self) -> float:
        bt = self.burn_time
        return self.total_impulse / bt if bt > 0 else 0.0

    def summary(self) -> dict:
        I = self.total_impulse
        return {
            "propellant_mass_kg": round(self.propellant_mass, 4),
            "peak_pressure_MPa": round(self.peak_pressure / 1e6, 3),
            "peak_thrust_N": round(self.peak_thrust, 1),
            "average_thrust_N": round(self.average_thrust, 1),
            "total_impulse_Ns": round(I, 1),
            "burn_time_s": round(self.burn_time, 3),
            "grain_burnout_s": round(self.t_burnout, 3),
            "specific_impulse_s": round(self.specific_impulse, 1),
            "motor_class": motor_class(I) + str(int(round(self.average_thrust))),
            "initial_Kn": round(float(self.Kn[0]), 1),
            "peak_Kn": round(float(self.Kn.max()), 1),
        }

    def to_csv(self, path: str):
        with open(path, "w", newline="") as f:
            f.write(self.csv_string())

    def csv_string(self) -> str:
        f = io.StringIO()
        if True:
            wr = csv.writer(f)
            wr.writerow(["t_s", "p_MPa", "F_N", "web_mm", "Ab_mm2", "Kn", "mdot_kg_s", "r_mm_s"])
            for row in zip(self.t, self.p / 1e6, self.F, self.w * 1e3, self.Ab * 1e6, self.Kn,
                           self.mdot, self.r * 1e3):
                wr.writerow([f"{v:.6g}" for v in row])
        return f.getvalue()


class Motor:
    """A motor with one grain of length L or N segments (see grains.py)."""

    def __init__(self, propellant: Propellant, grain: Grain, nozzle: Nozzle,
                 chamber: Optional[Chamber] = None, cstar_efficiency: float = 0.975,
                 burn_rate_multiplier: float = 1.0, ambient_pressure: float = 101325.0,
                 name: str = "motor", burnout_spread: float = 0.0, spread_slices: int = 21):
        self.name = name
        self.propellant = propellant
        self.grain = grain
        self.nozzle = nozzle
        if chamber is None:
            D = grain.outer_diameter
            chamber = Chamber(D, grain.length + max(0.25 * D, 5e-3))
        self.chamber = chamber
        self.cstar_efficiency = cstar_efficiency
        self.burn_rate_multiplier = burn_rate_multiplier
        self.p_a = ambient_pressure
        if not 0.0 <= burnout_spread < 0.5:
            raise ValueError("burnout_spread must be between 0 and 0.5")
        self.burnout_spread = float(burnout_spread)
        k = int(spread_slices) if burnout_spread > 0 else 1
        self._d = np.linspace(-burnout_spread, burnout_spread, k)
        self.T = propellant.combustion_temperature * cstar_efficiency ** 2
        self.R = propellant.gas_constant()
        if grain.propellant_volume(0.0) >= self.chamber.volume:
            raise ValueError("the grain does not fit into the chamber")

    @property
    def web(self) -> float:
        """Nominal burnt distance at which the last slice is consumed."""
        return self.grain.web / (1.0 - self.burnout_spread)

    def burning_area(self, w: float) -> float:
        """Geometric burning area (mean over slices)."""
        g = self.grain
        return sum(g.burning_area((1.0 + d) * w) for d in self._d) / len(self._d)

    def _generating_area(self, w: float) -> float:
        """Burning area weighted with the local burn-rate factor (1 + d)."""
        g = self.grain
        return sum((1.0 + d) * g.burning_area((1.0 + d) * w) for d in self._d) / len(self._d)

    def free_volume(self, w: float) -> float:
        g = self.grain
        return self.chamber.volume - sum(g.propellant_volume((1.0 + d) * w) for d in self._d) / len(self._d)

    def propellant_mass(self) -> float:
        return self.propellant.density * self.grain.propellant_volume(0.0)

    def burn_rate(self, p: float) -> float:
        return self.burn_rate_multiplier * self.propellant.burn_rate(p)

    def kn(self, w: float) -> float:
        return self.burning_area(w) / self.nozzle.throat_area

    def steady_state_pressure(self, w: float = 0.0) -> float:
        """Quasi-steady chamber pressure p = (Kn rho_p a c*)^(1/(1-n)), solved consistently
        with the piecewise burn-rate law by fixed-point iteration."""
        kn = self.kn(w)
        cstar = self.propellant.cstar(self.cstar_efficiency)
        rho = self.propellant.density
        p = 3e6
        for _ in range(200):
            rr = self.propellant.range_for(p)
            p_new = (kn * rho * self.burn_rate_multiplier * rr.a * cstar) ** (1.0 / (1.0 - rr.n))
            if abs(p_new - p) < 1.0:
                break
            p = 0.5 * (p + p_new)
        return p

    def _rhs(self, t, y, burning: bool):
        p, w = max(y[0], self.p_a), y[1]
        pr = self.propellant
        V = self.free_volume(min(w, self.web))
        mdot_n = self.nozzle.mass_flow(p, self.p_a, self.R, self.T, pr.gamma_chamber)
        if burning:
            r = self.burn_rate(p)
            Ab = self._generating_area(w)
        else:
            r, Ab = 0.0, 0.0
        rho_g = p / (self.R * self.T)
        dpdt = (self.R * self.T / V) * (Ab * r * (pr.density - rho_g) - mdot_n)
        return [dpdt, r]

    def time_constant(self) -> float:
        """Filling/emptying time constant of the chamber, tau = V c* / (R T A_t)."""
        cstar = self.propellant.cstar(self.cstar_efficiency)
        return self.free_volume(0.0) * cstar / (self.R * self.T * self.nozzle.throat_area)

    def simulate(self, dt: float = 1e-3, t_max: float = 120.0, max_points: int = 6000,
                 progress: Optional[Callable[[float], None]] = None,
                 tau_fraction: float = 0.25) -> SimulationResult:
        """Integrate the chamber-pressure and web equations with classical RK4.

        The fixed step is h = min(dt, tau_fraction * tau(0)), where tau(0) is the chamber
        time constant at ignition (the smallest value during the burn, because the free
        volume only grows), so that the mildly stiff pressure equation is resolved during
        ignition and tail-off.  Initial state: p = p_a, w = 0 (whole surface ignited).
        The burn phase ends when w reaches the web; the tail-off is integrated until
        p <= 1.02 p_a (or t_max).
        ``progress(f)``, if given, is called now and then with the completed
        fraction 0 <= f <= 1 (burnt web until burnout, then the pressure decay).
        """
        warnings = []
        h = min(dt, tau_fraction * self.time_constant())
        web = self.web
        p, w, t = self.p_a, 0.0, 0.0
        ts, ps, ws = [t], [p], [w]
        f = self._rhs
        burning = True
        t_bo = None
        p_bo = None
        step = 0
        while t < t_max:
            step += 1
            if progress is not None and step % 250 == 0:
                if burning:
                    frac = 0.92 * min(w / web, 1.0)
                else:
                    decay = math.log(max(p, self.p_a) / self.p_a) / max(math.log(p_bo / self.p_a), 1e-9)
                    frac = 0.92 + 0.08 * min(max(1.0 - decay, 0.0), 1.0)
                progress(float(frac))
            k1 = f(t, (p, w), burning)
            k2 = f(t + 0.5 * h, (p + 0.5 * h * k1[0], w + 0.5 * h * k1[1]), burning)
            k3 = f(t + 0.5 * h, (p + 0.5 * h * k2[0], w + 0.5 * h * k2[1]), burning)
            k4 = f(t + h, (p + h * k3[0], w + h * k3[1]), burning)
            p += h / 6.0 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
            w += h / 6.0 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
            p = max(p, self.p_a)
            t += h
            if burning and w >= web:
                burning = False
                w = web
                t_bo = t
                p_bo = max(p, 1.0001 * self.p_a)
            ts.append(t); ps.append(p); ws.append(w)
            if not burning and p <= 1.02 * self.p_a:
                break
        else:
            warnings.append("simulation stopped at t_max before the motor burned out")
        if t_bo is None:
            t_bo = t
        t = np.array(ts); p = np.array(ps); w = np.array(ws)
        if len(t) > max_points:
            idx = np.unique(np.concatenate([np.linspace(0, len(t) - 1, max_points).astype(int),
                                            [int(np.argmax(p))]]))
            t, p, w = t[idx], p[idx], w[idx]
        burning = t <= t_bo + 1e-12
        pr = self.propellant
        Ab = np.array([self.burning_area(wi) if b else 0.0 for wi, b in zip(w, burning)])
        r = np.array([self.burn_rate(pi) if b else 0.0 for pi, b in zip(p, burning)])
        F = np.array([self.nozzle.thrust(pi, self.p_a, self.R, self.T, pr.gamma_chamber, pr.gamma_exhaust)
                      for pi in p])
        mdot = np.array([self.nozzle.mass_flow(pi, self.p_a, self.R, self.T, pr.gamma_chamber) for pi in p])
        pmin, pmax = pr.p_valid
        if p.max() > pmax:
            warnings.append(f"peak pressure {p.max()/1e6:.2f} MPa exceeds the burn-rate data "
                            f"({pmax/1e6:.2f} MPa); last law extrapolated")
        if progress is not None:
            progress(1.0)
        return SimulationResult(t=t, p=p, F=F, w=w, Ab=Ab, Kn=Ab / self.nozzle.throat_area, mdot=mdot,
                                r=r, p_ambient=self.p_a, propellant_mass=self.propellant_mass(),
                                t_burnout=t_bo, warnings=warnings)

    @classmethod
    def from_dict(cls, d: dict, base_dir: str = ".") -> "Motor":
        prop = d["propellant"]
        if isinstance(prop, dict):
            propellant = Propellant.from_dict(prop)
        else:
            cand = os.path.join(base_dir, prop)
            propellant = Propellant.load(cand if os.path.isfile(cand) else prop)
        grain = grain_from_dict(d["grain"])
        nd = d["nozzle"]
        nozzle = Nozzle(nd["throat_diameter_mm"] * 1e-3, nd["exit_diameter_mm"] * 1e-3,
                        nd.get("divergence_half_angle_deg", 15.0), nd.get("efficiency", 0.90),
                        nd.get("separation_ratio", 0.4))
        ch = d.get("chamber")
        chamber = Chamber(ch["inner_diameter_mm"] * 1e-3, ch["length_mm"] * 1e-3) if ch else None
        return cls(propellant, grain, nozzle, chamber,
                   cstar_efficiency=d.get("cstar_efficiency", 0.975),
                   burn_rate_multiplier=d.get("burn_rate_multiplier", 1.0),
                   burnout_spread=d.get("burnout_spread", 0.0),
                   ambient_pressure=d.get("ambient_pressure_Pa", 101325.0),
                   name=d.get("name", "motor"))

    @classmethod
    def load(cls, path: str) -> "Motor":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f), base_dir=os.path.dirname(os.path.abspath(path)))


def size_throat(make_motor, p_target: float, d_lo: float = 0.5e-3, d_hi: float = 80e-3,
                tol: float = 1e-5, progress: Optional[Callable[[int, int], None]] = None):
    """Find the throat diameter for which the simulated peak pressure equals p_target.

    ``make_motor(d_throat)`` must return a Motor.  Uses bisection on the full
    simulation (peak pressure decreases monotonically with throat diameter).
    ``progress(k, n)``, if given, is called before bisection step k of about n.
    """
    lo, hi = d_lo, d_hi
    n_steps = min(40, max(1, math.ceil(math.log2((d_hi - d_lo) / tol))))
    for k in range(40):
        if progress is not None:
            progress(k + 1, n_steps)
        mid = 0.5 * (lo + hi)
        pk = make_motor(mid).simulate(dt=2e-3).peak_pressure
        if pk > p_target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)
