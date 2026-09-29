import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app import data, eo
from app.config import settings
from app.main import app

client = TestClient(app)
LAT0, LON0 = 20.85, 70.20  # Veraval offshore point


@pytest.fixture(autouse=True)
def _env(tmp_path):
    settings.cache_dir, settings.force_mock, settings.demo_scenarios = tmp_path, False, True
    data._mem.clear(); data._transport = None
    yield
    data._transport = None
    settings.force_mock = True


def _iso(days_ago):
    return (datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _erddap(req: httpx.Request):
    url = str(req.url)
    if "jplMURSST41" in url:
        rows = []
        for i in range(41):
            for j in range(41):
                lat, lon = LAT0 - 1 + i * 0.05, LON0 - 1 + j * 0.05
                rows.append([_iso(1), lat, lon, 28.0 + (0.8 if lon > LON0 else 0.0)])  # a north-south SST front at LON0
        return httpx.Response(200, json={"table": {"columnNames": ["time", "latitude", "longitude", "analysed_sst"],
                                                   "columnUnits": ["UTC", "degrees_north", "degrees_east", "degree_C"], "rows": rows}})
    rows = []
    for d in (0, 1, 2):  # day 0 (newest) is fully cloudy -> must be skipped; day 1 has real pixels
        for i in range(53):
            for j in range(53):
                lat, lon = LAT0 + 1 - i * 0.0375, LON0 - 1 + j * 0.0375
                chl = None if d == 0 else (1.2 if abs(lon - LON0) < 0.25 and abs(lat - LAT0) < 0.25 else 0.15)
                rows.append([_iso(d), 0.0, lat, lon, chl])
    return httpx.Response(200, json={"table": {"columnNames": ["time", "altitude", "latitude", "longitude", "chlor_a"],
                                               "columnUnits": ["UTC", "m", "degrees_north", "degrees_east", "mg m^-3"], "rows": rows}})


def test_eo_uses_latest_valid_day_and_finds_zone_at_the_front():
    data._transport = httpx.MockTransport(_erddap)
    j = client.get("/api/eo", params={"place": "Veraval"}).json()
    assert j["available"] and j["data_mode"] == "live"
    assert j["chl"]["obs_time"] == _iso(1)          # skipped the all-cloud newest day, reports the real observation date
    assert j["chl"]["age_days"] >= 1
    z = j["zones"][0]
    assert z["is_sample"] is False and z["is_incois_pfz"] is False
    assert abs(z["centre"]["lat"] - LAT0) < 0.3 and abs(z["centre"]["lon"] - LON0) < 0.3 and z["mean_chl_mg_m3"] >= 1.0
    assert z["sst_gradient_c_per_km"] > 0 and "Heuristic" in j["method"]


def test_eo_all_cloud_is_reported_not_invented():
    def cloudy(req):
        r = _erddap(req)
        if "jplMURSST41" in str(req.url):
            return r
        t = r.json()["table"]; [row.__setitem__(4, None) for row in t["rows"]]
        return httpx.Response(200, json={"table": t})
    data._transport = httpx.MockTransport(cloudy)
    j = client.get("/api/eo", params={"place": "Veraval"}).json()
    assert j["available"] is False and "valid pixels" in j["reason"]
    f = client.get("/api/fishing-zones", params={"place": "Veraval"}).json()
    assert f["advisory"]["is_sample"] is True     # falls back to clearly-labelled sample zones, never silently


def test_eo_source_down_then_stale_cache():
    data._transport = httpx.MockTransport(_erddap)
    assert client.get("/api/eo", params={"place": "Veraval"}).json()["data_mode"] == "live"
    for e in data._mem.values():
        e["fetched_at"] = "2020-01-01T00:00:00+00:00"
    settings.stale_max_s = 10 ** 12
    data._transport = httpx.MockTransport(lambda r: (_ for _ in ()).throw(httpx.ConnectError("offline", request=r)))
    j = client.get("/api/eo", params={"place": "Veraval"}).json()
    assert j["data_mode"] == "cached" and j["available"] and "ConnectError" in j["note"]


def test_query_shape_matches_erddap_griddap_syntax():
    seen = []
    def h(req):
        seen.append(str(req.url)); return _erddap(req)
    data._transport = httpx.MockTransport(h)
    client.get("/api/eo", params={"place": "Veraval"})
    chl = next(u for u in seen if "nesdisVHNnoaa20chlaDaily" in u)
    assert ".json?chlor_a" in chl and "last" in chl
    hi = float(chl.split("(")[1].split(")")[0])           # descending latitude axis: first bound must be the larger one
    lo = float(chl.split("(")[2].split(")")[0])
    assert hi > lo


def test_chat_fishing_uses_eo_and_says_so():
    data._transport = httpx.MockTransport(_erddap)
    j = client.post("/api/chat", json={"message": "Where is the nearest fishing zone today?", "place": "Veraval, Gujarat", "scenario": "calm"}).json()
    assert j["intent"] == "fishing" and j["pfz"]["is_sample"] is False
    assert "NOT an INCOIS advisory" in j["answer"] and _iso(1)[:10] in j["answer"]
    assert any(e["label"].startswith("Nearest satellite-derived") for e in j["evidence"])


def test_tide_extrema_and_chat_and_conditions():
    settings.force_mock = True
    hrs = [{"t": f"2026-01-01T{h:02d}:00", "tide_m": v} for h, v in enumerate([0, .5, 1.0, .6, 0, -.6, -1.0, -.4, .2])]
    ex = data.tide_extrema(hrs)
    assert [(x["kind"], x["at"][11:13]) for x in ex] == [("high", "02"), ("low", "06")]
    c = client.get("/api/conditions", params={"place": "Kochi", "day": "today"}).json()
    assert c["tide"]["extrema"] and "not for navigation" in c["tide"]["note"].lower() or "navigation" in c["tide"]["note"].lower()
    j = client.post("/api/chat", json={"message": "When is high tide tomorrow at Veraval?"}).json()
    assert j["intent"] == "tide" and j["tide"]["extrema"] and "Tide (model estimate" in j["answer"]
