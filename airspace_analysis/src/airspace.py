"""
src/airspace.py
---------------
Shared utilities for the Airspace Conflict Analysis project.
Covers coordinate math, FAA separation standards, conflict detection,
and risk scoring. Imported by all notebooks.
"""

import math
import itertools
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ── FAA Separation Standards (7110.65 ATC Order) ─────────────────────────────

# Horizontal separation minimums
FAA_HORIZONTAL_SEP_NM = 3.0          # nautical miles (terminal/TRACON)
FAA_HORIZONTAL_SEP_EN_ROUTE_NM = 5.0 # nautical miles (en route)

# Vertical separation minimums
FAA_VERTICAL_SEP_FT = 1000           # feet (below FL410)
FAA_VERTICAL_SEP_RVSM_FT = 1000     # feet (FL290-FL410, RVSM airspace)

# Nautical miles per degree of latitude (constant)
NM_PER_DEG_LAT = 60.0

# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class AircraftState:
    """Snapshot of a single aircraft at one point in time."""
    icao24: str
    callsign: str
    time: float          # Unix timestamp
    lat: float           # degrees
    lon: float           # degrees
    altitude_ft: float   # barometric altitude in feet
    velocity_kts: float  # ground speed in knots
    heading_deg: float   # true heading in degrees
    on_ground: bool


@dataclass
class ConflictEvent:
    """A detected separation violation between two aircraft."""
    time: float
    icao_a: str
    icao_b: str
    callsign_a: str
    callsign_b: str
    horizontal_dist_nm: float
    vertical_dist_ft: float
    severity: str        # "CRITICAL", "WARNING", "ADVISORY"
    lat_midpoint: float
    lon_midpoint: float


# ── Coordinate & Distance Math ────────────────────────────────────────────────

def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance between two lat/lon points in nautical miles.
    Uses the haversine formula — accurate for short and medium distances.
    """
    R_nm = 3440.065  # Earth radius in nautical miles

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2

    return R_nm * 2 * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """True bearing from point 1 to point 2 in degrees (0-360)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - \
        math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def closing_speed_kts(state_a: AircraftState, state_b: AircraftState) -> float:
    """
    Estimate closing speed between two aircraft in knots.
    Projects each velocity vector onto the bearing between them.
    """
    brg = bearing_deg(state_a.lat, state_a.lon, state_b.lat, state_b.lon)
    brg_rad = math.radians(brg)

    vax = state_a.velocity_kts * math.sin(math.radians(state_a.heading_deg))
    vay = state_a.velocity_kts * math.cos(math.radians(state_a.heading_deg))
    vbx = state_b.velocity_kts * math.sin(math.radians(state_b.heading_deg))
    vby = state_b.velocity_kts * math.cos(math.radians(state_b.heading_deg))

    # Closing velocity = component of relative velocity along bearing
    rel_x = vax - vbx
    rel_y = vay - vby
    closing = rel_x * math.sin(brg_rad) + rel_y * math.cos(brg_rad)
    return closing  # positive = converging, negative = diverging


# ── Separation & Conflict Detection ──────────────────────────────────────────

def check_separation(a: AircraftState, b: AircraftState,
                     horizontal_min_nm: float = FAA_HORIZONTAL_SEP_NM,
                     vertical_min_ft: float = FAA_VERTICAL_SEP_FT
                     ) -> Optional[ConflictEvent]:
    """
    Check if two aircraft violate FAA separation standards.
    Returns a ConflictEvent if a violation is detected, else None.
    """
    if a.on_ground or b.on_ground:
        return None  # Ground traffic excluded

    h_dist = haversine_nm(a.lat, a.lon, b.lat, b.lon)
    v_dist = abs(a.altitude_ft - b.altitude_ft)

    if h_dist >= horizontal_min_nm or v_dist >= vertical_min_ft:
        return None  # No violation

    # Severity classification
    h_ratio = h_dist / horizontal_min_nm
    v_ratio = v_dist / vertical_min_ft

    if h_ratio < 0.3 and v_ratio < 0.3:
        severity = "CRITICAL"
    elif h_ratio < 0.6 and v_ratio < 0.6:
        severity = "WARNING"
    else:
        severity = "ADVISORY"

    return ConflictEvent(
        time=a.time,
        icao_a=a.icao24,
        icao_b=b.icao24,
        callsign_a=a.callsign.strip(),
        callsign_b=b.callsign.strip(),
        horizontal_dist_nm=round(h_dist, 3),
        vertical_dist_ft=round(v_dist, 1),
        severity=severity,
        lat_midpoint=(a.lat + b.lat) / 2,
        lon_midpoint=(a.lon + b.lon) / 2,
    )


