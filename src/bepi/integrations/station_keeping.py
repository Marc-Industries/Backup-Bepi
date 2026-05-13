"""Station-keeping and delta-V budget tool for orbital missions."""

import math
from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Common propellant catalogue  (name → Isp in seconds)
# ---------------------------------------------------------------------------
PROPELLANT_ISP: dict[str, float] = {
    "HYDRAZINE": 220.0,
    "BIPROP_MMH_NTO": 310.0,
    "COLD_GAS_N2": 70.0,
    "XENON_HALL": 1500.0,
    "XENON_ION": 3000.0,
    "GREEN_AF_M315E": 250.0,
    "BIPROP_LOX_LH2": 450.0,
}

G0 = 9.80665  # m/s²
RE = 6371.0    # Earth radius km
MU_EARTH = 3.986004418e14  # m³/s²

# Exponential atmosphere scale heights (km) and reference densities (kg/m³)
# Approximate US Standard 1976 piecewise fit
_ATMOSPHERE_BANDS: list[tuple[float, float, float]] = [
    # (h_base_km, rho0 kg/m³, H km)
    (0,   1.225,    8.44),
    (25,  3.899e-2, 6.49),
    (30,  1.774e-2, 6.75),
    (40,  3.972e-3, 7.26),
    (50,  1.057e-3, 7.26),
    (60,  3.206e-4, 6.33),
    (70,  8.770e-5, 5.88),
    (80,  1.905e-5, 5.84),
    (90,  3.396e-6, 6.00),
    (100, 5.604e-7, 6.55),
    (110, 9.708e-8, 7.89),
    (120, 2.222e-8, 9.50),
    (150, 2.076e-9, 22.0),
    (200, 2.541e-10, 37.5),
    (250, 6.073e-11, 45.5),
    (300, 1.916e-11, 53.6),
    (400, 2.803e-12, 59.4),
    (500, 5.215e-13, 62.2),
    (600, 1.137e-13, 65.8),
    (700, 3.070e-14, 71.8),
    (800, 1.136e-14, 80.0),
    (900, 5.759e-15, 90.0),
    (1000, 3.561e-15, 105.0),
]

# Solar-activity density multiplier (relative to moderate)
_SOLAR_MULT = {"low": 0.5, "medium": 1.0, "high": 3.0}


@dataclass
class SKParams:
    orbit_type: Literal["LEO", "GEO", "SSO", "HALO", "LUNAR"] = "LEO"
    altitude_km: float = 500.0
    inclination_deg: float = 51.6
    mission_duration_years: float = 5.0
    drag_coefficient: float = 2.2
    area_to_mass_ratio: float = 0.01  # m²/kg
    solar_activity: Literal["low", "medium", "high"] = "medium"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _density_at_altitude(h_km: float, solar: str = "medium") -> float:
    """Exponential atmosphere density (kg/m³) at altitude *h_km*."""
    band = _ATMOSPHERE_BANDS[0]
    for b in _ATMOSPHERE_BANDS:
        if h_km >= b[0]:
            band = b
        else:
            break
    h_base, rho0, H = band
    rho = rho0 * math.exp(-(h_km - h_base) / H)
    return rho * _SOLAR_MULT.get(solar, 1.0)


def _orbital_velocity(alt_km: float) -> float:
    """Circular orbital velocity (m/s) at altitude above Earth."""
    r = (RE + alt_km) * 1e3
    return math.sqrt(MU_EARTH / r)


def _orbital_period(alt_km: float) -> float:
    """Orbital period in seconds."""
    r = (RE + alt_km) * 1e3
    return 2.0 * math.pi * math.sqrt(r**3 / MU_EARTH)


# ---------------------------------------------------------------------------
# Station-keeping ΔV functions
# ---------------------------------------------------------------------------

def sk_delta_v_leo(params: SKParams) -> dict:
    """Atmospheric drag compensation ΔV for LEO.

    Uses exponential atmosphere model.  Returns dict with delta_v_m_s,
    delta_v_per_year, density_kg_m3, orbital_velocity_m_s.
    """
    h = params.altitude_km
    rho = _density_at_altitude(h, params.solar_activity)
    v = _orbital_velocity(h)
    T = _orbital_period(h)
    Cd = params.drag_coefficient
    A_m = params.area_to_mass_ratio  # m²/kg

    # Drag acceleration  a_drag = 0.5 * rho * v² * Cd * (A/m)
    a_drag = 0.5 * rho * v**2 * Cd * A_m  # m/s²

    # ΔV per orbit ≈ a_drag * T  (impulse needed to maintain orbit)
    dv_per_orbit = a_drag * T
    orbits_per_year = 365.25 * 86400.0 / T
    dv_per_year = dv_per_orbit * orbits_per_year
    dv_total = dv_per_year * params.mission_duration_years

    return {
        "orbit_type": "LEO",
        "altitude_km": h,
        "density_kg_m3": rho,
        "orbital_velocity_m_s": round(v, 1),
        "drag_acceleration_m_s2": a_drag,
        "delta_v_per_year_m_s": round(dv_per_year, 3),
        "delta_v_total_m_s": round(dv_total, 3),
        "mission_duration_years": params.mission_duration_years,
    }


