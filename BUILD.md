# Building a stand-alone Rocket Propulsion Simulator

The stand-alone build is a folder (or a single file) that contains Python, all libraries and
the application, so the computer it runs on needs **no Python installation**. It is made with
[PyInstaller](https://pyinstaller.org); the configuration is in
`rocket_propulsion_simulator.spec`.

> **Build on the system you build for.** PyInstaller does not cross-compile: a Windows `.exe`
> must be built on Windows, a Linux program on Linux and a macOS program on macOS (on an
> Apple-silicon Mac for Apple-silicon Macs, on an Intel Mac for Intel Macs).

## 1. Prerequisites (all systems)

* [uv](https://docs.astral.sh/uv/getting-started/installation/) – it also installs the right
  Python (3.12, from `.python-version`) automatically.
* An internet connection for the first `uv sync`.

Open a terminal in the project folder (the one that contains `app`); every block below starts
with `cd app`.

## 2. Windows (PowerShell)

```powershell
cd app
uv sync --group build                         # application + PyInstaller in .venv
uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean
.\dist\RocketPropulsionSimulator\RocketPropulsionSimulator.exe   # test it
```

Single `.exe` instead of a folder:

```powershell
$env:RPS_ONEFILE = "1"
uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean
Remove-Item Env:RPS_ONEFILE
.\dist\RocketPropulsionSimulator.exe
```

(in the classic Command Prompt use `set RPS_ONEFILE=1` and `set RPS_ONEFILE=`).

Notes: Windows SmartScreen may warn about an unsigned program (*More info → Run anyway*);
some antivirus programs flag PyInstaller single-file executables – the folder build is less
affected. The program window is a console window: keep it open while you use the app.

## 3. Linux (bash)

```bash
cd app
uv sync --group build
uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean
./dist/RocketPropulsionSimulator/RocketPropulsionSimulator      # test it

# single file instead of a folder
RPS_ONEFILE=1 uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean
./dist/RocketPropulsionSimulator
```

The program runs on Linux distributions with the same or a **newer** glibc than the system it
was built on, so build on the oldest distribution you want to support (for example in an
Ubuntu 20.04 or 22.04 container or virtual machine). Start it from a terminal.

## 4. macOS (Terminal)

```bash
cd app
uv sync --group build
uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean
./dist/RocketPropulsionSimulator/RocketPropulsionSimulator      # test it

RPS_ONEFILE=1 uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean   # single file
```

The result is a command-line program (double-clicking it in Finder opens it in Terminal).
It is not signed, so macOS Gatekeeper blocks it on other Macs: right-click → *Open*, or remove
the quarantine flag after copying it:

```bash
xattr -dr com.apple.quarantine RocketPropulsionSimulator
```

## 5. Running the built application

Start the program; the console shows

```
================================================================
  Rocket Propulsion Simulator 2.3.0
  Go to http://localhost:8050 in your favorite browser.
  (If that address does not open, use http://127.0.0.1:8050)
  Keep this window open while you use the app; press Ctrl+C to stop it.
================================================================
```

Open the address in any browser. Port **8050** is the default; if it is already taken (for
example by a second copy of the app), the next free port (8051, 8052, …) is chosen and the
message says so. A different starting port can be given with `--port 9000` or the `PORT`
environment variable. The app only listens on the local computer (127.0.0.1).

Custom propellants uploaded in the app are stored in a `user_propellants` folder next to the
program (or in `~/.rocket_propulsion_simulator/user_propellants` if that folder is not
writable).

To distribute the app, zip the folder `dist/RocketPropulsionSimulator` (or the single file)
and include the `LICENSE` file.
The first start can take several seconds (the single-file build unpacks itself to a temporary
folder on every start; Matplotlib builds its font cache once).

## 6. Troubleshooting

* **`ModuleNotFoundError` when the built program starts** – add the module to `hiddenimports`
  in `rocket_propulsion_simulator.spec` and build again.
* **Template or static file not found** – check the `datas` list in the spec file.
* **The program window closes immediately** – start it from a terminal (PowerShell, Command
  Prompt or Terminal) instead of double-clicking it, so the error message stays visible.
* **Changes to the code are missing in the program** – the build is a snapshot; build it again
  after every change.
* **Clean rebuild** – delete the `build` and `dist` folders (the `--clean` option clears
  PyInstaller's cache).
