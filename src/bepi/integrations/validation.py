"""Benchmark validation for radiation and debris computations."""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# ── Radiation Benchmarks (AP-8/AE-8 known values) ──────────────────────

@dataclass
class RadiationBenchmark:
    label: str
    altitude_km: float
    inclination_deg: float
    dose_si_per_year: float  # rad(Si)/year behind 1mm Al
    proton_flux_gt10MeV: float  # #/cm2/s integral flux
    electron_flux_gt1MeV: float  # #/cm2/s integral flux
    source: str = "AP-8/AE-8 MAX"

RADIATION_BENCHMARKS = [
    RadiationBenchmark(
        label="ISS orbit",
        altitude_km=400, inclination_deg=51.6,
        dose_si_per_year=8.0e3,
        proton_flux_gt10MeV=1.5e3,
        electron_flux_gt1MeV=2.0e4,
    ),
    RadiationBenchmark(
        label="SSO 550km",
        altitude_km=550, inclination_deg=97.6,
        dose_si_per_year=1.5e4,
        proton_flux_gt10MeV=3.0e3,
        electron_flux_gt1MeV=5.0e4,
    ),
    RadiationBenchmark(
        label="SSO 800km",
        altitude_km=800, inclination_deg=98.6,
        dose_si_per_year=5.0e4,
        proton_flux_gt10MeV=1.0e4,
        electron_flux_gt1MeV=3.0e5,
    ),
    RadiationBenchmark(
        label="MEO 20200km (GPS)",
        altitude_km=20200, inclination_deg=55.0,
        dose_si_per_year=1.0e5,
        proton_flux_gt10MeV=2.0e4,
        electron_flux_gt1MeV=1.0e6,
    ),
    RadiationBenchmark(
        label="GEO",
        altitude_km=35786, inclination_deg=0.0,
        dose_si_per_year=5.0e4,
        proton_flux_gt10MeV=5.0e2,
        electron_flux_gt1MeV=5.0e5,
    ),
]


# ── Debris Benchmarks (NASA SBM known events) ──────────────────────────

@dataclass
class DebrisBenchmark:
    label: str
    event_type: str  # "collision" or "explosion"
    total_fragments_gt10cm: int
    total_fragments_gt1cm: int
    characteristic_length_m: float
    source: str = "NASA SBM"

DEBRIS_BENCHMARKS = [
    DebrisBenchmark(
        label="Cosmos-Iridium (2009)",
        event_type="collision",
        total_fragments_gt10cm=2296,
        total_fragments_gt1cm=100000,
        characteristic_length_m=0.1,
    ),
    DebrisBenchmark(
        label="Fengyun-1C ASAT (2007)",
        event_type="collision",
        total_fragments_gt10cm=3438,
        total_fragments_gt1cm=150000,
        characteristic_length_m=0.1,
    ),
    DebrisBenchmark(
        label="Cosmos-1408 ASAT (2021)",
        event_type="collision",
        total_fragments_gt10cm=1500,
        total_fragments_gt1cm=50000,
        characteristic_length_m=0.1,
    ),
    DebrisBenchmark(
        label="DMSP-F13 battery explosion (2015)",
        event_type="explosion",
        total_fragments_gt10cm=149,
        total_fragments_gt1cm=5000,
        characteristic_length_m=0.05,
    ),
]


# ── Validation Functions ────────────────────────────────────────────────

def _pct_deviation(computed: float, reference: float) -> float:
    if reference == 0:
        return 0.0 if computed == 0 else float("inf")
    return abs(computed - reference) / abs(reference) * 100.0


def validate_radiation(params: dict, computed_results: dict) -> dict:
    alt = params.get("altitude_km", 0)
    inc = params.get("inclination_deg", 0)

    best_match = min(
        RADIATION_BENCHMARKS,
        key=lambda b: math.hypot(b.altitude_km - alt, (b.inclination_deg - inc) * 50)
    )

    deviations = {}
    field_map = {
        "dose_si_per_year": "dose_si_per_year",
        "total_dose_rad": "dose_si_per_year",
        "proton_flux_gt10MeV": "proton_flux_gt10MeV",
        "proton_flux": "proton_flux_gt10MeV",
        "electron_flux_gt1MeV": "electron_flux_gt1MeV",
        "electron_flux": "electron_flux_gt1MeV",
    }

    for comp_key, bench_attr in field_map.items():
        if comp_key in computed_results:
            ref = getattr(best_match, bench_attr)
            dev = _pct_deviation(computed_results[comp_key], ref)
            deviations[comp_key] = {
                "computed": computed_results[comp_key],
                "benchmark": ref,
                "deviation_pct": round(dev, 2),
                "within_50pct": dev <= 50.0,
            }

    return {
        "benchmark_used": best_match.label,
        "benchmark_source": best_match.source,
        "altitude_match_km": best_match.altitude_km,
        "inclination_match_deg": best_match.inclination_deg,
        "deviations": deviations,
        "overall_valid": all(d["within_50pct"] for d in deviations.values()),
    }


def validate_debris(params: dict, computed_results: dict) -> dict:
    event_type = params.get("event_type", "collision")
    benchmarks = [b for b in DEBRIS_BENCHMARKS if b.event_type == event_type]
    if not benchmarks:
        benchmarks = DEBRIS_BENCHMARKS

    best = benchmarks[0]

    deviations = {}
    field_map = {
        "fragments_gt10cm": "total_fragments_gt10cm",
        "fragments_gt1cm": "total_fragments_gt1cm",
        "total_fragments_gt10cm": "total_fragments_gt10cm",
        "total_fragments_gt1cm": "total_fragments_gt1cm",
    }

    for comp_key, bench_attr in field_map.items():
        if comp_key in computed_results:
            ref = getattr(best, bench_attr)
            dev = _pct_deviation(computed_results[comp_key], ref)
            deviations[comp_key] = {
                "computed": computed_results[comp_key],
                "benchmark": ref,
                "deviation_pct": round(dev, 2),
                "within_factor_2": dev <= 100.0,
            }

    return {
        "benchmark_used": best.label,
        "benchmark_source": best.source,
        "deviations": deviations,
        "overall_valid": all(d["within_factor_2"] for d in deviations.values()),
    }


def compare_internal_vs_imported(internal_data: dict, imported_data: dict) -> dict:
    all_keys = sorted(set(internal_data.keys()) | set(imported_data.keys()))
    rows = []
    for key in all_keys:
        iv = internal_data.get(key)
        ev = imported_data.get(key)
        delta = None
        delta_pct = None
        if isinstance(iv, (int, float)) and isinstance(ev, (int, float)):
            delta = iv - ev
            delta_pct = _pct_deviation(iv, ev) if ev != 0 else None

        rows.append({
            "field": key,
            "internal": iv,
            "imported": ev,
            "delta": delta,
            "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
        })

    numeric_rows = [r for r in rows if r["delta_pct"] is not None]
    max_dev = max((r["delta_pct"] for r in numeric_rows), default=0.0)
    avg_dev = (sum(r["delta_pct"] for r in numeric_rows) / len(numeric_rows)) if numeric_rows else 0.0

    return {
        "comparisons": rows,
        "summary": {
            "total_fields": len(rows),
            "numeric_fields": len(numeric_rows),
            "max_deviation_pct": round(max_dev, 2),
            "avg_deviation_pct": round(avg_dev, 2),
        },
    }
