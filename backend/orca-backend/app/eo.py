"""Satellite Earth-Observation layer: chlorophyll-a (VIIRS) + sea-surface temperature (MUR) via NOAA CoastWatch ERDDAP.

Datasets (dataset pages checked 29 Sep 2026; live queries could NOT be tested from the build sandbox):
  chlorophyll : nesdisVHNnoaa20chlaDaily  var chlor_a   (NOAA-20 VIIRS, near-real-time, 4 km daily, dims time/altitude/latitude(desc)/longitude)
  SST         : jplMURSST41               var analysed_sst
Chlorophyll is cloud-gapped and lags real time, so we take the most recent day inside a look-back window that has enough
valid pixels and report that observation date. If nothing usable is found, we say so instead of inventing data.

The "candidate zones" are a transparent HEURISTIC (high chlorophyll, ranked up by SST-front strength). They are NOT INCOIS
PFZ advisories and thresholds are demo values (EO_CHL_HIGH, ...). Validate against INCOIS PFZ before any real use.
"""
import math
import os
from bisect import bisect_left
from datetime import datetime, timezone

import httpx

from . import data, geo
from . import reference as ref
from .config import settings

ERDDAP_BASE = os.getenv("ERDDAP_BASE", "https://coastwatch.pfeg.noaa.gov/erddap/griddap").rstrip("/")
CHL_DS, CHL_VAR = os.getenv("EO_CHL_DATASET", "nesdisVHNnoaa20chlaDaily"), "chlor_a"
SST_DS, SST_VAR = os.getenv("EO_SST_DATASET", "jplMURSST41"), "analysed_sst"
CHL_HIGH = float(os.getenv("EO_CHL_HIGH", "0.5"))          # mg m^-3, demo threshold
MIN_VALID = float(os.getenv("EO_MIN_VALID_FRACTION", "0.15"))
LOOKBACK = int(os.getenv("EO_LOOKBACK_DAYS", "7"))
HALF_DEG = float(os.getenv("EO_BOX_HALF_DEG", "1.0"))
CACHE_S = int(float(os.getenv("EO_CACHE_HOURS", "6")) * 3600)
BIN_DEG = 0.2
METHOD = ("Heuristic: 0.2° cells with >=3 pixels above the chlorophyll threshold, ranked by chlorophyll boosted by local "
          "SST-gradient (front) strength. Demo thresholds; not the INCOIS PFZ algorithm.")


