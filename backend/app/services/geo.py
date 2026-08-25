"""Distance helpers.

Deliberately dependency-free: no paid mapping API is required anywhere in the
product.  Straight-line (haversine) distance is adjusted by a road factor to
approximate travel distance, which is honest and good enough for allocation.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0

#: Typical ratio of road distance to straight-line distance in Indian cities.
ROAD_FACTOR = 1.25

#: Beyond this the location score bottoms out at zero.
MAX_SERVICE_RADIUS_KM = 25.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two coordinates, in kilometres."""
    p1, p2 = radians(lat1), radians(lat2)
    d_lat = p2 - p1
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(p1) * cos(p2) * sin(d_lng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def travel_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Estimated road distance, rounded to one decimal."""
    return round(haversine_km(lat1, lng1, lat2, lng2) * ROAD_FACTOR, 1)


def proximity_score(distance_km: float) -> float:
    """Map a distance to 0..1, linearly decaying to the service radius."""
    if distance_km <= 0:
        return 1.0
    if distance_km >= MAX_SERVICE_RADIUS_KM:
        return 0.0
    return round(1.0 - (distance_km / MAX_SERVICE_RADIUS_KM), 4)


def eta_minutes(distance_km: float, avg_speed_kmph: float = 22.0) -> int:
    """Rough travel time used for the tracking view."""
    if distance_km <= 0:
        return 0
    return max(3, int(round((distance_km / avg_speed_kmph) * 60)))
