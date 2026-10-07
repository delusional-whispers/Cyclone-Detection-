from backend.services.forecast import formation_probabilities


def test_formation_keys():
    p = formation_probabilities(16.0, 87.0, 10)
    assert set(p["window_hours"]) == {"24", "48", "72"}
    for v in p["window_hours"].values():
        assert 0.0 <= v <= 1.0
