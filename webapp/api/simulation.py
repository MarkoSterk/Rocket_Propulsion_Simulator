from flask import Blueprint, request

from .deps import services
from .streaming import stream_job

bp = Blueprint("simulation", __name__)


@bp.post("/simulate")
def simulate():
    form = request.get_json(force=True)
    service = services().simulation
    return stream_job(lambda emit: service.simulate(form, emit))


@bp.post("/size_throat")
def size_throat():
    form = request.get_json(force=True)
    service = services().simulation
    return stream_job(lambda emit: service.size_throat(form, emit))
