"""Propellant definitions and the piecewise burn-rate law.

A propellant is described by a small JSON file (see ``srmsim/propellants``).
The burn rate follows Saint Robert's (Vieille's) law ``r = a * p**n``, where the
coefficients ``a`` and ``n`` may change from one pressure interval to the next
("step" in the coefficients).  Pressures in the JSON files are given in MPa and
burn rates in mm/s, which is the convention used by most amateur-rocketry
sources (R. Nakka, openMotor, ...).  Internally everything is SI.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import List, Optional

R_UNIVERSAL = 8.314462618
G0 = 9.80665

PROPELLANT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "propellants")


@dataclass
class BurnRateRange:
    p_min: float
    p_max: float
    a: float
    n: float

    def rate(self, p: float) -> float:
        return self.a * p ** self.n


@dataclass
class Propellant:
    name: str
    density: float
    combustion_temperature: float
    molar_mass: float
    gamma_chamber: float
    gamma_exhaust: float
    ranges: List[BurnRateRange]
    description: str = ""
    density_ideal: Optional[float] = None
    composition: dict = field(default_factory=dict)
    references: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Propellant":
        br = d["burn_rate"]
        units = br.get("units", {"pressure": "MPa", "rate": "mm/s"})
        p_scale = {"Pa": 1.0, "kPa": 1e3, "MPa": 1e6, "psi": 6894.757}[units.get("pressure", "MPa")]
        r_scale = {"m/s": 1.0, "mm/s": 1e-3, "in/s": 0.0254}[units.get("rate", "mm/s")]
        ranges = []
        for rr in br["ranges"]:
            n = float(rr["n"])
            a_si = float(rr["a"]) * r_scale / p_scale ** n
            ranges.append(BurnRateRange(float(rr["p_min"]) * p_scale,
                                        float(rr["p_max"]) * p_scale, a_si, n))
        ranges.sort(key=lambda r: r.p_min)
        mm = float(d["molar_mass"])
        if mm > 1.0:
            mm *= 1e-3
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            density=float(d["density"]),
            density_ideal=d.get("density_ideal"),
            combustion_temperature=float(d["combustion_temperature"]),
            molar_mass=mm,
            gamma_chamber=float(d["gamma_chamber"]),
            gamma_exhaust=float(d.get("gamma_exhaust", d["gamma_chamber"])),
            ranges=ranges,
            composition=d.get("composition", {}),
            references=d.get("references", []),
        )

    @classmethod
    def load(cls, name_or_path: str) -> "Propellant":
        """Load a propellant by bundled name (``"KNDX"``) or by JSON file path."""
        path = name_or_path
        if not os.path.isfile(path):
            cand = os.path.join(PROPELLANT_DIR, name_or_path.lower() + ".json")
            if os.path.isfile(cand):
                path = cand
            else:
                raise FileNotFoundError(
                    f"Propellant '{name_or_path}' not found (available: {', '.join(available())})")
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def burn_rate(self, p: float) -> float:
        """Burn rate r(p) in m/s for chamber pressure p in Pa.

        Below the first interval the first law is extrapolated, above the last
        interval the last law is extrapolated (a warning is recorded by the
        motor simulation in that case).
        """
        if p <= 0.0:
            return 0.0
        rr = self.range_for(p)
        return rr.rate(p)

    def range_for(self, p: float) -> BurnRateRange:
        for rr in self.ranges:
            if p < rr.p_max:
                return rr
        return self.ranges[-1]

    def n_at(self, p: float) -> float:
        return self.range_for(p).n

    @property
    def p_valid(self):
        return self.ranges[0].p_min, self.ranges[-1].p_max

    def gas_constant(self) -> float:
        """Specific gas constant R = R_u / M in J/(kg K)."""
        return R_UNIVERSAL / self.molar_mass

    def cstar(self, efficiency: float = 1.0) -> float:
        """Characteristic velocity c* in m/s (ideal times efficiency)."""
        g = self.gamma_chamber
        big_gamma = math.sqrt(g) * (2.0 / (g + 1.0)) ** ((g + 1.0) / (2.0 * (g - 1.0)))
        return efficiency * math.sqrt(self.gas_constant() * self.combustion_temperature) / big_gamma


def available() -> List[str]:
    return sorted(os.path.splitext(f)[0].upper() for f in os.listdir(PROPELLANT_DIR)
                  if f.endswith(".json"))
