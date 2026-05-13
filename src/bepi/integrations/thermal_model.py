"""Simplified thermal node model for satellite preliminary thermal analysis."""

import csv
import io
import math
from dataclasses import dataclass, field

import numpy as np
import plotly.graph_objects as go

from .celestial_bodies import get_body, solar_flux_at_body

STEFAN_BOLTZMANN = 5.67e-8  # W/m²/K⁴


@dataclass
class ThermalNode:
    name: str
    mass_kg: float
    cp_j_kgk: float = 900.0
    area_m2: float = 1.0
    absorptivity: float = 0.3
    emissivity: float = 0.8
    internal_dissipation_w: float = 0.0
    initial_temp_k: float = 293.0
    mli: bool = False
    mli_effective_emissivity: float = 0.03
    heater_power_w: float = 0.0
    heater_setpoint_k: float = 263.0
    temp_limit_hot_k: float = 323.0
    temp_limit_cold_k: float = 253.0
    absorptivity_eol: float | None = None
    emissivity_eol: float | None = None


@dataclass
class ThermalCoupling:
    node_a: str
    node_b: str
    conductance_w_k: float
    radiative_gr_m2: float = 0.0


@dataclass
class EnvironmentFluxes:
    solar_w_m2: float = 1361.0
    albedo_factor: float = 0.3
    earth_ir_w_m2: float = 237.0
    view_factor_earth: float = 0.5


@dataclass
class ThermalModelParams:
    nodes: list[ThermalNode]
    couplings: list[ThermalCoupling]
    env: EnvironmentFluxes
    orbit_period_s: float
    eclipse_fraction: float


@dataclass
class TransientResult:
    time_s: list[float]
    temperatures: dict[str, list[float]]


@dataclass
class WorstCaseResult:
    hot_case: dict[str, float]
    cold_case: dict[str, float]
    hot_margins: dict[str, float]
    cold_margins: dict[str, float]
    violations: list[str]
    radiator_min_area_m2: float


@dataclass
class SatFace:
    name: str
    normal: list[float]
    area_m2: float
    alpha_s: float = 0.3
    epsilon_ir: float = 0.8


# ---------------------------------------------------------------------------
# Geometry presets
# ---------------------------------------------------------------------------

BOX_FACES = [
    SatFace("+X", [1, 0, 0], 0.6),
    SatFace("-X", [-1, 0, 0], 0.6),
    SatFace("+Y", [0, 1, 0], 0.6),
    SatFace("-Y", [0, -1, 0], 0.6),
    SatFace("+Z nadir", [0, 0, 1], 0.8),
    SatFace("-Z zenith", [0, 0, -1], 0.8),
]

CYLINDER_FACES = [
    SatFace("Cyl +X", [1, 0, 0], 0.5),
    SatFace("Cyl -X", [-1, 0, 0], 0.5),
    SatFace("Cyl +Y", [0, 1, 0], 0.5),
    SatFace("Cyl -Y", [0, -1, 0], 0.5),
    SatFace("Top", [0, 0, -1], 0.3),
    SatFace("Bottom nadir", [0, 0, 1], 0.3),
]

HEX_FACES: list[SatFace] = []
for i in range(6):
    angle = math.radians(60 * i)
    HEX_FACES.append(SatFace(f"Hex{i}", [math.cos(angle), math.sin(angle), 0], 0.4))
HEX_FACES.append(SatFace("Hex Top", [0, 0, -1], 0.35))
HEX_FACES.append(SatFace("Hex Bottom", [0, 0, 1], 0.35))


# ---------------------------------------------------------------------------
# View factor & per-face flux helpers
# ---------------------------------------------------------------------------

def compute_view_factor_to_body(altitude_km: float, body_radius_km: float) -> float:
    r = body_radius_km
    h = altitude_km
    ratio = r / (r + h)
    return 1.0 - math.sqrt(1.0 - ratio ** 2)


