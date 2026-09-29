"""ORCA agents + orchestration.

Planner -> (Weather | Ocean | Geospatial | Geofence | PFZ | Route) in parallel -> Risk (rule engine)
        -> Explainability (evidence, confidence) -> Language (templates, optional LLM re-phrase).
"""
import asyncio
import re
import time
import uuid
from collections import OrderedDict

from . import data, eo, geo, llm, risk
from . import lang as L
from . import reference as ref
from .config import settings
from .schemas import ChatIn

TIDE_NOTE = "Model-derived (8 km grid), referenced to mean sea level, not chart datum. Do not use for navigation or port entry."
DISCLAIMER = "Demo system. Always verify with official INCOIS/IMD advisories before going to sea."
SESSIONS: OrderedDict[str, dict] = OrderedDict()

KW = {
    "boundary": ["boundary", "border", "imbl", "protected", "restrict", "geofenc", "सीमा", "बॉर्डर", "સીમા", "બોર્ડર", "எல்லை"],
    "route": ["route", "distance", "path", "रास्ता", "मार्ग", "રસ્તો", "માર્ગ", "பாதை", "வழி"],
    "tide": ["tide", "high tide", "low tide", "ज्वार", "भाटा", "ભરતી", "ઓટ", "ஓதம்"],
    "fishing": ["fish", "pfz", "catch", "मछली", "मत्स्य", "માછલી", "மீன்"],
    "alerts": ["alert", "warning", "cyclone", "storm", "lightning", "चेतावनी", "चक्रवात", "तूफान", "તોફાન",
               "વાવાઝોડ", "எச்சரிக்கை", "புயல்"],
    "safety": ["safe", "danger", "risk", "go to sea", "सुरक्षित", "सुरक्षा", "खतरा", "સુરક્ષિત", "સલામત", "பாதுகாப்பு"],
}
DAY2 = ["day after", "parso", "परसों", "પરમદિવસ", "நாளை மறுநாள்"]
DAY1 = ["tomorrow", "kal", "कल", "કાલે", "આવતીકાલ", "நாளை"]
DAY0 = ["today", "aaj", "आज", "આજે", "இன்று"]
DAY_WORDS = {"today": 0, "tomorrow": 1, "day_after": 2, "day-after": 2, "0": 0, "1": 1, "2": 2}


def _has(text: str, words, prefix: bool = False) -> bool:
    """ASCII words match on word boundaries (prefix=True also allows suffixes: fish -> fishing). Indic scripts use substring."""
    end = "" if prefix else r"\b"
    return any((re.search(rf"\b{re.escape(w)}{end}", text) if w.isascii() else w in text) for w in words)


def parse_day(s) -> int:
    d = DAY_WORDS.get(str(s).lower().strip())
    if d is None:
        raise ValueError("day must be today, tomorrow or day_after")
    return d


def default_bearing(place) -> int:
    return 270 if place["coast"] == "west" else 90


def sea_side(place, bearing: float) -> bool:
    return bearing >= 180 if place["coast"] == "west" else bearing <= 180


async def timed(name, coro, trace):
    t0 = time.perf_counter()
    try:
        return await coro
    finally:
        trace.append({"agent": name, "ms": int((time.perf_counter() - t0) * 1000)})


def _session(sid):
    sid = sid or uuid.uuid4().hex[:12]
    s = SESSIONS.get(sid)
    if s is None:
        s = SESSIONS[sid] = {}
        while len(SESSIONS) > 500:
            SESSIONS.popitem(last=False)
    else:
        SESSIONS.move_to_end(sid)
    return sid, s


async def fetch_bundle(pt, scenario=None):
    marine, weather = await asyncio.gather(data.get_marine(*pt, scenario), data.get_weather(*pt, scenario))
    return {"hours": data.merge(marine, weather), "mode": data.worst(marine.mode, weather.mode),
            "marine": marine, "weather": weather}


