"""Tests for the extended propagators in bepi.integrations.mission_sim:
elliptical two_body/j2, j2_drag (King-Hele decay + exponential atmosphere),
estimate_lifetime, SGP4, and the loads_from_equipment helper.

Drag references are 30-day mean-SMA decay figures from a GMAT R2026a
cross-check table (exponential atmosphere matching GMAT's default
EarthExponentialAtmosphereData), computed for ISS-class ballistics
(Cd*A/m ~ 0.022 m^2/kg). The satellites below use exactly Cd*A/m =
2.2 * 1.0 / 100 = 0.022 m^2/kg, so the references apply unscaled; the
brackets are LOOSE (factor ~2, atmosphere-table differences are real)
while the orderings (altitude-monotonic, retrograde > prograde) are STRICT.
"""

import math
import warnings
from datetime import datetime, timezone

import numpy as np
import pytest
from pytest import approx

from bepi.integrations import mission_sim
from bepi.integrations.mission_sim import (
    BatterySpec,
    GroundStationSpec,
    LinkSpec,
    LoadSpec,
    MissionSpec,
    OrbitSpec,
    SatelliteSpec,
    SolarFace,
    analyze,
    atmosphere_density,
    estimate_lifetime,
    loads_from_equipment,
)

MU = mission_sim.MU_EARTH
R_EARTH = mission_sim.R_EARTH
EPOCH = datetime(2026, 7, 20, 8, 27, 38, tzinfo=timezone.utc)

# ISS TLE from the python-sgp4 documentation (epoch 2019-12-09).
ISS_TLE1 = "1 25544U 98067A   19343.69339541  .00001764  00000-0  40967-4 0  9997"
ISS_TLE2 = "2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472202482"


def _albasat_spec() -> MissionSpec:
    """The documented AlbaSat reference scenario (see test_mission_sim.py),
    with the orbit eccentricity spelled out at 0.0 so this file guards the
    circular limit of the ELLIPTICAL code path."""
    orbit = OrbitSpec(
        semi_major_axis_km=6878.137,
        inclination_deg=97.4,
        raan_deg=0.0,
        eccentricity=0.0,
        propagator="j2",
    )
    faces = [
        SolarFace(name="+X", area_m2=0.02, normal_body=(1, 0, 0)),
        SolarFace(name="-X", area_m2=0.02, normal_body=(-1, 0, 0)),
        SolarFace(name="+Y", area_m2=0.02, normal_body=(0, 1, 0)),
        SolarFace(name="-Y", area_m2=0.02, normal_body=(0, -1, 0)),
        SolarFace(name="-Z", area_m2=0.01, normal_body=(0, 0, -1)),
    ]
    loads = [
        LoadSpec(name="bus", power_w=1.5, when="always"),
        LoadSpec(name="debris_sensor", power_w=0.4, when="always"),
        LoadSpec(name="vibration_sensor", power_w=0.2, when="always"),
        LoadSpec(name="slr_corner_cubes", power_w=0.0, when="always"),
        LoadSpec(name="mrr_optical_comms", power_w=2.0, when="pass",
                 station_name="Padova GS"),
    ]
    link = LinkSpec(
        name="sband_down",
        frequency_hz=2.4e9,
        tx_power_w=1.0,
        tx_antenna_gain_dbi=5.0,
        rx_antenna_gain_dbi=30.0,
        tx_line_loss_db=0.8,
        rx_line_loss_db=1.0,
        system_noise_temperature_k=150.0,
        data_rate_bps=1e6,
        required_eb_n0_db=9.6,
        polarization_loss_db=0.5,
        pointing_loss_db=0.5,
        atmospheric_loss_db=0.3,
    )
    sat = SatelliteSpec(
        name="AlbaSat",
        orbit=orbit,
        pointing_mode="nadir",
        faces=faces,
        efficiency=0.30,
        degradation_per_year=0.025,
        battery=BatterySpec(capacity_wh=30.0, min_soc=0.3, max_soc=1.0,
                            initial_soc=0.8, round_trip_efficiency=0.9),
        loads=loads,
        links=[link],
    )
    station = GroundStationSpec(name="Padova GS", latitude_deg=45.406,
                                longitude_deg=11.876, altitude_m=12.0,
                                min_elevation_deg=10.0)
    return MissionSpec(
        name="AlbaSat",
        satellites=[sat],
        stations=[station],
        start_utc=EPOCH,
        duration_hours=48.0,
        step_seconds=30.0,
        years_since_bol=0.0,
    )


def _raan_from_state(r: np.ndarray, v: np.ndarray) -> float:
    h = np.cross(r, v)
    n_vec = np.cross([0.0, 0.0, 1.0], h)
    return math.atan2(n_vec[1], n_vec[0])