def _coerce_faces(geometry) -> list[SatFace]:
    from .sat_3d_model import SatelliteGeometry, geometry_to_sat_faces
    if isinstance(geometry, SatelliteGeometry):
        dicts = geometry_to_sat_faces(geometry)
        return [SatFace(name=d["name"], normal=d["normal"], area_m2=d["area_m2"],
                        alpha_s=d["alpha_s"], epsilon_ir=d["epsilon_ir"]) for d in dicts]
    faces: list[SatFace] = []
    for item in geometry:
        if isinstance(item, SatFace):
            faces.append(item)
        else:
            faces.append(SatFace(name=item["name"], normal=item["normal"], area_m2=item["area_m2"],
                                 alpha_s=item.get("alpha_s", 0.3), epsilon_ir=item.get("epsilon_ir", 0.8)))
    return faces


def compute_face_fluxes(
    geometry,
    body_name: str,
    altitude_km: float,
    sun_direction: list[float],
    albedo: float | None = None,
    ir_flux: float | None = None,
) -> dict[str, dict[str, float]]:
    geometry = _coerce_faces(geometry)
    body = get_body(body_name)
    vf = compute_view_factor_to_body(altitude_km, body.radius_km)
    solar = solar_flux_at_body(body_name)
    alb = albedo if albedo is not None else body.albedo
    ir = ir_flux if ir_flux is not None else body.ir_flux_w_m2

    sun_arr = np.asarray(sun_direction, dtype=float)
    sun_norm = np.linalg.norm(sun_arr)
    if sun_norm > 0:
        sun_arr = sun_arr / sun_norm

    result: dict[str, dict[str, float]] = {}
    for face in geometry:
        n = np.asarray(face.normal, dtype=float)
        cos_sun = float(np.dot(n, sun_arr))
        cos_sun_pos = max(cos_sun, 0.0)
        cos_nadir = max(float(n[2]), 0.0)

        direct = solar * cos_sun_pos
        albedo_flux = solar * alb * vf * cos_nadir
        ir_face = ir * vf * cos_nadir

        result[face.name] = {
            "direct_solar_w_m2": direct,
            "albedo_w_m2": albedo_flux,
            "planetary_ir_w_m2": ir_face,
            "total_w_m2": direct + albedo_flux + ir_face,
        }
    return result


def first_order_thermal(
    geometry,
    body_name: str,
    altitude_km: float,
    internal_power_w: float,
    sun_direction: list[float] | None = None,
) -> dict[str, float]:
    if sun_direction is None:
        sun_direction = [1.0, 0.0, 0.0]

    geometry = _coerce_faces(geometry)
    fluxes = compute_face_fluxes(geometry, body_name, altitude_km, sun_direction)
    total_area = sum(f.area_m2 for f in geometry)
    power_share_per_m2 = internal_power_w / total_area if total_area > 0 else 0.0

    temps: dict[str, float] = {}
    for face in geometry:
        ff = fluxes[face.name]
        q_solar = face.alpha_s * ff["direct_solar_w_m2"] * face.area_m2
        q_albedo = face.alpha_s * ff["albedo_w_m2"] * face.area_m2
        q_ir = face.epsilon_ir * ff["planetary_ir_w_m2"] * face.area_m2
        q_int = power_share_per_m2 * face.area_m2
        q_abs = q_solar + q_albedo + q_ir + q_int

        denom = face.epsilon_ir * STEFAN_BOLTZMANN * face.area_m2
        if denom > 0 and q_abs > 0:
            temps[face.name] = (q_abs / denom) ** 0.25
        else:
            temps[face.name] = 2.7
    return temps


# ---------------------------------------------------------------------------
# Default satellite nodes
# ---------------------------------------------------------------------------

