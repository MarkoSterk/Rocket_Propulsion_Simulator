from flask import current_app, jsonify

from ..services import Services


def services() -> Services:
    return current_app.extensions["rps"]


def error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status
