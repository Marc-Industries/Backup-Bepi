"""Structured report section generators for radiation, debris, and comparison data."""
from __future__ import annotations

from datetime import datetime


def generate_radiation_report_section(params: dict, results: dict) -> dict:
    alt = params.get("altitude_km", "N/A")
    inc = params.get("inclination_deg", "N/A")
    dose = results.get("total_dose_rad", results.get("dose_si_per_year", "N/A"))
    mission_years = params.get("mission_years", 1)

    table_rows = []
    for shield_mm, dose_val in results.get("dose_depth", {}).items():
        table_rows.append([str(shield_mm), f"{dose_val:.2e}"])

    if not table_rows and isinstance(dose, (int, float)):
        table_rows.append(["1.0", f"{dose:.2e}"])

    spectra_proton = results.get("proton_spectrum", {})
    spectra_electron = results.get("electron_spectrum", {})
    figure_data = {
        "dose_depth": {
            "type": "scatter",
            "x": [r[0] for r in table_rows],
            "y": [r[1] for r in table_rows],
            "xaxis": "Shielding (mm Al)",
            "yaxis": "Dose (rad Si)",
            "title": "Dose-Depth Curve",
        },
        "proton_spectrum": {
            "type": "scatter",
            "x": list(spectra_proton.keys()),
            "y": list(spectra_proton.values()),
            "xaxis": "Energy (MeV)",
            "yaxis": "Flux (#/cm2/s)",
            "title": "Proton Integral Spectrum",
        } if spectra_proton else None,
        "electron_spectrum": {
            "type": "scatter",
            "x": list(spectra_electron.keys()),
            "y": list(spectra_electron.values()),
            "xaxis": "Energy (MeV)",
            "yaxis": "Flux (#/cm2/s)",
            "title": "Electron Integral Spectrum",
        } if spectra_electron else None,
    }

    return {
        "title": "Radiation Environment Analysis",
        "summary_text": (
            f"Radiation analysis for {alt} km / {inc}° orbit, {mission_years}-year mission. "
            f"Total ionising dose behind 1 mm Al: {dose} rad(Si). "
            f"Models: AP-8 MAX (protons), AE-8 MAX (electrons)."
        ),
        "table_data": {
            "headers": ["Shielding (mm Al)", "TID rad(Si)"],
            "rows": table_rows,
        },
        "figure_data": {k: v for k, v in figure_data.items() if v},
        "export_files": [
            {"name": f"radiation_{alt}km_{inc}deg.csv", "format": "csv"},
            {"name": f"radiation_{alt}km_{inc}deg.tex", "format": "latex_table"},
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


def generate_debris_report_section(compliance: dict, ecob: dict | None = None,
                                   nacrac: dict | None = None, ssr: dict | None = None) -> dict:
    comp_rows = []
    for key, val in compliance.items():
        if isinstance(val, dict):
            comp_rows.append([key, str(val.get("status", val.get("compliant", ""))),
                              str(val.get("value", ""))])
        else:
            comp_rows.append([key, str(val), ""])

    summary_parts = [f"Debris compliance assessment with {len(comp_rows)} checks."]
    if ecob:
        summary_parts.append(f"ECOB index: {ecob.get('score', 'N/A')}.")
    if nacrac:
        summary_parts.append(f"Casualty risk: {nacrac.get('casualty_risk', 'N/A')}.")
    if ssr:
        summary_parts.append(f"SSR score: {ssr.get('score', 'N/A')}.")

    figure_data = {}
    if ecob and "breakdown" in ecob:
        cats = list(ecob["breakdown"].keys())
        vals = list(ecob["breakdown"].values())
        figure_data["ecob_breakdown"] = {
            "type": "bar",
            "x": cats,
            "y": vals,
            "title": "ECOB Score Breakdown",
        }

    return {
        "title": "Space Debris Compliance & Sustainability",
        "summary_text": " ".join(summary_parts),
        "table_data": {
            "headers": ["Check", "Status", "Value"],
            "rows": comp_rows,
        },
        "figure_data": figure_data,
        "export_files": [
            {"name": "debris_compliance.csv", "format": "csv"},
            {"name": "debris_compliance.tex", "format": "latex_table"},
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


def generate_comparison_report_section(internal: dict, imported: dict,
                                       source_tool: str) -> dict:
    all_keys = sorted(set(internal.keys()) | set(imported.keys()))
    rows = []
    deltas = []
    labels = []

    for key in all_keys:
        iv = internal.get(key)
        ev = imported.get(key)
        delta_pct = None
        if isinstance(iv, (int, float)) and isinstance(ev, (int, float)) and ev != 0:
            delta_pct = round((iv - ev) / abs(ev) * 100, 2)
        rows.append([key, _fmt(iv), _fmt(ev), _fmt(delta_pct)])
        if delta_pct is not None:
            labels.append(key)
            deltas.append(delta_pct)

    figure_data = {}
    if deltas:
        figure_data["delta_chart"] = {
            "type": "bar",
            "x": labels,
            "y": deltas,
            "title": f"BEPI vs {source_tool} — Relative Deviation (%)",
            "yaxis": "Deviation (%)",
        }

    return {
        "title": f"Comparison: BEPI vs {source_tool}",
        "summary_text": (
            f"Cross-validation of {len(rows)} fields between BEPI internal computation "
            f"and {source_tool} imported data. "
            f"Max deviation: {max(abs(d) for d in deltas):.1f}%." if deltas else
            f"Cross-validation with {source_tool}: no numeric fields to compare."
        ),
        "table_data": {
            "headers": ["Field", "BEPI", source_tool, "Delta (%)"],
            "rows": rows,
        },
        "figure_data": figure_data,
        "export_files": [
            {"name": f"comparison_bepi_vs_{source_tool.lower().replace(' ', '_')}.csv", "format": "csv"},
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}" if abs(v) < 1e6 else f"{v:.2e}"
    return str(v)
