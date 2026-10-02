"""Web application tests (application factory, controllers and services):  uv run pytest"""
import base64
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from webapp import create_app

FORM = {
    "propellant": "KNSU", "compare_all": False,
    "grain": {"type": "circular", "length_mm": 75, "outer_diameter_mm": 46, "core_diameter_mm": 16,
              "segments": 4, "burning_faces": "both", "segment_gap_mm": 0},
    "nozzle": {"throat_diameter_mm": 14.15, "exit_diameter_mm": 34.66, "half_angle_deg": 15, "efficiency": 0.9},
    "target_pressure_MPa": 4.0, "cstar_efficiency": 0.975, "burn_rate_multiplier": 1.0,
    "free_length_mm": 10, "ambient_pressure_kPa": 101.325, "burnout_spread_pct": 0,
}


def make_client():
    app = create_app({"TESTING": True, "USER_PROPELLANT_DIR": tempfile.mkdtemp()})
    return app, app.test_client()


def stream_result(response):
    lines = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line.strip()]
    assert lines[-1]["type"] == "result", lines[-1]
    assert any(m["type"] == "progress" for m in lines)
    return lines[-1]["data"]


def test_factory_creates_independent_apps():
    a, _ = make_client()
    b, _ = make_client()
    assert a is not b and a.extensions["rps"] is not b.extensions["rps"]
    assert a.config["USER_PROPELLANT_DIR"] != b.config["USER_PROPELLANT_DIR"]


def test_index_and_propellant_list():
    _, client = make_client()
    page = client.get("/")
    assert page.status_code == 200 and b"Rocket Propulsion Simulator" in page.data
    names = [p["name"] for p in client.get("/api/propellants").get_json()]
    assert {"KNDX", "KNSU", "KNSB"} <= set(names)


def test_upload_propellant_valid_and_invalid():
    app, client = make_client()
    data = json.load(open(os.path.join(ROOT, "srmsim", "propellants", "knsu.json"), encoding="utf-8"))
    data["name"] = "TEST1"
    ok = client.post("/api/propellants", json=data).get_json()
    assert ok["ok"] and ok["name"] == "TEST1"
    assert os.path.isfile(os.path.join(app.config["USER_PROPELLANT_DIR"], "test1.json"))
    bad = client.post("/api/propellants", json={"name": "X"})
    assert bad.status_code == 400 and not bad.get_json()["ok"]


def test_simulate_bates_stream():
    _, client = make_client()
    data = stream_result(client.post("/api/simulate", json=FORM))
    s = data["summary"]["KNSU"]
    assert abs(s["peak_pressure_MPa"] - 4.0) < 0.05
    assert data["burnback"]["n_seg"] == 4 and data["burnback"]["faces"] == "both"
    assert data["plots"]["pressure"].startswith("<svg")


def test_simulate_unknown_propellant_reports_error():
    _, client = make_client()
    lines = client.post("/api/simulate", json=dict(FORM, propellant="NOPE")).get_data(as_text=True).splitlines()
    last = json.loads(lines[-1])
    assert last["type"] == "error" and "unknown propellant" in last["error"]


def test_export_gif():
    from PIL import Image
    _, client = make_client()
    frames = []
    for colour in ("red", "blue"):
        buf = io.BytesIO()
        Image.new("RGB", (20, 10), colour).save(buf, format="PNG")
        frames.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    r = client.post("/api/export_gif", json={"frames": frames, "fps": 10})
    assert r.status_code == 200 and r.data[:6] in (b"GIF89a", b"GIF87a")
    assert client.post("/api/export_gif", json={"frames": []}).status_code == 400
