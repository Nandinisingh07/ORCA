import httpx
import pytest
from fastapi.testclient import TestClient

from app import data, reference as ref, risk
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _env(tmp_path):
    settings.cache_dir, settings.force_mock, settings.demo_scenarios = tmp_path, True, True
    data._mem.clear(); data._transport = None
    yield
    data._transport = None


def test_health():
    j = client.get("/api/health").json()
    assert j["status"] == "ok" and j["force_mock"] is True


def test_risk_thresholds():
    h = lambda w, v: [{"t": "2026-01-01T06:00", "wave_m": w, "wind_kn": v}]  # noqa: E731
    assert risk.assess(h(1.0, 10))["level"] == "safe"
    assert risk.assess(h(1.6, 10))["level"] == "caution"
    assert risk.assess(h(1.0, 26))["level"] == "unsafe"
    assert risk.assess([])["level"] == "unknown"


def test_chat_english_safety_and_labelling():
    j = client.post("/api/chat", json={"message": "Is it safe to go to sea tomorrow?", "place": "Veraval, Gujarat"}).json()
    assert j["intent"] == "safety" and j["day"] == 1 and j["place"]["key"] == "veraval"
    assert j["data_mode"] == "mock" and j["confidence"]["level"] == "demo"
    assert j["evidence"] and all(e["data_mode"] == "mock" for e in j["evidence"])
    assert "synthetic sample data" in j["answer"]  # provenance must be visible in the text itself, not only in flags
    assert {"planner", "weather", "ocean", "risk", "explainability"} <= {t["agent"] for t in j["trace"]}


def test_storm_scenario_is_unsafe():
    j = client.post("/api/chat", json={"message": "safe today at Mumbai?", "scenario": "storm"}).json()
    assert j["verdict"]["level"] == "unsafe" and j["verdict"]["reasons"]


def test_hindi_detection_and_followup():
    j = client.post("/api/chat", json={"message": "कल वेरावल में समुद्र सुरक्षित है?", "language": "English"}).json()
    assert j["detected_language"] == "hi" and j["language"] == "hi" and j["day"] == 1 and j["place"]["key"] == "veraval"
    assert any("\u0900" <= c <= "\u097F" for c in j["answer"])
    j2 = client.post("/api/chat", json={"message": "what about the day after?", "session_id": j["session_id"]}).json()
    assert j2["day"] == 2 and j2["place"]["key"] == "veraval" and j2["followup"] is True


def test_default_place_is_disclosed():
    j = client.post("/api/chat", json={"message": "how are the waves?"}).json()
    assert j["place"]["assumed"] is True


def test_route_inland_bearing_rejected_and_ok_case():
    r = client.post("/api/route", json={"origin": "Veraval", "distance_km": 20, "bearing_deg": 90})
    assert r.status_code == 422
    r = client.post("/api/route", json={"origin": "Veraval, Gujarat", "distance_km": 20}).json()
    assert r["route"]["bearing_deg"] == 270 and len(r["route"]["samples"]) == 3
    assert r["route"]["boundary"]["level"] in ("caution", "unsafe")  # demo protected area sits ~12 km off the default track


def test_boundary_check_inside_demo_area():
    j = client.post("/api/boundaries/check", json={"lat": 20.7, "lon": 70.1}).json()
    assert j["level"] == "unsafe" and j["nearest"][0]["inside"] is True


def test_other_endpoints_shape():
    assert client.get("/api/conditions", params={"place": "Kochi, Kerala", "day": "tomorrow"}).json()["periods"]
    assert client.get("/api/fishing-zones", params={"place": "Gujarat coast"}).json()["advisory"]["is_sample"] is True
    a = client.get("/api/alerts", params={"region": "West coast"}).json()
    assert any(x["is_sample"] for x in a["alerts"])
    assert client.get("/api/boundaries", params={"layer": "Coastal reference"}).json()["layer"] == "coastal"
    b = client.get("/api/briefing", params={"place": "Panaji, Goa", "lang": "ta"}).json()
    assert b["audio"] is None and "காலை" in b["text"]
    assert client.get("/api/conditions", params={"place": "Atlantis"}).status_code == 404


MARINE = {"hourly": {"time": [], "wave_height": [], "wave_period": [], "wave_direction": [], "swell_wave_height": [], "sea_surface_temperature": []}}
WEATHER = {"hourly": {"time": [], "wind_speed_10m": [], "wind_gusts_10m": [], "weather_code": [], "precipitation_probability": []}}


def _payload(url):
    base = data._mock("marine", 20.85, 70.2, None).hours  # reuse valid hourly timestamps for today..+2
    if "marine" in url:
        h = {"time": [x["t"] for x in base], "wave_height": [3.2] * 72, "wave_period": [9.0] * 72,
             "wave_direction": [250.0] * 72, "swell_wave_height": [2.0] * 72, "sea_surface_temperature": [28.4] * 72}
    else:
        h = {"time": [x["t"] for x in base], "wind_speed_10m": [12.0] * 72, "wind_gusts_10m": [20.0] * 72,
             "weather_code": [3] * 72, "precipitation_probability": [10] * 72}
    return {"hourly": h}


def test_live_parse_then_stale_cache_then_mock():
    settings.force_mock = False
    calls = {"n": 0, "fail": False}

    def handler(req: httpx.Request):
        calls["n"] += 1
        if calls["fail"]:
            raise httpx.ConnectError("offline", request=req)
        return httpx.Response(200, json=_payload(str(req.url)))

    data._transport = httpx.MockTransport(handler)
    j = client.get("/api/conditions", params={"place": "Veraval", "day": "tomorrow"}).json()
    assert j["data_mode"] == "live" and j["summary"]["wave_m_max"] == 3.2 and j["summary"]["level"] == "unsafe"
    # make the cache stale, break the network -> must serve 'cached', not crash
    for e in data._mem.values():
        e["fetched_at"] = "2020-01-01T00:00:00+00:00"
    settings.stale_max_s = 10 ** 12
    calls["fail"] = True
    j = client.get("/api/conditions", params={"place": "Veraval", "day": "tomorrow"}).json()
    assert j["data_mode"] == "cached"
    # nothing cached + network down -> labelled mock
    data._mem.clear()
    for f in settings.cache_dir.glob("*.json"):
        f.unlink()
    j = client.get("/api/conditions", params={"place": "Mumbai"}).json()
    assert j["data_mode"] == "mock" and "live fetch failed" in (j["sources"]["marine"]["note"] or "")
