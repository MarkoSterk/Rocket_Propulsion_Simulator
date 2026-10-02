from flask import Blueprint, render_template

from .deps import services

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    svc = services()
    return render_template("index.html", propellants=svc.propellants.names(), info=svc.info)
