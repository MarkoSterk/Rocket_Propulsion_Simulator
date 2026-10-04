"""Consistency checks:  uv run pytest"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from srmsim import (CircularCoreGrain, CoreMapGrain, EndBurnerGrain, Motor, Nozzle, Propellant,
                    moon_core)

mm = 1e-3


def test_units_conversion():
    assert abs(Propellant.load("KNSU").burn_rate(1e6) * 1e3 - 8.26) < 1e-9


def test_numeric_canal_matches_circular():
    a = CircularCoreGrain(46 * mm, 16 * mm, 300 * mm)
    b = CoreMapGrain(46 * mm, 300 * mm, moon_core(16 * mm, 0.0), resolution=601)
    for w in (1 * mm, 5 * mm, 10 * mm, 14 * mm):
        assert abs(b.burning_area(w) / a.burning_area(w) - 1) < 0.01
        assert abs(b.propellant_volume(w) / a.propellant_volume(w) - 1) < 0.03


def test_mass_conservation():
    m = Motor(Propellant.load("KNDX"), CircularCoreGrain(46 * mm, 16 * mm, 300 * mm), Nozzle(14.6 * mm, 35.8 * mm))
    r = m.simulate()
    trapz = getattr(np, "trapezoid", None) or np.trapz
    assert abs(trapz(r.mdot, r.t) / r.propellant_mass - 1) < 0.01


def test_end_burner_quasi_steady():
    """A neutral end burner runs at the quasi-steady pressure (Kn rho a c*)^(1/(1-n))."""
    m = Motor(Propellant.load("KNSU"), EndBurnerGrain(46 * mm, 100 * mm), Nozzle(3.0 * mm, 7.3 * mm))
    r = m.simulate()
    i = np.argmin(abs(r.t - 0.5 * r.t_burnout))
    assert abs(r.p[i] / m.steady_state_pressure(r.w[i]) - 1) < 0.02


def test_burnout_spread_lengthens_tail_off_and_conserves_mass():
    g = CircularCoreGrain(46 * mm, 16 * mm, 300 * mm)
    trapz = getattr(np, "trapezoid", None) or np.trapz

    def tail(s):
        m = Motor(Propellant.load("KNDX"), g, Nozzle(14.65 * mm, 35.9 * mm), burnout_spread=s)
        r = m.simulate()
        assert abs(trapz(r.mdot, r.t) / r.propellant_mass - 1) < 0.01
        pk = r.p.max()
        t50 = r.t[np.where(r.p >= 0.5 * pk)[0][-1]]
        return r.t[np.where((r.t > t50) & (r.p <= 0.1 * pk))[0][0]] - t50

    assert tail(0.05) > 3 * tail(0.0)


def test_segments_without_faces_equal_one_long_grain():
    """N segments with inhibited faces (no gap) behave exactly like one grain of length N L."""
    from srmsim import SegmentedGrain
    one = Motor(Propellant.load("KNSU"), CircularCoreGrain(46 * mm, 16 * mm, 300 * mm), Nozzle(16.8 * mm, 41 * mm))
    three = Motor(Propellant.load("KNSU"), SegmentedGrain(CircularCoreGrain(46 * mm, 16 * mm, 100 * mm), 3, "none"),
                  Nozzle(16.8 * mm, 41 * mm))
    a, b = one.simulate(), three.simulate()
    assert abs(a.peak_pressure / b.peak_pressure - 1) < 1e-6
    assert abs(a.total_impulse / b.total_impulse - 1) < 1e-6


def test_bates_burning_area_and_mass():
    """Circular canal burning on both faces: analytic A_b(w), web = min(R - r0, L/2), mass conservation."""
    import math
    from srmsim import SegmentedGrain, grain_from_dict
    D, d, L, N = 46 * mm, 16 * mm, 60 * mm, 4
    g = grain_from_dict({"type": "circular", "outer_diameter_mm": 46, "core_diameter_mm": 16, "length_mm": 60,
                         "segments": N, "burning_faces": "both", "segment_gap_mm": 3})
    assert isinstance(g, SegmentedGrain) and abs(g.length - (N * L + 3 * 3 * mm)) < 1e-12
    assert abs(g.web - 15 * mm) < 1e-12
    for w in (0.0, 4 * mm, 9 * mm, 14 * mm):
        r = 0.5 * d + w
        ana = N * (2 * math.pi * r * (L - 2 * w) + 2 * math.pi * ((0.5 * D) ** 2 - r * r))
        assert abs(g.burning_area(w) / ana - 1) < 1e-9
    one_face = grain_from_dict({"type": "circular", "outer_diameter_mm": 46, "core_diameter_mm": 16,
                                "length_mm": 20, "burning_faces": "aft"})
    assert abs(one_face.web - 15 * mm) < 1e-12 and one_face.k == 1
    short = grain_from_dict({"type": "circular", "outer_diameter_mm": 46, "core_diameter_mm": 16,
                             "length_mm": 20, "burning_faces": "both"})
    assert abs(short.web - 10 * mm) < 1e-12
    m = Motor(Propellant.load("KNSU"), g, Nozzle(17 * mm, 41 * mm))
    res = m.simulate()
    trapz = getattr(np, "trapezoid", None) or np.trapz
    assert abs(trapz(res.mdot, res.t) / res.propellant_mass - 1) < 0.01


def test_star_segments_with_faces():
    from srmsim import SegmentedGrain, StarGrain
    seg = StarGrain(46 * mm, 80 * mm, 7, 8 * mm, 26 * mm, resolution=401)
    g = SegmentedGrain(seg, 3, "aft")
    w = 3 * mm
    expect = 3 * (seg.burning_area(w) * (80 * mm - w) / (80 * mm) + seg.propellant_volume(w) / (80 * mm))
    assert abs(g.burning_area(w) / expect - 1) < 1e-12


def test_end_burner_cannot_be_segmented():
    import pytest
    from srmsim import SegmentedGrain
    with pytest.raises(ValueError):
        SegmentedGrain(EndBurnerGrain(46 * mm, 100 * mm), 2, "none")


def test_separated_nozzle_thrust_coefficient_stays_positive():
    n = Nozzle(10 * mm, 10 * mm * 6 ** 0.5)
    g = Propellant.load("KNSU").gamma_exhaust
    for pc in np.linspace(0.18e6, 6e6, 200):
        assert n.thrust_coefficient(pc, 101325.0, g) > 0
    assert n.is_separated(0.5e6, 101325.0, g)
    assert not n.is_separated(4e6, 101325.0, g)
    assert abs(n.thrust_coefficient(4e6, 101325.0, g) -
               Nozzle(10 * mm, 10 * mm * 6 ** 0.5, separation_ratio=0.0).thrust_coefficient(4e6, 101325.0, g)) < 1e-12


def test_time_step_convergence():
    from srmsim import Chamber
    m = Motor(Propellant.load("KNSU"), CircularCoreGrain(46 * mm, 16 * mm, 300 * mm),
              Nozzle(16.78 * mm, 16.78 * mm * 6 ** 0.5), Chamber(46 * mm, 310 * mm))
    a = m.simulate()
    b = m.simulate(tau_fraction=0.0625, max_points=10 ** 7)
    assert abs(a.total_impulse / b.total_impulse - 1) < 1e-3
    assert abs(a.peak_pressure / b.peak_pressure - 1) < 1e-3
