"""
NACRAC — New Algorithm for Collision Risk Assessment and Classification
Based on Federico Toson's thesis (UniPD, 2021/2022).

3 components: R_C (collective risk) | R_I (individual risk) | M_S (mitigation solutions)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

R_EARTH_KM = 6371.0
MU_EARTH = 398600.4418  # km^3/s^2
GAMMA_KG = 20_000  # cost per kg (conservative LEO estimate, $/kg)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RCLetterGrade(str, Enum):
    F = "F"
    E = "E"
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    A_PLUS = "A+"
    A_PLUS_PLUS = "A++"
    A_CARET_A = "A^A"


class WorstRisk(str, Enum):
    VL = "VL"
    L = "L"
    M = "M"
    H = "H"
    VH = "VH"


class SurvivalClass(str, Enum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"


class ReentryStrategy(int, Enum):
    UNCONTROLLED = 1
    SLOW = 2       # > 1 year
    FAST = 3       # < 1 year
    CONTROLLED = 4


# ---------------------------------------------------------------------------
# Input / Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RCParams:
    perigee_km: float
    apogee_km: float
    mass_kg: float
    cross_section_m2: float

@dataclass
class RIParams:
    n_cdm_warnings: int = 0
    n_high_risk_cdm: int = 0
    max_collision_prob: float = 0.0
    fragmentation_event: bool = False
    confirmed_collision: bool = False
    residual_lifetime_years: float = 25.0
    sigma_surv: float = 0.5

@dataclass
class MSParams:
    reentry_strategy: int  # 1-4
    has_collision_avoidance: bool = False
    has_design_for_demise: bool = False

@dataclass
class NACRACParams:
    rc: RCParams
    ri: RIParams
    ms: MSParams

@dataclass
class RCResult:
    semi_major_axis_km: float
    period_s: float
    surface_range: int
    v_orbital_ms: float
    collision_zone_m: float
    dt_s: float
    p_orbit: float
    severity: float
    risk: float
    letter_grade: str
    coefficient: int
    code: str  # e.g. "A9"

@dataclass
class RIResult:
    worst_risk: str   # VL/L/M/H/VH
    dt_surv_years: float
    survival_class: str  # I-V
    code: str  # e.g. "L III"

@dataclass
class MSResult:
    reentry: int
    active: int
    passive: int
    code: str  # e.g. "301"

@dataclass
class NACRACResult:
    rc: RCResult
    ri: RIResult
    ms: MSResult
    rc_code: str
    ri_code: str
    ms_code: str
    full_code: str  # "A9 | L III | 301"


# ---------------------------------------------------------------------------
# R_C: Collective Scenario Risk
# ---------------------------------------------------------------------------

def _semi_major_axis(perigee_km: float, apogee_km: float) -> float:
    return R_EARTH_KM + (perigee_km + apogee_km) / 2


def _orbital_period(a_km: float) -> float:
    return 2 * math.pi * math.sqrt(a_km ** 3 / MU_EARTH)


def _surface_range(cross_section_cm2: float) -> int:
    """Table 7: surface range from cross-section in cm^2."""
    if cross_section_cm2 < 500:
        return 1
    elif cross_section_cm2 < 1500:
        return 2
    elif cross_section_cm2 < 3000:
        return 3
    elif cross_section_cm2 < 5000:
        return 4
    else:
        return 5


def _rc_letter_grade(exponent: int) -> str:
    """Table 8: exponent -> letter grade."""
    if exponent >= 0:
        return "F"
    if exponent <= -9:
        return "A^A"
    grade_map = {
        -1: "F", -2: "E", -3: "D", -4: "C", -5: "B",
        -6: "A", -7: "A+", -8: "A++",
    }
    return grade_map.get(exponent, "F")


def compute_rc(params: RCParams) -> RCResult:
    a_km = _semi_major_axis(params.perigee_km, params.apogee_km)
    period_s = _orbital_period(a_km)

    cross_section_cm2 = params.cross_section_m2 * 10_000
    surf_range = _surface_range(cross_section_cm2)

    v_orbital = math.sqrt(MU_EARTH / a_km) * 1000  # m/s
    collision_zone = math.sqrt(params.cross_section_m2) * surf_range
    dt = collision_zone / v_orbital
    p_orbit = dt / period_s

    severity = GAMMA_KG * params.mass_kg
    risk = p_orbit * severity

    if risk <= 0:
        return RCResult(
            semi_major_axis_km=a_km, period_s=period_s,
            surface_range=surf_range, v_orbital_ms=v_orbital,
            collision_zone_m=collision_zone, dt_s=dt,
            p_orbit=p_orbit, severity=severity, risk=risk,
            letter_grade="A^A", coefficient=1, code="A^A1",
        )

    exponent = int(math.floor(math.log10(risk)))
    coefficient = int(round(risk / (10 ** exponent)))
    coefficient = max(1, min(coefficient, 9))

    letter = _rc_letter_grade(exponent)
    code = f"{letter}{coefficient}"

    return RCResult(
        semi_major_axis_km=a_km, period_s=period_s,
        surface_range=surf_range, v_orbital_ms=v_orbital,
        collision_zone_m=collision_zone, dt_s=dt,
        p_orbit=p_orbit, severity=severity, risk=risk,
        letter_grade=letter, coefficient=coefficient, code=code,
    )


# ---------------------------------------------------------------------------
# R_I: Individual Scenario Risk
# ---------------------------------------------------------------------------

def _worst_risk_class(p: RIParams) -> str:
    """Table 9: worst risk classification."""
    if p.confirmed_collision:
        return "VH"
    if p.fragmentation_event:
        return "H"
    if p.n_high_risk_cdm > 5:
        return "H"
    if p.n_high_risk_cdm > 0 or p.max_collision_prob > 1e-4:
        return "M"
    if p.n_cdm_warnings > 10:
        return "M"
    if p.n_cdm_warnings > 0:
        return "L"
    return "VL"


def _survival_class(residual_lifetime_years: float, sigma_surv: float) -> tuple[str, float]:
    """Table 10: survival class from dt_surv = D_t * (1 - sigma_surv)."""
    dt_surv = residual_lifetime_years * (1 - sigma_surv)
    if dt_surv < 2:
        cls = "I"
    elif dt_surv < 4:
        cls = "II"
    elif dt_surv < 8:
        cls = "III"
    elif dt_surv < 16:
        cls = "IV"
    else:
        cls = "V"
    return cls, dt_surv


def compute_ri(params: RIParams) -> RIResult:
    worst = _worst_risk_class(params)
    surv_cls, dt_surv = _survival_class(params.residual_lifetime_years, params.sigma_surv)
    code = f"{worst} {surv_cls}"
    return RIResult(
        worst_risk=worst,
        dt_surv_years=dt_surv,
        survival_class=surv_cls,
        code=code,
    )


# ---------------------------------------------------------------------------
# M_S: Mitigation Solutions
# ---------------------------------------------------------------------------

def compute_ms(params: MSParams) -> MSResult:
    reentry = max(1, min(params.reentry_strategy, 4))
    active = 1 if params.has_collision_avoidance else 0
    passive = 1 if params.has_design_for_demise else 0
    code = f"{reentry}{active}{passive}"
    return MSResult(reentry=reentry, active=active, passive=passive, code=code)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_nacrac(params: NACRACParams) -> NACRACResult:
    rc = compute_rc(params.rc)
    ri = compute_ri(params.ri)
    ms = compute_ms(params.ms)
    full_code = f"{rc.code} | {ri.code} | {ms.code}"
    return NACRACResult(
        rc=rc, ri=ri, ms=ms,
        rc_code=rc.code, ri_code=ri.code, ms_code=ms.code,
        full_code=full_code,
    )
