"""Convergent-divergent nozzle: mass flow and thrust (quasi-1D isentropic flow)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from scipy.optimize import brentq


def critical_pressure_ratio(g: float) -> float:
    """p*/p_c at which the throat becomes choked."""
    return (2.0 / (g + 1.0)) ** (g / (g - 1.0))


def area_ratio_from_mach(M: float, g: float) -> float:
    return (1.0 / M) * ((2.0 / (g + 1.0)) * (1.0 + 0.5 * (g - 1.0) * M * M)) ** ((g + 1.0) / (2.0 * (g - 1.0)))


@lru_cache(maxsize=256)
def exit_pressure_ratio(eps: float, g: float) -> float:
    """p_e/p_c for a supersonic exit with expansion ratio eps = A_e/A_t."""
    if eps <= 1.0 + 1e-9:
        return critical_pressure_ratio(g)
    Me = brentq(lambda M: area_ratio_from_mach(M, g) - eps, 1.0 + 1e-9, 50.0)
    return (1.0 + 0.5 * (g - 1.0) * Me * Me) ** (-g / (g - 1.0))


@dataclass
class Nozzle:
    throat_diameter: float
    exit_diameter: float
    divergence_half_angle: float = 15.0
    efficiency: float = 0.90

    @property
    def throat_area(self) -> float:
        return math.pi * 0.25 * self.throat_diameter ** 2

    @property
    def exit_area(self) -> float:
        return math.pi * 0.25 * self.exit_diameter ** 2

    @property
    def expansion_ratio(self) -> float:
        return self.exit_area / self.throat_area

    @property
    def divergence_factor(self) -> float:
        """lambda = (1 + cos alpha)/2, loss due to non-axial exit velocity."""
        return 0.5 * (1.0 + math.cos(math.radians(self.divergence_half_angle)))

    def mass_flow(self, p_c: float, p_a: float, R: float, T: float, g: float) -> float:
        """Mass flow through the throat [kg/s] (choked or subsonic)."""
        if p_c <= p_a:
            return 0.0
        At = self.throat_area
        pr = p_a / p_c
        if pr <= critical_pressure_ratio(g):
            return p_c * At * math.sqrt(g / (R * T)) * (2.0 / (g + 1.0)) ** ((g + 1.0) / (2.0 * (g - 1.0)))
        return p_c * At * math.sqrt(2.0 * g / ((g - 1.0) * R * T) *
                                    (pr ** (2.0 / g) - pr ** ((g + 1.0) / g)))

    def thrust_coefficient(self, p_c: float, p_a: float, g_e: float) -> float:
        """Ideal thrust coefficient C_F (choked nozzle, supersonic exit)."""
        pe_pc = exit_pressure_ratio(self.expansion_ratio, g_e)
        term = (2.0 * g_e * g_e / (g_e - 1.0)) * (2.0 / (g_e + 1.0)) ** ((g_e + 1.0) / (g_e - 1.0)) \
            * (1.0 - pe_pc ** ((g_e - 1.0) / g_e))
        return math.sqrt(term) + (pe_pc - p_a / p_c) * self.expansion_ratio

    def thrust(self, p_c: float, p_a: float, R: float, T: float, g_c: float, g_e: float) -> float:
        if p_c <= p_a:
            return 0.0
        k = self.efficiency * self.divergence_factor
        if p_a / p_c <= critical_pressure_ratio(g_c):
            F = k * self.thrust_coefficient(p_c, p_a, g_e) * p_c * self.throat_area
        else:
            mdot = self.mass_flow(p_c, p_a, R, T, g_c)
            v = math.sqrt(2.0 * g_c / (g_c - 1.0) * R * T * (1.0 - (p_a / p_c) ** ((g_c - 1.0) / g_c)))
            F = k * mdot * v
        return max(F, 0.0)
