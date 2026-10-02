"""srmsim - internal-ballistics simulator for solid rocket motors with one grain or N segments (BATES).

    from srmsim import Propellant, CircularCoreGrain, Nozzle, Motor
    grain = CircularCoreGrain(outer_diameter=0.046, core_diameter=0.016, length=0.30)
    motor = Motor(Propellant.load("KNDX"), grain, Nozzle(0.0146, 0.0358))
    print(motor.simulate().summary())
"""
from .propellant import Propellant, available as available_propellants
from .grains import (Grain, CircularCoreGrain, EndBurnerGrain, StarGrain, CrossGrain, MoonGrain,
                     CoreMapGrain, SegmentedGrain, BURNING_FACES, unwrap, star_core, cross_core, moon_core,
                     grain_from_dict, GRAIN_TYPES)
from .nozzle import Nozzle
from .motor import Motor, Chamber, SimulationResult, size_throat, motor_class

__version__ = "2.2.0"
