from __future__ import annotations

import math

from backend.models.geo import destination_point, haversine_km
from backend.models.imd import classify_wind_kt, rapid_intensification


def test_haversine_delhi_kolkata_scale():
    d = haversine_km(28.6, 77.2, 22.6, 88.4)
    assert 1200 < d < 1400


def test_destination_roundtrip():
    lat2, lon2 = destination_point(15.0, 85.0, 90.0, 111.2)
    assert abs(lat2 - 15.0) < 0.2
    assert 85.9 < lon2 < 86.2


def test_imd_scale():
    assert classify_wind_kt(20).code == "D"
    assert classify_wind_kt(40).code == "CS"
    assert classify_wind_kt(70).code == "VSCS"
    assert classify_wind_kt(125).code == "SuCS"
    assert rapid_intensification(32)
    assert not rapid_intensification(10)
