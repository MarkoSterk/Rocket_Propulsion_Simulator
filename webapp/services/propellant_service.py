"""Bundled and user-uploaded propellants."""
from __future__ import annotations

import json
import os
import re

from srmsim import Propellant

from .errors import ServiceError

PREFERRED_ORDER = {"KNDX": 0, "KNSU": 1, "KNSB": 2}


class PropellantService:
    def __init__(self, bundled_dir: str, user_dir: str, max_upload_bytes: int):
        self.bundled_dir = bundled_dir
        self.user_dir = user_dir
        self.max_upload_bytes = max_upload_bytes

    def files(self) -> dict[str, str]:
        """name -> path of every readable propellant file, bundled ones first."""
        out = {}
        for folder in (self.bundled_dir, self.user_dir):
            for fname in sorted(os.listdir(folder)):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(folder, fname)
                try:
                    with open(path, encoding="utf-8") as fh:
                        out[json.load(fh)["name"]] = path
                except (OSError, ValueError, KeyError, TypeError):
                    continue
        return dict(sorted(out.items(), key=lambda kv: (PREFERRED_ORDER.get(kv[0], 9), kv[0])))

    def names(self) -> list[str]:
        return list(self.files())

    def load(self, name: str) -> Propellant:
        files = self.files()
        if name not in files:
            raise ServiceError(f"unknown propellant '{name}'")
        return Propellant.load(files[name])

    @staticmethod
    def info(p: Propellant) -> dict:
        return {
            "name": p.name, "description": p.description,
            "density": p.density, "T": p.combustion_temperature, "M": round(p.molar_mass * 1e3, 2),
            "gamma_c": p.gamma_chamber, "gamma_e": p.gamma_exhaust, "cstar": round(p.cstar(), 0),
            "ranges": [{"p_min": round(r.p_min / 1e6, 3), "p_max": round(r.p_max / 1e6, 3),
                        "a": round(r.a * 1e3 * 1e6 ** r.n, 4), "n": r.n} for r in p.ranges],
        }

    def list_info(self) -> list[dict]:
        return [self.info(self.load(n)) for n in self.files()]

    def add(self, data: dict) -> Propellant:
        """Validate an uploaded propellant definition and store it in the user folder."""
        try:
            propellant = Propellant.from_dict(data)
        except Exception as exc:
            raise ServiceError(f"invalid propellant file: {exc}") from exc
        if not propellant.ranges:
            raise ServiceError("invalid propellant file: burn_rate.ranges is empty")
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", propellant.name)[:40] or "custom"
        with open(os.path.join(self.user_dir, safe.lower() + ".json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        return propellant
