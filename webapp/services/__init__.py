"""Service (handler) layer: application logic used by the API controllers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from srmsim.propellant import PROPELLANT_DIR

from ..motor import GrainCache, MotorFactory
from .errors import ServiceError
from .export_service import ExportService
from .propellant_service import PropellantService
from .simulation_service import SimulationService


@dataclass
class Services:
    propellants: PropellantService
    simulation: SimulationService
    export: ExportService
    info: dict


def build_services(config: Mapping[str, Any]) -> Services:
    propellants = PropellantService(PROPELLANT_DIR, config["USER_PROPELLANT_DIR"], config["MAX_PROPELLANT_BYTES"])
    grains = GrainCache(config["GRAIN_CACHE_SIZE"], config["GRAIN_RESOLUTION"])
    return Services(
        propellants=propellants,
        simulation=SimulationService(propellants, MotorFactory(grains)),
        export=ExportService(config["MAX_GIF_FRAMES"]),
        info=dict(config["APP_INFO"]),
    )


__all__ = ["Services", "ServiceError", "build_services"]