# ------------------------------------------------------------------ planner
def plan_question(inp: ChatIn, sess: dict) -> dict:
    text = inp.message.lower()
    intents = [k for k, w in KW.items() if _has(text, w, prefix=True)]
    primary = next((k for k in ("boundary", "route", "tide", "safety", "fishing", "alerts") if k in intents), None)
    followup = False
    if primary is None:
        primary, followup = (sess["primary"], True) if sess.get("primary") else ("conditions", False)
    day = 2 if _has(text, DAY2) else 1 if _has(text, DAY1) else 0 if _has(text, DAY0) else sess.get("day", 0)
    key = ref.resolve_place(inp.message) or ref.resolve_place(inp.place) or sess.get("place")
    if not key and inp.lat is not None and inp.lon is not None:
        key = ref.nearest_place(inp.lat, inp.lon)
    assumed = key is None
    key = key or ref.resolve_place(settings.default_place) or "veraval"
    m = re.search(r"(\d{1,3})\s*(?:km|किमी|કિમી|கி\.?\s?மீ)", text)
    dist = min(200, max(1, int(m.group(1)))) if m else 20
    return {"primary": primary, "followup": followup, "day": day, "place_key": key, "assumed": assumed, "dist_km": dist}


# ------------------------------------------------------------------ specialist agents
def geo_agent(place, inp: ChatIn):
    out = {"landing_centre": {"lat": place["harbour"][0], "lon": place["harbour"][1]},
           "forecast_point": {"lat": place["offshore"][0], "lon": place["offshore"][1]}}
    if inp.lat is not None and inp.lon is not None:
        u = (inp.lat, inp.lon)
        b = geo.bearing_deg(u, place["harbour"])
        out["user_to_landing_centre"] = {"distance_km": round(geo.haversine_km(u, place["harbour"]), 1),
                                         "bearing_deg": round(b), "compass": geo.compass(b)}
    return out


def geofence_agent(place, inp: ChatIn):
    from_user = inp.lat is not None and inp.lon is not None
    pt = (inp.lat, inp.lon) if from_user else place["offshore"]
    hits = ref.nearest_features(pt)
    return {"from": "user_position" if from_user else "forecast_point", "point": {"lat": pt[0], "lon": pt[1]},
            "level": ref.proximity_level(hits), "nearest": hits[:3],
            "alert_within_km": settings.boundary_alert_km}


async def pfz_agent(place_key):
    """Satellite-derived candidate zones when the EO layer works; otherwise clearly-labelled sample zones."""
    res = await eo.get_eo(place_key)
    if res.get("available"):
        return {"zones": res["zones"], "is_sample": False, "eo": res}
    return {"zones": ref.pfz_zones(place_key), "is_sample": True, "eo": res}


async def _route_option(place, dist, brg, day, scenario):
    start = place["harbour"]
    end, mid = geo.destination(start, brg, dist), geo.destination(start, brg, dist / 2)
    pts = [("Departure (nearshore)", place["offshore"]), ("Midpoint", mid), ("Furthest point", end)]
    bundles = await asyncio.gather(*[fetch_bundle(p, scenario) for _, p in pts])
    samples, levels, waves, winds = [], [], [], []
    for (name, p), b in zip(pts, bundles):
        out, ret = risk.assess(data.window(b["hours"], day, 5, 12)), risk.assess(data.window(b["hours"], day, 12, 20))
        levels += [out["level"], ret["level"]]
        for a in (out, ret):
            waves.append(a["metrics"].get("wave_m_max"))
            winds.append(a["metrics"].get("wind_kn_max"))
        samples.append({"name": name, "lat": round(p[0], 4), "lon": round(p[1], 4), "data_mode": b["mode"],
                        "outbound": {"window": "05:00-12:00", "level": out["level"], **out["metrics"]},
                        "return": {"window": "12:00-20:00", "level": ret["level"], **ret["metrics"]}})
    line = geo.interpolate(start, end, 24)
    agg = {}
    for p in line:
        for h in ref.nearest_features(p):
            a = agg.get(h["id"])
            if a is None:
                agg[h["id"]] = dict(h)
            else:
                ins = a["inside"] or h["inside"]
                if h["distance_km"] < a["distance_km"]:
                    a.update(h)
                a["inside"] = ins
    hits = sorted(agg.values(), key=lambda x: x["distance_km"])
    b_level = ref.proximity_level(hits)
    cond = risk.combine(*levels)
    waves, winds = [w for w in waves if w is not None], [w for w in winds if w is not None]
    return {"bearing_deg": round(brg), "compass": geo.compass(brg), "distance_km": dist, "samples": samples,
            "conditions_level": cond, "boundary": {"level": b_level, "nearest": hits[:3]},
            "overall_level": risk.combine(cond, b_level), "wave_m_max": max(waves) if waves else None,
            "wind_kn_max": max(winds) if winds else None,
            "data_mode": data.worst(*[s["data_mode"] for s in samples]),
            "line": [[round(a, 4), round(b, 4)] for a, b in line]}


