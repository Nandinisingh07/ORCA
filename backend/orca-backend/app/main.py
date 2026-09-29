import asyncio

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import agents, data, eo, llm, risk
from . import lang as L
from . import reference as ref
from .config import settings
from .schemas import ChatIn, PointIn, RouteIn

app = FastAPI(title="ORCA demo backend", version="0.1.0",
              description="Demo API for the ORCA marine decision-support prototype. Rule-based safety verdicts; "
                          "live Open-Meteo data with cache and labelled fallbacks.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_origin_regex=r"https://.*\.(lovable\.app|lovable\.dev|vercel\.app)",
                   allow_methods=["*"], allow_headers=["*"])


def _place(q: str) -> dict:
    key = ref.resolve_place(q)
    if not key:
        raise HTTPException(404, {"error": f"unknown place '{q}'", "supported": [p["display"] for p in ref.PLACES.values()]})
    return ref.PLACES[key]


def _day(s) -> int:
    try:
        return agents.parse_day(s)
    except ValueError as e:
        raise HTTPException(422, str(e))


def _scenario(s):
    if s and s not in ("calm", "rough", "storm"):
        raise HTTPException(422, "scenario must be calm, rough or storm")
    return s


@app.get("/api/health")
async def health(deep: bool = False):
    out = {"status": "ok", "version": app.version, "force_mock": settings.force_mock,
           "demo_scenarios": settings.demo_scenarios, "llm_configured": llm.enabled(),
           "last_live_fetch": data.last_live_ok, "cache_dir": str(settings.cache_dir),
           "cache_files": len(list(settings.cache_dir.glob("*.json"))) if settings.cache_dir.exists() else 0,
           "language_layer": "template stub (not Bhashini)",
           "boundary_data": "illustrative sample" if all(f["properties"].get("is_illustrative") for f in ref.load_features()) else "custom GeoJSON"}
    if deep:
        out["probes"] = await asyncio.gather(data.probe("marine"), data.probe("weather"))
        if not all(p["ok"] for p in out["probes"]):
            out["status"] = "degraded"
    return out


@app.get("/api/places")
def places():
    return [{"key": k, "name": p["display"], "coast": p["coast"], "lat": p["harbour"][0], "lon": p["harbour"][1]}
            for k, p in ref.PLACES.items()]


@app.post("/api/chat")
async def chat(body: ChatIn):
    _scenario(body.scenario)
    return await agents.handle_chat(body)


@app.get("/api/conditions")
async def conditions(place: str, day: str = "today", scenario: str | None = None):
    p, d, scen = _place(place), _day(day), _scenario(scenario)
    b = await agents.fetch_bundle(p["offshore"], scen)
    periods = []
    for name, (s, e) in {"Morning": (5, 12), "Afternoon": (12, 18), "Evening": (18, 24)}.items():
        a = risk.assess(data.window(b["hours"], d, s, e))
        periods.append({"period": name, "level": a["level"], "label": a["label"],
                        "wave_m_max": a["metrics"].get("wave_m_max"), "wind_kn_max": a["metrics"].get("wind_kn_max"),
                        "reasons": a["reasons"]})
    whole = risk.assess(data.window(b["hours"], d))
    tide = data.tide_extrema(data.window(b["hours"], d))
    return {"place": {"key": p["key"], "name": p["display"]}, "day": d,
            "tide": {"extrema": tide, "note": agents.TIDE_NOTE},
            "forecast_point": {"lat": p["offshore"][0], "lon": p["offshore"][1],
                               "note": "approximate nearshore sampling point"},
            "summary": {"level": whole["level"], "label": whole["label"], **whole["metrics"]},
            "periods": periods,
            "sources": {"marine": {"name": b["marine"].source, "data_mode": b["marine"].mode,
                                   "fetched_at": b["marine"].fetched_at, "note": b["marine"].note},
                        "weather": {"name": b["weather"].source, "data_mode": b["weather"].mode,
                                    "fetched_at": b["weather"].fetched_at, "note": b["weather"].note}},
            "confidence": risk.confidence(b["mode"], d),
            "rules": {"rule_set": risk.RULE_SET, "thresholds": risk.THRESHOLDS},
            "data_mode": b["mode"], "disclaimer": agents.DISCLAIMER}


