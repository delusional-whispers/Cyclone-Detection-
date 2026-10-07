"""India Meteorological Department tropical cyclone intensity scale.

Wind thresholds are 3-minute sustained, in knots, matching IMD operational practice.
IBTrACS NEWDELHI_WIND is in knots when present.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImdClass:
    code: str
    name: str
    min_kt: float
    max_kt: float | None


IMD_CLASSES: tuple[ImdClass, ...] = (
    ImdClass("L", "Low pressure area", 0, 16),
    ImdClass("D", "Depression", 17, 27),
    ImdClass("DD", "Deep depression", 28, 33),
    ImdClass("CS", "Cyclonic storm", 34, 47),
    ImdClass("SCS", "Severe cyclonic storm", 48, 63),
    ImdClass("VSCS", "Very severe cyclonic storm", 64, 89),
    ImdClass("ESCS", "Extremely severe cyclonic storm", 90, 119),
    ImdClass("SuCS", "Super cyclonic storm", 120, None),
)

GRADE_ALIASES = {
    "L": "L",
    "LOW": "L",
    "D": "D",
    "DEP": "D",
    "DD": "DD",
    "CS": "CS",
    "SCS": "SCS",
    "VSCS": "VSCS",
    "ESCS": "ESCS",
    "SUCS": "SuCS",
    "SUPER": "SuCS",
}


def classify_wind_kt(wind_kt: float | None) -> ImdClass:
    if wind_kt is None or wind_kt != wind_kt:
        return IMD_CLASSES[0]
    for cls in IMD_CLASSES:
        if cls.max_kt is None:
            if wind_kt >= cls.min_kt:
                return cls
        elif cls.min_kt <= wind_kt <= cls.max_kt:
            return cls
    return IMD_CLASSES[0]


def from_ibtracs_grade(grade: str | None, wind_kt: float | None) -> ImdClass:
    if grade:
        key = GRADE_ALIASES.get(str(grade).strip().upper())
        if key:
            for cls in IMD_CLASSES:
                if cls.code == key:
                    return cls
    return classify_wind_kt(wind_kt)


def is_cyclonic_storm(wind_kt: float | None) -> bool:
    return classify_wind_kt(wind_kt).min_kt >= 34


def rapid_intensification(delta_kt_24h: float | None) -> bool:
    """IMD/WMO-style RI: ≥30 kt in 24 h (research threshold often 30 kt / 24 h)."""
    return delta_kt_24h is not None and delta_kt_24h >= 30


def rapid_weakening(delta_kt_24h: float | None) -> bool:
    return delta_kt_24h is not None and delta_kt_24h <= -30
