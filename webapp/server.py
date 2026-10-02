"""Command-line entry point: chooses a free port and runs the development server."""
from __future__ import annotations

import argparse
import logging
import os
import socket

import flask.cli

from . import create_app
from .config import APP_INFO

DEFAULT_PORT = 8050
HOST = "127.0.0.1"


def port_in_use(port: int, host: str = HOST) -> bool:
    """True if another program already serves on the port (IPv4 or IPv6 localhost) or it cannot be bound."""
    for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.3)
                if sock.connect_ex((address, port)) == 0:
                    return True
        except OSError:
            pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
    except OSError:
        return True
    return False


def choose_port(preferred: int = DEFAULT_PORT, host: str = HOST, tries: int = 50) -> int:
    """The preferred port if it is free, otherwise the next free one (or any free port)."""
    for port in range(preferred, min(preferred + tries, 65536)):
        if not port_in_use(port, host):
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def _print_banner(requested: int, port: int) -> None:
    line = "=" * 64
    print(line)
    print(f"  {APP_INFO['name']} {APP_INFO['version']}")
    if port != requested:
        print(f"  Port {requested} is already in use, using port {port} instead.")
    print(f"  Go to http://localhost:{port} in your favorite browser.")
    print(f"  (If that address does not open, use http://127.0.0.1:{port})")
    print("  Keep this window open while you use the app; press Ctrl+C to stop it.")
    print(line, flush=True)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="RocketPropulsionSimulator",
                                     description=f"{APP_INFO['name']} {APP_INFO['version']}")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)),
                        help=f"preferred port (default {DEFAULT_PORT}; the next free port is used if it is taken)")
    args = parser.parse_args(argv)
    port = choose_port(args.port)
    flask.cli.show_server_banner = lambda *a, **k: None
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    _print_banner(args.port, port)
    create_app().run(host=HOST, port=port, debug=False, threaded=True, use_reloader=False)
