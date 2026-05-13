from .gmat import SpacecraftParams, OrbitParams, PropagationConfig, GroundStation
from .celestial_bodies import get_body
import math


def _body_propagator(body: str) -> str:
    if body in ("Earth", "Moon"):
        return "two-body-keplerian"
    return "two-body-keplerian"


def generate_propagation_script(
    sc: SpacecraftParams,
    orbit: OrbitParams,
    config: PropagationConfig,
    ground_stations: list[GroundStation] | None = None,
    body: str = "Earth",
) -> str:
    b = get_body(body)
    sma_km = orbit.sma_km
    period_s = 2 * math.pi * (sma_km ** 3 / b.mu_km3s2) ** 0.5
    period_min = period_s / 60
    dur_h = config.duration_days * 24

    gs_lines = ""
    if ground_stations:
        for gs in ground_stations:
            gs_name_var = gs.name.lower().replace(" ", "_").replace("-", "_")
            gs_lines += (
                f"gs_{gs_name_var} = groundStation(sc, 'Name', '{gs.name}', "
                f"'Latitude', {gs.lat_deg}, 'Longitude', {gs.lon_deg}, "
                f"'MinElevationAngle', {gs.min_elevation_deg});\n"
            )

    access_block = ""
    if ground_stations:
        access_block = """
%% Access analysis
gsList = sc.GroundStations;
for i = 1:numel(gsList)
    ac = access(sat, gsList(i));
    ac.LineColor = 'green';
end
"""

    return f"""%% BEPI — MATLAB Satellite Scenario ({body})
%% Auto-generated — requires Satellite Communications Toolbox / Aerospace Toolbox
%% Run in MATLAB R2021a+ with satcom toolbox

startTime = datetime(2027, 6, 1, 12, 0, 0);
stopTime = startTime + hours({dur_h:.0f});
sampleTime = 60;  % seconds

sc = satelliteScenario(startTime, stopTime, sampleTime);

%% Satellite — Keplerian elements around {body}
mu_{body.lower()} = {b.mu_km3s2:.4f};  % km^3/s^2
R_{body.lower()} = {b.radius_km:.1f};  % km
sma = {sma_km:.1f};  % km (semi-major axis)
ecc_val = {orbit.ecc};
inc_val = {orbit.inc_deg};  % deg
raan_val = {orbit.raan_deg};  % deg
aop_val = {orbit.aop_deg};  % deg
ta_val = {orbit.ta_deg};    % deg (true anomaly)

sat = satellite(sc, sma * 1e3, ecc_val, inc_val, raan_val, aop_val, ta_val, ...
    'Name', 'BEPISAT', 'OrbitPropagator', '{_body_propagator(body)}');

%% Ground Stations
{gs_lines}{access_block}
%% 3D Visualization
v = satelliteScenarioViewer(sc);
sat.ShowLabel = true;
sat.MarkerSize = 10;
campos(v, 0, 0);
play(sc);

%% Ground track
groundTrack(sat, 'LeadTime', {period_min:.0f}*60, 'TrailTime', {period_min:.0f}*60);

%% Orbital elements report
[pos, vel] = states(sat, startTime, 'CoordinateFrame', 'inertial');
fprintf('=== BEPISAT Orbital Parameters ({body}) ===\\n');
fprintf('SMA: %.1f km\\n', sma);
fprintf('Eccentricity: %.4f\\n', ecc_val);
fprintf('Inclination: %.1f deg\\n', inc_val);
fprintf('Orbit period: {period_min:.1f} min\\n');
fprintf('Scenario duration: %.0f hours\\n', {dur_h:.0f});
fprintf('Initial position: [%.1f, %.1f, %.1f] km\\n', pos/1e3);
fprintf('Initial velocity: [%.3f, %.3f, %.3f] km/s\\n', vel/1e3);
"""