DEFAULT_SAT_NODES = [
    ThermalNode("Body (+X)", 8.0, area_m2=0.6, internal_dissipation_w=5.0),
    ThermalNode("Body (-X)", 8.0, area_m2=0.6, internal_dissipation_w=3.0),
    ThermalNode("Body (+Y)", 8.0, area_m2=0.6, internal_dissipation_w=4.0),
    ThermalNode("Body (-Y)", 8.0, area_m2=0.6, internal_dissipation_w=4.0),
    ThermalNode("Body (+Z nadir)", 10.0, area_m2=0.8, emissivity=0.85, internal_dissipation_w=2.0),
    ThermalNode("Body (-Z zenith)", 6.0, area_m2=0.8, absorptivity=0.2, emissivity=0.85),
    ThermalNode("Solar Panel +Y", 2.0, cp_j_kgk=700.0, area_m2=2.0, absorptivity=0.75, emissivity=0.82),
    ThermalNode("Solar Panel -Y", 2.0, cp_j_kgk=700.0, area_m2=2.0, absorptivity=0.75, emissivity=0.82),
    ThermalNode("Radiator", 3.0, area_m2=0.5, absorptivity=0.15, emissivity=0.92, internal_dissipation_w=0.0),
    ThermalNode("Battery Pack", 5.0, cp_j_kgk=1000.0, area_m2=0.2, internal_dissipation_w=8.0, initial_temp_k=298.0),
    ThermalNode("Payload", 12.0, area_m2=0.3, internal_dissipation_w=25.0, initial_temp_k=295.0),
]


# ---------------------------------------------------------------------------
# Solver helpers
# ---------------------------------------------------------------------------

def _build_coupling_map(params: ThermalModelParams) -> dict[str, list[tuple[str, float, float]]]:
    cmap: dict[str, list[tuple[str, float, float]]] = {n.name: [] for n in params.nodes}
    for c in params.couplings:
        gr = getattr(c, "radiative_gr_m2", 0.0)
        cmap[c.node_a].append((c.node_b, c.conductance_w_k, gr))
        cmap[c.node_b].append((c.node_a, c.conductance_w_k, gr))
    return cmap


def _effective_props(node: ThermalNode, eol: bool = False):
    alpha = node.absorptivity
    eps = node.emissivity
    if eol:
        alpha = node.absorptivity_eol if node.absorptivity_eol is not None else alpha
        eps = node.emissivity_eol if node.emissivity_eol is not None else eps
    if node.mli:
        eps = node.mli_effective_emissivity
    return alpha, eps


def _q_env(node: ThermalNode, env: EnvironmentFluxes, in_sunlight: bool, eol: bool = False,
           heater_on: bool = False) -> float:
    alpha, eps = _effective_props(node, eol)
    q = 0.0
    if in_sunlight:
        q += alpha * env.solar_w_m2 * node.area_m2
        q += alpha * env.solar_w_m2 * env.albedo_factor * node.area_m2 * env.view_factor_earth
    q += eps * env.earth_ir_w_m2 * node.area_m2 * env.view_factor_earth
    q += node.internal_dissipation_w
    if heater_on:
        q += node.heater_power_w
    return q


def _q_rad(node: ThermalNode, T: float, eol: bool = False) -> float:
    _, eps = _effective_props(node, eol)
    return eps * STEFAN_BOLTZMANN * node.area_m2 * T**4


# ---------------------------------------------------------------------------
# Steady-state solver (relaxation)
# ---------------------------------------------------------------------------

def solve_steady_state(params: ThermalModelParams, max_iter: int = 1000, tol: float = 0.01,
                       eol: bool = False) -> dict[str, float]:
    temps = {n.name: n.initial_temp_k for n in params.nodes}
    cmap = _build_coupling_map(params)
    sunlight_frac = 1.0 - params.eclipse_fraction

    for _ in range(max_iter):
        max_dT = 0.0
        for n in params.nodes:
            heater_on = (n.heater_power_w > 0 and temps[n.name] < n.heater_setpoint_k)
            q_in = (_q_env(n, params.env, True, eol) * sunlight_frac
                    + _q_env(n, params.env, False, eol, heater_on=heater_on) * params.eclipse_fraction)
            for nb_name, gl, gr in cmap[n.name]:
                q_in += gl * (temps[nb_name] - temps[n.name])
                if gr > 0:
                    q_in += gr * STEFAN_BOLTZMANN * (temps[nb_name]**4 - temps[n.name]**4)
            q_out = _q_rad(n, temps[n.name], eol)
            residual = q_in - q_out
            _, eps = _effective_props(n, eol)
            C = n.mass_kg * n.cp_j_kgk
            dT = 0.5 * residual / (C / 100.0 + 4.0 * eps * STEFAN_BOLTZMANN * n.area_m2 * temps[n.name]**3)
            temps[n.name] += dT
            if temps[n.name] < 50.0:
                temps[n.name] = 50.0
            max_dT = max(max_dT, abs(dT))
        if max_dT < tol:
            break
    return temps


