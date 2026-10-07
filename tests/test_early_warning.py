from backend.cyclone.pipeline import analyze
from backend.satellite.provider import MockSatelliteProvider
from backend.services.catalog import storms


def test_satellite_frame_is_cropped():
    storms_list = storms()
    assert storms_list
    p = storms_list[0]["track"][min(8, len(storms_list[0]["track"]) - 1)]
    frame = MockSatelliteProvider().frame(p, "ir", "nio")
    assert len(frame["values"]) <= 28
    assert len(frame["values"][0]) <= 28
    assert frame["live"] is False


def test_analyze_returns_detection():
    named = next(s for s in storms() if s["name"] == "AMPHAN")
    idx = min(20, len(named["track"]) - 1)
    out = analyze(named, idx, "ir", "bob")
    assert out["detection"]["cyclone_probability"] > 0.5
    assert out["detection"]["latitude"]
    assert out["satellite"]["loop"]
    assert all(item["frame"] and item["frame"]["values"] for item in out["satellite"]["loop"])
    assert "risk" in out and 1 <= out["risk"]["level"] <= 5
    if out["analogs"]:
        assert "track" not in out["analogs"][0]
