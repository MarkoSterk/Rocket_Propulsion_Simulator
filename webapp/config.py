"""Configuration defaults and file locations."""
from __future__ import annotations

import os
import sys

from srmsim import __version__

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)

APP_INFO = {
    "name": "Rocket Propulsion Simulator",
    "version": __version__,
    "author": "Marko Šterk, PhD in physics",
    "email": "marko_sterk@hotmail.com",
    "license": "MIT License",
    "year": "2026",
}


class DefaultConfig:
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024
    MAX_PROPELLANT_BYTES = 256 * 1024
    MAX_GIF_FRAMES = 900
    GRAIN_CACHE_SIZE = 32
    GRAIN_RESOLUTION = 501
    USER_PROPELLANT_DIR: str | None = None
    APP_INFO = APP_INFO


def _writable(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write_test")
        with open(probe, "w") as fh:
            fh.write("")
        os.remove(probe)
        return True
    except OSError:
        return False


def resolve_user_propellant_dir(configured: str | None = None) -> str:
    """Folder for uploaded propellants.

    An explicitly configured folder is used as is. Otherwise app/user_propellants is used when
    running from the sources, and in the stand-alone build a folder next to the executable or,
    if that is read-only, one in the home folder.
    """
    if configured:
        os.makedirs(configured, exist_ok=True)
        return configured
    if not FROZEN:
        path = os.path.join(os.path.dirname(PACKAGE_DIR), "user_propellants")
        os.makedirs(path, exist_ok=True)
        return path
    for path in (os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "user_propellants"),
                 os.path.join(os.path.expanduser("~"), ".rocket_propulsion_simulator", "user_propellants")):
        if _writable(path):
            return path
    raise RuntimeError("no writable folder for user propellants")
