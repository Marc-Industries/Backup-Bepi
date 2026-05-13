from dataclasses import dataclass, field
import math
import numpy as np
import plotly.graph_objects as go
import io, csv

SOLAR_CONSTANT = 1361.0  # W/m²
R_EARTH_KM = 6371.0

@dataclass
class SolarArrayParams:
    area_m2: float
    efficiency: float = 0.30
    degradation_per_year: float = 0.02
    packing_factor: float = 0.9
    n_wings: int = 2
    tracking: str = "fixed"  # "fixed" | "1axis" | "2axis"

@dataclass
class OrbitLightingParams:
    altitude_km: float
    inclination_deg: float
    beta_angle_deg: float = 0.0
    epoch_year: int = 2027

@dataclass
class PowerProfile:
    orbit_angles: list[float] = field(default_factory=list)
    power_w: list[float] = field(default_factory=list)
    avg_power_sunlit_w: float = 0.0
    avg_power_orbit_w: float = 0.0
    eclipse_fraction: float = 0.0
    eclipse_duration_min: float = 0.0
    peak_power_w: float = 0.0
    eol_degradation: float = 0.0
    battery_doc: float = 0.0
    bol_power_w: float = 0.0
    eol_power_w: float = 0.0

@dataclass
class BatterySizing:
    capacity_wh: float
    capacity_ah: float
    n_cycles_per_day: float
    eol_capacity_wh: float


def compute_eclipse_fraction(altitude_km: float, beta_angle_deg: float) -> float:
    beta = math.radians(beta_angle_deg)
    rho = math.asin(R_EARTH_KM / (R_EARTH_KM + altitude_km))
    if abs(beta) < rho:
        cos_ratio = math.cos(rho) / math.cos(beta)
        cos_ratio = max(-1.0, min(1.0, cos_ratio))
        return (1.0 / math.pi) * math.acos(cos_ratio)
    return 0.0


def _orbit_period_min(altitude_km: float) -> float:
    mu = 3.986e5  # km^3/s^2
    a = R_EARTH_KM + altitude_km
    return 2.0 * math.pi * math.sqrt(a**3 / mu) / 60.0


def compute_solar_power_profile(
    sa_params: SolarArrayParams,
    orbit_params: OrbitLightingParams,
    mission_year: int,
) -> PowerProfile:
    ef = compute_eclipse_fraction(orbit_params.altitude_km, orbit_params.beta_angle_deg)
    period = _orbit_period_min(orbit_params.altitude_km)
    eclipse_deg = ef * 360.0
    eclipse_start = 180.0 - eclipse_deg / 2.0
    eclipse_end = 180.0 + eclipse_deg / 2.0

    years_in_service = max(0, mission_year - orbit_params.epoch_year)
    eol_deg = 1.0 - (1.0 - sa_params.degradation_per_year) ** years_in_service

    total_area = sa_params.area_m2 * sa_params.n_wings * sa_params.packing_factor
    bol_peak = SOLAR_CONSTANT * total_area * sa_params.efficiency

    angles = [float(a) for a in range(361)]
    power = []
    for a in angles:
        if eclipse_start <= a <= eclipse_end:
            power.append(0.0)
            continue
        if sa_params.tracking == "2axis":
            inc_factor = 1.0
        elif sa_params.tracking == "1axis":
            inc_factor = abs(math.cos(math.radians(orbit_params.beta_angle_deg)))
        else:
            theta = a if a <= 180 else 360 - a
            inc_factor = max(0.0, math.cos(math.radians(theta - 90.0)))
        p = bol_peak * inc_factor
        power.append(p)

    sunlit = [p for p in power if p > 0]
    avg_sunlit = float(np.mean(sunlit)) if sunlit else 0.0
    avg_orbit = float(np.mean(power))
    peak = max(power) if power else 0.0
    eol_avg = avg_orbit * (1.0 - eol_deg)

    eclipse_min = ef * period
    battery_doc = ef / (1.0 - ef) if ef < 1.0 else 1.0

    return PowerProfile(
        orbit_angles=angles,
        power_w=power,
        avg_power_sunlit_w=avg_sunlit,
        avg_power_orbit_w=avg_orbit,
        eclipse_fraction=ef,
        eclipse_duration_min=eclipse_min,
        peak_power_w=peak,
        eol_degradation=eol_deg,
        battery_doc=battery_doc,
        bol_power_w=avg_orbit,
        eol_power_w=eol_avg,
    )


