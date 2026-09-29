"""Forecast data layer: Open-Meteo (live) -> disk cache (stale-if-error) -> bundled synthetic sample.

Every result carries a provenance mode so the UI/answers never present fallback data as live:
  live   = fetched from Open-Meteo (or a cache hit younger than CACHE_TTL_MIN)
  cached = live source failed; last real response from disk is served (fetched_at shows its age)
  mock   = nothing real available (or FORCE_MOCK / ?scenario=); synthetic sample, NOT a forecast
"""
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from .config import settings

IST = ZoneInfo("Asia/Kolkata")
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_VARS = "wave_height,wave_period,wave_direction,swell_wave_height,sea_surface_temperature,sea_level_height_msl"
WEATHER_VARS = "wind_speed_10m,wind_gusts_10m,weather_code,precipitation_probability"
SOURCES = {"marine": "Open-Meteo Marine API", "weather": "Open-Meteo Weather API"}
MODE_RANK = {"live": 0, "cached": 1, "mock": 2}

_transport = None  # tests inject httpx.MockTransport here
_mem: dict[str, dict] = {}
last_live_ok: dict[str, str] = {}


@dataclass
class Series:
    hours: list
    mode: str
    fetched_at: str | None
    source: str
    note: str | None = None


def worst(*modes: str) -> str:
    return max(modes, key=lambda m: MODE_RANK[m])


# ---------------- cache ----------------
def _key(kind, lat, lon):
    return f"{kind}_{lat:.2f}_{lon:.2f}"


def _read(key):
    if key in _mem:
        return _mem[key]
    p = settings.cache_dir / f"{key}.json"
    if p.exists():
        try:
            _mem[key] = json.loads(p.read_text())
            return _mem[key]
        except Exception:
            return None
    return None


def _write(key, entry):
    _mem[key] = entry
    try:
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        (settings.cache_dir / f"{key}.json").write_text(json.dumps(entry))
    except Exception:
        pass  # cache is best-effort


def _age_s(entry):
    return (datetime.now(timezone.utc) - datetime.fromisoformat(entry["fetched_at"])).total_seconds()


# ---------------- remote ----------------
def _v(h, k, i):
    arr = h.get(k)
    return arr[i] if arr and i < len(arr) else None


async def _remote(kind, lat, lon):
    params = {"latitude": round(lat, 4), "longitude": round(lon, 4), "timezone": "Asia/Kolkata", "forecast_days": 3}
    if kind == "marine":
        url, params["hourly"] = MARINE_URL, MARINE_VARS
    else:
        url, params["hourly"], params["wind_speed_unit"] = WEATHER_URL, WEATHER_VARS, "kn"
    async with httpx.AsyncClient(timeout=settings.http_timeout, transport=_transport) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        h = (r.json().get("hourly")) or {}
    out = []
    for i, t in enumerate(h.get("time") or []):
        if kind == "marine":
            out.append({"t": t, "wave_m": _v(h, "wave_height", i), "wave_period_s": _v(h, "wave_period", i),
                        "wave_dir": _v(h, "wave_direction", i), "swell_m": _v(h, "swell_wave_height", i),
                        "sst_c": _v(h, "sea_surface_temperature", i),
                        "tide_m": _v(h, "sea_level_height_msl", i)})
        else:
            out.append({"t": t, "wind_kn": _v(h, "wind_speed_10m", i), "gust_kn": _v(h, "wind_gusts_10m", i),
                        "wcode": _v(h, "weather_code", i), "precip_pct": _v(h, "precipitation_probability", i)})
    probe = "wave_m" if kind == "marine" else "wind_kn"
    return out if any(x[probe] is not None for x in out) else []  # all-null => land cell / no coverage


