"""HTTP controllers (Flask blueprints)."""
from flask import Flask

from .export import bp as export_bp
from .pages import bp as pages_bp
from .propellants import bp as propellants_bp
from .simulation import bp as simulation_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(pages_bp)
    app.register_blueprint(propellants_bp, url_prefix="/api")
    app.register_blueprint(simulation_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")


__all__ = ["register_blueprints"]