def detect_conflicts(states: List[AircraftState],
                     horizontal_min_nm: float = FAA_HORIZONTAL_SEP_NM,
                     vertical_min_ft: float = FAA_VERTICAL_SEP_FT
                     ) -> List[ConflictEvent]:
    """
    Run pairwise separation checks across all aircraft at a single timestep.
    O(n^2) — acceptable for typical ATC sector sizes (<100 aircraft).
    """
    conflicts = []
    for a, b in itertools.combinations(states, 2):
        event = check_separation(a, b, horizontal_min_nm, vertical_min_ft)
        if event:
            conflicts.append(event)
    return conflicts


# ── Risk Scoring ──────────────────────────────────────────────────────────────

def severity_score(severity: str) -> int:
    """Numeric score for sorting/aggregating severity levels."""
    return {"CRITICAL": 3, "WARNING": 2, "ADVISORY": 1}.get(severity, 0)


def conflict_risk_score(event: ConflictEvent,
                         closing_spd: Optional[float] = None) -> float:
    """
    Composite risk score [0-100] combining:
      - Separation margin (how close to the limit)
      - Severity level
      - Closing speed (if available)
    """
    h_margin = max(0, 1 - event.horizontal_dist_nm / FAA_HORIZONTAL_SEP_NM)
    v_margin = max(0, 1 - event.vertical_dist_ft  / FAA_VERTICAL_SEP_FT)
    geo_score = (h_margin * 0.6 + v_margin * 0.4) * 50  # up to 50 pts

    sev_score = severity_score(event.severity) / 3 * 30  # up to 30 pts

    spd_score = 0.0
    if closing_spd is not None and closing_spd > 0:
        spd_score = min(closing_spd / 600, 1.0) * 20   # up to 20 pts

    return round(geo_score + sev_score + spd_score, 2)


# ── DataFrame Helpers ─────────────────────────────────────────────────────────

def states_to_df(states: List[AircraftState]) -> pd.DataFrame:
    """Convert a list of AircraftState objects to a tidy DataFrame."""
    return pd.DataFrame([vars(s) for s in states])


def conflicts_to_df(conflicts: List[ConflictEvent]) -> pd.DataFrame:
    """Convert a list of ConflictEvent objects to a tidy DataFrame."""
    if not conflicts:
        return pd.DataFrame(columns=[
            "time","icao_a","icao_b","callsign_a","callsign_b",
            "horizontal_dist_nm","vertical_dist_ft","severity",
            "lat_midpoint","lon_midpoint"
        ])
    return pd.DataFrame([vars(c) for c in conflicts])


# ── OpenSky API Helper ────────────────────────────────────────────────────────

def parse_opensky_response(data: dict) -> List[AircraftState]:
    """
    Parse raw OpenSky /states/all response into AircraftState objects.
    OpenSky state vector indices:
      0:icao24  1:callsign  2:origin_country  3:time_position
      4:last_contact  5:longitude  6:latitude  7:baro_altitude(m)
      8:on_ground  9:velocity(m/s)  10:true_track  11:vertical_rate
      12:sensors  13:geo_altitude(m)  14:squawk  15:spi  16:position_source
    """
    states = []
    for sv in data.get("states", []) or []:
        try:
            alt_m = sv[7]
            vel_ms = sv[9]
            if alt_m is None or sv[5] is None or sv[6] is None:
                continue

            states.append(AircraftState(
                icao24=sv[0] or "",
                callsign=(sv[1] or "UNKNOWN").strip(),
                time=float(data.get("time", 0)),
                lat=float(sv[6]),
                lon=float(sv[5]),
                altitude_ft=float(alt_m) * 3.28084,      # meters → feet
                velocity_kts=float(vel_ms or 0) * 1.944, # m/s → knots
                heading_deg=float(sv[10] or 0),
                on_ground=bool(sv[8]),
            ))
        except (TypeError, ValueError):
            continue
    return states
