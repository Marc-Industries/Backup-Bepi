from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .celestial_bodies import get_body, BODIES

_AU_KM = 1.496e8  # 1 AU in km


class PhaseType(Enum):
    PARKING_ORBIT = "parking_orbit"
    TRANSFER = "transfer"
    CAPTURE_ORBIT = "capture_orbit"
    SURFACE_OPS = "surface_ops"
    ESCAPE = "escape"
    REENTRY = "reentry"
    STATION_KEEPING = "station_keeping"
    FLYBY = "flyby"


def _mu(body_name: str) -> float:
    """Get gravitational parameter (km^3/s^2) from centralized registry."""
    return get_body(body_name).mu_km3s2


def _helio_radius(body_name: str) -> float:
    """Get mean orbital radius around Sun (km) from centralized registry."""
    return get_body(body_name).sma_au * _AU_KM


ALL_SUBSYSTEMS = ["STR", "EPS", "AOCS", "COM", "CDH", "TCS", "PROP", "PL", "HRN"]

DEFAULT_ACTIVE_SUBSYSTEMS: dict[PhaseType, list[str]] = {
    PhaseType.PARKING_ORBIT:   ["STR", "EPS", "AOCS", "COM", "CDH", "TCS", "HRN"],
    PhaseType.TRANSFER:        ["STR", "EPS", "AOCS", "COM", "CDH", "TCS", "PROP", "HRN"],
    PhaseType.CAPTURE_ORBIT:   ["STR", "EPS", "AOCS", "COM", "CDH", "TCS", "PROP", "HRN"],
    PhaseType.SURFACE_OPS:     ALL_SUBSYSTEMS.copy(),
    PhaseType.ESCAPE:          ["STR", "EPS", "AOCS", "COM", "CDH", "TCS", "PROP", "HRN"],
    PhaseType.REENTRY:         ["STR", "EPS", "CDH", "TCS", "HRN"],
    PhaseType.STATION_KEEPING: ALL_SUBSYSTEMS.copy(),
    PhaseType.FLYBY:           ["STR", "EPS", "AOCS", "COM", "CDH", "TCS", "PL", "HRN"],
}


@dataclass
class MissionPhase:
    name: str
    phase_type: PhaseType
    body: str
    orbital_params: dict[str, float] = field(default_factory=dict)
    duration_days: float = 0.0
    delta_v_ms: float = 0.0
    notes: str = ""
    active_subsystems: list[str] = field(default_factory=lambda: ALL_SUBSYSTEMS.copy())
    full_orbital_params: dict[str, float] = field(default_factory=lambda: {
        "alt_km": 550, "inc_deg": 97.6, "ecc": 0.001,
        "raan_deg": 0.0, "aop_deg": 0.0, "mass_kg": 285.0, "area_m2": 1.5,
    })

    def to_shared_orbit_dict(self) -> dict[str, Any]:
        fp = self.full_orbital_params
        return {
            "orb_alt": fp.get("alt_km", 550),
            "orb_inc": fp.get("inc_deg", 97.6),
            "orb_ecc": fp.get("ecc", 0.001),
            "orb_raan": fp.get("raan_deg", 0.0),
            "orb_aop": fp.get("aop_deg", 0.0),
            "orb_mass": fp.get("mass_kg", 285.0),
            "orb_area": fp.get("area_m2", 1.5),
        }


