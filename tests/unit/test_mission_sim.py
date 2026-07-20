"""Regression tests for bepi.integrations.mission_sim.

Expected values are REFERENCE numbers from the Apside cloud tool (independently
reproduced by a local POC) — they are NOT regenerated from the engine, so a
failure here means the engine drifted, not the test.

One deviation from the reference sheet, on physical grounds (see
test_sensitivity_couplings): a +5% change of transmit POWER moves the link
margin by 10*log10(1.05) = +0.212 dB, not 20*log10(1.05) = 0.424 dB
(20*log10 applies to amplitude ratios, not power ratios).
"""

import math
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
    fspl_db,
    sensitivity,
    slant_range_km,
    sweep,
    walker_delta,
)

EPOCH = datetime(2026, 7, 20, 8, 27, 38, tzinfo=timezone.utc)


def albasat_spec() -> MissionSpec:
    """2U CubeSat, 500 km SSO-like orbit, Padova ground station (reference scenario)."""
    orbit = OrbitSpec(
        semi_major_axis_km=6878.137,
        inclination_deg=97.4,
        raan_deg=0.0,
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


@pytest.fixture(scope="module")
def albasat_result():
    return analyze(albasat_spec())


# ---------------------------------------------------------------------------
# 1. Full-scenario regression against the Apside reference numbers
# ---------------------------------------------------------------------------

def test_albasat_regression(albasat_result):
    res = albasat_result
    assert res.n_samples == 5761
    sr = res.satellites[0]
    assert len(sr.times) == 5761
    assert sr.gen_w.shape == (5761,)

    # orbital period (from the module constants, not the engine run)
    period_min = 2 * math.pi * math.sqrt(6878.137**3 / mission_sim.MU_EARTH) / 60.0
    assert period_min == approx(94.62, abs=0.05)

    # eclipses
    assert sr.eclipse_count in {30, 31, 32}
    assert sr.eclipse_fraction == approx(0.253, abs=0.015)
    assert sr.worst_eclipse_min == approx(25.0, abs=2.0)

    # beta angle at epoch
    assert sr.beta_deg == approx(-58.3, abs=1.5)

    # per-face average solar power [W]
    expected_faces = {"+X": 1.21, "-X": 1.17, "+Y": 0.00, "-Y": 5.15, "-Z": 0.20}
    assert set(sr.face_avg_w) == set(expected_faces)
    for name, expected_w in expected_faces.items():
        assert sr.face_avg_w[name] == approx(expected_w, abs=0.2), name
    assert sr.avg_gen_w == approx(7.72, abs=0.2)
    assert sr.avg_net_w == approx(5.59, abs=0.25)

    # ground-station passes
    assert res.total_passes == 8
    assert res.passes_by_station == {"Padova GS": 8}
    assert len(sr.passes) == 8
    assert all(p.station == "Padova GS" for p in sr.passes)

    # link budget at 10 deg elevation, h = 500 km
    lr = sr.link_results[0]
    assert lr.slant_range_km == approx(1695.0, abs=5.0)
    assert lr.fspl_db == approx(164.6, abs=0.1)
    assert lr.worst_margin_db == approx(4.4, abs=0.6)


# ---------------------------------------------------------------------------
# 2. Two-body propagation closes after one period
# ---------------------------------------------------------------------------

def test_two_body_period_closure():
    orbit = OrbitSpec(semi_major_axis_km=7000.0, inclination_deg=51.6,
                      raan_deg=30.0, true_anomaly_deg=45.0,
                      propagator="two_body")
    period_s = 2 * math.pi * math.sqrt(7000.0**3 / mission_sim.MU_EARTH)
    r, _v = mission_sim._propagate(orbit, np.array([0.0, period_s]))
    rel_err = np.linalg.norm(r[1] - r[0]) / np.linalg.norm(r[0])
    assert rel_err < 1e-6


# ---------------------------------------------------------------------------
# 3. FSPL: doubling the distance adds 6.02 dB
# ---------------------------------------------------------------------------

def test_fspl_doubling():
    f = 2.4e9
    d = 1_000_000.0
    assert fspl_db(2 * d, f) - fspl_db(d, f) == approx(20 * math.log10(2.0), abs=0.01)
    assert fspl_db(2 * d, f) - fspl_db(d, f) == approx(6.02, abs=0.01)


# ---------------------------------------------------------------------------
# 4. Sun pointing: a +X face generates exactly S * A * eff whenever sunlit
# ---------------------------------------------------------------------------

def test_sun_pointing_generation():
    sat = SatelliteSpec(
        name="SunPointer",
        orbit=OrbitSpec(semi_major_axis_km=6878.137, inclination_deg=97.4),
        pointing_mode="sun",
        faces=[SolarFace(name="+X", area_m2=0.1, normal_body=(1, 0, 0))],
        efficiency=0.3,
    )
    spec = MissionSpec(name="sun-test", satellites=[sat], stations=[],
                       start_utc=EPOCH, duration_hours=3.0, step_seconds=30.0)
    sr = analyze(spec).satellites[0]
    sunlit = ~sr.eclipse_mask
    assert sunlit.any() and sr.eclipse_mask.any()
    expected_w = mission_sim.SOLAR_CONSTANT * 0.1 * 0.3
    np.testing.assert_allclose(sr.gen_w[sunlit], expected_w, rtol=0, atol=1e-6)
    assert np.all(sr.gen_w[sr.eclipse_mask] == 0.0)


# ---------------------------------------------------------------------------
# 5. SoC stays within bounds; a starved battery is a FAIL / WILL-NOT-FLY
# ---------------------------------------------------------------------------

def test_soc_bounds():
    sat = SatelliteSpec(
        name="Drainer",
        orbit=OrbitSpec(semi_major_axis_km=6878.137, inclination_deg=97.4),
        faces=[],  # no generation at all
        loads=[LoadSpec(name="big_heater", power_w=50.0, when="always")],
        battery=BatterySpec(capacity_wh=30.0, min_soc=0.3, max_soc=1.0,
                            initial_soc=0.8, round_trip_efficiency=0.9),
    )
    spec = MissionSpec(name="drain-test", satellites=[sat], stations=[],
                       start_utc=EPOCH, duration_hours=2.0, step_seconds=30.0)
    res = analyze(spec)
    sr = res.satellites[0]
    assert np.all(sr.soc >= 0.0)
    assert np.all(sr.soc <= sat.battery.max_soc + 1e-12)
    assert sr.min_soc_reached <= sat.battery.min_soc + 1e-9
    battery_check = next(c for c in res.checks if c.area == "battery")
    assert battery_check.status == "FAIL"
    assert res.verdict == "WILL-NOT-FLY"


# ---------------------------------------------------------------------------
# 6. Load scheduling: "pass" loads only inside pass windows, "sunlit" never
#    in eclipse
# ---------------------------------------------------------------------------

def test_load_scheduling():
    spec = albasat_spec()
    spec.duration_hours = 24.0
    sat = spec.satellites[0]
    sat.loads = [
        LoadSpec(name="pass_load", power_w=2.0, when="pass",
                 station_name="Padova GS"),
        LoadSpec(name="sun_load", power_w=1.0, when="sunlit"),
    ]
    res = analyze(spec)
    sr = res.satellites[0]
    assert len(sr.passes) > 0

    # rebuild the per-sample pass mask from the reported AOS/LOS events
    step = spec.step_seconds
    pass_mask = np.zeros(res.n_samples, dtype=bool)
    for p in sr.passes:
        s = round((p.aos - spec.start_utc).total_seconds() / step)
        e = round((p.los - spec.start_utc).total_seconds() / step)
        assert 0 <= s <= e < res.n_samples
        pass_mask[s:e + 1] = True

    expected_load = 2.0 * pass_mask + 1.0 * (~sr.eclipse_mask)
    np.testing.assert_allclose(sr.load_w, expected_load, rtol=0, atol=1e-9)
    # explicit spot checks of the contract
    assert np.all(sr.load_w[~pass_mask] < 2.0)               # pass load off outside passes
    assert np.all(sr.load_w[sr.eclipse_mask] % 2.0 == 0.0)   # sunlit load off in eclipse


# ---------------------------------------------------------------------------
# 7. Altitude sweep of the worst-case link margin
# ---------------------------------------------------------------------------

def test_sweep_altitude_link_margin():
    spec = albasat_spec()
    spec.duration_hours = 1.0  # link margin is geometry-only, keep the runs cheap
    values = [float(v) for v in np.linspace(400.0, 800.0, 15)]
    points = sweep(spec, "altitude_km", values, "worst_link_margin_db")
    assert len(points) == 15
    assert [v for v, _ in points] == approx(values)
    margins = [m for _, m in points]
    assert all(margins[i + 1] < margins[i] for i in range(len(margins) - 1)), \
        "link margin must be strictly decreasing with altitude"
    assert margins[0] == approx(5.78, abs=0.4)
    assert margins[-1] == approx(1.53, abs=0.4)


# ---------------------------------------------------------------------------
# 8. Sensitivity couplings on the worst link margin
# ---------------------------------------------------------------------------

def test_sensitivity_couplings():
    spec = albasat_spec()
    spec.duration_hours = 1.0
    out = sensitivity(
        spec,
        "worst_link_margin_db",
        ["tx_power_w", "battery_capacity_wh", "solar_area_scale", "years_since_bol"],
        perturbation=0.05,
    )

    # A +/-5% POWER ratio in dB is 10*log10(1 +/- 0.05): +0.212 / -0.223 dB.
    # (The reference sheet's 20*log10(1.05) = 0.424 dB is the AMPLITUDE-ratio
    # formula and is not the correct expectation for a transmit-power change.)
    tx = out["tx_power_w"]
    assert tx["plus"] - tx["base"] == approx(10 * math.log10(1.05), abs=0.03)
    assert tx["minus"] - tx["base"] == approx(10 * math.log10(0.95), abs=0.03)

    # These parameters must not couple into the link margin at all.
    for param in ("battery_capacity_wh", "solar_area_scale", "years_since_bol"):
        entry = out[param]
        assert entry["plus"] == entry["base"] == entry["minus"], param


# ---------------------------------------------------------------------------
# 9. Walker delta 6/3/1 geometry
# ---------------------------------------------------------------------------

def test_walker_expansion():
    base = SatelliteSpec(
        name="W",
        orbit=OrbitSpec(semi_major_axis_km=6878.137, inclination_deg=97.4,
                        raan_deg=10.0, true_anomaly_deg=20.0),
    )
    sats = walker_delta(6, 3, 1, base)
    assert len(sats) == 6
    by_name = {s.name: s for s in sats}
    assert set(by_name) == {"W-P1S1", "W-P1S2", "W-P2S1", "W-P2S2", "W-P3S1", "W-P3S2"}

    for p in range(3):
        s1 = by_name[f"W-P{p + 1}S1"]
        s2 = by_name[f"W-P{p + 1}S2"]
        # plane RAAN: base + 120 deg per plane
        assert s1.orbit.raan_deg % 360.0 == approx((10.0 + 120.0 * p) % 360.0)
        assert s2.orbit.raan_deg == s1.orbit.raan_deg
        # in-plane spacing: 360/(T/P) = 180 deg
        assert (s2.orbit.true_anomaly_deg - s1.orbit.true_anomaly_deg) % 360.0 == approx(180.0)
        # inter-plane phasing: 360*F/T = 60 deg per plane
        assert s1.orbit.true_anomaly_deg % 360.0 == approx((20.0 + 60.0 * p) % 360.0)
    # base spec untouched
    assert base.orbit.raan_deg == 10.0
    assert base.orbit.true_anomaly_deg == 20.0


# ---------------------------------------------------------------------------
# 10. A healthy spec gets a clean GO
# ---------------------------------------------------------------------------

def test_verdict_go():
    spec = albasat_spec()
    spec.duration_hours = 24.0
    sat = spec.satellites[0]
    sat.pointing_mode = "sun"
    sat.faces = [SolarFace(name="wing", area_m2=0.5, normal_body=(1, 0, 0))]
    sat.loads = [LoadSpec(name="bus", power_w=1.0, when="always")]
    sat.links[0].tx_power_w = 10.0  # +10 dB on an already-closing link
    res = analyze(spec)
    assert all(c.status == "PASS" for c in res.checks), \
        [(c.area, c.status, c.message) for c in res.checks]
    assert res.verdict == "GO"


# ---------------------------------------------------------------------------
# 11. Input hardening regressions
# ---------------------------------------------------------------------------

def _sun_pointer(**overrides) -> MissionSpec:
    sat = SatelliteSpec(
        name="SunPointer",
        orbit=OrbitSpec(semi_major_axis_km=6878.137, inclination_deg=97.4),
        pointing_mode="sun",
        faces=[SolarFace(name="+X", area_m2=0.1, normal_body=(1, 0, 0))],
        efficiency=0.3,
    )
    spec = MissionSpec(name="hardening", satellites=[sat], stations=[],
                       start_utc=EPOCH, duration_hours=3.0, step_seconds=30.0)
    for key, value in overrides.items():
        setattr(spec, key, value)
    return spec


def test_degradation_never_negative():
    # years_since_bol beyond 1/degradation used to flip generation NEGATIVE
    spec = _sun_pointer(years_since_bol=50.0)  # 50 * 0.025 = 1.25 > 1
    sr = analyze(spec).satellites[0]
    assert np.all(sr.gen_w == 0.0)
    # and a sweep crossing the zero point stays monotonically non-negative
    points = sweep(_sun_pointer(), "years_since_bol", [0.0, 20.0, 40.0, 60.0], "avg_net_w")
    gens = [m for _, m in points]
    assert gens[-1] == approx(gens[-2], abs=1e-9)  # clamped, not sign-flipped


def test_face_normal_is_normalized():
    # a canted face entered as (1, 0, 1) must generate cos(45 deg), not sqrt(2)*cos(45 deg)
    spec = _sun_pointer()
    spec.satellites[0].faces = [SolarFace(name="cant", area_m2=0.1, normal_body=(1, 0, 1))]
    sr = analyze(spec).satellites[0]
    sunlit = ~sr.eclipse_mask
    assert sunlit.any()
    expected_w = mission_sim.SOLAR_CONSTANT * 0.1 * 0.3 * math.cos(math.radians(45.0))
    np.testing.assert_allclose(sr.gen_w[sunlit], expected_w, rtol=0, atol=1e-6)


def test_face_normal_zero_or_nan_rejected():
    for bad in [(0.0, 0.0, 0.0), (float("nan"),) * 3]:
        spec = _sun_pointer()
        spec.satellites[0].faces = [SolarFace(name="bad", area_m2=0.1, normal_body=bad)]
        with pytest.raises(ValueError, match="normal_body"):
            analyze(spec)


def test_walker_rejects_invalid_configs():
    base = SatelliteSpec(
        name="W", orbit=OrbitSpec(semi_major_axis_km=6878.137, inclination_deg=97.4))
    with pytest.raises(ValueError):  # T < P used to return [] silently
        walker_delta(2, 3, 0, base)
    with pytest.raises(ValueError):  # T not a multiple of P used to drop satellites
        walker_delta(10, 3, 1, base)
    with pytest.raises(ValueError):
        walker_delta(0, 1, 0, base)
    assert len(walker_delta(6, 3, 1, base)) == 6


def test_naive_start_utc_treated_as_utc():
    # a NAIVE datetime must not shift GMST by the machine's local UTC offset
    naive = EPOCH.replace(tzinfo=None)
    assert mission_sim.gmst_rad(naive) == approx(mission_sim.gmst_rad(EPOCH))
    res_naive = analyze(_sun_pointer(start_utc=naive))
    res_aware = analyze(_sun_pointer())
    np.testing.assert_allclose(res_naive.satellites[0].gen_w,
                               res_aware.satellites[0].gen_w, rtol=0, atol=1e-9)
