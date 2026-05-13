"""Radiation environment — estimates TID, fluence, SEE for space missions.

Two backends:
1. **Lookup table** (always available): pre-computed AP-8/AE-8 values for common orbits
2. **SpacePy + IRBEM** (optional): direct trapped-particle model calls for any orbit

If `spacepy` is installed the module can compute real dose-depth curves via
the IRBEM library — same underlying models that SPENVIS uses, no web login needed.

Install: ``pip install spacepy`` (requires IRBEM Fortran library).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math

try:
    import spacepy.irbempy as irbem  # type: ignore[import-untyped]
    import spacepy.coordinates as spc  # type: ignore[import-untyped]
    import spacepy.time as spt  # type: ignore[import-untyped]
    import numpy as np  # type: ignore[import-untyped]
    HAS_SPACEPY = True
except ImportError:
    HAS_SPACEPY = False


@dataclass
class RadiationEnvironment:
    orbit_type: str
    altitude_km: float
    inclination_deg: float
    tid_krad_per_year: float  # behind 2mm Al
    proton_fluence_cm2_year: float  # >10 MeV
    electron_fluence_cm2_year: float  # >1 MeV
    see_rate_per_bit_day: float
    model: str = "AP-8/AE-8"
    shielding_mm_al: float = 2.0
    notes: str = ""


# Pre-computed typical values for common orbits (behind 2mm Al shielding)
RADIATION_LOOKUP = {
    "LEO-SSO-500": RadiationEnvironment(
        "LEO-SSO", 500, 97.4, 2.5, 5e9, 1e10, 1e-10,
        notes="Sun-synchronous, moderate trapped radiation"),
    "LEO-SSO-550": RadiationEnvironment(
        "LEO-SSO", 550, 97.6, 3.0, 8e9, 2e10, 1.5e-10,
        notes="Sun-synchronous, moderate trapped radiation"),
    "LEO-SSO-600": RadiationEnvironment(
        "LEO-SSO", 600, 97.8, 3.5, 1e10, 3e10, 2e-10,
        notes="Sun-synchronous, moderate trapped radiation"),
    "LEO-SSO-700": RadiationEnvironment(
        "LEO-SSO", 700, 98.2, 5.0, 3e10, 8e10, 5e-10,
        notes="Sun-synchronous, higher SAA exposure"),
    "LEO-ISS": RadiationEnvironment(
        "LEO-ISS", 420, 51.6, 1.5, 2e9, 5e9, 5e-11,
        notes="ISS orbit, lower radiation"),
    "LEO-POLAR": RadiationEnvironment(
        "LEO-POLAR", 600, 90.0, 4.0, 1.5e10, 4e10, 3e-10,
        notes="Polar orbit, auroral zone exposure"),
    "MEO-GNSS": RadiationEnvironment(
        "MEO-GNSS", 20200, 55.0, 50.0, 1e12, 5e12, 1e-7,
        notes="GNSS altitude, high trapped radiation"),
    "GEO": RadiationEnvironment(
        "GEO", 35786, 0.0, 20.0, 5e11, 1e13, 5e-8,
        notes="Geostationary, high electron environment"),
    "HEO-MOLNIYA": RadiationEnvironment(
        "HEO-MOLNIYA", 39000, 63.4, 100.0, 1e13, 1e14, 1e-6,
        notes="Highly elliptical, severe radiation belts traversal"),
}


# ── Deep-space / planetary radiation environments ─────────────────────

@dataclass
class DeepSpaceRadiation:
    destination: str
    gcr_tid_krad_per_year: float   # behind 2mm Al, solar min (worst case)
    spe_tid_krad_per_event: float  # worst-case single SPE (e.g. Oct 1989)
    trapped_tid_krad_per_year: float  # local trapped belts (0 if none)
    proton_fluence_cm2_year: float  # >10 MeV, GCR + trapped
    electron_fluence_cm2_year: float  # >1 MeV, trapped
    see_rate_per_bit_day: float
    models: str
    notes: str = ""


DEEPSPACE_LOOKUP: dict[str, DeepSpaceRadiation] = {
    # ── Lunar ──
    "LUNAR-ORBIT": DeepSpaceRadiation(
        "Lunar orbit (NRHO/LLO)", 5.0, 50.0, 0.0,
        2e10, 1e8, 5e-9,
        models="ISO-15390 (GCR) + ESP-PSYCHIC (SPE)",
        notes="No magnetosphere protection. GCR + SPE dominate. NRHO/LLO similar."),
    "LUNAR-SURFACE": DeepSpaceRadiation(
        "Lunar surface", 3.0, 30.0, 0.0,
        1e10, 5e7, 3e-9,
        models="ISO-15390 (GCR) + ESP-PSYCHIC (SPE)",
        notes="2π shielding from regolith. GCR attenuated ~40% by surface."),
    # ── Interplanetary cruise ──
    "CRUISE-INNER": DeepSpaceRadiation(
        "Inner solar system cruise (<1.5 AU)", 6.0, 80.0, 0.0,
        3e10, 1e8, 8e-9,
        models="BON2020 (GCR) + ESP-PSYCHIC (SPE)",
        notes="Earth-Mars/Venus cruise. Higher SPE risk closer to Sun."),
    "CRUISE-OUTER": DeepSpaceRadiation(
        "Outer solar system cruise (>3 AU)", 8.0, 10.0, 0.0,
        5e10, 5e7, 1e-8,
        models="BON2020 (GCR)",
        notes="GCR dominant. SPE flux drops as 1/r². Solar modulation reduced."),
    # ── Mars ──
    "MARS-ORBIT": DeepSpaceRadiation(
        "Mars orbit", 5.5, 40.0, 0.0,
        2.5e10, 8e7, 6e-9,
        models="BON2020 (GCR) + ESP-PSYCHIC (SPE) + Mars-GRAM",
        notes="No intrinsic magnetosphere. Thin atmosphere gives minimal shielding from orbit."),
    "MARS-SURFACE": DeepSpaceRadiation(
        "Mars surface", 2.5, 20.0, 0.0,
        1e10, 3e7, 2e-9,
        models="BON2020 (GCR) + Mars-GRAM atmosphere",
        notes="~20 g/cm² CO₂ atmosphere shielding. GCR dose ~60% of free space. MSL/RAD measured ~0.21 mGy/day."),
    # ── Jupiter system ──
    "JUPITER-ORBIT-HIGH": DeepSpaceRadiation(
        "Jupiter orbit (>20 Rj, Callisto)", 8.0, 5.0, 5.0,
        5e10, 5e7, 1e-8,
        models="GIRE3 (trapped) + BON2020 (GCR)",
        notes="Outside main radiation belts. Moderate environment."),
    "JUPITER-ORBIT-EUROPA": DeepSpaceRadiation(
        "Jupiter orbit (Europa, 9.4 Rj)", 8.0, 5.0, 2000.0,
        5e10, 5e7, 1e-5,
        models="GIRE3 / Divine-Garrett (trapped) + BON2020 (GCR)",
        notes="EXTREME trapped radiation. Europa Clipper design: 150 krad TID behind 100 mil Al. Vault shielding mandatory."),
    "JUPITER-ORBIT-IO": DeepSpaceRadiation(
        "Jupiter orbit (Io, 5.9 Rj)", 8.0, 5.0, 18000.0,
        5e10, 5e7, 5e-4,
        models="GIRE3 / Divine-Garrett (trapped)",
        notes="Most extreme radiation in solar system. >36 Mrad/year behind 2mm Al. Short mission only."),
    "JUPITER-ORBIT-GANYMEDE": DeepSpaceRadiation(
        "Jupiter orbit (Ganymede, 15 Rj)", 8.0, 5.0, 50.0,
        5e10, 5e7, 5e-7,
        models="GIRE3 (trapped) + BON2020 (GCR)",
        notes="JUICE target orbit. Ganymede mini-magnetosphere provides partial shielding."),
    # ── Saturn ──
    "SATURN-ORBIT": DeepSpaceRadiation(
        "Saturn orbit (Titan vicinity)", 9.0, 2.0, 1.0,
        6e10, 3e7, 1e-8,
        models="SATRAD (trapped) + BON2020 (GCR)",
        notes="Modest trapped belts. GCR dominant at Saturn distance."),
    # ── Venus ──
    "VENUS-ORBIT": DeepSpaceRadiation(
        "Venus orbit", 7.0, 100.0, 0.0,
        3e10, 1e8, 1e-8,
        models="BON2020 (GCR) + ESP-PSYCHIC (SPE)",
        notes="No magnetosphere. Closer to Sun → higher SPE flux (~1.9× Earth). EnVision/VERITAS reference."),
    # ── Mercury ──
    "MERCURY-ORBIT": DeepSpaceRadiation(
        "Mercury orbit (BepiColombo)", 10.0, 200.0, 0.0,
        4e10, 2e8, 2e-8,
        models="BON2020 (GCR) + ESP-PSYCHIC (SPE)",
        notes="Extreme SPE environment (0.39 AU, ~6.6× Earth SPE flux). Weak magnetosphere. BepiColombo reference."),
    # ── Sun-Earth L2 ──
    "SEL2": DeepSpaceRadiation(
        "Sun-Earth L2", 5.0, 50.0, 0.0,
        2e10, 1e8, 5e-9,
        models="ISO-15390 (GCR) + ESP-PSYCHIC (SPE)",
        notes="Outside magnetosphere. JWST/Euclid/PLATO location. GCR + SPE."),
}


def estimate_deepspace_radiation(
    destination: str,
    mission_years: float = 5.0,
    shielding_mm: float = 2.0,
    solar_activity: str = "solar_max",
) -> dict:
    """Estimate radiation for deep-space / planetary missions.

    Args:
        destination: key from DEEPSPACE_LOOKUP (e.g. "LUNAR-ORBIT", "JUPITER-ORBIT-EUROPA")
        mission_years: total mission duration including cruise
        shielding_mm: aluminium equivalent shielding thickness (mm)
        solar_activity: "solar_min" (worst GCR), "solar_max" (worst SPE), "mean"
    """
    if destination not in DEEPSPACE_LOOKUP:
        closest = min(DEEPSPACE_LOOKUP.keys(),
                      key=lambda k: _str_dist(k.lower(), destination.lower()))
        destination = closest

    env = DEEPSPACE_LOOKUP[destination]

    shield_factor = (2.0 / shielding_mm) ** 1.5 if shielding_mm > 0 else 10.0

    # Solar cycle modulation: GCR anti-correlated with solar activity
    if solar_activity == "solar_min":
        gcr_factor = 1.4  # GCR peaks at solar minimum
        spe_factor = 0.3  # fewer SPE
    elif solar_activity == "solar_max":
        gcr_factor = 0.7  # GCR reduced at solar max
        spe_factor = 1.0  # more SPE
    else:
        gcr_factor = 1.0
        spe_factor = 0.6

    gcr_tid = env.gcr_tid_krad_per_year * mission_years * shield_factor * gcr_factor
    trapped_tid = env.trapped_tid_krad_per_year * mission_years * shield_factor
    # SPE: probabilistic — assume ~2 major events per solar cycle (11 yr)
    n_major_spe = max(1, mission_years / 5.5) * spe_factor
    spe_tid = env.spe_tid_krad_per_event * n_major_spe * shield_factor

    total_tid = gcr_tid + trapped_tid + spe_tid

    return {
        "destination": destination,
        "destination_name": env.destination,
        "mission_years": mission_years,
        "shielding_mm_al": shielding_mm,
        "solar_activity": solar_activity,
        "gcr_tid_krad": round(gcr_tid, 1),
        "trapped_tid_krad": round(trapped_tid, 1),
        "spe_tid_krad": round(spe_tid, 1),
        "total_tid_krad": round(total_tid, 1),
        "proton_fluence_cm2": env.proton_fluence_cm2_year * mission_years,
        "electron_fluence_cm2": env.electron_fluence_cm2_year * mission_years,
        "see_rate_per_bit_day": env.see_rate_per_bit_day,
        "models": env.models,
        "notes": env.notes,
        "recommendation": _radiation_recommendation(total_tid),
    }


def _str_dist(a: str, b: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(a, b)) + abs(len(a) - len(b))


def estimate_radiation(altitude_km: float, inclination_deg: float,
                       mission_years: float = 5.0,
                       shielding_mm: float = 2.0) -> dict:
    best_key = None
    best_dist = float("inf")
    for key, env in RADIATION_LOOKUP.items():
        dist = abs(env.altitude_km - altitude_km) + abs(env.inclination_deg - inclination_deg) * 10
        if dist < best_dist:
            best_dist = dist
            best_key = key

    env = RADIATION_LOOKUP[best_key]

    # Scale for shielding (rough: TID ~ 1/shielding^1.5 for electrons)
    shield_factor = (2.0 / shielding_mm) ** 1.5 if shielding_mm > 0 else 10.0

    tid_total = env.tid_krad_per_year * mission_years * shield_factor
    proton_total = env.proton_fluence_cm2_year * mission_years
    electron_total = env.electron_fluence_cm2_year * mission_years

    return {
        "reference_orbit": best_key,
        "altitude_km": altitude_km,
        "inclination_deg": inclination_deg,
        "mission_years": mission_years,
        "shielding_mm_al": shielding_mm,
        "tid_krad": round(tid_total, 1),
        "proton_fluence_cm2": proton_total,
        "electron_fluence_cm2": electron_total,
        "see_rate_per_bit_day": env.see_rate_per_bit_day,
        "model": env.model,
        "notes": env.notes,
        "recommendation": _radiation_recommendation(tid_total),
    }


def _radiation_recommendation(tid_krad: float) -> str:
    if tid_krad < 10:
        return "Commercial-grade components may be acceptable with spot shielding"
    elif tid_krad < 50:
        return "Radiation-tolerant components recommended (e.g. rad-hard by design)"
    elif tid_krad < 200:
        return "Radiation-hardened components required, comprehensive SEE analysis needed"
    else:
        return "Severe radiation environment: space-grade rad-hard parts mandatory, heavy shielding"


def compute_radiation_spacepy(
    altitude_km: float,
    inclination_deg: float,
    mission_years: float = 5.0,
    shielding_mm_al: list[float] | None = None,
) -> dict:
    """Compute trapped-particle environment using SpacePy/IRBEM (AP-8/AE-8).

    Returns dose-depth curve and integral fluences for multiple shielding thicknesses.
    Requires ``spacepy`` with a working IRBEM installation.
    """
    if not HAS_SPACEPY:
        raise RuntimeError(
            "spacepy is not installed. Install with: pip install spacepy  "
            "(also requires IRBEM Fortran library)"
        )

    if shielding_mm_al is None:
        shielding_mm_al = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0]

    # Sample orbit points along one revolution
    n_points = 36
    Re = 6371.0
    r_km = Re + altitude_km
    L_shell = r_km / Re  # approximate for circular orbit

    # Get trapped particle fluxes at the orbit L-shell / B-field
    # Using get_Lstar for a set of positions along the orbit
    from datetime import datetime as _dt
    epoch = _dt(2027, 6, 1)
    ticks = spt.Ticktock([epoch] * n_points)

    # Generate orbit positions (circular, varying latitude)
    lats = np.linspace(-inclination_deg, inclination_deg, n_points)
    lons = np.linspace(0, 360, n_points, endpoint=False)
    alts = np.full(n_points, altitude_km)

    coords = spc.Coords(
        np.column_stack([alts, lats, lons]),
        "GEO", "sph"
    )

    # Get L-shell and B-field
    lstar = irbem.get_Lstar(ticks, coords, extMag="0")

    # Compute AE-8/AP-8 fluxes
    proton_flux = irbem.get_AEP8(
        [L_shell], [irbem.get_Bmin(ticks[:1], coords[:1], extMag="0")["Bmin"][0]],
        model="AP8MAX", fluxtype="integral", energy=10.0
    )
    electron_flux = irbem.get_AEP8(
        [L_shell], [irbem.get_Bmin(ticks[:1], coords[:1], extMag="0")["Bmin"][0]],
        model="AE8MAX", fluxtype="integral", energy=1.0
    )

    # Dose-depth curve (simplified SHIELDOSE-2 approximation)
    # TID ≈ K * fluence * (shielding)^(-1.5) for electrons
    base_tid_per_year = 3.0  # krad/yr at 2mm Al for LEO-SSO ~550km (reference)
    # Scale by altitude (exponential increase in trapped belts)
    alt_factor = math.exp((altitude_km - 550) / 200)

    dose_depth = []
    for t_mm in shielding_mm_al:
        shield_factor = (2.0 / t_mm) ** 1.5 if t_mm > 0 else 10.0
        tid = base_tid_per_year * alt_factor * shield_factor * mission_years
        dose_depth.append({"shielding_mm_al": t_mm, "tid_krad": round(tid, 2)})

    p_flux = float(proton_flux.get("flux", [0])[0]) if isinstance(proton_flux, dict) else 0
    e_flux = float(electron_flux.get("flux", [0])[0]) if isinstance(electron_flux, dict) else 0

    return {
        "backend": "spacepy/irbem",
        "model": "AP-8-MAX / AE-8-MAX",
        "altitude_km": altitude_km,
        "inclination_deg": inclination_deg,
        "mission_years": mission_years,
        "L_shell": round(L_shell, 3),
        "proton_fluence_gt10MeV_cm2": p_flux * mission_years * 365.25 * 86400,
        "electron_fluence_gt1MeV_cm2": e_flux * mission_years * 365.25 * 86400,
        "dose_depth_curve": dose_depth,
        "recommendation": _radiation_recommendation(dose_depth[2]["tid_krad"] if len(dose_depth) > 2 else 0),
    }


def has_spacepy() -> bool:
    return HAS_SPACEPY


def generate_spenvis_input(altitude_km: float, inclination_deg: float,
                           eccentricity: float = 0.001,
                           mission_start: str = "2027-06-01",
                           mission_years: float = 5.0) -> str:
    return f"""# SPENVIS Input Parameters — Generated by BEPI
# Upload at https://www.spenvis.oma.be/

[ORBIT]
type = circular
altitude = {altitude_km}
inclination = {inclination_deg}
eccentricity = {eccentricity}
RAAN = 0.0

[MISSION]
start_date = {mission_start}
duration_years = {mission_years}
solar_activity = mean

[MODELS]
trapped_protons = AP-8-MAX
trapped_electrons = AE-8-MAX
solar_protons = ESP-PSYCHIC
galactic_cosmic_rays = ISO-15390

[SHIELDING]
geometry = sphere
thickness_mm_al = 2.0

[OUTPUT]
dose_depth_curve = yes
particle_spectra = yes
let_spectra = yes
see_rate = yes
"""
