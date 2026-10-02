"""Data for the interactive burn-back viewer, which is drawn in the browser.

The expensive part, the distance d(x, y) at which the flame front reaches each point of the
cross-section, is known for every grain. The canal at time t is the region d <= w(t), so the
browser only needs d once plus the time series of the burnt web w(t).
"""
from __future__ import annotations

import base64
import math

import numpy as np
from srmsim import (
    CircularCoreGrain,
    CoreMapGrain,
    EndBurnerGrain,
    Motor,
    SegmentedGrain,
    SimulationResult,
    unwrap,
)

MAX_POINTS = 800
FIELD_SIZE = 260


def burnback_payload(motor: Motor, result: SimulationResult, propellant_name: str) -> dict:
    stack = motor.grain
    grain = unwrap(stack)
    n = len(result.t)
    idx = np.unique(np.linspace(0, n - 1, min(n, MAX_POINTS)).round().astype(int))
    segmented = stack if isinstance(stack, SegmentedGrain) else None
    out = {
        "propellant": propellant_name,
        "R_mm": 0.5 * grain.outer_diameter * 1e3,
        "L_mm": grain.length * 1e3,
        "n_seg": segmented.n if segmented else 1,
        "gap_mm": segmented.gap * 1e3 if segmented else 0.0,
        "faces": segmented.faces if segmented else ("aft" if isinstance(grain, EndBurnerGrain) else "none"),
        "chamber_mm": motor.chamber.length * 1e3,
        "throat_mm": motor.nozzle.throat_diameter * 1e3,
        "exit_mm": motor.nozzle.exit_diameter * 1e3,
        "half_angle_deg": motor.nozzle.divergence_half_angle,
        "web_mm": stack.web * 1e3,
        "t": np.round(result.t[idx], 5).tolist(),
        "w_mm": np.round(result.w[idx] * 1e3, 4).tolist(),
        "p_MPa": np.round(result.p[idx] / 1e6, 4).tolist(),
        "F_N": np.round(result.F[idx], 2).tolist(),
        "Kn": np.round(result.Kn[idx], 2).tolist(),
    }
    if isinstance(grain, CoreMapGrain):
        out.update(_field(grain))
    elif isinstance(grain, CircularCoreGrain):
        out.update(kind="circle", r0_mm=0.5 * grain.core_diameter * 1e3)
    elif isinstance(grain, EndBurnerGrain):
        out.update(kind="end")
    else:
        out.update(kind="none")
    return out


def _field(grain: CoreMapGrain) -> dict:
    """Arrival distance d(x, y) in 0.01 mm steps as base64 uint16; 65535 marks points outside the case."""
    _, _, dist, _, inside = grain.field()
    step = max(1, int(math.ceil((dist.shape[0] - 1) / FIELD_SIZE)))  # noqa: RUF046
    d = dist[::step, ::step] * 1e3
    q = np.clip(np.round(d * 100.0), 0, 65534).astype("<u2")
    q[~inside[::step, ::step]] = 65535
    cut = dist[:, dist.shape[1] // 2] * 1e3
    return {"kind": "field", "n": int(q.shape[0]), "scale_mm": 0.01,
            "field": base64.b64encode(q.tobytes()).decode("ascii"),
            "cut_mm": np.round(cut, 3).tolist()}
