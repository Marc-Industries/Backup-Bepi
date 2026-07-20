"""Mission-level simulator: circular orbit propagation (two-body / J2 secular),
eclipse and per-face solar power, battery state of charge, ground-station
passes, RF link margins, and GO/NO-GO checks. Pure module: numpy + stdlib only.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np

MU_EARTH = 398600.4418   # km^3/s^2
R_EARTH = 6378.137       # km (WGS-84 equatorial)
SOLAR_CONSTANT = 1361.0  # W/m^2
J2 = 1.08262668e-3
BOLTZMANN_DBW = 228.6    # -10*log10(k_B), dB(W/(K*Hz))

_C_LIGHT = 299_792_458.0  # m/s


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------

@dataclass
class OrbitSpec:
    semi_major_axis_km: float
    inclination_deg: float
    raan_deg: float = 0.0
    arg_perigee_deg: float = 0.0
    true_anomaly_deg: float = 0.0
    eccentricity: float = 0.0  # kept for forward-compat; v1 propagates circular
    propagator: str = "j2"     # "two_body" | "j2" (J2 = secular RAAN drift only)


@dataclass
class SolarFace:
    name: str
    area_m2: float
    normal_body: tuple  # (x, y, z) in body frame; normalized by the engine, must be non-zero


@dataclass
class BatterySpec:
    capacity_wh: float = 30.0
    min_soc: float = 0.3
    max_soc: float = 1.0
    initial_soc: float = 0.8
    round_trip_efficiency: float = 0.9


@dataclass
class LoadSpec:
    name: str
    power_w: float
    when: str = "always"    # "always" | "sunlit" | "eclipse" | "pass"
    station_name: str = ""  # for when="pass"; empty = any station


@dataclass
class LinkSpec:
    name: str
    frequency_hz: float
    tx_power_w: float
    tx_antenna_gain_dbi: float
    rx_antenna_gain_dbi: float
    tx_line_loss_db: float
    rx_line_loss_db: float
    system_noise_temperature_k: float
    data_rate_bps: float
    required_eb_n0_db: float
    polarization_loss_db: float = 0.0
    pointing_loss_db: float = 0.0
    atmospheric_loss_db: float = 0.0


@dataclass
class GroundStationSpec:
    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_m: float = 0.0
    min_elevation_deg: float = 10.0


@dataclass
class SatelliteSpec:
    name: str
    orbit: OrbitSpec
    pointing_mode: str = "nadir"  # "nadir" | "sun" (+X body toward the Sun)
    faces: list = field(default_factory=list)
    efficiency: float = 0.3
    degradation_per_year: float = 0.025
    battery: BatterySpec = field(default_factory=BatterySpec)
    loads: list = field(default_factory=list)
    links: list = field(default_factory=list)
    mass_kg: float = 0.0
    drag_area_m2: float = 0.0


@dataclass
class MissionSpec:
    name: str
    satellites: list
    stations: list
    start_utc: datetime  # tz-aware
    duration_hours: float = 48.0
    step_seconds: float = 30.0
    years_since_bol: float = 0.0


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class PassEvent:
    station: str
    aos: datetime
    los: datetime
    max_elevation_deg: float
    duration_min: float


@dataclass
class LinkResult:
    name: str
    worst_margin_db: float
    slant_range_km: float
    fspl_db: float


@dataclass
class CheckResult:
    area: str     # "power" | "battery" | "link" | "passes"
    status: str   # "PASS" | "WATCH" | "FAIL"
    message: str


@dataclass
class SatResult:
    name: str
    times: list
    eclipse_mask: np.ndarray
    gen_w: np.ndarray
    load_w: np.ndarray
    net_w: np.ndarray
    soc: np.ndarray
    face_avg_w: dict
    avg_gen_w: float
    avg_load_w: float
    avg_net_w: float
    eclipse_count: int
    eclipse_fraction: float
    worst_eclipse_min: float
    beta_deg: float
    min_soc_reached: float
    passes: list
    link_results: list
    ground_track: list  # (lat_deg, lon_deg) per sample


@dataclass
class MissionResult:
    satellites: list
    total_passes: int
    passes_by_station: dict
    checks: list
    verdict: str  # "GO" | "REVIEW" | "WILL-NOT-FLY"
    n_samples: int


# ---------------------------------------------------------------------------
# Astro helpers (exposed for testability)
# ---------------------------------------------------------------------------

def _as_utc(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC (dt.timestamp() would use the local tz)."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _jd(dt: datetime) -> float:
    return 2440587.5 + _as_utc(dt).timestamp() / 86400.0


def _sun_eci_from_jd(jd):
    """Low-precision analytic Sun (Meeus/Montenbruck), ECI equatorial. Vectorized."""
    n = np.asarray(jd) - 2451545.0
    L = np.radians((280.460 + 0.9856474 * n) % 360.0)
    g = np.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = L + np.radians(1.915) * np.sin(g) + np.radians(0.020) * np.sin(2 * g)
    eps = np.radians(23.439 - 4e-7 * n)
    return np.stack(
        [np.cos(lam), np.cos(eps) * np.sin(lam), np.sin(eps) * np.sin(lam)], axis=-1
    )


def sun_direction_eci(dt: datetime) -> np.ndarray:
    """Unit vector from Earth to Sun in ECI equatorial frame."""
    return _sun_eci_from_jd(_jd(dt))


def gmst_rad(dt: datetime) -> float:
    """Greenwich mean sidereal time, radians."""
    n = _jd(dt) - 2451545.0
    return math.radians((280.46061837 + 360.98564736629 * n) % 360.0)


def fspl_db(distance_m: float, frequency_hz: float) -> float:
    """Free-space path loss, dB."""
    wavelength = _C_LIGHT / frequency_hz
    return 20.0 * math.log10(4.0 * math.pi * distance_m / wavelength)


def slant_range_km(altitude_km: float, elevation_rad: float) -> float:
    """Worst-case slant range to a circular orbit at a given elevation angle."""
    h = altitude_km
    se = math.sin(elevation_rad)
    return math.sqrt(R_EARTH**2 * se**2 + 2.0 * R_EARTH * h + h**2) - R_EARTH * se


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _propagate(orbit: OrbitSpec, t: np.ndarray):
    """Circular propagation. Returns (r, v) in ECI, km and km/s, shape (N, 3).

    "j2" adds the secular RAAN drift only: raan_dot = -1.5*n*J2*(RE/a)^2*cos(i).
    """
    a = orbit.semi_major_axis_km
    inc = math.radians(orbit.inclination_deg)
    n_mean = math.sqrt(MU_EARTH / a**3)
    raan_dot = 0.0
    if orbit.propagator == "j2":
        raan_dot = -1.5 * n_mean * J2 * (R_EARTH / a) ** 2 * math.cos(inc)
    raan = math.radians(orbit.raan_deg) + raan_dot * t
    u = math.radians(orbit.arg_perigee_deg + orbit.true_anomaly_deg) + n_mean * t
    ci, si = math.cos(inc), math.sin(inc)
    cu, su = np.cos(u), np.sin(u)
    cr, sr = np.cos(raan), np.sin(raan)
    # Rx(inc) applied to the in-plane vector, then Rz(raan)
    px, py, pz = cu, su * ci, su * si
    r = a * np.stack([px * cr - py * sr, px * sr + py * cr, pz], axis=1)
    qx, qy, qz = -su, cu * ci, cu * si
    v = a * n_mean * np.stack([qx * cr - qy * sr, qx * sr + qy * cr, qz], axis=1)
    return r, v


def _normalize_rows(m: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(m, axis=1, keepdims=True)
    norm[norm == 0.0] = 1.0
    return m / norm


def _body_axes(pointing_mode: str, r_hat: np.ndarray, v: np.ndarray, sun: np.ndarray):
    """Body axes in ECI, each (N, 3). Nadir: +Z = zenith, +X = along-track.
    Sun-pointing: +X = Sun direction, +Z as close to zenith as possible."""
    if pointing_mode == "sun":
        xb = sun
        zb = _normalize_rows(r_hat - np.sum(r_hat * xb, axis=1, keepdims=True) * xb)
        yb = np.cross(zb, xb)
    else:  # nadir
        zb = r_hat
        xb = _normalize_rows(v - np.sum(v * zb, axis=1, keepdims=True) * zb)
        yb = np.cross(zb, xb)
    return xb, yb, zb


def _runs(mask: np.ndarray):
    """Contiguous True runs of a boolean array -> list of (start, end_exclusive)."""
    padded = np.concatenate(([False], mask, [False])).astype(np.int8)
    d = np.diff(padded)
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return list(zip(starts, ends))


def _link_result(link: LinkSpec, altitude_km: float, min_elevation_deg: float) -> LinkResult:
    slant = slant_range_km(altitude_km, math.radians(min_elevation_deg))
    fspl = fspl_db(slant * 1000.0, link.frequency_hz)
    eirp = 10.0 * math.log10(link.tx_power_w) + link.tx_antenna_gain_dbi - link.tx_line_loss_db
    g_over_t = (link.rx_antenna_gain_dbi - link.rx_line_loss_db
                - 10.0 * math.log10(link.system_noise_temperature_k))
    eb_n0 = (eirp - fspl + g_over_t + BOLTZMANN_DBW
             - 10.0 * math.log10(link.data_rate_bps)
             - link.polarization_loss_db - link.pointing_loss_db
             - link.atmospheric_loss_db)
    return LinkResult(
        name=link.name,
        worst_margin_db=eb_n0 - link.required_eb_n0_db,
        slant_range_km=slant,
        fspl_db=fspl,
    )


_SEVERITY = {"PASS": 0, "WATCH": 1, "FAIL": 2}


def _worst(status_a: str, status_b: str) -> str:
    return status_a if _SEVERITY[status_a] >= _SEVERITY[status_b] else status_b


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def analyze(spec: MissionSpec) -> MissionResult:
    n_samples = int(spec.duration_hours * 3600.0 / spec.step_seconds) + 1
    step = spec.step_seconds
    t = np.arange(n_samples) * step
    start_utc = _as_utc(spec.start_utc)
    epoch_ts = start_utc.timestamp()
    jd_arr = 2440587.5 + (epoch_ts + t) / 86400.0
    times = [start_utc + timedelta(seconds=float(tk)) for tk in t]
    sun = _sun_eci_from_jd(jd_arr)  # (N, 3)
    gmst = np.radians((280.46061837 + 360.98564736629 * (jd_arr - 2451545.0)) % 360.0)

    if spec.stations:
        link_elev_deg = min(st.min_elevation_deg for st in spec.stations)
    else:
        link_elev_deg = 10.0

    sat_results: list[SatResult] = []
    for sat in spec.satellites:
        r, v = _propagate(sat.orbit, t)
        r_norm = np.linalg.norm(r, axis=1)
        r_hat = r / r_norm[:, None]

        # eclipse: cylindrical umbra (behind Earth, inside a cylinder of radius RE)
        proj = np.sum(r * sun, axis=1)
        perp = np.linalg.norm(r - proj[:, None] * sun, axis=1)
        eclipse = (proj < 0.0) & (perp < R_EARTH)

        # solar generation per face
        xb, yb, zb = _body_axes(sat.pointing_mode, r_hat, v, sun)
        # degradation cannot drive generation negative: clamp the scale at zero
        power_scale = sat.efficiency * max(0.0, 1.0 - sat.degradation_per_year * spec.years_since_bol)
        gen = np.zeros(n_samples)
        face_avg_w: dict[str, float] = {}
        for face in sat.faces:
            nx, ny, nz = face.normal_body
            n_norm = math.sqrt(nx * nx + ny * ny + nz * nz)
            if not math.isfinite(n_norm) or n_norm == 0.0:
                raise ValueError(
                    f"SolarFace {face.name!r}: normal_body must be a finite, "
                    f"non-zero vector (got {face.normal_body!r})")
            n_eci = (nx * xb + ny * yb + nz * zb) / n_norm
            cos_i = np.clip(np.sum(n_eci * sun, axis=1), 0.0, None)
            p = SOLAR_CONSTANT * face.area_m2 * power_scale * cos_i
            p[eclipse] = 0.0
            gen += p
            face_avg_w[face.name] = float(np.mean(p))

        # ground-station visibility (stations rotated to pseudo-inertial via GMST)
        pass_masks: dict[str, np.ndarray] = {}
        elevations: dict[str, np.ndarray] = {}
        for st in spec.stations:
            lat = math.radians(st.latitude_deg)
            lon = math.radians(st.longitude_deg)
            radius = R_EARTH + st.altitude_m / 1000.0
            gs = radius * np.stack(
                [np.cos(lat) * np.cos(lon + gmst),
                 np.cos(lat) * np.sin(lon + gmst),
                 np.full(n_samples, math.sin(lat))], axis=1)
            rng = r - gs
            gs_hat = gs / radius
            elev = np.arcsin(np.sum(rng * gs_hat, axis=1) / np.linalg.norm(rng, axis=1))
            elevations[st.name] = elev
            pass_masks[st.name] = elev > math.radians(st.min_elevation_deg)
        if pass_masks:
            any_pass = np.logical_or.reduce(list(pass_masks.values()))
        else:
            any_pass = np.zeros(n_samples, dtype=bool)

        # loads
        load = np.zeros(n_samples)
        for ld in sat.loads:
            if ld.when == "always":
                load += ld.power_w
            elif ld.when == "sunlit":
                load += ld.power_w * (~eclipse)
            elif ld.when == "eclipse":
                load += ld.power_w * eclipse
            elif ld.when == "pass":
                mask = pass_masks.get(ld.station_name, None) if ld.station_name else any_pass
                if mask is not None:
                    load += ld.power_w * mask
        net = gen - load

        # battery SoC: sqrt-split of round-trip efficiency (charge *= sqrt(rte),
        # discharge /= sqrt(rte)) so the full cycle loses exactly (1 - rte)
        batt = sat.battery
        soc = np.empty(n_samples)
        state = batt.initial_soc
        sqrt_eff = math.sqrt(batt.round_trip_efficiency)
        cap = batt.capacity_wh if batt.capacity_wh > 0 else 1e-9
        for k in range(n_samples):
            e_wh = net[k] * step / 3600.0
            if e_wh > 0.0:
                state += e_wh * sqrt_eff / cap
            else:
                state += e_wh / (sqrt_eff * cap)
            state = min(max(state, 0.0), batt.max_soc)
            soc[k] = state
        min_soc_reached = float(min(batt.initial_soc, soc.min()))

        # eclipse statistics
        ecl_runs = _runs(eclipse)
        worst_eclipse_min = max((e - s for s, e in ecl_runs), default=0) * step / 60.0

        # passes
        passes: list[PassEvent] = []
        for st in spec.stations:
            elev = elevations[st.name]
            for s_idx, e_idx in _runs(pass_masks[st.name]):
                passes.append(PassEvent(
                    station=st.name,
                    aos=times[s_idx],
                    los=times[e_idx - 1],
                    max_elevation_deg=float(np.degrees(elev[s_idx:e_idx].max())),
                    duration_min=(e_idx - s_idx) * step / 60.0,
                ))
        passes.sort(key=lambda p: p.aos)

        # links (worst case at the lowest station minimum elevation)
        altitude_km = sat.orbit.semi_major_axis_km - R_EARTH
        link_results = [_link_result(lk, altitude_km, link_elev_deg) for lk in sat.links]

        # beta angle at epoch (orbit normal vs Sun)
        normal = np.cross(r[0], v[0])
        normal /= np.linalg.norm(normal)
        beta_deg = math.degrees(math.asin(float(np.clip(np.dot(normal, sun[0]), -1.0, 1.0))))

        # ground track (GMST Earth rotation)
        lat_deg = np.degrees(np.arcsin(r[:, 2] / r_norm))
        lon = np.arctan2(r[:, 1], r[:, 0]) - gmst
        lon_deg = np.degrees((lon + np.pi) % (2.0 * np.pi) - np.pi)
        ground_track = list(zip(lat_deg.tolist(), lon_deg.tolist()))

        sat_results.append(SatResult(
            name=sat.name,
            times=times,
            eclipse_mask=eclipse,
            gen_w=gen,
            load_w=load,
            net_w=net,
            soc=soc,
            face_avg_w=face_avg_w,
            avg_gen_w=float(np.mean(gen)),
            avg_load_w=float(np.mean(load)),
            avg_net_w=float(np.mean(net)),
            eclipse_count=len(ecl_runs),
            eclipse_fraction=float(np.mean(eclipse)),
            worst_eclipse_min=worst_eclipse_min,
            beta_deg=beta_deg,
            min_soc_reached=min_soc_reached,
            passes=passes,
            link_results=link_results,
            ground_track=ground_track,
        ))

    total_passes = sum(len(sr.passes) for sr in sat_results)
    passes_by_station: dict[str, int] = {st.name: 0 for st in spec.stations}
    for sr in sat_results:
        for p in sr.passes:
            passes_by_station[p.station] = passes_by_station.get(p.station, 0) + 1

    checks = _build_checks(spec, sat_results, total_passes)
    worst_status = "PASS"
    for c in checks:
        worst_status = _worst(worst_status, c.status)
    verdict = {"PASS": "GO", "WATCH": "REVIEW", "FAIL": "WILL-NOT-FLY"}[worst_status]

    return MissionResult(
        satellites=sat_results,
        total_passes=total_passes,
        passes_by_station=passes_by_station,
        checks=checks,
        verdict=verdict,
        n_samples=n_samples,
    )


def _build_checks(spec: MissionSpec, sat_results: list, total_passes: int) -> list:
    checks: list[CheckResult] = []

    # power: FAIL if avg_net < 0, WATCH if avg_net < 0.2*avg_load
    status, message = "PASS", "Positive average power margin on all satellites."
    for sr in sat_results:
        if sr.avg_net_w < 0.0:
            s = "FAIL"
            m = f"{sr.name}: average net power is {sr.avg_net_w:+.2f} W — generation does not cover the loads."
        elif sr.avg_net_w < 0.2 * sr.avg_load_w:
            s = "WATCH"
            m = f"{sr.name}: average net power {sr.avg_net_w:+.2f} W is thin against a {sr.avg_load_w:.2f} W load."
        else:
            s = "PASS"
            m = f"{sr.name}: average net power {sr.avg_net_w:+.2f} W over a {sr.avg_load_w:.2f} W load."
        if _SEVERITY[s] >= _SEVERITY[status]:
            status, message = s, m
    checks.append(CheckResult(area="power", status=status, message=message))

    # battery: FAIL at/below the SoC floor, WATCH within 0.05 above it
    status, message = "PASS", "Battery state of charge stays clear of its floor."
    for sr in sat_results:
        floor = next((s.battery.min_soc for s in spec.satellites if s.name == sr.name), 0.0)
        if sr.min_soc_reached <= floor + 1e-9:
            s = "FAIL"
            m = f"{sr.name}: battery hits its {floor:.0%} floor (min SoC {sr.min_soc_reached:.0%})."
        elif sr.min_soc_reached <= floor + 0.05:
            s = "WATCH"
            m = f"{sr.name}: battery min SoC {sr.min_soc_reached:.0%} is within 5 points of the {floor:.0%} floor."
        else:
            s = "PASS"
            m = f"{sr.name}: battery min SoC {sr.min_soc_reached:.0%} against a {floor:.0%} floor."
        if _SEVERITY[s] >= _SEVERITY[status]:
            status, message = s, m
    checks.append(CheckResult(area="battery", status=status, message=message))

    # link: FAIL if worst margin < 0 dB, WATCH if < 3 dB
    has_links = any(sr.link_results for sr in sat_results)
    if has_links:
        status, message = "PASS", "All links close with margin."
        for sr in sat_results:
            for lr in sr.link_results:
                if lr.worst_margin_db < 0.0:
                    s = "FAIL"
                    m = f"{sr.name}/{lr.name}: link does not close ({lr.worst_margin_db:+.1f} dB worst case)."
                elif lr.worst_margin_db < 3.0:
                    s = "WATCH"
                    m = f"{sr.name}/{lr.name}: worst-case link margin {lr.worst_margin_db:+.1f} dB is under 3 dB."
                else:
                    s = "PASS"
                    m = f"{sr.name}/{lr.name}: worst-case link margin {lr.worst_margin_db:+.1f} dB."
                if _SEVERITY[s] >= _SEVERITY[status]:
                    status, message = s, m
        checks.append(CheckResult(area="link", status=status, message=message))

    # passes: FAIL only if stations exist and nothing is ever visible
    if spec.stations and total_passes == 0:
        checks.append(CheckResult(
            area="passes", status="FAIL",
            message="No ground-station passes in the whole window — check orbit and station geometry."))
    else:
        checks.append(CheckResult(
            area="passes", status="PASS",
            message=f"{total_passes} ground-station passes in the analysis window."))

    return checks


# ---------------------------------------------------------------------------
# Constellations, sweeps, sensitivity
# ---------------------------------------------------------------------------

def walker_delta(total_sats: int, planes: int, phasing: int, base: SatelliteSpec) -> list:
    """Walker delta T/P/F constellation built from a template satellite."""
    if planes < 1 or total_sats < 1:
        raise ValueError(f"Walker delta needs T >= 1 and P >= 1 (got T={total_sats}, P={planes})")
    if total_sats % planes != 0:
        raise ValueError(
            f"Walker delta T must be a multiple of P (got T={total_sats}, P={planes})")
    per_plane = total_sats // planes
    sats: list[SatelliteSpec] = []
    for p in range(planes):
        for s in range(per_plane):
            sat = copy.deepcopy(base)
            sat.name = f"{base.name}-P{p + 1}S{s + 1}"
            sat.orbit.raan_deg = base.orbit.raan_deg + 360.0 * p / planes
            sat.orbit.true_anomaly_deg = (base.orbit.true_anomaly_deg
                                          + 360.0 * s / per_plane
                                          + 360.0 * phasing * p / total_sats)
            sats.append(sat)
    return sats


def _apply_parameter(spec: MissionSpec, parameter: str, value: float) -> None:
    if parameter == "altitude_km":
        for sat in spec.satellites:
            sat.orbit.semi_major_axis_km = R_EARTH + value
    elif parameter == "inclination_deg":
        for sat in spec.satellites:
            sat.orbit.inclination_deg = value
    elif parameter == "battery_capacity_wh":
        for sat in spec.satellites:
            sat.battery.capacity_wh = value
    elif parameter == "tx_power_w":
        for sat in spec.satellites:
            for link in sat.links:
                link.tx_power_w = value
    elif parameter == "data_rate_bps":
        for sat in spec.satellites:
            for link in sat.links:
                link.data_rate_bps = value
    elif parameter == "solar_area_scale":
        # scale relative to the ORIGINAL spec: callers always deepcopy it first
        for sat in spec.satellites:
            for face in sat.faces:
                face.area_m2 *= value
    elif parameter == "years_since_bol":
        spec.years_since_bol = value
    else:
        raise ValueError(f"Unknown sweep parameter: {parameter!r}")


def _parameter_base(spec: MissionSpec, parameter: str) -> float:
    sat0 = spec.satellites[0]
    if parameter == "altitude_km":
        return sat0.orbit.semi_major_axis_km - R_EARTH
    if parameter == "inclination_deg":
        return sat0.orbit.inclination_deg
    if parameter == "battery_capacity_wh":
        return sat0.battery.capacity_wh
    if parameter == "tx_power_w":
        return sat0.links[0].tx_power_w
    if parameter == "data_rate_bps":
        return sat0.links[0].data_rate_bps
    if parameter == "solar_area_scale":
        return 1.0
    if parameter == "years_since_bol":
        return spec.years_since_bol
    raise ValueError(f"Unknown sweep parameter: {parameter!r}")


def _extract_measure(result: MissionResult, measure: str) -> float:
    if measure == "avg_net_w":
        return result.satellites[0].avg_net_w
    if measure == "min_soc":
        return min(sr.min_soc_reached for sr in result.satellites)
    if measure == "worst_link_margin_db":
        margins = [lr.worst_margin_db for sr in result.satellites for lr in sr.link_results]
        return min(margins) if margins else float("nan")
    if measure == "total_passes":
        return float(result.total_passes)
    if measure == "eclipse_fraction":
        return result.satellites[0].eclipse_fraction
    raise ValueError(f"Unknown measure: {measure!r}")


def sweep(spec: MissionSpec, parameter: str, values: list, measure: str) -> list:
    """Re-run the analysis over a range of one parameter. Returns [(value, measure)]."""
    points = []
    for value in values:
        trial = copy.deepcopy(spec)
        _apply_parameter(trial, parameter, value)
        points.append((float(value), _extract_measure(analyze(trial), measure)))
    return points


def sensitivity(spec: MissionSpec, measure: str, parameters: list,
                perturbation: float = 0.05) -> dict:
    """One-at-a-time relative perturbation of each parameter around its base value."""
    base_value = _extract_measure(analyze(copy.deepcopy(spec)), measure)
    out: dict[str, dict[str, float]] = {}
    for parameter in parameters:
        base = _parameter_base(spec, parameter)
        entry = {"base": base_value}
        for key, factor in (("minus", 1.0 - perturbation), ("plus", 1.0 + perturbation)):
            trial = copy.deepcopy(spec)
            _apply_parameter(trial, parameter, base * factor)
            entry[key] = _extract_measure(analyze(trial), measure)
        out[parameter] = entry
    return out
