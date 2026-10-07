from backend.cyclone.risk import assess_risk


def test_risk_levels_span():
    weak = assess_risk(
        wind_kt=18,
        d_wind_24h=0,
        dist2land_km=500,
        landfall_probability=0.05,
        landfall_region="Maldives",
        spread_km_72=80,
        ri_probability=0.02,
    )
    strong = assess_risk(
        wind_kt=115,
        d_wind_24h=25,
        dist2land_km=40,
        landfall_probability=0.7,
        landfall_region="Odisha — Paradip",
        spread_km_72=90,
        ri_probability=0.4,
    )
    assert weak["level"] <= 2
    assert strong["level"] >= 4
    assert 1 <= weak["level"] <= 5
    assert "disclaimer" in strong