def _rank(level):
    return risk.LEVELS.index(level) if level in risk.LEVELS else 1


async def route_agent(place, dist, bearing, day, scenario=None):
    if not sea_side(place, bearing):
        raise ValueError(f"bearing {bearing:.0f}° points inland from {place['display']}")
    cands = [bearing] + [b for b in ((bearing - 30) % 360, (bearing + 30) % 360) if sea_side(place, b)]
    options = await asyncio.gather(*[_route_option(place, dist, b, day, scenario) for b in cands])
    primary = options[0]
    best = min(options, key=lambda o: (_rank(o["overall_level"]), o["wave_m_max"] or 0))
    better = best is not primary and _rank(best["overall_level"]) < _rank(primary["overall_level"])
    primary["alternatives"] = [{k: o[k] for k in ("bearing_deg", "compass", "overall_level", "wave_m_max", "wind_kn_max")}
                               | {"boundary_level": o["boundary"]["level"]} for o in options]
    primary["recommended_bearing"] = best["bearing_deg"] if better else None
    primary["method_note"] = ("Conditions sampled at 3 points (~8 km forecast grid); boundary check uses demo/illustrative "
                              "geometry unless real GeoJSON is loaded. Not a navigation tool.")
    return primary


# ------------------------------------------------------------------ alerts
def _alert_kind(metric):
    return "sea" if metric == "wave_height" else "weather"


_TITLES = {"wave_height": "High waves and rough seas", "wind_speed": "Strong winds", "wind_gust": "Strong wind gusts",
           "thunderstorm": "Thunderstorm / lightning risk"}


async def build_alerts(region="all", kind="all", days=(0, 1), scenario=None, include_samples=True):
    places = [p for p in ref.PLACES.values() if region in ("all", p["coast"])]
    bundles = await asyncio.gather(*[fetch_bundle(p["offshore"], scenario) for p in places])
    best: dict = {}
    for p, b in zip(places, bundles):
        for d in days:
            a = risk.assess(data.window(b["hours"], d, only_future=True))
            for r in a["reasons"]:
                k = _alert_kind(r["metric"])
                key = (p["key"], d, k)
                if key not in best or _rank(r["level"]) > _rank(best[key]["severity"]):
                    detail = (f"Forecast peak {r['value']} {r['unit']} (caution above {r['caution_above']}, unsafe above "
                              f"{r['unsafe_above']}); rule set {risk.RULE_SET}." if r["caution_above"] is not None
                              else f"Thunderstorm forecast (WMO code {r['value']}); rule set {risk.RULE_SET}.")
                    best[key] = {"id": f"{p['key']}-d{d}-{k}", "kind": k, "severity": r["level"],
                                 "title": _TITLES[r["metric"]], "area": p["display"], "region": p["coast"],
                                 "day": d, "peak_at": r["at"], "valid_from": a["first_breach"],
                                 "valid_to": a["last_breach"], "detail": detail,
                                 "source": f"ORCA rule engine on {b['marine'].source if k == 'sea' else b['weather'].source}",
                                 "data_mode": b["mode"], "is_sample": False}
    alerts = sorted(best.values(), key=lambda x: (-_rank(x["severity"]), x["day"], x["area"]))
    if kind != "all":
        alerts = [a for a in alerts if a["kind"] == kind]
    if include_samples and kind in ("all", "weather"):
        alerts.append({"id": "sample-cyclone", "kind": "weather", "severity": "sample",
                       "title": "SAMPLE — how a cyclone warning would appear", "area": "Set by the IMD bulletin",
                       "region": region, "day": None, "peak_at": None, "valid_from": None, "valid_to": None,
                       "detail": "IMD cyclone bulletins have no public API and are not connected. This item only "
                                 "demonstrates the alert format.",
                       "source": "None (format example)", "data_mode": "mock", "is_sample": True})
    modes = [b["mode"] for b in bundles]
    return {"region": region, "kind": kind, "alerts": alerts, "data_mode": data.worst(*modes) if modes else "live",
            "generated_at": data.datetime.now(data.IST).isoformat(timespec="seconds"), "disclaimer": DISCLAIMER}


