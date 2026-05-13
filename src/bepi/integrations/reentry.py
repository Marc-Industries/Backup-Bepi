"""Atmospheric re-entry trajectory and heat-shield sizing tool."""

import math
from dataclasses import dataclass
from typing import Literal

import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ---------------------------------------------------------------------------
# Atmosphere models  (exponential approximation)
# ---------------------------------------------------------------------------
# Each entry: (rho0 kg/m³, scale_height km, gamma_ratio, gas_name)
ATMOSPHERE_MODELS: dict[str, dict] = {
    "Earth": {
        "rho0": 1.225,
        "H_km": 8.5,
        "R_planet_km": 6371.0,
        "g0_m_s2": 9.80665,
        "gamma": 1.4,
        "gas": "N2/O2",
    },
    "Mars": {
        "rho0": 0.020,
        "H_km": 11.1,
        "R_planet_km": 3389.5,
        "g0_m_s2": 3.721,
        "gamma": 1.3,
        "gas": "CO2",
    },
    "Venus": {
        "rho0": 65.0,
        "H_km": 15.9,
        "R_planet_km": 6051.8,
        "g0_m_s2": 8.87,
        "gamma": 1.29,
        "gas": "CO2",
    },
    "Titan": {
        "rho0": 5.428,
        "H_km": 21.0,
        "R_planet_km": 2574.7,
        "g0_m_s2": 1.352,
        "gamma": 1.4,
        "gas": "N2/CH4",
    },
}

# TPS material properties: (effective heat of ablation J/kg, density kg/m³, name)
TPS_MATERIALS: dict[str, dict] = {
    "PICA": {"q_ablation_J_kg": 28e6, "density_kg_m3": 265.0, "name": "PICA"},
    "SLA-561V": {"q_ablation_J_kg": 18e6, "density_kg_m3": 256.0, "name": "SLA-561V"},
    "Avcoat": {"q_ablation_J_kg": 22e6, "density_kg_m3": 513.0, "name": "Avcoat"},
    "UHTC": {"q_ablation_J_kg": 40e6, "density_kg_m3": 6000.0, "name": "UHTC"},
}

# Default TPS choice per shield type
_SHIELD_MAP = {
    "ablative": "PICA",
    "reusable": "UHTC",
    "none": None,
}


@dataclass
class ReentryParams:
    body: Literal["Earth", "Mars", "Venus", "Titan"] = "Earth"
    entry_velocity_kms: float = 7.8
    entry_angle_deg: float = -5.0          # flight path angle (negative = descending)
    ballistic_coefficient_kg_m2: float = 100.0  # m / (Cd * A)
    nose_radius_m: float = 1.0
    vehicle_mass_kg: float = 3000.0
    heat_shield_type: Literal["ablative", "reusable", "none"] = "ablative"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _atmo_density(h_km: float, model: dict) -> float:
    return model["rho0"] * math.exp(-h_km / model["H_km"])


# ---------------------------------------------------------------------------
# Allen-Eggers ballistic re-entry
# ---------------------------------------------------------------------------