def compute_battery_sizing(
    power_eclipse_w: float,
    eclipse_duration_min: float,
    dod_max: float = 0.4,
    bus_voltage: float = 28.0,
    battery_efficiency: float = 0.95,
) -> BatterySizing:
    eclipse_h = eclipse_duration_min / 60.0
    energy_wh = power_eclipse_w * eclipse_h / battery_efficiency
    capacity_wh = energy_wh / dod_max
    capacity_ah = capacity_wh / bus_voltage
    orbit_period_approx = 90.0  # min, typical LEO
    n_cycles = 1440.0 / orbit_period_approx
    eol_capacity_wh = capacity_wh * 0.8  # 80% EOL retention typical
    return BatterySizing(
        capacity_wh=capacity_wh,
        capacity_ah=capacity_ah,
        n_cycles_per_day=n_cycles,
        eol_capacity_wh=eol_capacity_wh,
    )


def compute_power_budget_balance(
    generation: PowerProfile,
    consumption_modes: dict[str, float],
) -> dict[str, dict[str, float]]:
    result = {}
    for mode, consumption_w in consumption_modes.items():
        surplus_bol = generation.bol_power_w - consumption_w
        surplus_eol = generation.eol_power_w - consumption_w
        result[mode] = {
            "consumption_w": consumption_w,
            "generation_bol_w": generation.bol_power_w,
            "generation_eol_w": generation.eol_power_w,
            "surplus_bol_w": surplus_bol,
            "surplus_eol_w": surplus_eol,
            "status": "OK" if surplus_eol >= 0 else "DEFICIT",
        }
    return result


def export_systema_power_csv(profile: PowerProfile, sa_params: SolarArrayParams) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "OrbitAngle_deg", "Power_W", "Eclipse",
        "ArrayArea_m2", "Efficiency", "Tracking",
    ])
    for i, angle in enumerate(profile.orbit_angles):
        in_eclipse = 1 if profile.power_w[i] == 0.0 and profile.eclipse_fraction > 0 else 0
        w.writerow([
            f"{angle:.1f}",
            f"{profile.power_w[i]:.2f}",
            in_eclipse,
            f"{sa_params.area_m2:.3f}",
            f"{sa_params.efficiency:.3f}",
            sa_params.tracking,
        ])
    return buf.getvalue()


def plot_power_profile(profile: PowerProfile) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=profile.orbit_angles,
        y=profile.power_w,
        mode="lines",
        name="Power (BOL)",
        line=dict(color="#1f77b4", width=2),
    ))
    eol_power = [p * (1.0 - profile.eol_degradation) for p in profile.power_w]
    fig.add_trace(go.Scatter(
        x=profile.orbit_angles,
        y=eol_power,
        mode="lines",
        name="Power (EOL)",
        line=dict(color="#ff7f0e", width=2, dash="dash"),
    ))
    # shade eclipse
    eclipse_deg = profile.eclipse_fraction * 360.0
    if eclipse_deg > 0:
        e_start = 180.0 - eclipse_deg / 2.0
        e_end = 180.0 + eclipse_deg / 2.0
        fig.add_vrect(
            x0=e_start, x1=e_end,
            fillcolor="gray", opacity=0.2,
            annotation_text="Eclipse", annotation_position="top",
            line_width=0,
        )
    fig.update_layout(
        title="Solar Array Power vs Orbit Angle",
        xaxis_title="Orbit Angle (deg)",
        yaxis_title="Power (W)",
        template="plotly_white",
        legend=dict(x=0.01, y=0.99),
    )
    return fig