def _argp_from_state(r: np.ndarray, v: np.ndarray) -> float:
    h = np.cross(r, v)
    n_vec = np.cross([0.0, 0.0, 1.0], h)
    e_vec = np.cross(v, h) / MU - r / np.linalg.norm(r)
    cosw = np.dot(n_vec, e_vec) / (np.linalg.norm(n_vec) * np.linalg.norm(e_vec))
    argp = math.acos(float(np.clip(cosw, -1.0, 1.0)))
    if e_vec[2] < 0.0:
        argp = 2.0 * math.pi - argp
    return argp


def _wrap_pi(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


# ---------------------------------------------------------------------------
# 1. Elliptical geometry: at nu0 = 0 the radius is exactly the perigee radius
# ---------------------------------------------------------------------------

def test_elliptical_perigee_radius():
    a, e = 26562.0, 0.7
    orbit = OrbitSpec(semi_major_axis_km=a, inclination_deg=63.4,
                      raan_deg=40.0, arg_perigee_deg=270.0,
                      true_anomaly_deg=0.0, eccentricity=e,
                      propagator="two_body")
    r, _v = mission_sim._propagate(orbit, np.array([0.0]))
    r0 = float(np.linalg.norm(r[0]))
    assert r0 == approx(a * (1.0 - e), rel=1e-6)


# ---------------------------------------------------------------------------
# 2. Two-body invariants: energy and angular momentum constant along the orbit
# ---------------------------------------------------------------------------

def test_two_body_conservation():
    a, e = 10000.0, 0.3
    orbit = OrbitSpec(semi_major_axis_km=a, inclination_deg=40.0,
                      raan_deg=25.0, arg_perigee_deg=60.0,
                      true_anomaly_deg=30.0, eccentricity=e,
                      propagator="two_body")
    period_s = 2.0 * math.pi * math.sqrt(a**3 / MU)
    t = np.linspace(0.0, period_s, 400)
    r, v = mission_sim._propagate(orbit, t)

    r_norm = np.linalg.norm(r, axis=1)
    v_norm = np.linalg.norm(v, axis=1)
    energy = 0.5 * v_norm**2 - MU / r_norm
    h_norm = np.linalg.norm(np.cross(r, v), axis=1)

    # constant across all samples to 1e-9 relative
    assert (energy.max() - energy.min()) / abs(energy.mean()) < 1e-9
    assert (h_norm.max() - h_norm.min()) / h_norm.mean() < 1e-9
    # and equal to the analytic values for (a, e)
    assert float(energy.mean()) == approx(-MU / (2.0 * a), rel=1e-9)
    assert float(h_norm.mean()) == approx(math.sqrt(MU * a * (1.0 - e**2)), rel=1e-9)


# ---------------------------------------------------------------------------
# 3. Backcompat: the elliptical path at e = 0 reproduces the documented
#    circular AlbaSat reference (guards the refactor)
# ---------------------------------------------------------------------------

def test_circular_backcompat():
    res = analyze(_albasat_spec())
    assert res.n_samples == 5761
    sr = res.satellites[0]
    assert sr.avg_net_w == approx(5.66, abs=0.05)


# ---------------------------------------------------------------------------
# 4. J2 secular argp drift: zero at the critical inclination, positive at 30 deg
# ---------------------------------------------------------------------------

def _argp_drift_deg_per_day(inc_deg: float) -> float:
    orbit = OrbitSpec(semi_major_axis_km=7000.0, inclination_deg=inc_deg,
                      raan_deg=30.0, arg_perigee_deg=45.0,
                      true_anomaly_deg=0.0, eccentricity=0.1,
                      propagator="j2")
    r, v = mission_sim._propagate(orbit, np.array([0.0, 86400.0]))
    w0 = _argp_from_state(r[0], v[0])
    w1 = _argp_from_state(r[1], v[1])
    return math.degrees(_wrap_pi(w1 - w0))


def test_critical_inclination():
    # 63.4349 deg: 5*cos^2(i) - 1 = 0 -> no perigee drift
    assert abs(_argp_drift_deg_per_day(63.4349)) < 1e-3
    # 30 deg: 5*cos^2(i) - 1 = 2.75 > 0 -> perigee advances; hand-computed
    # 0.75*n*J2*(RE/p)^2*(5cos^2 i - 1) = 10.09 deg/day for a=7000, e=0.1
    drift_30 = _argp_drift_deg_per_day(30.0)
    assert drift_30 > 1.0
    assert drift_30 == approx(10.09, abs=1.0)


# ---------------------------------------------------------------------------
# 5. J2 secular RAAN drift: sun-synchronous rate at 700 km / 98.16 deg
# ---------------------------------------------------------------------------

def test_sso_raan_rate():
    orbit = OrbitSpec(semi_major_axis_km=R_EARTH + 700.0, inclination_deg=98.16,
                      raan_deg=10.0, propagator="j2")
    r, v = mission_sim._propagate(orbit, np.array([0.0, 86400.0]))
    drift = math.degrees(_wrap_pi(_raan_from_state(r[1], v[1])
                                  - _raan_from_state(r[0], v[0])))
    assert drift == approx(0.9856, rel=0.02)


# ---------------------------------------------------------------------------
# 6. j2_drag: 30-day mean-SMA decay against GMAT-anchored references
# ---------------------------------------------------------------------------

def _drag_sat(alt_km: float, inc_deg: float) -> SatelliteSpec:
    # Cd*A/m = 2.2 * 1.0 / 100 = 0.022 m^2/kg (ISS-class, matches the refs)
    orbit = OrbitSpec(semi_major_axis_km=R_EARTH + alt_km,
                      inclination_deg=inc_deg, propagator="j2_drag")
    return SatelliteSpec(name=f"D{alt_km:.0f}i{inc_deg:.0f}", orbit=orbit,
                         mass_kg=100.0, drag_area_m2=1.0, drag_coefficient=2.2)


def _decay_30d_km(alt_km: float, inc_deg: float) -> float:
    sat = _drag_sat(alt_km, inc_deg)
    t = np.arange(0.0, 30.0 * 86400.0 + 1.0, 600.0)
    r, v = mission_sim._propagate(sat.orbit, t, sat)
    r0, v0 = np.linalg.norm(r[0]), np.linalg.norm(v[0])
    r1, v1 = np.linalg.norm(r[-1]), np.linalg.norm(v[-1])
    a0 = 1.0 / (2.0 / r0 - v0**2 / MU)  # vis-viva
    a1 = 1.0 / (2.0 / r1 - v1**2 / MU)
    return float(a0 - a1)


def test_drag_decay_brackets():
    d400 = _decay_30d_km(400.0, 51.6)
    d500_pro = _decay_30d_km(500.0, 75.0)
    d500_retro = _decay_30d_km(500.0, 105.0)
    d600 = _decay_30d_km(600.0, 51.6)

    # LOOSE brackets: GMAT-anchored refs (11.4 / 1.9 / 2.0 / 0.41 km), factor ~2
    assert 11.4 / 2.0 < d400 < 11.4 * 2.0
    assert 1.9 / 2.0 < d500_pro < 1.9 * 2.0
    assert 2.0 / 2.0 < d500_retro < 2.0 * 2.0
    assert 0.41 / 2.0 < d600 < 0.41 * 2.0

    # STRICT orderings: decay falls with altitude...
    assert d400 > d500_pro > d600
    assert d400 > d500_retro > d600
    # ...and a retrograde orbit meets the co-rotating air head-on
    # (King-Hele factor (1 - omega_E*cos(i)/n)^2 > 1 for cos(i) < 0)
    assert d500_retro > d500_pro


# ---------------------------------------------------------------------------
# 7. Atmosphere model: density positive and strictly decreasing 200 -> 1000 km
# ---------------------------------------------------------------------------

def test_atmosphere_density_monotonic():
    alts = np.arange(200.0, 1000.0 + 1e-9, 5.0)
    rho = np.array([atmosphere_density(h) for h in alts])
    assert np.all(rho > 0.0)
    assert np.all(np.diff(rho) < 0.0), "density must strictly decrease with altitude"


# ---------------------------------------------------------------------------
# 8. Lifetime: monotonic with altitude; 800 km outlives the 25-year horizon
# ---------------------------------------------------------------------------

def test_lifetime_orders():
    def sat_at(alt_km: float) -> SatelliteSpec:
        return SatelliteSpec(
            name=f"L{alt_km:.0f}",
            orbit=OrbitSpec(semi_major_axis_km=R_EARTH + alt_km,
                            inclination_deg=51.6),
            mass_kg=100.0, drag_area_m2=1.0, drag_coefficient=2.2)

    l300 = estimate_lifetime(sat_at(300.0), EPOCH)
    l400 = estimate_lifetime(sat_at(400.0), EPOCH)
    l500 = estimate_lifetime(sat_at(500.0), EPOCH)
    l800 = estimate_lifetime(sat_at(800.0), EPOCH, max_years=25.0)

    assert l800 is None
    for lt in (l300, l400, l500):
        assert lt is not None and lt > 0.0
    assert l300 < l400 < l500


# ---------------------------------------------------------------------------
# 9. SGP4: pinned ISS TLE gives ISS-like radii; analyze() runs end to end
# ---------------------------------------------------------------------------

def test_sgp4_iss():
    pytest.importorskip("sgp4")
    start = datetime(2019, 12, 9, 18, 0, 0, tzinfo=timezone.utc)  # near TLE epoch
    orbit = OrbitSpec(semi_major_axis_km=6796.0, inclination_deg=51.64,
                      propagator="sgp4", tle_line1=ISS_TLE1, tle_line2=ISS_TLE2)

    # radius stays ISS-like over a day
    jd = mission_sim._jd(start) + np.linspace(0.0, 1.0, 97)
    r, _v = mission_sim._propagate(orbit, np.zeros(97), None, jd)
    r_norm = np.linalg.norm(r, axis=1)
    assert np.all(r_norm > 6650.0) and np.all(r_norm < 6850.0)

    # end-to-end analysis with a mid-latitude ground station
    sat = SatelliteSpec(name="ISS", orbit=orbit)
    station = GroundStationSpec(name="Padova GS", latitude_deg=45.406,
                                longitude_deg=11.876, altitude_m=12.0,
                                min_elevation_deg=10.0)
    spec = MissionSpec(name="iss-sgp4", satellites=[sat], stations=[station],
                       start_utc=start, duration_hours=24.0, step_seconds=60.0)
    res = analyze(spec)
    assert res.n_samples == 1441
    assert res.total_passes > 0
    assert res.passes_by_station.get("Padova GS", 0) == res.total_passes


# ---------------------------------------------------------------------------
# 10. SGP4 without a TLE is rejected
# ---------------------------------------------------------------------------

def test_sgp4_missing_tle():
    pytest.importorskip("sgp4")
    orbit = OrbitSpec(semi_major_axis_km=6796.0, inclination_deg=51.64,
                      propagator="sgp4")  # tle_line1/tle_line2 left empty
    sat = SatelliteSpec(name="NoTLE", orbit=orbit)
    spec = MissionSpec(name="no-tle", satellites=[sat], stations=[],
                       start_utc=EPOCH, duration_hours=1.0, step_seconds=60.0)
    with pytest.raises(ValueError, match="tle_line"):
        analyze(spec)


# ---------------------------------------------------------------------------
# 11. loads_from_equipment: qty scaling, skips, empty input
# ---------------------------------------------------------------------------

def test_loads_from_equipment():
    items = [
        {"name": "OBC", "power_w": 2.0, "qty": 3},        # qty scales power
        {"name": "Radio", "power_w": 1.5},                # qty defaults to 1
        {"name": "Sensor", "power_w": 0.4, "qty": None},  # None qty -> 1
        {"name": "Corner cubes", "power_w": 0.0},         # zero power: skipped
        {"name": "Broken", "power_w": -3.0},              # negative: skipped
        {"name": "", "power_w": 5.0},                     # unnamed: skipped
        {"power_w": 5.0},                                 # missing name: skipped
        {"name": None, "power_w": 5.0},                   # None name: skipped
        {"name": "Bad", "power_w": "n/a"},                # non-numeric: skipped
    ]
    loads = loads_from_equipment(items)
    assert [(ld.name, ld.power_w, ld.when) for ld in loads] == [
        ("OBC", 6.0, "always"),
        ("Radio", 1.5, "always"),
        ("Sensor", 0.4, "always"),
    ]
    assert loads_from_equipment([]) == []


# ---------------------------------------------------------------------------
# 12. Eccentric drag: the orbit-averaged decay rate sees the perigee air
#     (regression: the old circular-average shortcut sampled rho at the SMA
#     altitude — for a GTO that is ~18000 km, rho ~ 1e-43, zero decay ever)
# ---------------------------------------------------------------------------

def _gto_sat() -> SatelliteSpec:
    rp, ra = R_EARTH + 250.0, R_EARTH + 35786.0
    a, e = 0.5 * (rp + ra), (ra - rp) / (ra + rp)
    orbit = OrbitSpec(semi_major_axis_km=a, inclination_deg=27.0,
                      eccentricity=e, propagator="j2_drag")
    return SatelliteSpec(name="GTO", orbit=orbit, mass_kg=100.0,
                         drag_area_m2=1.0, drag_coefficient=2.2)


def test_eccentric_drag_sees_perigee():
    sat = _gto_sat()
    a0_spec = sat.orbit.semi_major_axis_km
    t = np.arange(0.0, 86400.0 + 1.0, 600.0)
    r, v = mission_sim._propagate(sat.orbit, t, sat)
    rn0, vn0 = np.linalg.norm(r[0]), np.linalg.norm(v[0])
    rn1, vn1 = np.linalg.norm(r[-1]), np.linalg.norm(v[-1])
    a0 = 1.0 / (2.0 / rn0 - vn0**2 / MU)
    a1 = 1.0 / (2.0 / rn1 - vn1**2 / MU)
    # measurable decay in a day (perigee grazes 250 km air), loose bracket
    assert 0.05 < a0 - a1 < 50.0
    assert a0 == approx(a0_spec, rel=1e-9)

    # and the lifetime is finite, not "> 25 years"
    lt = estimate_lifetime(sat, EPOCH)
    assert lt is not None and 0.0 < lt < 25.0


def test_mean_decay_rate_circular_limit():
    # the e > 0 quadrature must reduce to the closed-form circular King-Hele
    # rate as e -> 0 (guards the validated circular decay results)
    a = R_EARTH + 400.0
    closed = mission_sim._mean_decay_rate_km_s(a, 0.0, 0.022, 1.0)
    quad = mission_sim._mean_decay_rate_km_s(a, 1e-6, 0.022, 1.0)
    assert closed < 0.0
    assert quad == approx(closed, rel=1e-3)


def test_atmosphere_density_arr_matches_scalar():
    alts = np.array([-5.0, 0.0, 90.0, 250.0, 400.0, 800.0, 1500.0])
    vec = mission_sim._atmosphere_density_arr(alts)
    for h, r in zip(alts, vec):
        assert r == approx(atmosphere_density(h), rel=1e-12)


# ---------------------------------------------------------------------------
# 13. Link budget: worst case follows the propagated trajectory's apogee,
#     not the spec SMA (regression: Molniya-like margin was 5 dB optimistic)
# ---------------------------------------------------------------------------

def test_link_worst_case_at_apogee():
    a, e = 26562.0, 0.72
    orbit = OrbitSpec(semi_major_axis_km=a, inclination_deg=63.4,
                      arg_perigee_deg=270.0, eccentricity=e,
                      propagator="two_body")
    link = LinkSpec(name="sband", frequency_hz=2.2e9, tx_power_w=2.0,
                    tx_antenna_gain_dbi=6.5, rx_antenna_gain_dbi=32.0,
                    tx_line_loss_db=1.0, rx_line_loss_db=0.5,
                    system_noise_temperature_k=220.0, data_rate_bps=256000.0,
                    required_eb_n0_db=9.6)
    sat = SatelliteSpec(name="Molniya", orbit=orbit, links=[link])
    station = GroundStationSpec(name="GS", latitude_deg=45.4,
                                longitude_deg=11.9, min_elevation_deg=10.0)
    spec = MissionSpec(name="molniya", satellites=[sat], stations=[station],
                       start_utc=EPOCH, duration_hours=24.0, step_seconds=60.0)
    res = analyze(spec)
    lr = res.satellites[0].link_results[0]
    apogee_alt = a * (1.0 + e) - R_EARTH
    expected_slant = mission_sim.slant_range_km(apogee_alt, math.radians(10.0))
    assert lr.slant_range_km == approx(expected_slant, rel=1e-3)
    # strictly worse than the old SMA-based figure
    sma_slant = mission_sim.slant_range_km(a - R_EARTH, math.radians(10.0))
    assert lr.slant_range_km > sma_slant


# ---------------------------------------------------------------------------
# 14. SGP4: a TLE far from the analysis window warns (accuracy degrades in
#     days-to-weeks); near-epoch propagation stays silent
# ---------------------------------------------------------------------------

def test_sgp4_stale_tle_warns():
    pytest.importorskip("sgp4")
    orbit = OrbitSpec(semi_major_axis_km=6796.0, inclination_deg=51.64,
                      propagator="sgp4", tle_line1=ISS_TLE1, tle_line2=ISS_TLE2)
    stale_start = datetime(2026, 7, 20, tzinfo=timezone.utc)  # ~6.6 y past epoch
    jd = mission_sim._jd(stale_start) + np.linspace(0.0, 0.1, 10)
    with pytest.warns(UserWarning, match="TLE epoch"):
        mission_sim._propagate(orbit, np.zeros(10), None, jd)

    # near the TLE epoch: no staleness warning
    near_start = datetime(2019, 12, 9, 18, 0, 0, tzinfo=timezone.utc)
    jd_near = mission_sim._jd(near_start) + np.linspace(0.0, 0.1, 10)
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        mission_sim._propagate(orbit, np.zeros(10), None, jd_near)
