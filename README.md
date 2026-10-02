<img src="webapp/static/logo.svg" width="72" alt="Rocket Propulsion Simulator logo">

# Rocket Propulsion Simulator

**Internal-ballistics simulator for solid rocket motors – web application and Python library**

Version 2.2.0 · Marko Šterk, PhD in physics · marko_sterk@hotmail.com · MIT License

*Odprtokodno simulacijsko orodje za raketne motorje na trdno pogonsko snov – spremljevalna koda
članka v reviji Dianoia.*

Rocket Propulsion Simulator computes the chamber pressure p(t) and the thrust F(t) of a solid
rocket motor. You choose the propellant, the grain geometry and the nozzle in the browser and
get the pressure and thrust curves, the main performance figures and an animated view of how
the grain burns back.

> **Safety warning.** Making, handling or firing rocket propellants and motors is dangerous
> and regulated by law. This software is for education only; its results are model estimates,
> not verified designs. Follow the law and the safety code of your national rocketry
> association, and never work with propellants without expert supervision.

## Contents

- [Features](#features)
- [Installation and start](#installation-and-start)
- [Using the app](#using-the-app)
- [Custom propellants](#custom-propellants)
- [Physical model](#physical-model)
- [Python library (srmsim)](#python-library-srmsim)
- [Project structure](#project-structure)
- [Development](#development)
- [Licence](#licence)

## Features

- **Grains:** one cylindrical grain of length L or a stack of N identical segments (BATES
  grain). Every grain is bonded to the case, so its outer surface never burns.
- **Canal shapes:** circular, n-point star, cross (radial slots), displaced circular canal
  (moon burner), and the end burner ("fireworks motor") without a canal.
- **Burning surfaces per segment:** canal only, canal and the nozzle-side end face, or canal
  and both end faces (classic BATES segment). The end burner always burns only on its
  nozzle-side face and is always a single grain.
- **Propellants:** KNDX (KNO₃/dextrose), KNSU (KNO₃/sucrose) and KNSB (KNO₃/sorbitol), all
  65/35, with data after R. Nakka. Your own propellants can be added as JSON files.
- **Results:** peak pressure, peak and average thrust, total and specific impulse, burn time,
  motor class, plots of p(t), F(t) and K_n(w), CSV export of the time series, and a comparison
  of all propellants on the same motor.
- **Burn-back viewer:** cross-section seen from the nozzle and a longitudinal section of the
  whole motor (segments, case, nozzle), controlled by a time slider or a play button, with
  export to PNG, animated GIF or video (MP4/WebM).
- **Throat sizing:** finds the throat diameter that gives a chosen peak pressure.

## Installation and start

### From the source code (recommended)

Requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/). uv installs the
right Python version (3.12, see `.python-version`) and all libraries by itself.

```bash
cd app
uv sync                    # creates .venv with all dependencies (first time needs internet)
uv run python -m webapp    # starts the app
```

The console shows the address to open:

```
================================================================
  Rocket Propulsion Simulator 2.2.0
  Go to http://localhost:8050 in your favorite browser.
  (If that address does not open, use http://127.0.0.1:8050)
  Keep this window open while you use the app; press Ctrl+C to stop it.
================================================================
```

Port **8050** is the default. If it is already in use, the next free port (8051, 8052, …) is
used and the message says so. A different starting port can be chosen with
`uv run python -m webapp --port 9000` or the `PORT` environment variable. The app only listens
on the local computer (127.0.0.1). `uv run python run_app.py` starts it in the same way.

### Stand-alone program (no Python needed)

The app can be built into a program for Windows, Linux or macOS with PyInstaller:

```bash
uv sync --group build
uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean
```

The result is in `dist/RocketPropulsionSimulator/`. See [BUILD.md](BUILD.md) for the full
instructions for each operating system, the single-file variant and troubleshooting.

## Using the app

The page has an input panel on the left and the results on the right.

1. **Propellant** – choose KNSU, KNDX or KNSB, or add your own JSON file (see
   [Custom propellants](#custom-propellants)). *Compare all propellants* overlays the results of
   all propellants for the same motor.
2. **Grain** – choose the canal shape and enter the segment length L, the outer diameter D and
   the canal dimensions, then the number of segments N, the gap between them and the burning
   surfaces. For a circular canal burning on both end faces the app shows the segment length
   for approximately neutral burning, L ≈ (3D + d)/2.
3. **Nozzle** – throat and exit diameter, divergence half-angle and nozzle efficiency η_F.
   *Size throat* finds the throat diameter for the target peak pressure and then runs the
   simulation.
4. **Other parameters**

   | parameter | meaning | default |
   |---|---|---|
   | c* efficiency η* | ratio of the real to the ideal characteristic velocity (combustion losses) | 0.975 |
   | burn-rate multiplier k_r | scales the burn rate, e.g. to match a test firing | 1.0 |
   | free chamber length | empty chamber length in front of the nozzle | 10 mm |
   | ambient pressure | 101.325 kPa at sea level | 101.325 kPa |
   | burnout spread ± | optional empirical tail-off correction (see [Physical model](#physical-model)); 0 = ideal model | 0 % |

5. **Run simulation** – the results show:
   - the performance figures;
   - plots of chamber pressure, thrust and K_n = A_b/A_t versus burnt web;
   - the burn-back viewer;
   - a results table and CSV downloads of the time series (columns: time, pressure, thrust,
     burnt web, burning area, K_n, mass flow and burn rate).

   Warnings appear above the plots, for example when the pressure leaves the range of the
   burn-rate data.
6. **Export the burn-back** – below the viewer:
   - *PNG* saves the current frame;
   - *GIF animation* renders the whole burn with the chosen length and frame rate;
   - *Video* records an MP4 (H.264) or WebM file in the browser in real time.

   Every frame shows both sections, the pressure curve with the current time and the values of
   t, w, p, F and K_n.
7. **About** – the button in the header shows the version, author, contact, licence and the
   safety warning.

The **motor class** follows the NAR/NFPA 1125 code: the letter gives the total-impulse range
(each letter doubles the impulse, e.g. J = 640–1280 N s) and the number is the average thrust
in newtons.

## Custom propellants

A propellant is a JSON file. Copy `examples/custom_propellant_template.json`, fill in your
data and load it with *Add a custom propellant* in the app. Uploaded files are stored in
`user_propellants/` (in the stand-alone build: next to the program, or in
`~/.rocket_propulsion_simulator/user_propellants` if that folder is read-only).

```json
{
  "name": "MYPROP",
  "density": 1800,
  "combustion_temperature": 1650,
  "molar_mass": 41.0,
  "gamma_chamber": 1.13,
  "gamma_exhaust": 1.04,
  "burn_rate": {
    "units": {"pressure": "MPa", "rate": "mm/s"},
    "ranges": [
      {"p_min": 0.1, "p_max": 2.0, "a": 8.0, "n": 0.30},
      {"p_min": 2.0, "p_max": 8.0, "a": 7.0, "n": 0.45}
    ]
  }
}
```

| key | required | meaning |
|---|---|---|
| `name` | yes | short name shown in the app (a file with the same name replaces the earlier one) |
| `density` | yes | density of the cast grain, kg/m³ |
| `combustion_temperature` | yes | adiabatic flame temperature, K |
| `molar_mass` | yes | effective molar mass of the products including the condensed phase, g/mol |
| `gamma_chamber` | yes | ratio of specific heats in the chamber |
| `gamma_exhaust` | no | effective ratio of specific heats for the two-phase nozzle flow (default: `gamma_chamber`) |
| `burn_rate.ranges` | yes | list of pressure ranges `{p_min, p_max, a, n}` with r = a·pⁿ |
| `burn_rate.units` | no | pressure `MPa` (default), `kPa`, `Pa` or `psi`; rate `mm/s` (default), `m/s` or `in/s` |
| `description`, `composition`, `density_ideal`, `references` | no | information only |

The flame temperature, molar mass and ratios of specific heats can be computed with a
thermochemical code such as PROPEP or NASA CEA; the burn-rate coefficients come from
measurements (e.g. a strand burner). Outside the given pressure ranges the first or last law
is extrapolated and the app shows a warning.

## Physical model

The motor is described by a zero-dimensional (0-D) internal-ballistics model: pressure and
temperature are the same everywhere in the free chamber volume V, the gas temperature equals
the combustion temperature T_c, the products behave as an ideal gas, the whole grain ignites
at once and the nozzle flow is isentropic.

```
dw/dt = r(p_c)                                          burnt web
V/(R T_c) · dp_c/dt = A_b(w) r(p_c) (ρ_p − p_c/(R T_c)) − p_c A_t / c*   gas mass balance
r(p_c) = a_i p_c^n_i   for p_(i−1) ≤ p_c < p_i          piecewise burn-rate law
F = η_F λ C_F p_c A_t,   λ = (1 + cos α)/2              thrust
```

- **Nozzle:** the throat is choked as long as the chamber pressure is above about 1.7 times the
  ambient pressure. Below that the nozzle is treated as convergent with subsonic isentropic flow.
  C_F is the ideal thrust coefficient for the exit-to-throat area ratio ε and the two-phase
  ratio of specific heats.
- **Burning area:** for a canal grain A_b(w) = P(w)·L, where P(w) is the perimeter of the flame
  front. It is analytic for the circular canal; for the other shapes it is computed with a
  Euclidean distance transform and marching squares. For the end burner A_b = πR².
- **Segments and burning faces:** with N segments and k = 0, 1 or 2 burning end faces per segment,

  ```
  A_b(w) = N [ P(w) (L − k w) + k (πR² − A_port(w)) ]
  ```

  A segment is consumed when the canal reaches the case or when w = L/k. Because the pressure
  is uniform in the 0-D model, N segments with inhibited faces behave exactly like one grain of
  length N·L.
- **Numerics:** the equations are integrated with the 4th-order Runge–Kutta method. The time
  step is smaller than a quarter of the chamber time constant τ = V c*/(R T_c A_t), so ignition
  and tail-off are resolved.
- **Burnout spread (optional):** the local burn rate varies uniformly by ±s along the grain, so
  the flame front reaches the case gradually and the tail-off looks more like a real motor. With
  s = 0 the ideal model is used, in which the pressure falls exponentially with τ as soon as the
  grain is consumed.

**Not modelled:** erosive burning, ignition spreading along the grain, nozzle erosion and slag,
heat losses, and flow separation in strongly over-expanded nozzles.

## Python library (srmsim)

The simulation itself is the `srmsim` package, which can be used without the web app.

```python
from srmsim import CircularCoreGrain, Motor, Nozzle, Propellant, SegmentedGrain

mm = 1e-3
segment = CircularCoreGrain(outer_diameter=46 * mm, core_diameter=16 * mm, length=75 * mm)
grain = SegmentedGrain(segment, n_segments=4, faces="both")
motor = Motor(Propellant.load("KNSU"), grain, Nozzle(14.15 * mm, 34.66 * mm))
result = motor.simulate()
print(result.summary())
result.to_csv("knsu_bates.csv")
```

A whole motor can also be described as JSON (see `examples/`) and loaded with
`Motor.load("examples/bates_knsu.json")`. Grain keys: `type` (`circular`, `star`, `cross`,
`moon`, `endburner`), `outer_diameter_mm`, `length_mm` (one segment), the shape-specific
dimensions, and optionally `segments`, `burning_faces` (`none`, `aft`, `both`) and
`segment_gap_mm`. `srmsim.size_throat` finds the throat diameter for a target peak pressure.

## Project structure

```
app/
  pyproject.toml, .python-version   uv project (dependencies, Python version)
  run_app.py                        start script; entry point of the stand-alone build
  rocket_propulsion_simulator.spec  PyInstaller configuration (see BUILD.md)
  srmsim/                           simulation library: propellants, grains, nozzle, motor
    propellants/                    bundled propellant data (KNDX, KNSU, KNSB)
  webapp/                           Flask web application
    __init__.py                     create_app() application factory
    config.py                       default settings and file locations
    server.py                       port selection and start-up (main)
    api/                            controllers (blueprints): pages, propellants, simulation, export
    services/                       handlers: propellant, simulation and export services, charts
    motor/                          motor assembly from the web form, grain cache, burn-back data
    templates/, static/             page, JavaScript, styles, logo
  examples/                         propellant template and example motors
  tests/                            tests of the library and the web app
  tools/make_article_figures.py     reproduces the figures and numbers of the article
  packaging/                        application icons
  user_propellants/                 uploaded propellants
```

The web app is organised in layers: a controller in `webapp/api` reads the request and calls a
service in `webapp/services`. The service uses `webapp/motor` to build the motor from the form
and `srmsim` to simulate it. Long tasks (simulation, throat sizing) stream their progress to the
browser as NDJSON lines.

### HTTP API

| method and path | purpose |
|---|---|
| `GET /` | the application page |
| `GET /api/propellants` | list of propellants with their data |
| `POST /api/propellants` | add a propellant (JSON body or uploaded file) |
| `POST /api/simulate` | run a simulation (streamed progress, then the result) |
| `POST /api/size_throat` | size the throat for a target peak pressure (streamed) |
| `POST /api/export_gif` | build an animated GIF from frames rendered in the browser |

## Development

```bash
uv sync                                        # includes the test tools (dev group)
uv run pytest                                  # tests of the library and the web app
uv run python tools/make_article_figures.py    # figures and numbers of the article -> tools/figures/
```

The application is created with `create_app()`. Settings can be overridden, for example in
tests:

```python
from webapp import create_app

app = create_app({"TESTING": True, "USER_PROPELLANT_DIR": "/tmp/propellants"})
client = app.test_client()
```

Available settings: `USER_PROPELLANT_DIR`, `MAX_PROPELLANT_BYTES`, `MAX_GIF_FRAMES`,
`GRAIN_CACHE_SIZE`, `GRAIN_RESOLUTION` and `MAX_CONTENT_LENGTH`.

## Licence

MIT License, © 2026 Marko Šterk – see [LICENSE](LICENSE). The software is provided "as is",
without warranty of any kind.