# ------------------------------------------------------------------ explainability
def evidence_for(verdict, marine, weather, place, pt):
    if verdict["level"] == "unknown":
        return []
    m, at = verdict["metrics"], {p["metric"]: p["at"] for p in verdict["peaks"]}
    loc = {"name": f"Forecast point off {place['names']['en']}", "lat": pt[0], "lon": pt[1]}

    def item(label, value, unit, when, s):
        return {"label": label, "value": value, "unit": unit, "at": when, "source": s.source, "data_mode": s.mode,
                "fetched_at": s.fetched_at, "location": loc}

    ev = [item("Highest wave height", m["wave_m_max"], "m", at.get("wave_height"), marine),
          item("Strongest wind", m["wind_kn_max"], "kn", at.get("wind_speed"), weather),
          item("Strongest gust", m["gust_kn_max"], "kn", at.get("wind_gust"), weather),
          item("Mean sea surface temperature", m["sst_c_mean"], "°C", None, marine),
          item("Thunderstorm forecast", "yes" if m["lightning"] else "no", None, at.get("thunderstorm"), weather)]
    return [e for e in ev if e["value"] is not None]


def _compose(lang, mode, plan, place, verdict, extras, data_mode="live"):
    name = place["names"][lang]
    parts = [L.t(lang, "ask_place", place=name)] if plan["assumed"] else []
    lvl = verdict["level"]
    parts.append(L.t(lang, f"head_{lvl}", place=name, day=L.T[lang]["days"][plan["day"]]))
    if lvl != "unknown":
        m = verdict["metrics"]
        parts.append(L.t(lang, "detail", wave=L.num(m["wave_m_max"]), wind=L.num(m["wind_kn_max"], 0),
                         gust=L.num(m["gust_kn_max"], 0)))
        if mode == "technical":
            parts.append(L.t(lang, "tech", swell=L.num(m["swell_m_max"]), period=L.num(m["period_s_at_max_wave"]),
                             sst=L.num(m["sst_c_mean"])))
    note = [L.t(lang, f"note_{data_mode}")] if data_mode in ("mock", "cached") else []
    return " ".join(parts + extras + [L.t(lang, "advisory")] + note)