def generate_maneuver_script(
    sc: SpacecraftParams,
    orbit: OrbitParams,
    delta_v_ms: float,
    direction: str = "velocity",
    body: str = "Earth",
) -> str:
    b = get_body(body)
    dv_kms = delta_v_ms / 1000.0
    dir_map = {"velocity": "[1 0 0]", "normal": "[0 1 0]", "binormal": "[0 0 1]"}
    dv_vec = dir_map.get(direction, "[1 0 0]")

    return f"""%% BEPI — MATLAB Impulsive Maneuver Script ({body})
%% Auto-generated

mu = {b.mu_km3s2:.4f};  % km^3/s^2 ({body})
sma_pre = {orbit.sma_km:.1f};  % km
v_circ = sqrt(mu / sma_pre);  % km/s

fprintf('=== Pre-burn state ===\\n');
fprintf('SMA: %.1f km, V_circ: %.4f km/s\\n', sma_pre, v_circ);

%% Delta-V
dv = {dv_kms:.6f};  % km/s ({delta_v_ms:.1f} m/s)
dv_direction = {dv_vec};  % VNB frame: {direction}
dv_vector = dv * dv_direction;

%% Apply burn (Vis-viva post-burn)
v_post = v_circ + dv_vector(1);  % prograde component
sma_post = 1 / (2/sma_pre - v_post^2/mu);

fprintf('=== Post-burn state ===\\n');
fprintf('Delta-V: %.4f km/s (%.1f m/s) in {direction} direction\\n', dv, dv*1000);
fprintf('New SMA: %.1f km\\n', sma_post);
fprintf('Altitude change: %.1f km\\n', sma_post - sma_pre);

%% Propellant consumption (Tsiolkovsky)
Isp = 220;  % s (hydrazine)
g0 = 9.80665;  % m/s^2
m_dry = {sc.dry_mass_kg};  % kg
mass_ratio = exp(dv*1000 / (Isp * g0));
m_prop = m_dry * (mass_ratio - 1);
fprintf('Propellant used: %.2f kg (Isp=%d s)\\n', m_prop, Isp);
"""


def generate_stationkeeping_script(
    sc: SpacecraftParams,
    orbit: OrbitParams,
    target_alt_km: float,
    tolerance_km: float = 5.0,
    sim_days: float = 30.0,
    body: str = "Earth",
) -> str:
    b = get_body(body)

    return f"""%% BEPI — MATLAB Station-Keeping Script ({body})
%% Auto-generated

mu = {b.mu_km3s2:.4f};  % km^3/s^2 ({body})
R_body = {b.radius_km:.1f};  % km
target_alt = {target_alt_km:.1f};  % km
tolerance = {tolerance_km:.1f};  % km
sim_duration = {sim_days:.0f} * 86400;  % seconds

sma = R_body + target_alt;
v_circ = sqrt(mu / sma);
T_orb = 2*pi * sqrt(sma^3 / mu);  % orbital period (s)

fprintf('=== Station-Keeping Parameters ===\\n');
fprintf('Body: {body}, Target alt: %.1f km\\n', target_alt);
fprintf('Tolerance: ±%.1f km\\n', tolerance);
fprintf('Orbital period: %.1f min\\n', T_orb/60);

%% Simple altitude-threshold SK simulation
dt = T_orb;  % one step per orbit
t = 0;
alt = target_alt;
total_dv = 0;
n_burns = 0;
burn_log = [];

%% Atmospheric drag decay (simplified)
if {str(b.has_atmosphere).lower()}
    rho0 = 1e-12;  % kg/m^3 (approximate at {target_alt_km:.0f} km for {body})
    Cd = 2.2;
    A_m = {sc.drag_area_m2} / {sc.dry_mass_kg};  % area-to-mass ratio m^2/kg
    a_drag = 0.5 * rho0 * v_circ^2 * 1e6 * Cd * A_m;  % m/s^2
    alt_decay_per_orbit = a_drag * T_orb * T_orb / (2 * sma * 1e3) * 1e-3;  % km
else
    alt_decay_per_orbit = 0.001;  % minimal perturbation
end

while t < sim_duration
    alt = alt - alt_decay_per_orbit;
    if alt < target_alt - tolerance
        dv_burn = sqrt(mu / (R_body + alt)) * (sqrt(2*(R_body + target_alt) / ((R_body+alt) + (R_body+target_alt))) - 1);
        total_dv = total_dv + abs(dv_burn) * 1000;  % m/s
        n_burns = n_burns + 1;
        burn_log(end+1, :) = [t/86400, alt, dv_burn*1000];
        alt = target_alt;
    end
    t = t + dt;
end

fprintf('=== Results ===\\n');
fprintf('Total burns: %d\\n', n_burns);
fprintf('Total delta-V: %.2f m/s\\n', total_dv);
fprintf('Average delta-V per burn: %.2f m/s\\n', total_dv/max(n_burns,1));
fprintf('Simulation: %.0f days\\n', sim_duration/86400);
"""
