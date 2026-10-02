"""Simulation and throat sizing jobs; both report progress through an ``emit(fraction, message)`` callback."""
from __future__ import annotations

from srmsim import size_throat

from ..motor import MotorFactory, burnback_payload
from . import charts
from .progress import Emit, Stages
from .propellant_service import PropellantService

GEOMETRY_SECONDS = 1.0


class SimulationService:
    def __init__(self, propellants: PropellantService, motors: MotorFactory):
        self.propellants = propellants
        self.motors = motors

    def _ensure_geometry(self, form: dict, stages: Stages, index: int, msg: str) -> None:
        stages.start(index, msg)
        stages.timed(lambda: self.motors.grains.get(form["grain"]), GEOMETRY_SECONDS)

    def size_throat(self, form: dict, emit: Emit) -> dict:
        propellant = self.propellants.load(form["propellant"])
        target = float(form["target_pressure_MPa"]) * 1e6
        if not self.motors.grains.contains(form["grain"]):
            geo = Stages(lambda f, m: emit(0.1 * f, m), [("geometry", 1.0)])
            self._ensure_geometry(form, geo, 0, "Computing the grain geometry")

        def step(k: int, n: int) -> None:
            emit(0.1 + 0.9 * (k - 1) / n, f"Sizing the throat: bisection step {min(k, n)} of ~{n}")

        d_max = 0.95 * float(form["grain"]["outer_diameter_mm"]) * 1e-3
        throat = size_throat(lambda d: self.motors.build(form, propellant, d * 1e3), target, 0.5e-3, d_max,
                             progress=step)
        emit(1.0, "Throat sized")
        return {"ok": True, "throat_diameter_mm": round(throat * 1e3, 2)}

    def simulate(self, form: dict, emit: Emit) -> dict:
        order = self.propellants.names()
        names = [form["propellant"]]
        if form.get("compare_all"):
            names += [n for n in order if n != form["propellant"]]
        needs_geometry = not self.motors.grains.contains(form["grain"])
        weights = ([("geometry", 1.5)] if needs_geometry else []) + [(n, 0.6) for n in names] + [("charts", 0.8)]
        stages = Stages(emit, weights)
        offset = 0
        if needs_geometry:
            self._ensure_geometry(form, stages, 0, "Computing the grain geometry (burn-back map)")
            offset = 1
        runs, summaries, warnings = [], {}, []
        first_motor = None
        for i, name in enumerate(names):
            suffix = f" ({i + 1} of {len(names)})" if len(names) > 1 else ""
            stages.start(offset + i, f"Simulating {name}{suffix}")
            motor = self.motors.build(form, self.propellants.load(name))
            first_motor = first_motor or motor
            result = motor.simulate(progress=stages.inner)
            runs.append((name, result))
            summaries[name] = result.summary()
            warnings += [f"{name}: {w}" for w in result.warnings]
        stages.start(offset + len(names), "Drawing the charts")
        plots = {"pressure": charts.time_plot(runs, "p", "chamber pressure $p_\\mathrm{c}$ [MPa]", order, 1e-6)}
        stages.inner(0.4)
        plots["thrust"] = charts.time_plot(runs, "F", "thrust $F$ [N]", order)
        stages.inner(0.75)
        plots["kn"] = charts.kn_plot(first_motor)
        stages.inner(0.95)
        main_name, main_result = runs[0]
        out = {
            "ok": True,
            "summary": summaries,
            "grain": first_motor.grain.describe(),
            "tau_ms": round(float(first_motor.time_constant()) * 1e3, 2),
            "expansion_ratio": round(float(first_motor.nozzle.expansion_ratio), 2),
            "warnings": warnings,
            "plots": plots,
            "csv": {n: r.csv_string() for n, r in runs},
            "burnback": burnback_payload(first_motor, main_result, main_name),
        }
        emit(1.0, "Done")
        return out