@app.get("/api/fishing-zones")
async def fishing_zones(place: str, scenario: str | None = None):
    p, scen = _place(place), _scenario(scenario)
    b = await agents.fetch_bundle(p["offshore"], scen)
    v = risk.assess(data.window(b["hours"], 0, only_future=True))
    pz = await agents.pfz_agent(p["key"])
    return {"place": {"key": p["key"], "name": p["display"]},
            "advisory": {"date": data.day_date(0).isoformat(), "landing_centre": {"lat": p["harbour"][0], "lon": p["harbour"][1]},
                         "is_sample": pz["is_sample"],
                         "source": ("ORCA sample data in a PFZ-like format (NOT an INCOIS bulletin)" if pz["is_sample"]
                                    else "Satellite-derived candidate zones (heuristic; NOT an INCOIS PFZ advisory)"),
                         "official_source": "https://incois.gov.in/MarineFisheries/PfzAdvisory"},
            "zones": pz["zones"], "eo": pz["eo"],
            "sea_state": {"level": v["level"], "label": v["label"], "reasons": v["reasons"], "data_mode": b["mode"]},
            "safety_note": "Fishing potential is not a safety verdict: an area may be promising yet unsafe to reach.",
            "disclaimer": agents.DISCLAIMER}


@app.get("/api/alerts")
async def alerts(region: str = "all", type: str = "all", day: str = "both", include_samples: bool = True,
                 scenario: str | None = None):
    region = {"all coasts": "all", "west coast": "west", "east coast": "east"}.get(region.lower(), region.lower())
    kind = type.lower()
    if region not in ("all", "west", "east") or kind not in ("all", "weather", "sea"):
        raise HTTPException(422, "region: all|west|east, type: all|weather|sea")
    days = (0, 1) if day == "both" else (_day(day),)
    return await agents.build_alerts(region, kind, days, _scenario(scenario), include_samples)


@app.post("/api/route")
async def route(body: RouteIn):
    p, d, scen = _place(body.origin), _day(body.day), _scenario(body.scenario)
    try:
        r = await agents.route_agent(p, body.distance_km, body.bearing_deg if body.bearing_deg is not None
                                     else agents.default_bearing(p), d, scen)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"place": {"key": p["key"], "name": p["display"]}, "day": d, "route": r,
            "confidence": risk.confidence(r["data_mode"], d), "data_mode": r["data_mode"],
            "disclaimer": agents.DISCLAIMER + " Never use for navigation."}


@app.get("/api/boundaries")
def boundaries(layer: str = "reference"):
    t = layer.lower()
    name = "coastal" if "coastal" in t else "protected" if "protected" in t else "reference"
    feats = ref.coastal_features() if name == "coastal" else [f for f in ref.load_features() if f["properties"]["layer"] == name]
    illus = any(f["properties"].get("is_illustrative") for f in feats)
    return {"type": "FeatureCollection", "layer": name, "features": feats, "is_illustrative": illus,
            "legal_validity": "none (illustrative geometry)" if illus else "verify with the issuing authority",
            "notice": "Not a legal boundary or navigation chart. Load validated GeoJSON into data/boundaries/."}


@app.post("/api/boundaries/check")
def boundary_check(body: PointIn):
    hits = ref.nearest_features((body.lat, body.lon))
    return {"point": body.model_dump(), "level": ref.proximity_level(hits), "nearest": hits[:5],
            "alert_within_km": settings.boundary_alert_km,
            "notice": "Demo geometry unless real GeoJSON is loaded; not a legal position fix."}


@app.get("/api/briefing")
async def briefing(place: str, lang: str = "en", mode: str = "simple", scenario: str | None = None):
    p = _place(place)
    return await agents.build_briefing(p["key"], L.norm_lang(lang) or "en", "technical" if mode == "technical" else "simple",
                                       _scenario(scenario))


@app.get("/api/eo")
async def eo_summary(place: str):
    """Satellite chlorophyll + SST summary and candidate zones for the box around a place."""
    return await eo.get_eo(_place(place)["key"])
