from flask import Blueprint, Response, request

from ..services import ServiceError
from .deps import error, services

bp = Blueprint("export", __name__)


@bp.post("/export_gif")
def export_gif():
    data = request.get_json(force=True, silent=True) or {}
    try:
        gif = services().export.gif(data.get("frames") or [], data.get("fps", 15), data.get("hold_last_ms", 1000))
    except ServiceError as exc:
        return error(str(exc))
    return Response(gif, mimetype="image/gif", headers={"Content-Disposition": 'attachment; filename="burnback.gif"'})