@dataclass
class MissionProfile:
    name: str
    phases: list[MissionPhase] = field(default_factory=list)

    def add_phase(self, phase: MissionPhase, index: int | None = None):
        if index is None:
            self.phases.append(phase)
        else:
            self.phases.insert(index, phase)

    def remove_phase(self, index: int):
        self.phases.pop(index)

    def reorder(self, new_order: list[int]):
        self.phases = [self.phases[i] for i in new_order]

    def total_delta_v(self) -> float:
        return sum(p.delta_v_ms for p in self.phases)

    def total_duration(self) -> float:
        return sum(p.duration_days for p in self.phases)

    def phases_at_body(self, body_name: str) -> list[MissionPhase]:
        return [p for p in self.phases if p.body == body_name]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "phases": [
                {
                    "name": p.name,
                    "phase_type": p.phase_type.value,
                    "body": p.body,
                    "orbital_params": p.orbital_params,
                    "duration_days": p.duration_days,
                    "delta_v_ms": p.delta_v_ms,
                    "notes": p.notes,
                    "active_subsystems": p.active_subsystems,
                    "full_orbital_params": p.full_orbital_params,
                }
                for p in self.phases
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MissionProfile:
        phases = []
        for p in data["phases"]:
            pt = PhaseType(p["phase_type"])
            phases.append(MissionPhase(
                name=p["name"],
                phase_type=pt,
                body=p["body"],
                orbital_params=p.get("orbital_params", {}),
                duration_days=p.get("duration_days", 0.0),
                delta_v_ms=p.get("delta_v_ms", 0.0),
                notes=p.get("notes", ""),
                active_subsystems=p.get("active_subsystems", DEFAULT_ACTIVE_SUBSYSTEMS.get(pt, ALL_SUBSYSTEMS.copy())),
                full_orbital_params=p.get("full_orbital_params", {
                    "alt_km": p.get("orbital_params", {}).get("alt_km", 550),
                    "inc_deg": 97.6, "ecc": 0.001, "raan_deg": 0.0,
                    "aop_deg": 0.0, "mass_kg": 285.0, "area_m2": 1.5,
                }),
            ))
        return cls(name=data["name"], phases=phases)


# ---------------------------------------------------------------------------
# Delta-V estimation
# ---------------------------------------------------------------------------

def _hohmann_delta_v(mu: float, r1: float, r2: float) -> tuple[float, float]:
    """Returns (dv1, dv2) for a Hohmann transfer in km/s."""
    v1_circ = math.sqrt(mu / r1)
    v2_circ = math.sqrt(mu / r2)
    a_t = (r1 + r2) / 2.0
    v1_t = math.sqrt(mu * (2.0 / r1 - 1.0 / a_t))
    v2_t = math.sqrt(mu * (2.0 / r2 - 1.0 / a_t))
    return abs(v1_t - v1_circ), abs(v2_circ - v2_t)


def _circular_velocity(mu: float, r: float) -> float:
    return math.sqrt(mu / r)


def compute_phase_delta_v(phase: MissionPhase) -> float:
    """Estimate delta-v (m/s) for a phase based on type and orbital params.

    Supported orbital_params keys per phase type:
      PARKING_ORBIT / STATION_KEEPING: alt_km, body → station-keeping ~50 m/s/year
      TRANSFER: origin, destination → Hohmann heliocentric
      CAPTURE_ORBIT: alt_km, body → hyperbolic arrival minus circular
      ESCAPE: alt_km, body → escape velocity minus circular
      REENTRY: alt_km, body → deorbit burn ~100 m/s typical
      FLYBY: periapsis_km, body → gravity assist, ~0 propulsive
      SURFACE_OPS: 0 (no orbital manoeuvre)
    """
    p = phase.orbital_params
    pt = phase.phase_type

    if pt == PhaseType.SURFACE_OPS:
        return 0.0

    if pt == PhaseType.FLYBY:
        return 0.0

    if pt == PhaseType.REENTRY:
        return p.get("dv_ms", 100.0)

    body = p.get("body", phase.body)
    mu = _mu(body)
    alt_km = p.get("alt_km", 400.0)
    body_radius = p.get("body_radius_km", get_body(body).radius_km)
    r = body_radius + alt_km

    if pt == PhaseType.PARKING_ORBIT or pt == PhaseType.STATION_KEEPING:
        years = phase.duration_days / 365.25
        return years * p.get("sk_ms_per_year", 50.0)

    if pt == PhaseType.TRANSFER:
        origin = p.get("origin", "Earth")
        destination = p.get("destination", "Mars")
        r1 = _helio_radius(origin)
        r2 = _helio_radius(destination)
        dv1, dv2 = _hohmann_delta_v(_mu("Sun"), r1, r2)
        return (dv1 + dv2) * 1000.0  # km/s → m/s

    if pt == PhaseType.CAPTURE_ORBIT:
        v_circ = _circular_velocity(mu, r)
        v_inf = p.get("v_inf_kms", 2.0)
        v_hyp = math.sqrt(v_inf**2 + 2.0 * mu / r)
        return abs(v_hyp - v_circ) * 1000.0

    if pt == PhaseType.ESCAPE:
        v_circ = _circular_velocity(mu, r)
        v_esc = math.sqrt(2.0) * v_circ
        return (v_esc - v_circ) * 1000.0

    return phase.delta_v_ms


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def generate_phase_summary_table(profile: MissionProfile) -> list[dict]:
    rows = []
    cumulative_dv = 0.0
    cumulative_days = 0.0
    for i, p in enumerate(profile.phases):
        cumulative_dv += p.delta_v_ms
        cumulative_days += p.duration_days
        rows.append({
            "index": i,
            "name": p.name,
            "type": p.phase_type.value,
            "body": p.body,
            "duration_days": round(p.duration_days, 1),
            "delta_v_ms": round(p.delta_v_ms, 1),
            "cumulative_dv_ms": round(cumulative_dv, 1),
            "cumulative_days": round(cumulative_days, 1),
            "notes": p.notes,
        })
    return rows


# ---------------------------------------------------------------------------
# Pre-built mission templates
# ---------------------------------------------------------------------------

LEO_ONLY = MissionProfile(
    name="LEO Only",
    phases=[
        MissionPhase("Launch to LEO", PhaseType.PARKING_ORBIT, "Earth",
                     {"alt_km": 400.0, "body_radius_km": 6371.0}, 0.0, 9400.0, "Launch vehicle provides ~9.4 km/s"),
        MissionPhase("LEO Operations", PhaseType.STATION_KEEPING, "Earth",
                     {"alt_km": 400.0, "sk_ms_per_year": 50.0}, 365.0, 50.0),
    ],
)

GEO_TRANSFER = MissionProfile(
    name="GEO Transfer",
    phases=[
        MissionPhase("LEO Parking", PhaseType.PARKING_ORBIT, "Earth",
                     {"alt_km": 200.0}, 0.5, 0.0),
        MissionPhase("GTO", PhaseType.TRANSFER, "Earth",
                     {"alt_km": 200.0}, 0.2, 2440.0, "Hohmann LEO→GEO"),
        MissionPhase("GEO Circularisation", PhaseType.CAPTURE_ORBIT, "Earth",
                     {"alt_km": 35786.0, "body_radius_km": 6371.0, "v_inf_kms": 1.6}, 0.0, 1470.0),
        MissionPhase("GEO Station Keeping", PhaseType.STATION_KEEPING, "Earth",
                     {"alt_km": 35786.0, "sk_ms_per_year": 50.0}, 5475.0, 750.0, "15 years"),
    ],
)

LUNAR_MISSION = MissionProfile(
    name="Lunar Mission",
    phases=[
        MissionPhase("LEO Parking", PhaseType.PARKING_ORBIT, "Earth",
                     {"alt_km": 200.0}, 0.1, 0.0),
        MissionPhase("Trans-Lunar Injection", PhaseType.ESCAPE, "Earth",
                     {"alt_km": 200.0, "body_radius_km": 6371.0}, 0.0, 3120.0),
        MissionPhase("Lunar Transfer", PhaseType.TRANSFER, "Moon",
                     {}, 3.0, 0.0, "Coast phase"),
        MissionPhase("Lunar Orbit Insertion", PhaseType.CAPTURE_ORBIT, "Moon",
                     {"alt_km": 100.0, "body_radius_km": 1737.4, "v_inf_kms": 0.8}, 0.0, 820.0),
        MissionPhase("Lunar Surface Ops", PhaseType.SURFACE_OPS, "Moon",
                     {}, 7.0, 0.0),
        MissionPhase("Lunar Ascent", PhaseType.ESCAPE, "Moon",
                     {"alt_km": 100.0, "body_radius_km": 1737.4}, 0.0, 1870.0),
        MissionPhase("Return Transfer", PhaseType.TRANSFER, "Earth",
                     {}, 3.0, 0.0, "Coast phase"),
        MissionPhase("Earth Reentry", PhaseType.REENTRY, "Earth",
                     {"dv_ms": 0.0}, 0.0, 0.0, "Direct entry, no burn"),
    ],
)

MARS_MISSION = MissionProfile(
    name="Mars Mission",
    phases=[
        MissionPhase("Earth Parking Orbit", PhaseType.PARKING_ORBIT, "Earth",
                     {"alt_km": 300.0}, 1.0, 0.0),
        MissionPhase("Trans-Mars Injection", PhaseType.ESCAPE, "Earth",
                     {"alt_km": 300.0, "body_radius_km": 6371.0}, 0.0, 3600.0),
        MissionPhase("Hohmann Transfer to Mars", PhaseType.TRANSFER, "Mars",
                     {"origin": "Earth", "destination": "Mars"}, 259.0, 0.0, "Computed via Hohmann"),
        MissionPhase("Mars Orbit Insertion", PhaseType.CAPTURE_ORBIT, "Mars",
                     {"alt_km": 250.0, "body_radius_km": 3389.5, "v_inf_kms": 2.65}, 0.0, 1440.0),
        MissionPhase("Mars Surface Operations", PhaseType.SURFACE_OPS, "Mars",
                     {}, 500.0, 0.0),
        MissionPhase("Mars Escape", PhaseType.ESCAPE, "Mars",
                     {"alt_km": 250.0, "body_radius_km": 3389.5}, 0.0, 1490.0),
        MissionPhase("Return Hohmann Transfer", PhaseType.TRANSFER, "Earth",
                     {"origin": "Mars", "destination": "Earth"}, 259.0, 0.0),
        MissionPhase("Earth Reentry", PhaseType.REENTRY, "Earth",
                     {"dv_ms": 100.0}, 0.0, 100.0),
    ],
)

JUPITER_FLYBY = MissionProfile(
    name="Jupiter Flyby",
    phases=[
        MissionPhase("Earth Parking Orbit", PhaseType.PARKING_ORBIT, "Earth",
                     {"alt_km": 300.0}, 0.5, 0.0),
        MissionPhase("Trans-Jupiter Injection", PhaseType.ESCAPE, "Earth",
                     {"alt_km": 300.0, "body_radius_km": 6371.0}, 0.0, 6300.0),
        MissionPhase("Heliocentric Cruise", PhaseType.TRANSFER, "Jupiter",
                     {"origin": "Earth", "destination": "Jupiter"}, 998.0, 0.0, "~2.7 years"),
        MissionPhase("Jupiter Flyby", PhaseType.FLYBY, "Jupiter",
                     {"periapsis_km": 200000.0, "body_radius_km": 69911.0}, 1.0, 0.0, "Gravity assist"),
    ],
)

TEMPLATES: dict[str, MissionProfile] = {
    "LEO_ONLY": LEO_ONLY,
    "GEO_TRANSFER": GEO_TRANSFER,
    "LUNAR_MISSION": LUNAR_MISSION,
    "MARS_MISSION": MARS_MISSION,
    "JUPITER_FLYBY": JUPITER_FLYBY,
}