# ---------------------------------------------------------------------------
# Transient solver
# ---------------------------------------------------------------------------

def solve_transient(params: ThermalModelParams, n_orbits: int = 3, dt_s: float = 10.0,
                    eol: bool = False) -> TransientResult:
    temps = {n.name: n.initial_temp_k for n in params.nodes}
    cmap = _build_coupling_map(params)

    total_time = n_orbits * params.orbit_period_s
    steps = int(total_time / dt_s)
    sunlight_end = params.orbit_period_s * (1.0 - params.eclipse_fraction)
    node_map = {n.name: n for n in params.nodes}

    time_s: list[float] = []
    history: dict[str, list[float]] = {n.name: [] for n in params.nodes}

    for i in range(steps):
        t = i * dt_s
        orbit_phase = t % params.orbit_period_s
        in_sun = orbit_phase < sunlight_end

        time_s.append(t)
        for n in params.nodes:
            history[n.name].append(temps[n.name])

        for n in params.nodes:
            heater_on = (n.heater_power_w > 0 and temps[n.name] < n.heater_setpoint_k)
            q_in = _q_env(n, params.env, in_sun, eol, heater_on=heater_on)
            for nb_name, gl, gr in cmap[n.name]:
                q_in += gl * (temps[nb_name] - temps[n.name])
                if gr > 0:
                    q_in += gr * STEFAN_BOLTZMANN * (temps[nb_name]**4 - temps[n.name]**4)
            q_out = _q_rad(n, temps[n.name], eol)
            C = n.mass_kg * n.cp_j_kgk
            dT = (q_in - q_out) * dt_s / C
            temps[n.name] = max(temps[n.name] + dT, 2.7)

    return TransientResult(time_s=time_s, temperatures=history)


# ---------------------------------------------------------------------------
# Worst-case hot/cold analysis
# ---------------------------------------------------------------------------

def solve_worst_case(params: ThermalModelParams, beta_range: tuple[float, float] = (0.0, 90.0),
                     dissipation_margin: float = 0.1) -> WorstCaseResult:
    import copy

    # Hot case: β=max (min eclipse → max avg sun), BOL props, max dissipation (+margin)
    hot_params = copy.deepcopy(params)
    for n in hot_params.nodes:
        n.internal_dissipation_w *= (1.0 + dissipation_margin)
    hot_params.eclipse_fraction = compute_eclipse_fraction_from_beta(
        params.orbit_period_s, params.eclipse_fraction, beta_range[1])
    hot_temps = solve_steady_state(hot_params, eol=False)

    # Cold case: β=min (max eclipse → min avg sun), EOL props, min dissipation (-margin), heaters on
    cold_params = copy.deepcopy(params)
    for n in cold_params.nodes:
        n.internal_dissipation_w *= max(0.0, 1.0 - dissipation_margin)
    cold_params.eclipse_fraction = compute_eclipse_fraction_from_beta(
        params.orbit_period_s, params.eclipse_fraction, beta_range[0])
    cold_temps = solve_steady_state(cold_params, eol=True)

    node_map = {n.name: n for n in params.nodes}
    hot_margins = {}
    cold_margins = {}
    violations = []
    for name in hot_temps:
        n = node_map[name]
        hm = n.temp_limit_hot_k - hot_temps[name]
        cm = cold_temps[name] - n.temp_limit_cold_k
        hot_margins[name] = hm
        cold_margins[name] = cm
        if hm < 0:
            violations.append(f"🔴 {name}: HOT violation by {abs(hm):.1f} K ({hot_temps[name]-273.15:.1f}°C > {n.temp_limit_hot_k-273.15:.1f}°C)")
        if cm < 0:
            violations.append(f"🔵 {name}: COLD violation by {abs(cm):.1f} K ({cold_temps[name]-273.15:.1f}°C < {n.temp_limit_cold_k-273.15:.1f}°C)")

    rad_area = radiator_sizing(params)

    return WorstCaseResult(
        hot_case=hot_temps, cold_case=cold_temps,
        hot_margins=hot_margins, cold_margins=cold_margins,
        violations=violations, radiator_min_area_m2=rad_area)