async def _griddap(ds, var, dims):
    url = f"{ERDDAP_BASE}/{ds}.json?{var}{dims}"
    async with httpx.AsyncClient(timeout=settings.http_timeout * 3, transport=data._transport, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        t = r.json()["table"]
    cols = t["columnNames"]
    units = dict(zip(cols, t.get("columnUnits") or []))
    return [dict(zip(cols, row)) for row in t["rows"]], units, url


def _age_days(iso):
    return round((datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 86400, 1)


def _pick_chl(rows):
    by_t = {}
    for r in rows:
        by_t.setdefault(r["time"], []).append(r)
    for t in sorted(by_t, reverse=True):
        cells = by_t[t]
        valid = [c for c in cells if c.get(CHL_VAR) is not None]
        if cells and len(valid) / len(cells) >= MIN_VALID:
            return t, valid, len(valid) / len(cells)
    return None, [], 0.0


def _sst_grid(rows, units):
    to_c = (lambda v: v - 273.15) if "K" in (units.get(SST_VAR) or "").upper() and "C" not in (units.get(SST_VAR) or "").upper() else (lambda v: v)
    g = {(r["latitude"], r["longitude"]): to_c(r[SST_VAR]) for r in rows if r.get(SST_VAR) is not None}
    lats, lons = sorted({k[0] for k in g}), sorted({k[1] for k in g})
    grad = {}
    for i in range(1, len(lats) - 1):
        for j in range(1, len(lons) - 1):
            la, lo = lats[i], lons[j]
            n = [g.get((lats[i - 1], lo)), g.get((lats[i + 1], lo)), g.get((la, lons[j - 1])), g.get((la, lons[j + 1]))]
            if None in n:
                continue
            dy = (lats[i + 1] - lats[i - 1]) * 110.574
            dx = (lons[j + 1] - lons[j - 1]) * 111.32 * math.cos(math.radians(la))
            grad[(la, lo)] = math.hypot((n[3] - n[2]) / dx, (n[1] - n[0]) / dy)
    return g, grad, lats, lons


def _nearest(arr, v):
    i = bisect_left(arr, v)
    return min(arr[max(0, i - 1): i + 1], key=lambda a: abs(a - v)) if arr else None


def analyse(chl_rows, sst_rows, sst_units, harbour):
    t, valid, frac = _pick_chl(chl_rows)
    if not valid:
        return {"available": False, "reason": f"no recent chlorophyll day with >= {int(MIN_VALID * 100)}% valid pixels "
                                              f"in the last {LOOKBACK} days (cloud cover or processing lag)"}
    g, grad, lats, lons = _sst_grid(sst_rows, sst_units)
    gvals = sorted(grad.values())
    pos = [v for v in gvals if v > 0]   # a sparse front must not make the normaliser 0
    p90 = pos[int(0.9 * (len(pos) - 1))] if pos else 0.0
    chl_vals = [c[CHL_VAR] for c in valid]
    bins = {}
    for c in valid:
        if c[CHL_VAR] < CHL_HIGH:
            continue
        la, lo = c["latitude"], c["longitude"]
        nla, nlo = _nearest(lats, la), _nearest(lons, lo)
        gr = grad.get((nla, nlo), 0.0) if nla is not None else 0.0
        boost = 1 + (min(gr / p90, 1.0) if p90 > 0 else 0.0)
        b = bins.setdefault((math.floor(la / BIN_DEG), math.floor(lo / BIN_DEG)), [])
        b.append((la, lo, c[CHL_VAR], g.get((nla, nlo)), gr, c[CHL_VAR] * boost))
    zones = []
    for (bi, bj), cells in bins.items():
        if len(cells) < 3:
            continue
        n = len(cells)
        clat, clon = sum(x[0] for x in cells) / n, sum(x[1] for x in cells) / n
        ssts = [x[3] for x in cells if x[3] is not None]
        brg = geo.bearing_deg(harbour, (clat, clon))
        la0, lo0 = bi * BIN_DEG, bj * BIN_DEG
        zones.append({
            "centre": {"lat": round(clat, 4), "lon": round(clon, 4)},
            "polygon": [[round(la0 + BIN_DEG, 4), round(lo0, 4)], [round(la0 + BIN_DEG, 4), round(lo0 + BIN_DEG, 4)],
                        [round(la0, 4), round(lo0 + BIN_DEG, 4)], [round(la0, 4), round(lo0, 4)]],
            "distance_km": round(geo.haversine_km(harbour, (clat, clon)), 1),
            "bearing_deg": round(brg), "compass": geo.compass(brg),
            "mean_chl_mg_m3": round(sum(x[2] for x in cells) / n, 2), "max_chl_mg_m3": round(max(x[2] for x in cells), 2),
            "sst_c": round(sum(ssts) / len(ssts), 1) if ssts else None,
            "sst_gradient_c_per_km": round(sum(x[4] for x in cells) / n, 3), "cells": n,
            "_score": sum(x[5] for x in cells),
            "is_sample": False, "is_incois_pfz": False,
        })
    zones = sorted(zones, key=lambda z: -z["_score"])[:3]
    for i, z in enumerate(zones, 1):
        z.pop("_score", None)
        z["id"], z["rank"] = f"eo-{i}", i
    return {"available": True,
            "chl": {"dataset": CHL_DS, "obs_time": t, "age_days": _age_days(t), "valid_fraction": round(frac, 2),
                    "mean_mg_m3": round(sum(chl_vals) / len(chl_vals), 2), "max_mg_m3": round(max(chl_vals), 2),
                    "frac_above_threshold": round(sum(v >= CHL_HIGH for v in chl_vals) / len(chl_vals), 2), "units": "mg m^-3"},
            "sst": {"dataset": SST_DS, "mean_c": round(sum(g.values()) / len(g), 1) if g else None,
                    "max_gradient_c_per_km": round(gvals[-1], 3) if gvals else None},
            "thresholds": {"chl_high_mg_m3": CHL_HIGH, "min_valid_fraction": MIN_VALID},
            "zones": zones, "method": METHOD}


async def _fetch(lat, lon):
    lo_lat, hi_lat, w, e = lat - HALF_DEG, lat + HALF_DEG, lon - HALF_DEG, lon + HALF_DEG
    chl_q = f"[last-{LOOKBACK}:1:last][0][({hi_lat:.3f}):({lo_lat:.3f})][({w:.3f}):({e:.3f})]"   # latitude axis is descending
    sst_q = f"[last][({lo_lat:.3f}):5:({hi_lat:.3f})][({w:.3f}):5:({e:.3f})]"
    (chl, _, u1), (sst, su, u2) = (await _griddap(CHL_DS, CHL_VAR, chl_q)), (await _griddap(SST_DS, SST_VAR, sst_q))
    return chl, sst, su, [u1, u2]


async def get_eo(place_key):
    """Cached, never raises. Result always carries available/data_mode (live|cached|mock) and a reason when unavailable."""
    place = ref.PLACES[place_key]
    if settings.force_mock:
        return {"available": False, "data_mode": "mock", "reason": "FORCE_MOCK is on; satellite layer skipped", "zones": []}
    key = f"eo_{place_key}"
    entry = data._read(key)
    if entry and data._age_s(entry) <= CACHE_S:
        return {**entry["result"], "data_mode": "live", "fetched_at": entry["fetched_at"]}
    try:
        chl, sst, su, urls = await _fetch(*place["offshore"])
        res = analyse(chl, sst, su, place["harbour"])
        res["query_urls"] = urls
        if res["available"]:
            ent = {"fetched_at": datetime.now(timezone.utc).isoformat(), "result": res}
            data._write(key, ent)
            return {**res, "data_mode": "live", "fetched_at": ent["fetched_at"]}
        return {**res, "data_mode": "live", "zones": [], "fetched_at": datetime.now(timezone.utc).isoformat()}
    except Exception as ex:
        note = f"{type(ex).__name__}: {ex}"[:200]
        if entry and data._age_s(entry) <= settings.stale_max_s:
            return {**entry["result"], "data_mode": "cached", "fetched_at": entry["fetched_at"], "note": note}
        return {"available": False, "data_mode": "mock", "zones": [], "reason": f"satellite source unreachable ({note})"}

