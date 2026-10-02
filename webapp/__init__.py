"""Rocket Propulsion Simulator web application (Flask, application factory)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Flask

from .api import register_blueprints
from .config import DefaultConfig, resolve_user_propellant_dir
from .services import build_services


def create_app(config: Mapping[str, Any] | None = None) -> Flask:
    """Create and configure a Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(DefaultConfig)
    if config:
        app.config.update(config)
    app.config["USER_PROPELLANT_DIR"] = resolve_user_propellant_dir(app.config.get("USER_PROPELLANT_DIR"))
    app.json.sort_keys = False
    app.extensions["rps"] = build_services(app.config)
    register_blueprints(app)
    return app


__all__ = ["create_app"]