def compute_eclipse_fraction_from_beta(orbit_period_s: float, base_eclipse: float, beta_deg: float) -> float:
    beta = abs(beta_deg)
    if beta >= 90.0:
        return 0.0
    return base_eclipse * math.cos(math.radians(beta))


# ---------------------------------------------------------------------------
# Radiator auto-sizing
# ---------------------------------------------------------------------------

def radiator_sizing(params: ThermalModelParams, target_hot_k: float = 313.0,
                    radiator_emissivity: float = 0.92, margin: float = 1.1) -> float:
    total_diss = sum(n.internal_dissipation_w for n in params.nodes) * margin
    q_rad_per_m2 = radiator_emissivity * STEFAN_BOLTZMANN * target_hot_k**4
    env_absorbed_per_m2 = 0.15 * params.env.solar_w_m2 * 0.1  # conservative: 10% solar on radiator
    net_rejection = q_rad_per_m2 - env_absorbed_per_m2
    if net_rejection <= 0:
        return 99.0
    return total_diss / net_rejection


# ---------------------------------------------------------------------------
# Heater sizing (cold case)
# ---------------------------------------------------------------------------

def heater_sizing(params: ThermalModelParams) -> dict[str, float]:
    cold_temps = solve_steady_state(params, eol=True)
    result = {}
    for n in params.nodes:
        if cold_temps[n.name] < n.temp_limit_cold_k:
            deficit = n.temp_limit_cold_k - cold_temps[n.name]
            _, eps = _effective_props(n, eol=True)
            power_needed = eps * STEFAN_BOLTZMANN * n.area_m2 * 4 * cold_temps[n.name]**3 * deficit
            result[n.name] = max(power_needed, 0.5)
    return result


# ---------------------------------------------------------------------------
# Sun arrow for 3D plot
# ---------------------------------------------------------------------------

def make_sun_arrow(sun_direction: tuple[float, float, float], scale: float = 2.0) -> go.Cone:
    dx, dy, dz = sun_direction
    norm = math.sqrt(dx**2 + dy**2 + dz**2)
    if norm == 0:
        dx, dy, dz = 1, 0, 0
    else:
        dx, dy, dz = dx/norm, dy/norm, dz/norm
    tip_x = -dx * scale
    tip_y = -dy * scale
    tip_z = -dz * scale
    return go.Cone(
        x=[tip_x], y=[tip_y], z=[tip_z],
        u=[dx], v=[dy], w=[dz],
        sizemode="absolute", sizeref=0.4,
        colorscale=[[0, "#FFD700"], [1, "#FFD700"]],
        showscale=False, name="☀ Sun",
        hovertext=f"Sun dir: ({dx:.2f}, {dy:.2f}, {dz:.2f})",
        anchor="tip",
    )


# ---------------------------------------------------------------------------
# Export: Systema CSV
# ---------------------------------------------------------------------------

