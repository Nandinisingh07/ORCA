"""Static reference data: coastal places, sample PFZ zones, boundary layers.

IMPORTANT: PFZ zones and the built-in boundary/protected-area geometry are ILLUSTRATIVE SAMPLES
(is_illustrative=true). Drop real GeoJSON (Survey of India / WII / MoEFCC) into data/boundaries/
and the sample geometry is replaced automatically.
"""
import json
import re
from functools import lru_cache

from . import geo
from .config import settings

# harbour = landing-centre reference (approx). offshore = approximate nearshore sea point used to sample
# marine forecasts (harbour cells are land, which the marine API returns as null).
PLACES = {
    "veraval": dict(display="Veraval, Gujarat", coast="west", harbour=(20.91, 70.37), offshore=(20.85, 70.20),
                    names={"en": "Veraval", "hi": "वेरावल", "gu": "વેરાવળ", "ta": "வெராவல்"},
                    aliases=["veraval", "gujarat", "वेरावल", "गुजरात", "વેરાવળ", "ગુજરાત", "வெராவல்"]),
    "mumbai": dict(display="Mumbai, Maharashtra", coast="west", harbour=(18.92, 72.83), offshore=(18.85, 72.65),
                   names={"en": "Mumbai", "hi": "मुंबई", "gu": "મુંબઈ", "ta": "மும்பை"},
                   aliases=["mumbai", "bombay", "maharashtra", "मुंबई", "महाराष्ट्र", "મુંબઈ", "மும்பை"]),
    "panaji": dict(display="Panaji, Goa", coast="west", harbour=(15.50, 73.83), offshore=(15.48, 73.62),
                   names={"en": "Panaji, Goa", "hi": "पणजी, गोवा", "gu": "પણજી, ગોવા", "ta": "பனாஜி, கோவா"},
                   aliases=["panaji", "panjim", "goa", "पणजी", "गोवा", "ગોવા", "கோவா", "பனாஜி"]),
    "kochi": dict(display="Kochi, Kerala", coast="west", harbour=(9.97, 76.27), offshore=(9.95, 76.05),
                  names={"en": "Kochi", "hi": "कोच्चि", "gu": "કોચી", "ta": "கொச்சி"},
                  aliases=["kochi", "cochin", "kerala", "कोच्चि", "कोचीन", "केरल", "કોચી", "கொச்சி", "கேரளா"]),
    "chennai": dict(display="Chennai, Tamil Nadu", coast="east", harbour=(13.08, 80.29), offshore=(13.08, 80.45),
                    names={"en": "Chennai", "hi": "चेन्नई", "gu": "ચેન્નઈ", "ta": "சென்னை"},
                    aliases=["chennai", "madras", "tamil nadu", "चेन्नई", "ચેન્નઈ", "சென்னை"]),
    "visakhapatnam": dict(display="Visakhapatnam, Andhra Pradesh", coast="east", harbour=(17.69, 83.29),
                          offshore=(17.65, 83.45),
                          names={"en": "Visakhapatnam", "hi": "विशाखापत्तनम", "gu": "વિશાખાપટ્ટનમ", "ta": "விசாகப்பட்டினம்"},
                          aliases=["visakhapatnam", "vizag", "vishakhapatnam", "andhra", "विशाखापत्तनम", "વિશાખાપટ્ટનમ",
                                   "விசாகப்பட்டினம்"]),
}
for _k, _p in PLACES.items():
    _p["key"] = _k


def _match(alias: str, text: str) -> bool:
    if alias.isascii():
        return re.search(rf"\b{re.escape(alias)}\b", text) is not None
    return alias in text


def resolve_place(text: str | None):
    """Return a place key for free text ('Veraval, Gujarat', 'Gujarat coast', 'वेरावल'...) or None."""
    if not text:
        return None
    t = text.lower().strip()
    if t in PLACES:
        return t
    for key, p in PLACES.items():
        if any(_match(a, t) for a in p["aliases"]):
            return key
    return None


def nearest_place(lat: float, lon: float, max_km: float = 400):
    key, d = min(((k, geo.haversine_km((lat, lon), p["harbour"])) for k, p in PLACES.items()), key=lambda x: x[1])
    return key if d <= max_km else None


