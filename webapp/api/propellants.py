import json

from flask import Blueprint, current_app, jsonify, request

from ..services import ServiceError
from .deps import error, services

bp = Blueprint("propellants", __name__)


@bp.get("/propellants")
def list_propellants():
    return jsonify(services().propellants.list_info())


@bp.post("/propellants")
def upload_propellant():
    if (request.content_length or 0) > current_app.config["MAX_PROPELLANT_BYTES"]:
        return error("invalid propellant file: the file is too large")
    upload = request.files.get("file")
    try:
        data = json.load(upload.stream) if upload else request.get_json(force=True)
    except ValueError as exc:
        return error(f"invalid propellant file: {exc}")
    try:
        propellant = services().propellants.add(data)
    except ServiceError as exc:
        return error(str(exc))
    return jsonify({"ok": True, "name": propellant.name, "info": services().propellants.info(propellant)})
