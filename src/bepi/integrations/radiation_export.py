"""Radiation data export — generate files compatible with Systema, OMERE, SPENVIS, etc.

BEPI calculates radiation environment internally and exports results in standard
formats that other tools can import directly, bypassing the need for OMERE/SPENVIS.

Supported output formats:
- SPENVIS dose-depth TXT (importable by Systema, OMERE, TRAD tools)
- OMERE-compatible CSV
- SHIELDOSE-2 output format
- Systema CSV (dose-depth + fluences)
- Generic CSV (universal)
- Proton/electron differential & integral spectra
"""
from __future__ import annotations
from datetime import datetime
from dataclasses import dataclass

from bepi.integrations.spenvis import (
    estimate_radiation, estimate_deepspace_radiation,
    RADIATION_LOOKUP, DEEPSPACE_LOOKUP,
)


# Standard shielding thicknesses used by SPENVIS/OMERE/SHIELDOSE
STANDARD_SHIELDS_MM = [0.05, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0,
                       4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0, 50.0]

# Standard proton energies (MeV) for AP-8 integral spectrum
PROTON_ENERGIES_MEV = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 50.0,
                       70.0, 100.0, 150.0, 200.0, 300.0, 400.0]

# Standard electron energies (MeV) for AE-8 integral spectrum
ELECTRON_ENERGIES_MEV = [0.04, 0.1, 0.2, 0.4, 0.6, 1.0, 1.5, 2.0, 2.5,
                         3.0, 4.0, 5.0, 6.0, 7.0]


@dataclass
class RadiationExportParams:
    altitude_km: float = 550.0
    inclination_deg: float = 97.6
    mission_years: float = 5.0
    mission_name: str = "BEPI-SAT"
    mission_start: str = "2027-06-01"
    solar_activity: str = "solar_max"
    destination: str | None = None  # None = Earth orbit, else deep-space key


def _compute_dose_depth(params: RadiationExportParams) -> list[dict]:
    rows = []
    for t_mm in STANDARD_SHIELDS_MM:
        if params.destination:
            r = estimate_deepspace_radiation(params.destination, params.mission_years, t_mm, params.solar_activity)
            rows.append({
                "shielding_mm": t_mm,
                "shielding_mils": t_mm * 39.37,  # mm → mils (1mm = 39.37 mils)
                "trapped_proton_krad": r.get("trapped_tid_krad", 0),
                "trapped_electron_krad": 0,
                "bremsstrahlung_krad": 0,
                "solar_proton_krad": r.get("spe_tid_krad", 0),
                "gcr_krad": r.get("gcr_tid_krad", 0),
                "total_krad": r["total_tid_krad"],
            })
        else:
            r = estimate_radiation(params.altitude_km, params.inclination_deg,
                                   params.mission_years, t_mm)
            # Split TID into components (approximate for Earth orbit)
            total = r["tid_krad"]
            # Trapped electrons dominate in LEO, ~60-70% of total
            e_frac = 0.65
            p_frac = 0.25
            brem_frac = 0.10
            rows.append({
                "shielding_mm": t_mm,
                "shielding_mils": t_mm * 39.37,
                "trapped_proton_krad": round(total * p_frac, 3),
                "trapped_electron_krad": round(total * e_frac, 3),
                "bremsstrahlung_krad": round(total * brem_frac, 3),
                "solar_proton_krad": 0,
                "gcr_krad": 0,
                "total_krad": round(total, 3),
            })
    return rows