def compute_reentry_trajectory(params: ReentryParams) -> dict:
    """Allen-Eggers approximate ballistic re-entry.

    Returns peak deceleration, peak heat flux, total heat load, time to peak
    heating, altitude of peak heating, terminal velocity, and trajectory arrays.
    """
    atm = ATMOSPHERE_MODELS[params.body]
    rho0 = atm["rho0"]
    H = atm["H_km"] * 1e3          # scale height in metres
    R = atm["R_planet_km"] * 1e3
    g = atm["g0_m_s2"]

    V0 = params.entry_velocity_kms * 1e3  # m/s
    gamma0 = math.radians(abs(params.entry_angle_deg))  # positive magnitude
    beta = params.ballistic_coefficient_kg_m2  # m/(Cd*A)
    Rn = params.nose_radius_m

    sin_g = math.sin(gamma0)

    # Allen-Eggers: peak deceleration
    # a_max = V0² * sin(γ) / (2 * e * H)
    e_val = math.e
    a_peak = V0**2 * sin_g / (2.0 * e_val * H)
    a_peak_g = a_peak / g

    # Altitude of peak deceleration
    # rho_peak = beta * sin(γ) / H   →  h_peak = -H * ln(rho_peak / rho0)
    rho_peak = beta * sin_g / H
    if rho_peak > 0 and rho_peak < rho0:
        h_peak = -H * math.log(rho_peak / rho0)
    else:
        h_peak = 40e3  # fallback

    # Velocity at peak deceleration
    V_peak = V0 / math.sqrt(e_val)

    # Stagnation-point heat flux  (Sutton-Graves): q = k * sqrt(rho/Rn) * V³
    # k depends on gas — typical Earth k ≈ 1.742e-4  (W/(m²) * (kg/m³)^-0.5 * (m/s)^-3)
    k_map = {"Earth": 1.742e-4, "Mars": 1.898e-4, "Venus": 1.742e-4, "Titan": 1.5e-4}
    k = k_map.get(params.body, 1.742e-4)

    rho_at_peak = _atmo_density(h_peak / 1e3, atm)
    q_peak = k * math.sqrt(rho_at_peak / Rn) * V_peak**3  # W/m²
    q_peak_W_cm2 = q_peak / 1e4

    # --- Numerical trajectory integration for total heat load & profiles ---
    dt = 0.5  # seconds
    h = 120e3  # entry interface (m)
    V = V0
    gamma = gamma0
    t = 0.0
    Q_total = 0.0  # J/m²

    altitudes, velocities, heat_fluxes, decels, times = [], [], [], [], []
    t_peak_heat = 0.0
    h_peak_heat = h
    q_max_found = 0.0

    while h > 0 and V > 50.0 and t < 2000.0:
        rho = _atmo_density(h / 1e3, atm)
        # Drag deceleration
        a_drag = 0.5 * rho * V**2 / beta
        # Gravity component along trajectory
        a_grav = g * math.sin(gamma)

        # Heat flux at this point
        q_dot = k * math.sqrt(rho / Rn) * V**3  # W/m²

        altitudes.append(h / 1e3)
        velocities.append(V / 1e3)
        heat_fluxes.append(q_dot / 1e4)  # W/cm²
        decels.append(a_drag / g)
        times.append(t)

        if q_dot > q_max_found:
            q_max_found = q_dot
            t_peak_heat = t
            h_peak_heat = h

        Q_total += q_dot * dt  # J/m²

        # Update velocity and altitude
        dV = -(a_drag + a_grav) * dt
        V = max(V + dV, 0.0)
        dh = -V * math.sin(gamma) * dt
        h += dh

        # Approximate gamma update (gravity turn)
        if V > 1.0:
            dgamma = (g * math.cos(gamma) / V - V * math.cos(gamma) / (R + h)) * dt
            gamma = max(gamma + dgamma, 0.001)

        t += dt

    Q_total_J_cm2 = Q_total / 1e4

    # Terminal velocity estimate
    rho_surface = atm["rho0"]
    V_terminal = math.sqrt(2.0 * params.vehicle_mass_kg * g / (rho_surface * beta))

    return {
        "body": params.body,
        "entry_velocity_km_s": params.entry_velocity_kms,
        "entry_angle_deg": params.entry_angle_deg,
        "peak_deceleration_g": round(a_peak_g, 2),
        "peak_heat_flux_W_cm2": round(q_peak_W_cm2, 2),
        "total_heat_load_J_cm2": round(Q_total_J_cm2, 1),
        "time_to_peak_heating_s": round(t_peak_heat, 1),
        "altitude_peak_heating_km": round(h_peak_heat / 1e3, 1),
        "terminal_velocity_m_s": round(V_terminal, 1),
        # Trajectory arrays for plotting
        "_altitudes_km": altitudes,
        "_velocities_km_s": velocities,
        "_heat_fluxes_W_cm2": heat_fluxes,
        "_decelerations_g": decels,
        "_times_s": times,
    }


