from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PhaseOutput:
    phase_name: str
    body: str
    duration_days: float = 0.0
    radiation_tid_krad: float = 0.0
    proton_fluence_cm2: float = 0.0
    electron_fluence_cm2: float = 0.0
    debris_collision_prob: float = 0.0
    debris_impacts_gt_1mm: float = 0.0
    avg_power_w: float = 0.0
    peak_power_w: float = 0.0
    eclipse_fraction: float = 0.0
    thermal_cycles: int = 0
    delta_v_ms: float = 0.0
    active_subsystems: list[str] = field(default_factory=list)


@dataclass
class AggregatedOutput:
    total_duration_days: float = 0.0
    total_tid_krad: float = 0.0
    total_proton_fluence_cm2: float = 0.0
    total_electron_fluence_cm2: float = 0.0
    total_collision_prob: float = 0.0
    total_debris_impacts_gt_1mm: float = 0.0
    worst_case_power_w: float = 0.0
    total_thermal_cycles: int = 0
    total_delta_v_ms: float = 0.0
    phases: list[PhaseOutput] = field(default_factory=list)

    def summary_table(self) -> list[dict]:
        rows = []
        for p in self.phases:
            rows.append({
                "Phase": p.phase_name,
                "Body": p.body,
                "Duration (days)": round(p.duration_days, 1),
                "TID (krad)": round(p.radiation_tid_krad, 2),
                "Debris P(coll)": f"{p.debris_collision_prob:.2e}",
                "Avg Power (W)": round(p.avg_power_w, 1),
                "ΔV (m/s)": round(p.delta_v_ms, 1),
                "Subsystems": ", ".join(p.active_subsystems),
            })
        rows.append({
            "Phase": "**TOTAL**",
            "Body": "",
            "Duration (days)": round(self.total_duration_days, 1),
            "TID (krad)": round(self.total_tid_krad, 2),
            "Debris P(coll)": f"{self.total_collision_prob:.2e}",
            "Avg Power (W)": round(self.worst_case_power_w, 1),
            "ΔV (m/s)": round(self.total_delta_v_ms, 1),
            "Subsystems": "",
        })
        return rows


def aggregate(phases: list[PhaseOutput]) -> AggregatedOutput:
    out = AggregatedOutput(phases=phases)
    for p in phases:
        out.total_duration_days += p.duration_days
        out.total_tid_krad += p.radiation_tid_krad
        out.total_proton_fluence_cm2 += p.proton_fluence_cm2
        out.total_electron_fluence_cm2 += p.electron_fluence_cm2
        out.total_collision_prob += p.debris_collision_prob
        out.total_debris_impacts_gt_1mm += p.debris_impacts_gt_1mm
        out.total_thermal_cycles += p.thermal_cycles
        out.total_delta_v_ms += p.delta_v_ms
        if p.avg_power_w > out.worst_case_power_w:
            out.worst_case_power_w = p.avg_power_w
    return out