def sk_delta_v_geo(
    inclination_drift_deg_yr: float = 0.75,
    ecc_control: bool = True,
    mission_duration_years: float = 15.0,
) -> dict:
    """GEO station-keeping ΔV (N-S + E-W).

    N-S: ~50 m/s/yr (luni-solar inclination drift).
    E-W: ~2-6 m/s/yr (longitude drift, triaxiality).
    Eccentricity control: ~0-2 m/s/yr (solar radiation pressure).
    """
    # N-S  ΔV ≈ 2 * v_geo * sin(Δi/2) per year, classic approximation ~50 m/s/yr
    ns_dv_yr = 2.0 * 3075.0 * math.sin(math.radians(inclination_drift_deg_yr / 2.0))
    # Simplified: industry standard ≈ 50 m/s/yr for full ±0.05° control
    ns_dv_yr = max(ns_dv_yr, 0.0)

    ew_dv_yr = 3.0  # m/s/yr typical
    ecc_dv_yr = 1.5 if ecc_control else 0.0

    total_yr = ns_dv_yr + ew_dv_yr + ecc_dv_yr
    total = total_yr * mission_duration_years

    return {
        "orbit_type": "GEO",
        "ns_dv_per_year_m_s": round(ns_dv_yr, 2),
        "ew_dv_per_year_m_s": round(ew_dv_yr, 2),
        "ecc_dv_per_year_m_s": round(ecc_dv_yr, 2),
        "total_dv_per_year_m_s": round(total_yr, 2),
        "delta_v_total_m_s": round(total, 2),
        "mission_duration_years": mission_duration_years,
    }


def sk_delta_v_sso(params: SKParams) -> dict:
    """Sun-synchronous orbit RAAN maintenance ΔV.

    J2 secular drift naturally maintains SSO if altitude/inclination are
    correct; ΔV corrects residual errors + drag-induced decay.
    Combines drag compensation + small inclination trim.
    """
    drag = sk_delta_v_leo(params)
    # Inclination trim ≈ 1-2 m/s/yr for typical SSO
    inc_trim_yr = 1.5  # m/s/yr
    inc_trim_total = inc_trim_yr * params.mission_duration_years

    total = drag["delta_v_total_m_s"] + inc_trim_total

    return {
        "orbit_type": "SSO",
        "altitude_km": params.altitude_km,
        "drag_dv_m_s": drag["delta_v_total_m_s"],
        "raan_trim_dv_m_s": round(inc_trim_total, 3),
        "delta_v_total_m_s": round(total, 3),
        "mission_duration_years": params.mission_duration_years,
    }


def sk_delta_v_lunar(
    orbit_type: Literal["NRHO", "LLO", "HALO"] = "NRHO",
    mission_duration_years: float = 5.0,
) -> dict:
    """Lunar orbit station-keeping ΔV.

    NRHO (near-rectilinear halo orbit): ~5-10 m/s/yr  (Gateway baseline).
    LLO (low lunar orbit): ~30-80 m/s/yr  (mascon perturbations).
    HALO (L1/L2 halo): ~5-15 m/s/yr.
    """
    budgets = {
        "NRHO": 7.5,
        "LLO": 50.0,
        "HALO": 10.0,
    }
    dv_yr = budgets.get(orbit_type, 10.0)
    total = dv_yr * mission_duration_years

    return {
        "orbit_type": f"LUNAR_{orbit_type}",
        "dv_per_year_m_s": dv_yr,
        "delta_v_total_m_s": round(total, 2),
        "mission_duration_years": mission_duration_years,
    }


# ---------------------------------------------------------------------------
# Propellant mass (Tsiolkovsky)
# ---------------------------------------------------------------------------

def compute_propellant_mass(
    delta_v_ms: float,
    dry_mass_kg: float,
    isp_s: float,
) -> dict:
    """Tsiolkovsky rocket equation → propellant mass."""
    ve = isp_s * G0
    mass_ratio = math.exp(delta_v_ms / ve)
    total_mass = dry_mass_kg * mass_ratio
    prop_mass = total_mass - dry_mass_kg

    return {
        "delta_v_m_s": round(delta_v_ms, 3),
        "dry_mass_kg": dry_mass_kg,
        "isp_s": isp_s,
        "exhaust_velocity_m_s": round(ve, 1),
        "mass_ratio": round(mass_ratio, 6),
        "propellant_mass_kg": round(prop_mass, 4),
        "total_mass_kg": round(total_mass, 4),
    }


# ---------------------------------------------------------------------------
# Total mission ΔV
# ---------------------------------------------------------------------------

def total_mission_delta_v(phases: list[dict]) -> dict:
    """Sum all ΔV phases with breakdown.

    Each phase dict must have at least ``name`` and ``delta_v_m_s``.
    """
    total = 0.0
    breakdown = []
    for p in phases:
        dv = p.get("delta_v_m_s", 0.0)
        total += dv
        breakdown.append({
            "name": p.get("name", "unnamed"),
            "delta_v_m_s": round(dv, 3),
        })

    return {
        "total_delta_v_m_s": round(total, 3),
        "num_phases": len(phases),
        "breakdown": breakdown,
    }