def _compute_proton_spectrum(params: RadiationExportParams) -> list[dict]:
    if params.destination:
        r = estimate_deepspace_radiation(params.destination, params.mission_years)
        base_fluence = r["proton_fluence_cm2"]
    else:
        r = estimate_radiation(params.altitude_km, params.inclination_deg, params.mission_years)
        base_fluence = r["proton_fluence_cm2"]

    rows = []
    for e in PROTON_ENERGIES_MEV:
        # AP-8 integral spectrum: power-law approximation flux(>E) ~ E^(-gamma)
        # gamma ~ 1.5 for trapped protons
        integral_fluence = base_fluence * (10.0 / e) ** 1.5 if e > 0 else base_fluence
        differential = integral_fluence * 1.5 / e if e > 0 else 0
        rows.append({
            "energy_MeV": e,
            "integral_fluence_cm2": integral_fluence,
            "differential_flux_cm2_MeV": differential / (params.mission_years * 365.25 * 86400),
        })
    return rows


def _compute_electron_spectrum(params: RadiationExportParams) -> list[dict]:
    if params.destination:
        r = estimate_deepspace_radiation(params.destination, params.mission_years)
        base_fluence = r["electron_fluence_cm2"]
    else:
        r = estimate_radiation(params.altitude_km, params.inclination_deg, params.mission_years)
        base_fluence = r["electron_fluence_cm2"]

    rows = []
    for e in ELECTRON_ENERGIES_MEV:
        integral_fluence = base_fluence * (1.0 / e) ** 2.5 if e > 0 else base_fluence
        differential = integral_fluence * 2.5 / e if e > 0 else 0
        rows.append({
            "energy_MeV": e,
            "integral_fluence_cm2": integral_fluence,
            "differential_flux_cm2_MeV": differential / (params.mission_years * 365.25 * 86400),
        })
    return rows


# ── SPENVIS-format output ───────────────────────────────────────────

def export_spenvis_dose_depth(params: RadiationExportParams) -> str:
    """Generate dose-depth curve in SPENVIS output TXT format.

    This format is directly importable by Systema and other tools that
    accept SPENVIS output files.
    """
    rows = _compute_dose_depth(params)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    dest_info = ""
    if params.destination:
        dest_info = f"Destination:      {params.destination}\n"
    else:
        dest_info = (f"Altitude:         {params.altitude_km} km\n"
                     f"Inclination:      {params.inclination_deg} deg\n")

    lines = [
        f"*  BEPI-SAT Radiation Analysis — SPENVIS-compatible output",
        f"*  Generated by BEPI on {now}",
        f"*",
        f"*  Mission:          {params.mission_name}",
        f"*  {dest_info.strip()}",
        f"*  Duration:         {params.mission_years} years",
        f"*  Start:            {params.mission_start}",
        f"*  Solar activity:   {params.solar_activity}",
        f"*  Model:            AP-8-MAX / AE-8-MAX / SHIELDOSE-2",
        f"*",
        f"*  Dose-Depth Curve (Si, centre of Al sphere)",
        f"*  Shielding in mm Al and mils Al",
        f"*",
        f"*  {'Shield(mm)':>12}  {'Shield(mils)':>12}  {'Trap.Prot':>12}  {'Trap.Elec':>12}  {'Bremss.':>12}  {'Sol.Prot':>12}  {'GCR':>12}  {'Total':>12}",
        f"*  {'':>12}  {'':>12}  {'(krad)':>12}  {'(krad)':>12}  {'(krad)':>12}  {'(krad)':>12}  {'(krad)':>12}  {'(krad)':>12}",
    ]

    for r in rows:
        lines.append(
            f"   {r['shielding_mm']:12.3f}  {r['shielding_mils']:12.1f}"
            f"  {r['trapped_proton_krad']:12.3e}  {r['trapped_electron_krad']:12.3e}"
            f"  {r['bremsstrahlung_krad']:12.3e}  {r['solar_proton_krad']:12.3e}"
            f"  {r['gcr_krad']:12.3e}  {r['total_krad']:12.3e}"
        )

    return "\n".join(lines) + "\n"


# ── OMERE-format output ─────────────────────────────────────────────

