"""Verify every real data source from YOUR machine (internet required):  python -m scripts.check_live
Prints PASS/FAIL per source with the exact request and the server's error text, so a wrong dataset ID / query is obvious."""
import asyncio
import sys

import httpx

from app import data, eo, reference as ref
from app.config import settings


async def main() -> int:
    settings.force_mock = False
    settings.cache_dir = settings.cache_dir  # real cache dir, so a passing run also warms the demo cache
    fails = 0

    print("== Open-Meteo marine (waves, swell, SST, tide) and weather (wind, gusts, thunder) ==")
    for key, p in ref.PLACES.items():
        m, w = await asyncio.gather(data.get_marine(*p["offshore"]), data.get_weather(*p["offshore"]))
        tide = [h.get("tide_m") for h in m.hours if h.get("tide_m") is not None]
        ok = m.mode == "live" and w.mode == "live"
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {key:14s} marine={m.mode:6s} weather={w.mode:6s} tide_points={len(tide):3d}"
              + ("" if ok else f"   {m.note or w.note}"))
        if ok and not tide:
            print("       (no tide values here: move this place's 'offshore' point slightly further out in app/reference.py)")

    print("\n== Satellite EO via ERDDAP (chlorophyll VIIRS + MUR SST) ==")
    for key in ref.PLACES:
        try:
            res = await eo.get_eo(key)
        except Exception as e:  # get_eo should never raise; report if it does
            res = {"available": False, "reason": repr(e)}
        if res.get("available"):
            c = res["chl"]
            print(f"  PASS {key:14s} obs {c['obs_time'][:10]} ({c['age_days']} d old) valid={c['valid_fraction']:.0%} "
                  f"mean chl={c['mean_mg_m3']} mg/m3, candidate zones={len(res['zones'])}")
        else:
            fails += 1
            print(f"  FAIL {key:14s} {res.get('reason')}")
            for u in res.get("query_urls", []):
                print("       url:", u)
    print("\nIf EO fails with HTTP 400/404, open the printed url in a browser: ERDDAP returns a plain-text explanation "
          "(bad dataset id, dimension order or time syntax).")
    print("Cloud gaps are normal: 'no recent day with enough valid pixels' means clouds, not a bug (try EO_MIN_VALID_FRACTION=0.05).")

    print("\n== Reachability of official pages (not machine-readable APIs, just up/down) ==")
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
        for name, url in {"INCOIS PFZ advisory page": "https://incois.gov.in/MarineFisheries/PfzAdvisory",
                          "Open-Meteo marine docs": "https://open-meteo.com/en/docs/marine-weather-api"}.items():
            try:
                r = await c.get(url)
                print(f"  {'PASS' if r.status_code < 400 else 'FAIL'} {name}: HTTP {r.status_code}")
            except Exception as e:
                print(f"  FAIL {name}: {type(e).__name__}")
    print(f"\n{'ALL LIVE SOURCES OK' if not fails else str(fails) + ' source(s) failed; see above'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
