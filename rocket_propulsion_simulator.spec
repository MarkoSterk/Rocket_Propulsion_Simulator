"""PyInstaller configuration of Rocket Propulsion Simulator (stand-alone build).

Build (on the operating system you build for; PyInstaller cannot cross-compile):

    uv sync --group build
    uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean

Result (default, one folder - starts fast):
    dist/RocketPropulsionSimulator/RocketPropulsionSimulator[.exe]

Single executable instead (starts slower, it unpacks itself on every start):
    set the environment variable RPS_ONEFILE=1 before the build
    -> dist/RocketPropulsionSimulator[.exe]

See BUILD.md for the step-by-step instructions for Windows, Linux and macOS.
"""
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

NAME = "RocketPropulsionSimulator"
ONEFILE = os.environ.get("RPS_ONEFILE", "0") == "1"
HERE = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(HERE, "webapp", "templates"), os.path.join("webapp", "templates")),
    (os.path.join(HERE, "webapp", "static"), os.path.join("webapp", "static")),
    (os.path.join(HERE, "srmsim", "propellants"), os.path.join("srmsim", "propellants")),
    (os.path.join(HERE, "examples"), "examples"),
    (os.path.join(HERE, "LICENSE"), "."),
    (os.path.join(HERE, "README.md"), "."),
]
datas += collect_data_files("skimage", includes=["**/*.pyi"])

hiddenimports = (
    collect_submodules("skimage.measure")
    + collect_submodules("webapp")
    + ["lazy_loader", "scipy.ndimage", "matplotlib.backends.backend_agg", "matplotlib.backends.backend_svg",
       "PIL.GifImagePlugin", "PIL.PngImagePlugin"]
)

excludes = ["tkinter", "_tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6", "wx", "IPython", "jupyter",
            "notebook", "pytest", "matplotlib.backends.backend_tkagg", "matplotlib.backends.backend_qtagg"]

if sys.platform == "win32":
    icon = os.path.join(HERE, "packaging", "logo.ico")
elif sys.platform == "darwin":
    icon = os.path.join(HERE, "packaging", "logo.png")
else:
    icon = None

a = Analysis(
    [os.path.join(HERE, "run_app.py")],
    pathex=[HERE],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={"matplotlib": {"backends": ["Agg", "SVG"]}},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name=NAME,
        console=True,
        icon=icon,
        upx=False,
        strip=False,
        debug=False,
    )
else:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name=NAME,
        console=True,
        icon=icon,
        upx=False,
        strip=False,
        debug=False,
    )
    coll = COLLECT(
        exe, a.binaries, a.datas,
        name=NAME,
        upx=False,
        strip=False,
    )