def export_omere_csv(params: RadiationExportParams) -> str:
    """Generate dose-depth in OMERE-compatible CSV format."""
    rows = _compute_dose_depth(params)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# BEPI Radiation Analysis — OMERE-compatible format",
        f"# Generated: {now}",
        f"# Mission: {params.mission_name} | Duration: {params.mission_years} yr",
        f"# Model: AP-8-MAX / AE-8-MAX / SHIELDOSE-2 approximation",
        f"Shielding (mm Al),Trapped Protons (krad),Trapped Electrons (krad),Bremsstrahlung (krad),Solar Protons (krad),Total Dose (krad)",
    ]

    for r in rows:
        lines.append(
            f"{r['shielding_mm']:.3f},{r['trapped_proton_krad']:.4e},"
            f"{r['trapped_electron_krad']:.4e},{r['bremsstrahlung_krad']:.4e},"
            f"{r['solar_proton_krad']:.4e},{r['total_krad']:.4e}"
        )

    return "\n".join(lines) + "\n"


# ── SHIELDOSE-2 output format ───────────────────────────────────────

def export_shieldose2(params: RadiationExportParams) -> str:
    """Generate dose-depth in SHIELDOSE-2 output format.

    Standard format used by radiation engineers, importable by many tools.
    """
    rows = _compute_dose_depth(params)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"SHIELDOSE-2 OUTPUT — Generated by BEPI ({now})",
        f"Mission: {params.mission_name}",
        f"Duration: {params.mission_years} years from {params.mission_start}",
        "",
        "DOSE IN SILICON AT CENTRE OF ALUMINIUM SPHERE",
        "",
        f"{'Thickness':>12} {'Thickness':>12} {'Trapped':>14} {'Trapped':>14} {'Bremss':>14} {'Solar':>14} {'Total':>14}",
        f"{'(mils Al)':>12} {'(mm Al)':>12} {'Protons':>14} {'Electrons':>14} {'':>14} {'Protons':>14} {'Dose':>14}",
        f"{'':>12} {'':>12} {'(rads Si)':>14} {'(rads Si)':>14} {'(rads Si)':>14} {'(rads Si)':>14} {'(rads Si)':>14}",
        "-" * 94,
    ]

    for r in rows:
        # Convert krad to rad for SHIELDOSE format
        lines.append(
            f"{r['shielding_mils']:12.1f} {r['shielding_mm']:12.3f}"
            f" {r['trapped_proton_krad']*1000:14.2e} {r['trapped_electron_krad']*1000:14.2e}"
            f" {r['bremsstrahlung_krad']*1000:14.2e} {r['solar_proton_krad']*1000:14.2e}"
            f" {r['total_krad']*1000:14.2e}"
        )

    return "\n".join(lines) + "\n"


# ── Systema CSV format ──────────────────────────────────────────────

