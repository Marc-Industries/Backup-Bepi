"""DRAMA/MASTER interface — space debris and re-entry analysis.

ESA DRAMA (Debris Risk Assessment and Mitigation Analysis):
- MASTER: debris flux model
- OSCAR: orbit evolution / re-entry prediction
- ARES: re-entry survivability

This module provides debris flux estimates and compliance checks.
"""
from dataclasses import dataclass


@dataclass
class DebrisEnvironment:
    altitude_km: float
    flux_gt_1cm: float  # #/m2/year, objects > 1cm
    flux_gt_1mm: float  # #/m2/year, objects > 1mm
    flux_gt_10cm: float  # #/m2/year, objects > 10cm (trackable)
    collision_prob_year: float  # Probability per year for typical smallsat


# MASTER-8 approximate flux values (2027 projection)
DEBRIS_FLUX = {
    300: DebrisEnvironment(300, 2.0e-5, 3.0e-3, 1.0e-7, 5e-6),
    400: DebrisEnvironment(400, 3.5e-5, 5.0e-3, 2.0e-7, 1e-5),
    500: DebrisEnvironment(500, 5.0e-5, 8.0e-3, 3.0e-7, 2e-5),
    550: DebrisEnvironment(550, 5.5e-5, 9.0e-3, 3.5e-7, 2.5e-5),
    600: DebrisEnvironment(600, 7.0e-5, 1.2e-2, 5.0e-7, 3e-5),
    700: DebrisEnvironment(700, 1.0e-4, 2.0e-2, 8.0e-7, 5e-5),
    800: DebrisEnvironment(800, 2.0e-4, 4.0e-2, 2.0e-6, 1e-4),
    900: DebrisEnvironment(900, 3.0e-4, 6.0e-2, 3.0e-6, 2e-4),
    1000: DebrisEnvironment(1000, 2.5e-4, 5.0e-2, 2.5e-6, 1.5e-4),
}


def estimate_debris_flux(altitude_km: float, cross_section_m2: float = 1.5,
                         mission_years: float = 5.0) -> dict:
    # Interpolate
    alts = sorted(DEBRIS_FLUX.keys())
    if altitude_km <= alts[0]:
        env = DEBRIS_FLUX[alts[0]]
    elif altitude_km >= alts[-1]:
        env = DEBRIS_FLUX[alts[-1]]
    else:
        for i in range(len(alts) - 1):
            if alts[i] <= altitude_km <= alts[i + 1]:
                f = (altitude_km - alts[i]) / (alts[i + 1] - alts[i])
                e1 = DEBRIS_FLUX[alts[i]]
                e2 = DEBRIS_FLUX[alts[i + 1]]
                env = DebrisEnvironment(
                    altitude_km,
                    e1.flux_gt_1cm * (1 - f) + e2.flux_gt_1cm * f,
                    e1.flux_gt_1mm * (1 - f) + e2.flux_gt_1mm * f,
                    e1.flux_gt_10cm * (1 - f) + e2.flux_gt_10cm * f,
                    e1.collision_prob_year * (1 - f) + e2.collision_prob_year * f,
                )
                break

    impacts_1cm = env.flux_gt_1cm * cross_section_m2 * mission_years
    impacts_1mm = env.flux_gt_1mm * cross_section_m2 * mission_years
    collision_prob = 1 - (1 - env.collision_prob_year) ** mission_years

    return {
        "altitude_km": altitude_km,
        "cross_section_m2": cross_section_m2,
        "mission_years": mission_years,
        "flux_gt_1cm_m2_year": env.flux_gt_1cm,
        "flux_gt_1mm_m2_year": env.flux_gt_1mm,
        "flux_gt_10cm_m2_year": env.flux_gt_10cm,
        "expected_impacts_gt_1cm": round(impacts_1cm, 4),
        "expected_impacts_gt_1mm": round(impacts_1mm, 2),
        "collision_probability": round(collision_prob, 6),
        "collision_prob_per_year": env.collision_prob_year,
    }


@dataclass
class DeorbitAnalysis:
    altitude_km: float
    mass_kg: float
    cross_section_m2: float
    cd: float = 2.2
    natural_decay_years: float = 0.0
    compliant_25yr: bool = False
    delta_v_deorbit_ms: float = 0.0
    target_perigee_km: float = 0.0
    notes: str = ""


def estimate_deorbit(altitude_km: float, mass_kg: float,
                     cross_section_m2: float = 1.5,
                     cd: float = 2.2) -> DeorbitAnalysis:
    """Estimate natural orbital decay time and delta-V for 25-year compliance."""
    # Simplified exponential model for LEO atmospheric drag decay
    # Based on empirical fits to STK/DRAMA results
    ballistic_coeff = mass_kg / (cd * cross_section_m2)  # kg/m2

    if altitude_km < 300:
        natural_years = 0.1
    elif altitude_km < 400:
        natural_years = 0.5 * (ballistic_coeff / 50)
    elif altitude_km < 500:
        natural_years = 2.0 * (ballistic_coeff / 50) * (altitude_km / 400) ** 3
    elif altitude_km < 600:
        natural_years = 5.0 * (ballistic_coeff / 50) * (altitude_km / 500) ** 4
    elif altitude_km < 700:
        natural_years = 15.0 * (ballistic_coeff / 50) * (altitude_km / 600) ** 5
    elif altitude_km < 800:
        natural_years = 50.0 * (ballistic_coeff / 50)
    else:
        natural_years = 200.0 * (ballistic_coeff / 50)

    compliant = natural_years <= 25.0

    # Delta-V for Hohmann to 250 km perigee (re-entry orbit)
    mu = 398600.4418  # km3/s2
    r1 = 6371 + altitude_km
    r2_perigee = 6371 + 250
    a_transfer = (r1 + r2_perigee) / 2
    v_circ = (mu / r1) ** 0.5
    v_transfer = (mu * (2 / r1 - 1 / a_transfer)) ** 0.5
    delta_v = abs(v_circ - v_transfer) * 1000  # m/s

    notes = ""
    if compliant:
        notes = f"Natural decay within 25 years ({natural_years:.1f} yr). No active deorbit required."
    else:
        notes = f"Natural decay {natural_years:.0f} yr > 25 yr limit. Active deorbit needed (dV={delta_v:.1f} m/s)."

    return DeorbitAnalysis(
        altitude_km=altitude_km,
        mass_kg=mass_kg,
        cross_section_m2=cross_section_m2,
        cd=cd,
        natural_decay_years=round(natural_years, 1),
        compliant_25yr=compliant,
        delta_v_deorbit_ms=round(delta_v, 1),
        target_perigee_km=250.0,
        notes=notes,
    )