# ---------------- synthetic sample ----------------
def _mock(kind, lat, lon, scenario):
    today = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    seed = int(abs(lat) * 10) + int(abs(lon) * 10)
    base_w = {"calm": 0.7, "rough": 3.2, "storm": 4.6}.get(scenario, 0.9 + (seed % 7) * 0.12)
    base_wind = {"calm": 6, "rough": 24, "storm": 36}.get(scenario, 8 + (seed % 5) * 1.5)
    hours = []
    for i in range(72):
        t, day = today + timedelta(hours=i), i // 24
        diurnal = math.sin(2 * math.pi * (t.hour - 8) / 24)
        ts = t.strftime("%Y-%m-%dT%H:%M")
        if kind == "marine":
            wave = max(0.2, base_w * (1 + 0.25 * diurnal) + 0.1 * day)
            hours.append({"t": ts, "wave_m": round(wave, 2), "wave_period_s": round(6 + wave, 1), "wave_dir": 250.0,
                          "swell_m": round(wave * 0.7, 2), "sst_c": round(29.0 - abs(lat - 12) * 0.08 + 0.2 * diurnal, 1),
                          "tide_m": round(0.9 * math.sin(2 * math.pi * i / 12.42), 2)})
        else:
            wind = max(1.0, base_wind * (1 + 0.3 * diurnal))
            wcode = 95 if scenario == "storm" and day == 1 and 15 <= t.hour <= 20 else (61 if scenario in ("rough", "storm") else 3)
            hours.append({"t": ts, "wind_kn": round(wind, 1), "gust_kn": round(wind * 1.35, 1), "wcode": wcode,
                          "precip_pct": 80 if wcode in (95, 61) else 20})
    note = f"scenario={scenario}" if scenario else "synthetic sample"
    return Series(hours, "mock", None, "ORCA bundled sample (synthetic)", note)


# ---------------- public API ----------------
async def _get(kind, lat, lon, scenario=None):
    if (scenario and settings.demo_scenarios) or settings.force_mock:
        return _mock(kind, lat, lon, scenario if settings.demo_scenarios else None)
    key = _key(kind, lat, lon)
    entry = _read(key)
    if entry and _age_s(entry) <= settings.cache_ttl_s:
        return Series(entry["hours"], "live", entry["fetched_at"], SOURCES[kind])
    try:
        hours = await _remote(kind, lat, lon)
        if not hours:
            raise ValueError("no usable data for this grid cell")
        entry = {"fetched_at": datetime.now(timezone.utc).isoformat(), "hours": hours}
        _write(key, entry)
        last_live_ok[kind] = entry["fetched_at"]
        return Series(hours, "live", entry["fetched_at"], SOURCES[kind])
    except Exception as e:  # network, HTTP status, parse: always degrade, never crash the demo
        note = f"{type(e).__name__}: {e}"[:160]
        if entry and _age_s(entry) <= settings.stale_max_s:
            return Series(entry["hours"], "cached", entry["fetched_at"], SOURCES[kind], note)
        s = _mock(kind, lat, lon, None)
        s.note = f"live fetch failed ({note}); showing synthetic sample"
        return s


async def get_marine(lat, lon, scenario=None) -> Series:
    return await _get("marine", lat, lon, scenario)


async def get_weather(lat, lon, scenario=None) -> Series:
    return await _get("weather", lat, lon, scenario)


def merge(marine: Series, weather: Series):
    w = {h["t"]: h for h in weather.hours}
    return [{**m, **{k: v for k, v in w.get(m["t"], {}).items() if k != "t"}} for m in marine.hours]


def day_date(offset: int):
    return (datetime.now(IST) + timedelta(days=offset)).date()


def window(hours, day_offset=0, start=0, end=24, only_future=False):
    d = day_date(day_offset).isoformat()
    sel = [h for h in hours if h["t"][:10] == d and start <= int(h["t"][11:13]) < end]
    if only_future and day_offset == 0:
        now_s = datetime.now(IST).strftime("%Y-%m-%dT%H:00")
        sel = [h for h in sel if h["t"] >= now_s] or sel
    return sel


async def probe(kind="marine", lat=20.85, lon=70.20):
    """Uncached live check used by /api/health?deep=true."""
    t0 = datetime.now()
    try:
        ok = bool(await _remote(kind, lat, lon))
        err = None if ok else "reachable but no usable data"
    except Exception as e:
        ok, err = False, f"{type(e).__name__}: {e}"[:160]
    return {"source": SOURCES[kind], "ok": ok, "latency_ms": int((datetime.now() - t0).total_seconds() * 1000), "error": err}


def tide_extrema(hours):
    """High/low water from the hourly sea_level_height_msl series (model-derived, ~8 km grid)."""
    pts = [(h["t"], h["tide_m"]) for h in hours if h.get("tide_m") is not None]
    out = []
    for (t0, a), (t1, b), (t2, c) in zip(pts, pts[1:], pts[2:]):
        if b > a and b >= c:
            out.append({"kind": "high", "at": t1, "height_m": b})
        elif b < a and b <= c:
            out.append({"kind": "low", "at": t1, "height_m": b})
    return out
