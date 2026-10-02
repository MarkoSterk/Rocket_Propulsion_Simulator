"""Start Rocket Propulsion Simulator.

Entry point of the stand-alone build made with PyInstaller (see BUILD.md); it can also be
run directly:   uv run python run_app.py   (same as  uv run python -m webapp).
"""
from webapp.server import main

if __name__ == "__main__":
    main()
