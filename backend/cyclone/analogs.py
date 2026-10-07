from backend.models.imd import classify_wind_kt
from backend.services.forecast import analog_storms


def similar_cyclones(storm: dict, now_idx: int, k: int = 5) -> list[dict]:
    analogs = analog_storms(storm, now_idx, k=k)
    out = []
    for other in analogs:
        winds = [p.get("wind_kt") for p in other["track"] if p.get("wind_kt") is not None]
        peak = max(winds) if winds else other.get("peak_wind_kt")
        land = other.get("landfall_hint")
        out.append(
            {
                "id": other["id"],
                "name": other["name"],
                "season": other["season"],
                "genesis_basin": other.get("genesis_basin"),
                "peak_wind_kt": peak,
                "peak_category": classify_wind_kt(peak).name if peak else None,
                "landfall": land,
                "n_points": len(other["track"]),
            }
        )
    return out
