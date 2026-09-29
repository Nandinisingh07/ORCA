"""Rule-based marine risk engine. NOT an LLM: same numbers in -> same verdict out.

The thresholds below are DEMO values (rule set 'demo-v1'). Replace with official IMD/INCOIS
small-craft criteria before any real use.
"""

RULE_SET = "demo-v1"
LEVELS = ["safe", "caution", "unsafe"]
LABELS = {"safe": "Safe", "caution": "Caution", "unsafe": "Unsafe", "unknown": "Unknown"}
THRESHOLDS = {  # (caution above, unsafe above)
    "wave_height": {"unit": "m", "caution": 1.5, "unsafe": 2.5},
    "wind_speed": {"unit": "kn", "caution": 15.0, "unsafe": 25.0},
    "wind_gust": {"unit": "kn", "caution": 25.0, "unsafe": 35.0},
}
THUNDER = {95: 1, 96: 2, 99: 2}  # WMO weather codes: thunderstorm / with hail


def _lvl(v, thr) -> int:
    return 2 if v > thr["unsafe"] else 1 if v > thr["caution"] else 0


def _hour_checks(h):
    for metric, field in (("wave_height", "wave_m"), ("wind_speed", "wind_kn"), ("wind_gust", "gust_kn")):
        v = h.get(field)
        if v is not None:
            t = THRESHOLDS[metric]
            yield metric, v, t["unit"], _lvl(v, t), t
    code = h.get("wcode")
    if code in THUNDER:
        yield "thunderstorm", code, "wmo_code", THUNDER[code], None


def _num(hours, field, fn=max):
    vals = [h[field] for h in hours if h.get(field) is not None]
    return fn(vals) if vals else None


def assess(hours):
    """hours: list of merged hourly dicts -> verdict dict."""
    if not hours or all(h.get("wave_m") is None and h.get("wind_kn") is None for h in hours):
        return {"level": "unknown", "label": LABELS["unknown"], "reasons": [], "peaks": [], "metrics": {},
                "first_breach": None, "last_breach": None, "rule_set": RULE_SET}
    peaks, breaches = {}, []
    for h in hours:
        hour_lvl = 0
        for metric, v, unit, lvl, thr in _hour_checks(h):
            hour_lvl = max(hour_lvl, lvl)
            cur = peaks.get(metric)
            if cur is None or (lvl, v) > (cur["_l"], cur["value"]):
                peaks[metric] = {"metric": metric, "value": v, "unit": unit, "level": LEVELS[lvl], "_l": lvl,
                                 "at": h["t"], "caution_above": thr["caution"] if thr else None,
                                 "unsafe_above": thr["unsafe"] if thr else None}
        if hour_lvl:
            breaches.append(h["t"])
    for p in peaks.values():
        p.pop("_l")
    overall = max((LEVELS.index(p["level"]) for p in peaks.values()), default=0)
    ordered = sorted(peaks.values(), key=lambda p: -LEVELS.index(p["level"]))
    wave_hour = next((h for h in hours if h.get("wave_m") == _num(hours, "wave_m")), {})
    return {
        "level": LEVELS[overall], "label": LABELS[LEVELS[overall]],
        "reasons": [p for p in ordered if p["level"] != "safe"],
        "peaks": ordered,
        "metrics": {
            "wave_m_max": _num(hours, "wave_m"), "swell_m_max": _num(hours, "swell_m"),
            "period_s_at_max_wave": wave_hour.get("wave_period_s"),
            "wind_kn_max": _num(hours, "wind_kn"), "gust_kn_max": _num(hours, "gust_kn"),
            "sst_c_mean": (round(sum(v) / len(v), 1) if (v := [h["sst_c"] for h in hours if h.get("sst_c") is not None]) else None),
            "precip_pct_max": _num(hours, "precip_pct"),
            "lightning": any(h.get("wcode") in THUNDER for h in hours),
        },
        "first_breach": breaches[0] if breaches else None,
        "last_breach": breaches[-1] if breaches else None,
        "rule_set": RULE_SET,
    }


def combine(*levels: str) -> str:
    known = [l for l in levels if l in LEVELS]
    return LEVELS[max(LEVELS.index(l) for l in known)] if known else "unknown"


def confidence(mode: str, day_offset: int) -> dict:
    """Forecast confidence: degrades with lead time and with weaker data provenance."""
    rank = 0 if day_offset <= 1 else 1 if day_offset == 2 else 2
    if mode == "mock":
        return {"level": "demo", "note": "Bundled synthetic sample data, not a real forecast."}
    if mode == "cached":
        rank = min(2, rank + 1)
    level = ["high", "medium", "low"][rank]
    note = {"live": "Recent forecast fetch.", "cached": "Live source unreachable; showing last saved forecast."}[mode]
    return {"level": level, "note": f"{note} Forecast skill drops with lead time."}