def export_systema_csv(params: RadiationExportParams) -> str:
    """Generate radiation data in CSV format importable by Airbus Systema.

    Systema accepts CSV with dose-depth curves and particle fluences.
    Includes both dose-depth and integral spectra in separate sections.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    dose_rows = _compute_dose_depth(params)
    proton_rows = _compute_proton_spectrum(params)
    electron_rows = _compute_electron_spectrum(params)

    lines = [
        f"# BEPI Radiation Export for Systema",
        f"# Generated: {now}",
        f"# Mission: {params.mission_name}",
        f"# Duration: {params.mission_years} years",
        f"# Solar activity: {params.solar_activity}",
        f"#",
        f"# SECTION: DOSE_DEPTH",
        f"Shielding_mm_Al,Shielding_mils_Al,TID_Total_krad,TID_TrappedProton_krad,TID_TrappedElectron_krad,TID_Bremsstrahlung_krad,TID_SolarProton_krad,TID_GCR_krad",
    ]

    for r in dose_rows:
        lines.append(
            f"{r['shielding_mm']:.3f},{r['shielding_mils']:.1f},"
            f"{r['total_krad']:.4e},{r['trapped_proton_krad']:.4e},"
            f"{r['trapped_electron_krad']:.4e},{r['bremsstrahlung_krad']:.4e},"
            f"{r['solar_proton_krad']:.4e},{r['gcr_krad']:.4e}"
        )

    lines.append("")
    lines.append("# SECTION: PROTON_SPECTRUM")
    lines.append("Energy_MeV,Integral_Fluence_cm2,Differential_Flux_cm2_s_MeV")
    for r in proton_rows:
        lines.append(f"{r['energy_MeV']:.2f},{r['integral_fluence_cm2']:.4e},{r['differential_flux_cm2_MeV']:.4e}")

    lines.append("")
    lines.append("# SECTION: ELECTRON_SPECTRUM")
    lines.append("Energy_MeV,Integral_Fluence_cm2,Differential_Flux_cm2_s_MeV")
    for r in electron_rows:
        lines.append(f"{r['energy_MeV']:.3f},{r['integral_fluence_cm2']:.4e},{r['differential_flux_cm2_MeV']:.4e}")

    return "\n".join(lines) + "\n"


# ── Generic CSV ─────────────────────────────────────────────────────

def export_generic_csv(params: RadiationExportParams) -> str:
    """Simple dose-depth CSV, importable anywhere."""
    rows = _compute_dose_depth(params)
    lines = ["Shielding_mm_Al,Total_TID_krad"]
    for r in rows:
        lines.append(f"{r['shielding_mm']:.3f},{r['total_krad']:.4e}")
    return "\n".join(lines) + "\n"


# ── Proton spectrum export ──────────────────────────────────────────

def export_proton_spectrum(params: RadiationExportParams) -> str:
    """AP-8 style integral proton spectrum, SPENVIS-compatible format."""
    rows = _compute_proton_spectrum(params)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"* BEPI Proton Spectrum — AP-8-MAX compatible ({now})",
        f"* Mission: {params.mission_name} | {params.mission_years} yr",
        f"*",
        f"* {'Energy (MeV)':>14}  {'Integral Fluence (cm-2)':>22}  {'Diff. Flux (cm-2 s-1 MeV-1)':>28}",
    ]
    for r in rows:
        lines.append(f"  {r['energy_MeV']:14.2f}  {r['integral_fluence_cm2']:22.4e}  {r['differential_flux_cm2_MeV']:28.4e}")

    return "\n".join(lines) + "\n"


# ── Electron spectrum export ────────────────────────────────────────

def export_electron_spectrum(params: RadiationExportParams) -> str:
    """AE-8 style integral electron spectrum, SPENVIS-compatible format."""
    rows = _compute_electron_spectrum(params)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"* BEPI Electron Spectrum — AE-8-MAX compatible ({now})",
        f"* Mission: {params.mission_name} | {params.mission_years} yr",
        f"*",
        f"* {'Energy (MeV)':>14}  {'Integral Fluence (cm-2)':>22}  {'Diff. Flux (cm-2 s-1 MeV-1)':>28}",
    ]
    for r in rows:
        lines.append(f"  {r['energy_MeV']:14.3f}  {r['integral_fluence_cm2']:22.4e}  {r['differential_flux_cm2_MeV']:28.4e}")

    return "\n".join(lines) + "\n"


# ── All-in-one export ───────────────────────────────────────────────

EXPORT_FORMATS = {
    "spenvis": ("SPENVIS TXT (dose-depth)", export_spenvis_dose_depth, ".txt"),
    "omere": ("OMERE CSV (dose-depth)", export_omere_csv, ".csv"),
    "shieldose2": ("SHIELDOSE-2 (dose-depth, rads Si)", export_shieldose2, ".txt"),
    "systema": ("Systema CSV (dose + spectra)", export_systema_csv, ".csv"),
    "generic": ("Generic CSV (dose-depth)", export_generic_csv, ".csv"),
    "proton_spectrum": ("Proton spectrum (AP-8 format)", export_proton_spectrum, ".txt"),
    "electron_spectrum": ("Electron spectrum (AE-8 format)", export_electron_spectrum, ".txt"),
}