# ---------------------------------------------------------------------------
# Heat shield mass
# ---------------------------------------------------------------------------

def compute_heat_shield_mass(
    params: ReentryParams,
    total_heat_load_J_cm2: float,
) -> dict:
    """TPS mass estimate from total heat load and shield type."""
    material_key = _SHIELD_MAP.get(params.heat_shield_type)
    if material_key is None:
        return {
            "heat_shield_type": "none",
            "tps_mass_kg": 0.0,
            "note": "No heat shield selected.",
        }

    mat = TPS_MATERIALS[material_key]
    q_abl = mat["q_ablation_J_kg"]
    rho_tps = mat["density_kg_m3"]

    # Convert J/cm² to J/m²
    Q_total_J_m2 = total_heat_load_J_cm2 * 1e4

    # Ablated mass per unit area = Q / q_ablation
    ablated_mass_per_m2 = Q_total_J_m2 / q_abl  # kg/m²

    # Estimate wetted area from ballistic coefficient + nose radius
    # A_ref ≈ π * Rn²  (simplified)
    A_ref = math.pi * params.nose_radius_m**2
    # Total shield area ≈ 2-3x reference area for blunt body
    A_shield = 2.5 * A_ref

    tps_mass = ablated_mass_per_m2 * A_shield
    # Add 30% margin for bondline, structure, margins
    tps_mass_with_margin = tps_mass * 1.3

    thickness_m = ablated_mass_per_m2 / rho_tps

    return {
        "heat_shield_type": params.heat_shield_type,
        "tps_material": mat["name"],
        "total_heat_load_J_cm2": round(total_heat_load_J_cm2, 1),
        "shield_area_m2": round(A_shield, 3),
        "ablated_thickness_m": round(thickness_m, 4),
        "tps_mass_kg": round(tps_mass_with_margin, 2),
        "tps_mass_no_margin_kg": round(tps_mass, 2),
        "margin_pct": 30,
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_reentry_profile(trajectory_result: dict) -> go.Figure:
    """3-subplot figure: alt vs velocity, alt vs heat flux, alt vs deceleration."""
    alt = trajectory_result["_altitudes_km"]
    vel = trajectory_result["_velocities_km_s"]
    qf = trajectory_result["_heat_fluxes_W_cm2"]
    dec = trajectory_result["_decelerations_g"]

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=(
            "Altitude vs Velocity",
            "Altitude vs Heat Flux",
            "Altitude vs Deceleration",
        ),
        horizontal_spacing=0.08,
    )

    fig.add_trace(
        go.Scatter(x=vel, y=alt, mode="lines", name="Velocity",
                   line=dict(color="#1f77b4")),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=qf, y=alt, mode="lines", name="Heat Flux",
                   line=dict(color="#d62728")),
        row=1, col=2,
    )
    fig.add_trace(
        go.Scatter(x=dec, y=alt, mode="lines", name="Deceleration",
                   line=dict(color="#2ca02c")),
        row=1, col=3,
    )

    fig.update_yaxes(title_text="Altitude (km)", row=1, col=1)
    fig.update_xaxes(title_text="Velocity (km/s)", row=1, col=1)
    fig.update_yaxes(title_text="Altitude (km)", row=1, col=2)
    fig.update_xaxes(title_text="Heat Flux (W/cm²)", row=1, col=2)
    fig.update_yaxes(title_text="Altitude (km)", row=1, col=3)
    fig.update_xaxes(title_text="Deceleration (g)", row=1, col=3)

    body = trajectory_result.get("body", "")
    fig.update_layout(
        title_text=f"Re-entry Profile — {body}",
        height=450,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Mars EDL sequence
# ---------------------------------------------------------------------------

def mars_edl_sequence(
    entry_params: ReentryParams,
    parachute_deploy_mach: float = 1.7,
    retro_thrust_decel_g: float = 3.0,
) -> dict:
    """Mars entry-descent-landing phase breakdown.

    Phases: hypersonic entry → peak heating → supersonic parachute →
    powered descent → landing.
    """
    atm = ATMOSPHERE_MODELS["Mars"]
    g_mars = atm["g0_m_s2"]
    H = atm["H_km"] * 1e3
    rho0 = atm["rho0"]

    V0 = entry_params.entry_velocity_kms * 1e3
    beta = entry_params.ballistic_coefficient_kg_m2
    gamma0 = math.radians(abs(entry_params.entry_angle_deg))
    Rn = entry_params.nose_radius_m
    mass = entry_params.vehicle_mass_kg

    # --- Phase 1: Hypersonic entry to peak heating ---
    traj = compute_reentry_trajectory(
        ReentryParams(
            body="Mars",
            entry_velocity_kms=entry_params.entry_velocity_kms,
            entry_angle_deg=entry_params.entry_angle_deg,
            ballistic_coefficient_kg_m2=beta,
            nose_radius_m=Rn,
            vehicle_mass_kg=mass,
            heat_shield_type=entry_params.heat_shield_type,
        )
    )

    # --- Phase 2: Parachute deploy ---
    # Speed of sound on Mars ≈ 240 m/s
    speed_of_sound_mars = 240.0
    V_chute_deploy = parachute_deploy_mach * speed_of_sound_mars

    # Find altitude where velocity drops to parachute deploy speed
    h_chute = 10.0  # km fallback
    alts = traj["_altitudes_km"]
    vels = traj["_velocities_km_s"]
    for i, v in enumerate(vels):
        if v * 1e3 <= V_chute_deploy and i > 0:
            h_chute = alts[i]
            break

    # Parachute phase: decelerate from V_chute_deploy to ~80 m/s
    V_after_chute = 80.0  # m/s typical

    # --- Phase 3: Powered descent ---
    # From ~80 m/s to ~2 m/s (landing)
    V_landing = 2.0
    dv_powered = V_after_chute - V_landing

    # Powered descent altitude ~1-2 km on Mars
    h_retro = 1.5  # km

    # Propellant for powered descent (Tsiolkovsky, assume hydrazine Isp=220)
    isp_retro = 220.0
    ve = isp_retro * 9.80665
    mass_ratio = math.exp(dv_powered / ve)
    prop_mass = mass * (1.0 - 1.0 / mass_ratio)

    return {
        "body": "Mars",
        "phases": [
            {
                "name": "Hypersonic Entry",
                "start_alt_km": 120.0,
                "end_alt_km": round(traj["altitude_peak_heating_km"], 1),
                "start_velocity_km_s": entry_params.entry_velocity_kms,
                "peak_deceleration_g": traj["peak_deceleration_g"],
                "peak_heat_flux_W_cm2": traj["peak_heat_flux_W_cm2"],
            },
            {
                "name": "Supersonic Parachute",
                "deploy_mach": parachute_deploy_mach,
                "deploy_alt_km": round(h_chute, 1),
                "deploy_velocity_m_s": round(V_chute_deploy, 0),
                "end_velocity_m_s": V_after_chute,
            },
            {
                "name": "Powered Descent",
                "start_alt_km": h_retro,
                "start_velocity_m_s": V_after_chute,
                "deceleration_g": retro_thrust_decel_g,
                "propellant_mass_kg": round(prop_mass, 2),
            },
            {
                "name": "Landing",
                "velocity_m_s": V_landing,
            },
        ],
        "total_heat_load_J_cm2": traj["total_heat_load_J_cm2"],
        "terminal_velocity_m_s": traj["terminal_velocity_m_s"],
    }
