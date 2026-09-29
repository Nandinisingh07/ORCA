"""Run ONCE with internet before the demo: saves real Open-Meteo forecasts to ./cache so the backend can
serve them (data_mode="cached") if venue wifi dies.   python -m scripts.warm_cache"""
import asyncio
import sys

from app import data, reference as ref
from app.config import settings


async def main() -> int:
    settings.force_mock = False
    bad = 0
    for key, p in ref.PLACES.items():
        m, w = await asyncio.gather(data.get_marine(*p["offshore"]), data.get_weather(*p["offshore"]))
        ok = m.mode == "live" and w.mode == "live"
        bad += not ok
        print(f"{key:15s} marine={m.mode:6s} weather={w.mode:6s} {'' if ok else '<-- ' + str(m.note or w.note)}")
    print("\nAll live and cached." if not bad else f"\n{bad} place(s) not live. Check internet / coordinates.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
