<img src="webapp/static/logo.svg" width="72" alt="Rocket Propulsion Simulator logo">

# Rocket Propulsion Simulator – solid rocket motor simulator (web app)

Version 2.2.0 · Marko Šterk, PhD in physics · marko_sterk@hotmail.com · MIT License

*Odprtokodno simulacijsko orodje za raketne motorje na trdno pogonsko snov (spremljevalna koda članka v reviji Dianoia).*

A small Flask web application that computes the chamber pressure p(t) and thrust
F(t) of a solid rocket motor with **one cylindrical grain of length L** or a stack of
**N identical segments (BATES grain)**. Every grain is bonded to the case, so its
outer surface never burns. The burning surfaces of each segment are selectable:
the **canal only** (both end faces inhibited), the canal and the **nozzle-side end
face**, or the canal and **both end faces** (classic BATES segment). The **end
burner** ("fireworks motor") has no canal and burns only on its nozzle-side face;
it is always a single grain.

Canal shapes: circular, n-point star, cross / radial slots, displaced circular
canal (moon burner) and end burner. Propellants included: **KNDX**
(KNO3/dextrose), **KNSU** (KNO3/sucrose) and **KNSB** (KNO3/sorbitol), 65/35, with
data after R. Nakka. Custom propellants can be added as JSON files.

## Quick start (uv)

```bash
cd app
uv sync                      # creates .venv and uv.lock from pyproject.toml
uv run python -m webapp      # then open http://localhost:8050
```

The console shows the address to open (port 8050 by default; if it is taken, the next free
port is used and printed). `uv run python run_app.py` does the same.

**Stand-alone program (no Python needed):** see [BUILD.md](BUILD.md) for building a Windows,
Linux or macOS executable with PyInstaller (`uv sync --group build`, then
`uv run pyinstaller rocket_propulsion_simulator.spec --noconfirm --clean`).

Other commands:

```bash
uv run pytest                                  # tests (library and web app)
uv run python tools/make_article_figures.py    # all figures/numbers of the article
uv run python -m webapp --port 8060             # different preferred port
```

## Using the app

1. **Propellant** – pick KNDX, KNSU or KNSB, or upload your own JSON file
   (see `examples/custom_propellant_template.json`; uploaded files are stored in
   `user_propellants/`). Tick *Compare all propellants* to overlay all of them.
2. **Grain** – choose the canal shape and enter the segment length L, the outer
   diameter and the canal dimensions, the number of segments N, the gap between
   them and the burning surfaces. For a circular canal burning on both faces the
   app shows the approximately neutral BATES length L ≈ (3D + d)/2.
3. **Nozzle** – throat and exit diameter, divergence half-angle and efficiency.
   *Size throat* finds the throat diameter that gives the chosen peak pressure.
4. **Run simulation** – you get peak/average thrust, total and specific impulse,
   burn time and motor class, plots of p(t), F(t) and Kn(w), an animated burn-back
   view (cross-section seen from the nozzle and longitudinal section of the whole
   motor with all segments, case and nozzle; play button or time slider), and CSV
   downloads of the time series.
5. **About** – the button in the header shows the version, author, contact, licence and
   the safety warning.
6. **Export the burn-back** – below the viewer: *PNG* saves the current frame, *GIF
   animation* renders the whole burn (chosen length and frame rate; the GIF is assembled
   on the server with Pillow) and *Video* records an MP4 (H.264) or WebM file in the
   browser in real time. Every frame shows the cross-section, the longitudinal section,
   the pressure trace with the current time and the values of t, w, p, F and Kn.

## Propellant JSON

| key | meaning |
|---|---|
| `name` | short name shown in the app |
| `density` | cast-grain density, kg/m³ |
| `combustion_temperature` | adiabatic flame temperature, K |
| `molar_mass` | effective molar mass of the products incl. condensed phase, g/mol |
| `gamma_chamber` / `gamma_exhaust` | ratio of specific heats in the chamber / two-phase nozzle flow |
| `burn_rate.ranges` | list of `{p_min, p_max, a, n}`: r = a·pⁿ in mm/s with p in MPa |

## Physical model

0-D internal ballistics: dw/dt = r(p);  V/(R T) dp/dt = A_b r (ρ_p − p/(R T)) − p A_t / c*;
piecewise Saint-Robert burn-rate law; choked/subsonic isentropic nozzle flow;
F = η_F λ C_F p A_t. A_b(w) = P(w)·L for canal grains (analytic for the circular
canal, distance transform + marching squares for other shapes) and A_b = πR² for
the end burner. With N segments and k = 0, 1 or 2 burning end faces per segment,
A_b(w) = N [P(w)(L − k w) + k (πR² − A_port(w))]; a segment is consumed when the
canal reaches the case or when w = L/k. In the 0-D model the pressure is uniform,
so N segments with inhibited faces behave exactly like one grain of length N·L. The system is integrated with 4th-order Runge–Kutta.

Optional tail-off correction: *burnout spread* lets the local burn rate vary uniformly by
±s along the grain (the grain is split into slices that burn out at different times). With
s = 0 the ideal model is recovered, in which the pressure drops exponentially with the chamber
time constant τ = V c*/(R T A_t) as soon as the grain is consumed.

Not modelled: erosive burning, ignition transient along the grain, nozzle
erosion/slag, heat losses. **For education only – amateur rocket motors are
dangerous; follow the law and your national rocketry association's safety code.**

## Layout

```
app/
  pyproject.toml, .python-version   uv project
  srmsim/                           simulation library of Rocket Propulsion Simulator (propellants/, grains, nozzle, motor)
  webapp/                           Flask web application
    __init__.py                     create_app() application factory
    config.py, server.py            configuration; port selection and start-up (main)
    api/                            controllers (blueprints): pages, propellants, simulation, export
    services/                       handlers: propellant, simulation and export services, charts
    motor/                          motor assembly from the web form, grain cache, burn-back data
    templates/, static/             page, JavaScript, styles, logo
  tools/make_article_figures.py     reproduces the article figures (tools/figures/)
  examples/                         custom propellant template, example motors
  tests/
  run_app.py                        start script (also the entry point of the stand-alone build)
  rocket_propulsion_simulator.spec  PyInstaller configuration (see BUILD.md)
  packaging/                        application icons (logo.png, logo.ico)
```

MIT licence.