# ---------------- sample PFZ (illustrative) ----------------
def pfz_zones(place_key: str):
    p = PLACES[place_key]
    bearings = (250, 290) if p["coast"] == "west" else (70, 110)
    out = []
    for i, (brg, km) in enumerate(zip(bearings, (28, 46)), start=1):
        c = geo.destination(p["harbour"], brg, km)
        h = 4.0  # half-size of the box, km
        corners = [geo.destination(geo.destination(c, 0, dy), 90, dx) for dy, dx in ((h, -h), (h, h), (-h, h), (-h, -h))]
        out.append({
            "id": f"{place_key}-sample-{i}",
            "centre": {"lat": round(c[0], 4), "lon": round(c[1], 4)},
            "polygon": [[round(a, 4), round(b, 4)] for a, b in corners],
            "distance_km": km,
            "bearing_deg": brg,
            "compass": geo.compass(brg),
            "is_sample": True,
        })
    return out


# ---------------- boundaries ----------------
_SAMPLE = [
    {"type": "Feature",
     "properties": {"id": "demo-ref-line", "name": "Demo reference line (not a real boundary)", "kind": "boundary",
                    "layer": "reference", "is_illustrative": True},
     "geometry": {"type": "LineString", "coordinates": [[69.55, 21.5], [69.5, 19.9]]}},
    {"type": "Feature",
     "properties": {"id": "demo-mpa", "name": "Demo protected area (illustrative)", "kind": "protected",
                    "layer": "protected", "is_illustrative": True},
     "geometry": {"type": "Polygon",
                  "coordinates": [[[70.05, 20.62], [70.20, 20.62], [70.20, 20.80], [70.05, 20.80], [70.05, 20.62]]]}},
]


@lru_cache(maxsize=1)
def load_features():
    feats = []
    if settings.boundary_dir.exists():
        for f in sorted(settings.boundary_dir.glob("*.geojson")):
            try:
                gj = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for ft in gj.get("features", []) if gj.get("type") == "FeatureCollection" else [gj]:
                props = dict(ft.get("properties") or {})
                props.setdefault("id", f"{f.stem}-{len(feats)}")
                props.setdefault("name", f.stem)
                props.setdefault("kind", "boundary")
                props.setdefault("layer", "protected" if props["kind"] == "protected" else "reference")
                props.setdefault("is_illustrative", False)
                props.setdefault("source_file", f.name)
                feats.append({"type": "Feature", "properties": props, "geometry": ft["geometry"]})
    return feats or json.loads(json.dumps(_SAMPLE))


def coastal_features():
    return [{"type": "Feature",
             "properties": {"id": f"lc-{k}", "name": p["display"], "kind": "landing_centre", "layer": "coastal",
                            "is_illustrative": False},
             "geometry": {"type": "Point", "coordinates": [p["harbour"][1], p["harbour"][0]]}}
            for k, p in PLACES.items()]


def _geoms(feature):
    """GeoJSON geometry -> list of (kind, [(lat, lon), ...])."""
    g, t = feature["geometry"], feature["geometry"]["type"]
    sw = lambda coords: [(c[1], c[0]) for c in coords]  # noqa: E731  (lon,lat) -> (lat,lon)
    if t == "LineString":
        return [("line", sw(g["coordinates"]))]
    if t == "MultiLineString":
        return [("line", sw(c)) for c in g["coordinates"]]
    if t == "Polygon":
        return [("poly", sw(g["coordinates"][0])[:-1] if g["coordinates"][0][0] == g["coordinates"][0][-1]
                 else sw(g["coordinates"][0]))]
    if t == "MultiPolygon":
        return [("poly", sw(p[0])[:-1]) for p in g["coordinates"]]
    return []


def nearest_features(pt, features=None):
    """Distance/bearing from pt to every boundary/protected feature, nearest first."""
    out = []
    for f in features or load_features():
        best = None
        for kind, coords in _geoms(f):
            d, near = geo.dist_to_polygon_km(pt, coords) if kind == "poly" else geo.dist_to_line_km(pt, coords)
            if best is None or d < best[0]:
                best = (d, near)
        if best is None:
            continue
        d, near = best
        pr = f["properties"]
        out.append({
            "id": pr["id"], "name": pr["name"], "kind": pr["kind"], "layer": pr["layer"],
            "is_illustrative": pr.get("is_illustrative", False),
            "inside": d == 0.0 and pr["kind"] == "protected",
            "distance_km": round(d, 1),
            "bearing_deg": round(geo.bearing_deg(pt, near)) if d > 0 else None,
            "compass": geo.compass(geo.bearing_deg(pt, near)) if d > 0 else None,
        })
    return sorted(out, key=lambda x: x["distance_km"])


def proximity_level(hits) -> str:
    """safe / caution / unsafe from nearest_features() output (demo thresholds)."""
    if any(h["inside"] for h in hits):
        return "unsafe"
    if hits and hits[0]["distance_km"] <= settings.boundary_alert_km:
        return "caution"
    return "safe"