# ------------------------------------------------------------------ chat orchestration
async def handle_chat(inp: ChatIn) -> dict:
    t_all, trace = time.perf_counter(), []
    sid, sess = _session(inp.session_id)
    detected = L.detect_language(inp.message)
    lang = detected if detected != "en" else (L.norm_lang(inp.language) or "en")

    t0 = time.perf_counter()
    plan = plan_question(inp, sess)
    trace.append({"agent": "planner", "ms": int((time.perf_counter() - t0) * 1000)})
    place, primary, day = ref.PLACES[plan["place_key"]], plan["primary"], plan["day"]
    pt, scen = place["offshore"], inp.scenario

    jobs = {"weather": timed("weather", data.get_weather(*pt, scen), trace),
            "ocean": timed("ocean", data.get_marine(*pt, scen), trace)}
    if primary == "fishing":
        jobs["pfz"] = timed("pfz", pfz_agent(plan["place_key"]), trace)
    if primary == "route":
        bearing = default_bearing(place)
        jobs["route"] = timed("route", route_agent(place, plan["dist_km"], bearing, day, scen), trace)
    got = dict(zip(jobs, await asyncio.gather(*jobs.values())))
    weather, marine = got["weather"], got["ocean"]

    t0 = time.perf_counter()
    geospatial = geo_agent(place, inp)
    trace.append({"agent": "geospatial", "ms": int((time.perf_counter() - t0) * 1000)})
    fence = None
    if primary == "boundary":
        t0 = time.perf_counter()
        fence = geofence_agent(place, inp)
        trace.append({"agent": "geofence", "ms": int((time.perf_counter() - t0) * 1000)})

    t0 = time.perf_counter()
    hours = data.merge(marine, weather)
    verdict = risk.assess(data.window(hours, day, only_future=True))
    mode_all = data.worst(marine.mode, weather.mode)
    trace.append({"agent": "risk", "ms": int((time.perf_counter() - t0) * 1000)})

    t0 = time.perf_counter()
    evidence = evidence_for(verdict, marine, weather, place, pt)
    extras, zones, route = [], [], got.get("route")
    name = place["names"][lang]
    if primary == "fishing":
        pfz = got["pfz"]
        zones, e = pfz["zones"], pfz["eo"]
        if pfz["is_sample"]:
            extras.append(L.t(lang, "pfz", place=name, n=len(zones), km=zones[0]["distance_km"], dir=zones[0]["compass"]))
            evidence.append({"label": "Nearest sample fishing zone", "value": zones[0]["distance_km"], "unit": "km",
                             "at": None, "source": "ORCA sample data (NOT an INCOIS advisory)", "data_mode": "mock",
                             "fetched_at": None, "location": geospatial["landing_centre"]})
        else:
            obs = e["chl"]["obs_time"][:10]
            mode_all = data.worst(mode_all, e["data_mode"])
            if zones:
                extras.append(L.t(lang, "eo", place=name, date=obs, n=len(zones), km=zones[0]["distance_km"], dir=zones[0]["compass"]))
                evidence.append({"label": "Nearest satellite-derived candidate zone", "value": zones[0]["distance_km"], "unit": "km",
                                 "at": e["chl"]["obs_time"], "source": f"{e['chl']['dataset']} chlorophyll + {e['sst']['dataset']} SST (heuristic)",
                                 "data_mode": e["data_mode"], "fetched_at": e.get("fetched_at"), "location": geospatial["landing_centre"]})
            else:
                extras.append(L.t(lang, "eo_none", place=name, date=obs))
            evidence.append({"label": "Mean chlorophyll in search box", "value": e["chl"]["mean_mg_m3"], "unit": "mg/m³",
                             "at": e["chl"]["obs_time"], "source": e["chl"]["dataset"], "data_mode": e["data_mode"],
                             "fetched_at": e.get("fetched_at"), "location": geospatial["landing_centre"]})
    if primary == "boundary" and fence["nearest"]:
        n0 = fence["nearest"][0]
        extras.append(L.t(lang, "boundary_inside" if n0["inside"] else "boundary", name=n0["name"], km=n0["distance_km"]))
        evidence.append({"label": "Distance to nearest demo boundary feature", "value": n0["distance_km"], "unit": "km",
                         "at": None, "source": "ORCA boundary layer (illustrative unless real GeoJSON is loaded)",
                         "data_mode": "mock" if n0["is_illustrative"] else "live", "fetched_at": None,
                         "location": fence["point"]})
    if primary == "alerts":
        n = len(verdict["reasons"])
        extras.append(L.t(lang, "alerts_n" if n else "alerts_none", place=name, n=n))
    tide = []
    if primary == "tide":
        tide = data.tide_extrema(data.window(hours, day, only_future=True))
        if tide:
            items = ", ".join(f"{'high' if x['kind'] == 'high' else 'low'} {x['at'][11:16]} ({x['height_m']:+.1f} m)" for x in tide[:4])
            extras.append(L.t(lang, "tide", items=items))
            evidence.append({"label": "Model tide extremes", "value": len(tide), "unit": "events", "at": tide[0]["at"],
                             "source": marine.source + " (sea_level_height_msl)", "data_mode": marine.mode,
                             "fetched_at": marine.fetched_at, "location": {"name": "Forecast point", "lat": pt[0], "lon": pt[1]}})
    if primary == "route" and route:
        extras.append(L.t(lang, "route", place=name, dist=route["distance_km"], dir=route["compass"],
                          wave=L.num(route["wave_m_max"])))
        if route["recommended_bearing"] is not None:
            extras.append(L.t(lang, "route_better", brg=route["recommended_bearing"],
                              dir=geo.compass(route["recommended_bearing"])))
        mode_all = data.worst(mode_all, route["data_mode"])
    answer = _compose(lang, inp.mode, plan, place, verdict, extras, mode_all)
    trace.append({"agent": "explainability", "ms": int((time.perf_counter() - t0) * 1000)})

    source = "template"
    if llm.enabled():
        new = await timed("language_llm", llm.rephrase(answer, lang, inp.mode), trace)
        if new:
            answer, source = new, "llm"

    sess.update(place=plan["place_key"], day=day, primary=primary)
    return {
        "session_id": sid, "language": lang, "detected_language": detected, "intent": primary,
        "followup": plan["followup"],
        "place": {"key": place["key"], "name": place["display"], "assumed": plan["assumed"]},
        "day": day, "day_label": L.T["en"]["days"][day],
        "verdict": {k: verdict[k] for k in ("level", "label", "reasons", "first_breach", "last_breach", "rule_set", "metrics")},
        "answer": answer, "answer_source": source, "evidence": evidence,
        "confidence": risk.confidence(mode_all, day),
        "rules": {"rule_set": risk.RULE_SET, "thresholds": risk.THRESHOLDS,
                  "note": "Demo thresholds; replace with official IMD/INCOIS criteria."},
        "data_mode": mode_all, "data_notes": [s.note for s in (marine, weather) if s.note],
        "geospatial": geospatial, "geofence": fence, "route": route,
        "pfz": {"is_sample": pfz["is_sample"], "zones": zones, "eo": pfz["eo"]} if primary == "fishing" else None,
        "tide": {"extrema": tide, "note": TIDE_NOTE} if primary == "tide" else None,
        "map": {"center": [pt[0], pt[1]],
                "markers": [{"name": place["display"], "kind": "landing_centre", **geospatial["landing_centre"]},
                            {"name": "Forecast point", "kind": "forecast_point", **geospatial["forecast_point"]}],
                "zones": [z["polygon"] for z in zones],
                "boundaries": ({"type": "FeatureCollection", "features": ref.load_features()} if primary == "boundary" else None),
                "route": route["line"] if route else None},
        "trace": trace, "total_ms": int((time.perf_counter() - t_all) * 1000), "disclaimer": DISCLAIMER,
    }


