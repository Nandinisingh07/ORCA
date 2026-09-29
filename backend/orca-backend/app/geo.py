"""Pure-python geometry helpers (no PostGIS/shapely needed for the demo). Points are (lat, lon)."""
import math

R_KM = 6371.0088
_COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def haversine_km(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R_KM * math.asin(math.sqrt(d))


def bearing_deg(a, b) -> float:
    la1, la2 = math.radians(a[0]), math.radians(b[0])
    dlo = math.radians(b[1] - a[1])
    y = math.sin(dlo) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlo)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def destination(a, bearing: float, km: float):
    d, t = km / R_KM, math.radians(bearing)
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2 = math.asin(math.sin(la1) * math.cos(d) + math.cos(la1) * math.sin(d) * math.cos(t))
    lo2 = lo1 + math.atan2(math.sin(t) * math.sin(d) * math.cos(la1), math.cos(d) - math.sin(la1) * math.sin(la2))
    return (math.degrees(la2), (math.degrees(lo2) + 540) % 360 - 180)


def compass(bearing: float) -> str:
    return _COMPASS[int((bearing + 11.25) // 22.5) % 16]


def interpolate(a, b, n: int):
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]


def _xy(p, ref):
    """Local equirectangular km offsets of p relative to ref (fine for <200 km)."""
    return ((p[1] - ref[1]) * math.cos(math.radians(ref[0])) * 111.32, (p[0] - ref[0]) * 110.574)


def dist_point_segment_km(p, a, b):
    ax, ay = _xy(a, p)
    bx, by = _xy(b, p)
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(cx, cy), (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def dist_to_line_km(p, line):
    best = (float("inf"), line[0])
    for a, b in zip(line, line[1:]):
        d = dist_point_segment_km(p, a, b)
        if d[0] < best[0]:
            best = d
    return best


def point_in_ring(p, ring) -> bool:
    x, y, inside = p[1], p[0], False
    for (la1, lo1), (la2, lo2) in zip(ring, ring[1:] + ring[:1]):
        if (la1 > y) != (la2 > y) and x < (lo2 - lo1) * (y - la1) / (la2 - la1) + lo1:
            inside = not inside
    return inside


def dist_to_polygon_km(p, ring):
    """(0, p) if inside, else distance to the nearest edge."""
    if point_in_ring(p, ring):
        return 0.0, p
    return dist_to_line_km(p, ring + ring[:1])
