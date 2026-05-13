"""Comprehensive space debris analysis module.

Implements NASA Standard Breakup Model, ECOB index, DAS-style compliance,
collision probability, casualty risk / demisability, Space Sustainability Rating,
NIAO index, and export functions for DAS/DRAMA/MASTER.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
R_EARTH_KM = 6371.0
MU_EARTH = 398600.4418  # km^3/s^2
EARTH_SURFACE_KM2 = 5.1e8
WORLD_POP_DENSITY = 52.0  # avg persons/km^2 (land-weighted)
LEO_UPPER_KM = 2000.0
GEO_ALTITUDE_KM = 35786.0
GEO_PROTECTED_BAND_KM = 200.0

# Atmospheric density model (simplified exponential, kg/m^3)
# rho(h) = rho0 * exp(-(h - h0) / H)
_ATM_LAYERS = [
    # (h0_km, rho0_kg_m3, scale_height_km)
    (200, 2.53e-10, 37.1),
    (300, 7.21e-11, 53.6),
    (400, 2.80e-11, 58.5),
    (500, 1.17e-11, 60.8),
    (600, 5.24e-12, 63.8),
    (700, 2.44e-12, 71.8),
    (800, 1.17e-12, 88.7),
    (900, 5.60e-13, 124.0),
    (1000, 2.79e-13, 181.0),
]


def _atmospheric_density(altitude_km: float) -> float:
    """Approximate atmospheric density at altitude (kg/m^3)."""
    if altitude_km < 200:
        return 1e-9
    if altitude_km > 1500:
        return 1e-15
    best = _ATM_LAYERS[0]
    for layer in _ATM_LAYERS:
        if layer[0] <= altitude_km:
            best = layer
    h0, rho0, H = best
    return rho0 * math.exp(-(altitude_km - h0) / H)


def _orbital_velocity_km_s(altitude_km: float) -> float:
    return math.sqrt(MU_EARTH / (R_EARTH_KM + altitude_km))


def _orbital_period_s(altitude_km: float) -> float:
    a = R_EARTH_KM + altitude_km
    return 2 * math.pi * math.sqrt(a ** 3 / MU_EARTH)


def _orbital_lifetime_years(altitude_km: float, ballistic_coeff_kg_m2: float) -> float:
    """Estimate orbital lifetime from altitude and ballistic coefficient.

    Uses semi-analytical drag decay integration with simplified atmospheric model.
    ballistic_coeff = mass / (Cd * A).
    """
    if altitude_km > 1500:
        return 1000.0
    if altitude_km < 200:
        return 0.01

    dt_days = 1.0
    alt = altitude_km
    elapsed_days = 0.0
    max_days = 1000 * 365.25

    while alt > 180 and elapsed_days < max_days:
        rho = _atmospheric_density(alt)
        r = (R_EARTH_KM + alt) * 1000.0
        v = math.sqrt(MU_EARTH * 1e9 / r)  # m/s
        # da/dt = -rho * v * a / BC  (simplified King-Hele)
        decay_rate_m_per_s = rho * v * r / ballistic_coeff_kg_m2
        decay_km_per_day = decay_rate_m_per_s * 86400 / 1000.0

        step = min(dt_days, max(0.1, alt / max(decay_km_per_day, 1e-12) * 0.05))
        alt -= decay_km_per_day * step
        elapsed_days += step

        if decay_km_per_day < 1e-8:
            return max_days / 365.25

    return elapsed_days / 365.25


# ---------------------------------------------------------------------------
# 1. NASA Standard Breakup Model (SBM)
# ---------------------------------------------------------------------------

class BreakupType(str, Enum):
    COLLISION = "collision"
    EXPLOSION = "explosion"


@dataclass
class Fragment:
    characteristic_length_m: float
    area_m2: float
    mass_kg: float
    area_to_mass: float
    delta_v_m_s: float


@dataclass
class BreakupResult:
    breakup_type: BreakupType
    parent_mass_kg: float
    total_fragments: int
    fragments_by_bin: dict  # {lc_bin_m: count}
    sample_fragments: List[Fragment]
    total_fragment_mass_kg: float
    total_cross_section_m2: float


def nasa_standard_breakup_model(
    parent_mass_kg: float,
    characteristic_length_m: float,
    breakup_type: BreakupType = BreakupType.COLLISION,
    target_mass_kg: float = 0.0,
    min_fragment_size_m: float = 0.01,
    num_size_bins: int = 20,
) -> BreakupResult:
    """NASA Standard Breakup Model (2001 revision).

    For collisions: N(Lc) = 0.1 * M_tot^0.75 * Lc^(-1.71)
    For explosions: N(Lc) = 6 * Lc^(-1.6)
    where N is cumulative number of fragments >= Lc.

    Area-to-mass ratio from log-normal distributions per Johnson et al.
    Delta-V from Maxwell-Boltzmann-like distribution.
    """
    if breakup_type == BreakupType.COLLISION:
        m_total = parent_mass_kg + target_mass_kg
        def cum_n(lc):
            return 0.1 * m_total ** 0.75 * lc ** (-1.71)
    else:
        def cum_n(lc):
            return 6.0 * characteristic_length_m ** 0.75 * lc ** (-1.6)

    lc_max = characteristic_length_m
    lc_min = min_fragment_size_m
    if lc_min >= lc_max:
        lc_min = lc_max / 100

    log_min = math.log10(lc_min)
    log_max = math.log10(lc_max)
    step = (log_max - log_min) / num_size_bins

    bins = {}
    sample_fragments = []
    total_mass = 0.0
    total_area = 0.0

    for i in range(num_size_bins):
        lc_lo = 10 ** (log_min + i * step)
        lc_hi = 10 ** (log_min + (i + 1) * step)
        n_lo = cum_n(lc_lo)
        n_hi = cum_n(lc_hi)
        count = max(0, int(round(n_lo - n_hi)))

        lc_mid = (lc_lo + lc_hi) / 2
        bins[round(lc_mid, 4)] = count

        if count > 0:
            # A/M ratio: log-normal, mu depends on size
            if lc_mid < 0.08:
                am_mean = 0.4
            elif lc_mid < 0.5:
                am_mean = 0.15
            else:
                am_mean = 0.05
            a_over_m = am_mean

            area = math.pi * (lc_mid / 2) ** 2
            mass = area / a_over_m if a_over_m > 0 else 0.01

            # Delta-V: chi distribution with peak ~ 1-10 m/s for explosions,
            # up to km/s for collisions
            if breakup_type == BreakupType.COLLISION:
                v_rel = _orbital_velocity_km_s(500) * 1000  # typical ~7.5 km/s
                dv = v_rel * (lc_mid / characteristic_length_m) ** (-0.5) * 0.01
                dv = min(dv, v_rel)
            else:
                dv = 100.0 * (lc_mid / characteristic_length_m) ** (-0.3)
                dv = min(dv, 500.0)

            total_mass += mass * count
            total_area += area * count

            sample_fragments.append(Fragment(
                characteristic_length_m=round(lc_mid, 4),
                area_m2=round(area, 6),
                mass_kg=round(mass, 4),
                area_to_mass=round(a_over_m, 4),
                delta_v_m_s=round(dv, 1),
            ))

    total_frags = sum(bins.values())

    return BreakupResult(
        breakup_type=breakup_type,
        parent_mass_kg=parent_mass_kg,
        total_fragments=total_frags,
        fragments_by_bin=bins,
        sample_fragments=sample_fragments,
        total_fragment_mass_kg=round(total_mass, 2),
        total_cross_section_m2=round(total_area, 4),
    )


# ---------------------------------------------------------------------------
# 2. ECOB Index
# ---------------------------------------------------------------------------

@dataclass
class ECOBResult:
    ecob_index: float
    total_fragments: int
    mean_lifetime_years: float
    total_cross_section_m2: float
    cumulative_collision_contribution: float
    rating: str  # "low", "medium", "high", "critical"


def compute_ecob(
    mass_kg: float,
    characteristic_length_m: float,
    altitude_km: float,
    inclination_deg: float,
    breakup_type: BreakupType = BreakupType.COLLISION,
    target_mass_kg: float = 0.0,
) -> ECOBResult:
    """Environmental Consequences of Orbital Breakups index.

    ECOB = sum_i(sigma_i * rho_spatial * v_rel * tau_i)
    where sigma = cross section, rho_spatial = spatial density of other objects,
    v_rel = relative velocity, tau = orbital lifetime of fragment.
    """
    sbm = nasa_standard_breakup_model(
        mass_kg, characteristic_length_m, breakup_type, target_mass_kg,
    )

    # Spatial density of trackable objects (approx, from MASTER)
    if altitude_km < 400:
        spatial_density = 1e-9  # obj/km^3
    elif altitude_km < 800:
        spatial_density = 2e-8
    elif altitude_km < 1000:
        spatial_density = 5e-8
    else:
        spatial_density = 1e-8

    # Inclination factor: higher density at common inclinations
    inc_factor = 1.0
    if 70 < inclination_deg < 110:
        inc_factor = 2.0
    elif 95 < inclination_deg < 105:
        inc_factor = 3.0

    spatial_density *= inc_factor

    v_rel = _orbital_velocity_km_s(altitude_km) * math.sqrt(2) * 1000  # m/s, avg relative

    ecob = 0.0
    lifetime_sum = 0.0
    total_cs = 0.0

    for frag in sbm.sample_fragments:
        count = sbm.fragments_by_bin.get(frag.characteristic_length_m, 1)
        bc = frag.mass_kg / max(frag.area_m2, 1e-6)
        lifetime = _orbital_lifetime_years(altitude_km, bc)
        cs = frag.area_m2

        contribution = cs * spatial_density * v_rel * lifetime * count
        ecob += contribution
        lifetime_sum += lifetime * count
        total_cs += cs * count

    total_frags = sbm.total_fragments
    mean_life = lifetime_sum / max(total_frags, 1)

    if ecob < 1e-3:
        rating = "low"
    elif ecob < 1e-1:
        rating = "medium"
    elif ecob < 10:
        rating = "high"
    else:
        rating = "critical"

    return ECOBResult(
        ecob_index=round(ecob, 6),
        total_fragments=total_frags,
        mean_lifetime_years=round(mean_life, 2),
        total_cross_section_m2=round(total_cs, 4),
        cumulative_collision_contribution=round(ecob, 6),
        rating=rating,
    )


# ---------------------------------------------------------------------------
# 3. DAS-style compliance check
# ---------------------------------------------------------------------------

@dataclass
class DebrisComplianceParams:
    mission_name: str
    altitude_km: float
    inclination_deg: float
    mass_kg: float
    cross_section_m2: float
    cd: float = 2.2
    mission_duration_years: float = 5.0
    # Req 1: operational debris
    operational_debris_count: int = 0
    operational_debris_orbit_lifetime_years: float = 25.0
    # Req 2: passivation
    stored_energy_j: float = 0.0
    passivation_planned: bool = True
    # Req 3: PMD orbit
    pmd_altitude_km: Optional[float] = None
    # Req 4: casualty
    casualty_risk: Optional[float] = None  # if pre-computed
    # Req 5: collision avoidance
    has_collision_avoidance: bool = True
    # Req 6: protected regions
    disposal_orbit_km: Optional[float] = None
    # Req 7: PMD reliability
    pmd_success_probability: float = 0.9


@dataclass
class ComplianceItem:
    requirement: str
    description: str
    compliant: bool
    details: str
    margin: Optional[float] = None


@dataclass
class ComplianceReport:
    mission_name: str
    overall_compliant: bool
    items: List[ComplianceItem]
    timestamp: str = ""


def check_debris_compliance(params: DebrisComplianceParams) -> ComplianceReport:
    items = []

    # Req 1: Debris released during operations
    req1_ok = params.operational_debris_count == 0 or (
        params.operational_debris_orbit_lifetime_years <= 25.0
    )
    items.append(ComplianceItem(
        requirement="SDM-01",
        description="Limit debris released during normal operations",
        compliant=req1_ok,
        details=f"{params.operational_debris_count} debris objects, "
                f"lifetime {params.operational_debris_orbit_lifetime_years:.1f} yr",
    ))

    # Req 2: Break-up potential
    req2_ok = params.passivation_planned and params.stored_energy_j < 1000
    items.append(ComplianceItem(
        requirement="SDM-02",
        description="Minimise break-up potential (passivation)",
        compliant=req2_ok,
        details=f"Stored energy {params.stored_energy_j:.0f} J, "
                f"passivation {'planned' if params.passivation_planned else 'NOT planned'}",
    ))

    # Req 3: Post-mission disposal (25-year rule)
    bc = params.mass_kg / (params.cd * params.cross_section_m2)
    pmd_alt = params.pmd_altitude_km if params.pmd_altitude_km is not None else params.altitude_km
    lifetime = _orbital_lifetime_years(pmd_alt, bc)
    req3_ok = lifetime <= 25.0
    items.append(ComplianceItem(
        requirement="SDM-03",
        description="25-year post-mission disposal rule",
        compliant=req3_ok,
        details=f"Estimated orbital lifetime from {pmd_alt:.0f} km: {lifetime:.1f} yr",
        margin=25.0 - lifetime if lifetime <= 25.0 else None,
    ))

    # Req 4: Casualty risk < 1:10,000
    if params.casualty_risk is not None:
        cas_risk = params.casualty_risk
    else:
        # Simple estimate: assume ~20% of mass survives, casualty area ~ 10 m^2
        surviving_mass_frac = 0.2
        cas_area = surviving_mass_frac * params.mass_kg * 0.01  # ~0.01 m^2/kg surviving
        cas_area = min(cas_area, 50.0)
        # Fraction of Earth under orbit (latitude band)
        inc_rad = math.radians(params.inclination_deg)
        earth_frac = min(1.0, math.sin(inc_rad)) if params.inclination_deg < 90 else 1.0
        cas_risk = cas_area * WORLD_POP_DENSITY * earth_frac / 1e6
    req4_ok = cas_risk < 1e-4
    items.append(ComplianceItem(
        requirement="SDM-04",
        description="On-ground casualty risk < 1:10,000",
        compliant=req4_ok,
        details=f"Estimated casualty expectation: {cas_risk:.2e}",
        margin=1e-4 - cas_risk if req4_ok else None,
    ))

    # Req 5: Collision avoidance
    items.append(ComplianceItem(
        requirement="SDM-05",
        description="Collision avoidance capability",
        compliant=params.has_collision_avoidance,
        details="Collision avoidance " + ("available" if params.has_collision_avoidance else "NOT available"),
    ))

    # Req 6: Long-term interference with protected regions
    disp_alt = params.disposal_orbit_km if params.disposal_orbit_km is not None else pmd_alt
    in_leo = disp_alt < LEO_UPPER_KM
    in_geo = abs(disp_alt - GEO_ALTITUDE_KM) < GEO_PROTECTED_BAND_KM
    if in_leo:
        req6_ok = lifetime <= 25.0
        detail = f"LEO protected region. Disposal at {disp_alt:.0f} km, lifetime {lifetime:.1f} yr"
    elif in_geo:
        req6_ok = False
        detail = f"Disposal at {disp_alt:.0f} km is within GEO protected region"
    else:
        req6_ok = True
        detail = f"Disposal at {disp_alt:.0f} km is outside protected regions"
    items.append(ComplianceItem(
        requirement="SDM-06",
        description="No long-term interference with protected regions",
        compliant=req6_ok,
        details=detail,
    ))

    # Req 7: Disposal reliability
    req7_ok = params.pmd_success_probability >= 0.9
    items.append(ComplianceItem(
        requirement="SDM-07",
        description="PMD reliability >= 90%",
        compliant=req7_ok,
        details=f"PMD success probability: {params.pmd_success_probability:.1%}",
    ))

    overall = all(item.compliant for item in items)

    return ComplianceReport(
        mission_name=params.mission_name,
        overall_compliant=overall,
        items=items,
    )


# ---------------------------------------------------------------------------
# 4. Collision probability (ARES-style)
# ---------------------------------------------------------------------------

@dataclass
class CollisionResult:
    probability: float
    flux_m2_year: float
    kinetic_energy_j: float
    kinetic_energy_mj: float
    relative_velocity_km_s: float
    is_catastrophic: bool
    catastrophic_threshold_mj: float


def compute_collision_probability(
    altitude_km: float,
    cross_section_m2: float,
    mission_duration_years: float,
    object_mass_kg: float,
    impactor_mass_kg: float = 0.01,
    spatial_density_override: Optional[float] = None,
) -> CollisionResult:
    """Compute collision probability using spatial density approach.

    P = 1 - exp(-flux * sigma * T)
    flux = rho_spatial * v_rel
    Kinetic energy = 0.5 * m_impactor * v_rel^2

    Catastrophic threshold: KE / target_mass > 40 J/g (NASA criterion).
    """
    if spatial_density_override is not None:
        rho_s = spatial_density_override
    else:
        # Approximate spatial density (objects > 1cm per km^3)
        if altitude_km < 400:
            rho_s = 5e-9
        elif altitude_km < 600:
            rho_s = 2e-8
        elif altitude_km < 800:
            rho_s = 5e-8
        elif altitude_km < 1000:
            rho_s = 8e-8
        else:
            rho_s = 2e-8

    v_rel_km_s = _orbital_velocity_km_s(altitude_km) * math.sqrt(2)  # random encounter
    v_rel_m_s = v_rel_km_s * 1000

    flux = rho_s * v_rel_km_s  # per km^2 per year? No — need units fix
    # rho_s is #/km^3, v_rel in km/s → flux = rho_s * v_rel * (seconds_per_year)
    # to get #/km^2/year
    flux_km2_year = rho_s * v_rel_km_s * 365.25 * 86400
    flux_m2_year = flux_km2_year * 1e-6  # convert km^2 to m^2

    lam = flux_m2_year * cross_section_m2 * mission_duration_years
    prob = 1 - math.exp(-lam)

    ke = 0.5 * impactor_mass_kg * v_rel_m_s ** 2
    ke_mj = ke / 1e6

    # Catastrophic: KE / target_mass > 40 J/g = 40000 J/kg
    catastrophic_threshold = object_mass_kg * 40000 / 1e6  # MJ
    is_catastrophic = ke_mj > catastrophic_threshold

    return CollisionResult(
        probability=round(prob, 8),
        flux_m2_year=flux_m2_year,
        kinetic_energy_j=round(ke, 1),
        kinetic_energy_mj=round(ke_mj, 4),
        relative_velocity_km_s=round(v_rel_km_s, 2),
        is_catastrophic=is_catastrophic,
        catastrophic_threshold_mj=round(catastrophic_threshold, 4),
    )


# ---------------------------------------------------------------------------
# 5. Casualty risk / demisability (SARA/SESAM-style)
# ---------------------------------------------------------------------------

class MaterialType(str, Enum):
    ALUMINUM = "aluminum"
    STEEL = "steel"
    TITANIUM = "titanium"
    CFRP = "cfrp"
    COPPER = "copper"
    GLASS = "glass"
    ELECTRONICS = "electronics"
    BATTERY = "battery"


# (melt_temp_K, heat_of_fusion_J_per_kg, density_kg_m3)
_MATERIAL_PROPS = {
    MaterialType.ALUMINUM:   (933, 397000, 2700),
    MaterialType.STEEL:      (1800, 270000, 7800),
    MaterialType.TITANIUM:   (1941, 365000, 4500),
    MaterialType.CFRP:       (3800, 500000, 1600),  # decomposition temp
    MaterialType.COPPER:     (1358, 205000, 8900),
    MaterialType.GLASS:      (1400, 300000, 2500),
    MaterialType.ELECTRONICS:(1200, 300000, 3000),
    MaterialType.BATTERY:    (600, 200000, 2500),
}


@dataclass
class ReentryComponent:
    name: str
    material: MaterialType
    mass_kg: float
    dimensions_m: tuple  # (length, width, height) or (diameter, height) etc.
    melt_temperature_k: Optional[float] = None


@dataclass
class SurvivorComponent:
    name: str
    mass_kg: float
    casualty_area_m2: float
    survived: bool
    demise_altitude_km: float


@dataclass
class CasualtyRiskResult:
    total_components: int
    surviving_components: int
    surviving_mass_kg: float
    total_casualty_area_m2: float
    casualty_expectation: float
    compliant: bool  # < 1e-4
    components: List[SurvivorComponent]


def compute_casualty_risk(
    components: List[ReentryComponent],
    inclination_deg: float,
    entry_velocity_km_s: float = 7.8,
) -> CasualtyRiskResult:
    """Estimate on-ground casualty risk from re-entry survivors.

    For each component, estimate if it survives based on heat load vs
    thermal capacity. Surviving components contribute to casualty area
    (component cross-section + human cross-section of 0.36 m^2).
    """
    HUMAN_CROSS_SECTION = 0.36  # m^2
    ENTRY_HEAT_FLUX_PEAK = 3e5  # W/m^2, typical uncontrolled LEO re-entry
    ENTRY_HEATING_DURATION_S = 60.0  # simplified

    survivors = []
    total_cas_area = 0.0
    surviving_mass = 0.0

    for comp in components:
        props = _MATERIAL_PROPS.get(comp.material, _MATERIAL_PROPS[MaterialType.ALUMINUM])
        melt_t = comp.melt_temperature_k if comp.melt_temperature_k else props[0]
        hof = props[1]
        density = props[2]

        # Component characteristic dimension
        if len(comp.dimensions_m) >= 2:
            char_dim = max(comp.dimensions_m)
        else:
            char_dim = comp.dimensions_m[0]

        # Exposed area (simplified as largest face)
        if len(comp.dimensions_m) == 3:
            dims = sorted(comp.dimensions_m, reverse=True)
            exposed_area = dims[0] * dims[1]
        elif len(comp.dimensions_m) == 2:
            exposed_area = comp.dimensions_m[0] * comp.dimensions_m[1]
        else:
            exposed_area = char_dim ** 2

        # Heat absorbed
        total_heat = ENTRY_HEAT_FLUX_PEAK * exposed_area * ENTRY_HEATING_DURATION_S

        # Heat needed to melt component
        delta_t = melt_t - 300  # from room temp
        specific_heat = hof / (melt_t - 300) if melt_t > 300 else 500
        heat_to_melt = comp.mass_kg * (specific_heat * delta_t + hof)

        survived = total_heat < heat_to_melt

        # Demise altitude estimate (higher = demises earlier = better)
        if survived:
            demise_alt = 0.0
        else:
            # Fraction of heating needed gives rough altitude
            frac = heat_to_melt / max(total_heat, 1)
            demise_alt = 80 - 50 * frac  # between ~30 and ~80 km

        cas_area = 0.0
        if survived:
            cas_area = exposed_area + HUMAN_CROSS_SECTION
            total_cas_area += cas_area
            surviving_mass += comp.mass_kg

        survivors.append(SurvivorComponent(
            name=comp.name,
            mass_kg=comp.mass_kg,
            casualty_area_m2=round(cas_area, 4),
            survived=survived,
            demise_altitude_km=round(demise_alt, 1),
        ))

    # Earth fraction under orbit
    inc_rad = math.radians(min(inclination_deg, 180 - inclination_deg))
    earth_fraction = math.sin(inc_rad) if inc_rad > 0 else 1.0

    casualty_expectation = total_cas_area * WORLD_POP_DENSITY * earth_fraction / 1e6

    return CasualtyRiskResult(
        total_components=len(components),
        surviving_components=sum(1 for s in survivors if s.survived),
        surviving_mass_kg=round(surviving_mass, 2),
        total_casualty_area_m2=round(total_cas_area, 4),
        casualty_expectation=round(casualty_expectation, 8),
        compliant=casualty_expectation < 1e-4,
        components=survivors,
    )


# ---------------------------------------------------------------------------
# 6. Space Sustainability Rating (SSR)
# ---------------------------------------------------------------------------

class SSRGrade(str, Enum):
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"


@dataclass
class SSRParams:
    # Mission index
    altitude_km: float = 500.0
    has_collision_avoidance: bool = True
    is_trackable: bool = True
    trackable_from_ground: bool = True
    # Debris index
    pmd_planned: bool = True
    pmd_success_probability: float = 0.9
    passivation_planned: bool = True
    operational_debris_count: int = 0
    orbit_lifetime_years: float = 5.0
    # Data sharing
    shares_orbital_data: bool = True
    shares_conjunction_data: bool = True
    registered_with_unoosa: bool = True


@dataclass
class SSRResult:
    mission_score: float
    debris_score: float
    data_sharing_score: float
    total_score: float
    grade: SSRGrade
    max_score: float


def compute_ssr(params: SSRParams) -> SSRResult:
    # Mission index (0-40)
    mission = 0.0
    if params.altitude_km < LEO_UPPER_KM:
        mission += 5  # LEO preferred over higher orbits
    if params.has_collision_avoidance:
        mission += 15
    if params.is_trackable:
        mission += 10
    if params.trackable_from_ground:
        mission += 10

    # Debris index (0-40)
    debris = 0.0
    if params.pmd_planned:
        debris += 10
        debris += min(10, params.pmd_success_probability * 10)
    if params.passivation_planned:
        debris += 10
    if params.operational_debris_count == 0:
        debris += 5
    if params.orbit_lifetime_years <= 5:
        debris += 5
    elif params.orbit_lifetime_years <= 25:
        debris += 2

    # Data sharing (0-20)
    data = 0.0
    if params.shares_orbital_data:
        data += 8
    if params.shares_conjunction_data:
        data += 7
    if params.registered_with_unoosa:
        data += 5

    total = mission + debris + data

    if total >= 85:
        grade = SSRGrade.PLATINUM
    elif total >= 65:
        grade = SSRGrade.GOLD
    elif total >= 45:
        grade = SSRGrade.SILVER
    else:
        grade = SSRGrade.BRONZE

    return SSRResult(
        mission_score=round(mission, 1),
        debris_score=round(debris, 1),
        data_sharing_score=round(data, 1),
        total_score=round(total, 1),
        grade=grade,
        max_score=100.0,
    )


# ---------------------------------------------------------------------------
# 7. Export functions
# ---------------------------------------------------------------------------

def export_das_xml(params: DebrisComplianceParams) -> str:
    """Generate DAS-compatible XML input file content."""
    root = ET.Element("DAS_Input")
    root.set("version", "3.2")

    mission = ET.SubElement(root, "Mission")
    ET.SubElement(mission, "Name").text = params.mission_name
    ET.SubElement(mission, "Duration_years").text = str(params.mission_duration_years)

    orbit = ET.SubElement(root, "Orbit")
    ET.SubElement(orbit, "Altitude_km").text = str(params.altitude_km)
    ET.SubElement(orbit, "Inclination_deg").text = str(params.inclination_deg)

    sc = ET.SubElement(root, "Spacecraft")
    ET.SubElement(sc, "Mass_kg").text = str(params.mass_kg)
    ET.SubElement(sc, "CrossSection_m2").text = str(params.cross_section_m2)
    ET.SubElement(sc, "Cd").text = str(params.cd)

    passiv = ET.SubElement(root, "Passivation")
    ET.SubElement(passiv, "StoredEnergy_J").text = str(params.stored_energy_j)
    ET.SubElement(passiv, "Planned").text = str(params.passivation_planned).lower()

    pmd = ET.SubElement(root, "PMD")
    if params.pmd_altitude_km is not None:
        ET.SubElement(pmd, "DisposalAltitude_km").text = str(params.pmd_altitude_km)
    ET.SubElement(pmd, "SuccessProbability").text = str(params.pmd_success_probability)

    collision = ET.SubElement(root, "CollisionAvoidance")
    ET.SubElement(collision, "Capable").text = str(params.has_collision_avoidance).lower()

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def export_drama_config(
    altitude_km: float,
    inclination_deg: float,
    mass_kg: float,
    cross_section_m2: float,
    mission_name: str = "BEPI_Mission",
    epoch_year: int = 2027,
) -> str:
    """Generate DRAMA/OSCAR configuration file content."""
    lines = [
        f"# DRAMA/OSCAR Configuration - {mission_name}",
        f"# Generated by BEPI debris analysis module",
        f"",
        f"[MISSION]",
        f"name = {mission_name}",
        f"epoch = {epoch_year}-01-01T00:00:00Z",
        f"",
        f"[ORBIT]",
        f"semi_major_axis_km = {R_EARTH_KM + altitude_km:.3f}",
        f"eccentricity = 0.001",
        f"inclination_deg = {inclination_deg:.2f}",
        f"raan_deg = 0.0",
        f"arg_perigee_deg = 0.0",
        f"true_anomaly_deg = 0.0",
        f"",
        f"[SPACECRAFT]",
        f"mass_kg = {mass_kg:.2f}",
        f"cross_section_m2 = {cross_section_m2:.4f}",
        f"drag_coefficient = 2.2",
        f"srp_coefficient = 1.2",
        f"srp_area_m2 = {cross_section_m2:.4f}",
        f"",
        f"[SIMULATION]",
        f"propagation_mode = OSCAR",
        f"max_duration_years = 50",
        f"output_step_days = 1",
    ]
    return "\n".join(lines)


def export_master_config(
    altitude_km: float,
    inclination_deg: float,
    cross_section_m2: float,
    epoch_year: int = 2027,
    projection_years: int = 25,
    min_size_m: float = 0.01,
) -> str:
    """Generate ESA MASTER model input configuration."""
    lines = [
        f"# ESA MASTER Configuration",
        f"# Generated by BEPI debris analysis module",
        f"",
        f"[TARGET_ORBIT]",
        f"altitude_km = {altitude_km:.1f}",
        f"inclination_deg = {inclination_deg:.1f}",
        f"eccentricity = 0.001",
        f"",
        f"[TARGET_OBJECT]",
        f"cross_section_m2 = {cross_section_m2:.4f}",
        f"shape = sphere",
        f"",
        f"[ANALYSIS]",
        f"epoch_year = {epoch_year}",
        f"projection_years = {projection_years}",
        f"min_object_size_m = {min_size_m}",
        f"flux_reference_frame = target_fixed",
        f"",
        f"[POPULATION_SOURCES]",
        f"fragments = true",
        f"nonfragment_debris = true",
        f"spacecraft = true",
        f"rocket_bodies = true",
        f"sodium_potassium = true",
        f"paint_flakes = true",
        f"ejecta = true",
        f"multi_layer_insulation = true",
        f"meteoroids = true",
        f"",
        f"[OUTPUT]",
        f"flux_vs_size = true",
        f"flux_vs_velocity = true",
        f"flux_vs_direction = true",
        f"spatial_density = true",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. NIAO (Normalised Index of Atmospheric Occupation)
# ---------------------------------------------------------------------------

@dataclass
class NIAOResult:
    niao: float
    cross_section_m2: float
    orbital_lifetime_years: float
    reference_value: float
    rating: str  # "negligible", "low", "moderate", "high"


def compute_niao(
    altitude_km: float,
    mass_kg: float,
    cross_section_m2: float,
    cd: float = 2.2,
    reference_value: float = 100.0,
) -> NIAOResult:
    """Normalised Index of Atmospheric Occupation.

    NIAO = (cross_section * orbital_lifetime) / reference_value
    Reference value: 100 m^2-years (typical reference from literature).
    """
    bc = mass_kg / (cd * cross_section_m2)
    lifetime = _orbital_lifetime_years(altitude_km, bc)
    raw = cross_section_m2 * lifetime
    niao = raw / reference_value

    if niao < 0.01:
        rating = "negligible"
    elif niao < 0.1:
        rating = "low"
    elif niao < 1.0:
        rating = "moderate"
    else:
        rating = "high"

    return NIAOResult(
        niao=round(niao, 6),
        cross_section_m2=cross_section_m2,
        orbital_lifetime_years=round(lifetime, 2),
        reference_value=reference_value,
        rating=rating,
    )