# ------------------------------------------------------------------ briefing
async def build_briefing(place_key, lang="en", mode="simple", scenario=None):
    place = ref.PLACES[place_key]
    b, pz = await asyncio.gather(fetch_bundle(place["offshore"], scenario), pfz_agent(place_key))
    v = risk.assess(data.window(b["hours"], 0, only_future=True))
    name = place["names"][lang]
    plan = {"day": 0, "assumed": False}
    text = f"{L.t(lang, 'greeting', place=name)} {_compose(lang, mode, plan, place, v, [], b['mode'])}"
    return {
        "place": {"key": place_key, "name": place["display"]}, "language": lang, "text": text,
        "audio": None, "audio_note": "Voice briefing not implemented (needs Bhashini TTS).",
        "sections": {
            "conditions": {"level": v["level"], "metrics": v["metrics"], "data_mode": b["mode"],
                           "fetched_at": b["marine"].fetched_at},
            "warnings": {"items": v["reasons"], "data_mode": b["mode"]},
            "pfz": {"is_sample": pz["is_sample"], "zones": pz["zones"],
                    "note": "Sample zones, not an INCOIS bulletin." if pz["is_sample"] else "Satellite-derived candidate zones (heuristic), not an INCOIS bulletin."},
        },
        "confidence": risk.confidence(b["mode"], 0), "data_mode": b["mode"], "disclaimer": DISCLAIMER,
        "generated_at": data.datetime.now(data.IST).isoformat(timespec="seconds"),
    }