def export_systema_thermal_csv(results: dict[str, float], nodes: list[ThermalNode]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Node", "Temp_K", "Temp_C", "Mass_kg", "Cp_J_kgK", "Area_m2", "Alpha", "Epsilon", "Q_int_W"])
    node_map = {n.name: n for n in nodes}
    for name, T in results.items():
        n = node_map[name]
        w.writerow([name, f"{T:.2f}", f"{T - 273.15:.2f}", n.mass_kg, n.cp_j_kgk, n.area_m2,
                     n.absorptivity, n.emissivity, n.internal_dissipation_w])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Export: ESATAN-TMS input (simplified)
# ---------------------------------------------------------------------------

def export_esatan_input(params: ThermalModelParams) -> str:
    lines = [
        "C ESATAN-TMS MODEL INPUT (auto-generated by BEPI)",
        f"C Orbit period: {params.orbit_period_s:.1f} s, eclipse fraction: {params.eclipse_fraction:.2f}",
        f"C Solar flux: {params.env.solar_w_m2:.1f} W/m2",
        "",
        "$NODES",
    ]
    for i, n in enumerate(params.nodes, 1):
        cap = n.mass_kg * n.cp_j_kgk
        lines.append(f"  N{i:03d}  '{n.name}'  D  {cap:.1f}  {n.initial_temp_k:.1f}")
    lines += ["", "$CONDUCTORS"]
    for i, c in enumerate(params.couplings, 1):
        a_idx = next(j for j, n in enumerate(params.nodes, 1) if n.name == c.node_a)
        b_idx = next(j for j, n in enumerate(params.nodes, 1) if n.name == c.node_b)
        lines.append(f"  GL{i:03d}  N{a_idx:03d}  N{b_idx:03d}  {c.conductance_w_k:.4f}")
    lines += ["", "$OPTICAL"]
    for i, n in enumerate(params.nodes, 1):
        lines.append(f"  N{i:03d}  ALPHA={n.absorptivity:.3f}  EPSILON={n.emissivity:.3f}  AREA={n.area_m2:.4f}")
    lines += ["", "$END"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_thermal_map(steady_results: dict[str, float], nodes: list[ThermalNode],
                     hot_limit_k: float = 323.0, cold_limit_k: float = 253.0) -> go.Figure:
    names = list(steady_results.keys())
    temps_c = [steady_results[n] - 273.15 for n in names]
    colors = ["#d62728" if t > hot_limit_k - 273.15 else "#1f77b4" if t < cold_limit_k - 273.15 else "#2ca02c" for t in temps_c]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=temps_c, marker_color=colors, name="Temperature"))
    fig.add_hline(y=hot_limit_k - 273.15, line_dash="dash", line_color="red", annotation_text="Hot limit")
    fig.add_hline(y=cold_limit_k - 273.15, line_dash="dash", line_color="blue", annotation_text="Cold limit")
    fig.update_layout(title="Steady-State Thermal Map", yaxis_title="Temperature (°C)",
                      xaxis_title="Node", template="plotly_white")
    return fig


def plot_transient(result: TransientResult, eclipse_fraction: float = 0.0,
                   orbit_period_s: float = 0.0) -> go.Figure:
    fig = go.Figure()
    time_min = [t / 60.0 for t in result.time_s]
    for name, temps in result.temperatures.items():
        temps_c = [T - 273.15 for T in temps]
        fig.add_trace(go.Scatter(x=time_min, y=temps_c, mode="lines", name=name))

    if orbit_period_s > 0 and eclipse_fraction > 0:
        sunlight_end = orbit_period_s * (1.0 - eclipse_fraction)
        t_max = result.time_s[-1] if result.time_s else 0
        orbit = 0.0
        while orbit < t_max:
            ecl_start = (orbit + sunlight_end) / 60.0
            ecl_end = (orbit + orbit_period_s) / 60.0
            fig.add_vrect(x0=ecl_start, x1=ecl_end, fillcolor="gray", opacity=0.15,
                          layer="below", line_width=0)
            orbit += orbit_period_s

    fig.update_layout(title="Transient Thermal Analysis", xaxis_title="Time (min)",
                      yaxis_title="Temperature (°C)", template="plotly_white",
                      legend=dict(font=dict(size=9)))
    return fig
