"""Builds srmsim motors from the JSON form sent by the browser."""
from __future__ import annotations

from srmsim import Chamber, Grain, Motor, Nozzle, Propellant, SegmentedGrain

from .grain_cache import GrainCache


class MotorFactory:
    def __init__(self, grains: GrainCache):
        self.grains = grains

    def grain(self, form: dict) -> Grain:
        """The cached segment, stacked into N segments with the selected burning faces."""
        grain_form = form["grain"]
        segment = self.grains.get(grain_form)
        if grain_form.get("type") == "endburner":
            return segment
        n = int(grain_form.get("segments", 1))
        faces = str(grain_form.get("burning_faces", "none"))
        gap = float(grain_form.get("segment_gap_mm", 0.0)) * 1e-3
        if n == 1 and faces == "none":
            return segment
        return SegmentedGrain(segment, n, faces, gap)

    @staticmethod
    def nozzle(form: dict, throat_mm: float | None = None) -> Nozzle:
        nz = form["nozzle"]
        throat = (throat_mm if throat_mm is not None else float(nz["throat_diameter_mm"])) * 1e-3
        exit_d = float(nz["exit_diameter_mm"]) * 1e-3
        if exit_d < throat:
            raise ValueError("exit diameter must not be smaller than the throat diameter")
        return Nozzle(throat, exit_d, float(nz.get("half_angle_deg", 15)), float(nz.get("efficiency", 0.9)))

    def build(self, form: dict, propellant: Propellant, throat_mm: float | None = None) -> Motor:
        grain = self.grain(form)
        free_length = float(form.get("free_length_mm", 10)) * 1e-3
        chamber = Chamber(grain.outer_diameter, grain.length + free_length)
        return Motor(propellant, grain, self.nozzle(form, throat_mm), chamber,
                     cstar_efficiency=float(form.get("cstar_efficiency", 0.975)),
                     burn_rate_multiplier=float(form.get("burn_rate_multiplier", 1.0)),
                     ambient_pressure=float(form.get("ambient_pressure_kPa", 101.325)) * 1e3,
                     burnout_spread=float(form.get("burnout_spread_pct", 0.0)) / 100.0)
