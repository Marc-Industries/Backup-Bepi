"""Launch vehicle selection and performance tool."""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import plotly.graph_objects as go


class VehicleStatus(str, Enum):
    ACTIVE = "active"
    RETIRED = "retired"
    DEVELOPMENT = "development"


class OrbitType(str, Enum):
    LEO = "LEO"
    GTO = "GTO"
    SSO = "SSO"
    ESCAPE = "escape"


@dataclass
class LaunchVehicle:
    name: str
    provider: str
    payload_leo_kg: float
    payload_gto_kg: float
    payload_sso_kg: Optional[float]
    fairing_diameter_m: float
    fairing_height_m: float
    cost_musd: Optional[float]
    reliability: float  # 0-1
    first_flight_year: int
    status: VehicleStatus
    # C3 reference points: list of (c3_km2s2, payload_kg) for interpolation
    c3_curve: list = field(default_factory=list)


# Gravitational parameters (km^3/s^2)
MU = {
    "earth": 398600.4418,
    "moon": 4902.800066,
    "mars": 42828.375214,
    "jupiter": 126686534.0,
    "saturn": 37931187.0,
    "venus": 324859.0,
    "mercury": 22031.78,
    "sun": 132712440041.94,
}

# Body radii (km)
BODY_RADIUS = {
    "earth": 6371.0,
    "moon": 1737.4,
    "mars": 3389.5,
    "jupiter": 69911.0,
    "saturn": 58232.0,
    "venus": 6051.8,
    "mercury": 2439.7,
}

# Approximate synodic periods (days) for departure from Earth
SYNODIC_PERIOD = {
    "mars": 780,
    "venus": 584,
    "jupiter": 399,
    "saturn": 378,
    "mercury": 116,
    "moon": 29.5,
}

# Approximate transfer C3 from Earth (km^2/s^2)
TYPICAL_C3 = {
    "mars": 10.0,
    "venus": 7.0,
    "jupiter": 80.0,
    "saturn": 110.0,
    "mercury": 50.0,
    "moon": 0.5,
}


def _make_c3_curve(leo_kg: float, gto_kg: float) -> list:
    """Build approximate C3 curve from LEO/GTO capacity.

    Uses a simplified quadratic decay model:
    - C3 = 0 => ~LEO payload (low orbit, minimal excess energy)
    - C3 ~ -15 to -20 => GTO payload (bound orbit, negative C3 convention
      not used here; instead we map GTO to C3~10 for trans-GTO injection)
    - C3 ~ 100+ => near-zero payload

    We anchor: C3=0 -> leo_kg, C3=10 -> gto_kg, and extrapolate.
    """
    if leo_kg <= 0:
        return [(0, 0)]
    ratio = gto_kg / leo_kg if leo_kg > 0 else 0.4
    # Quadratic: m(c3) = leo_kg * (1 - c3/c3_max)^alpha
    # Solve for alpha: at c3=10, m=gto_kg => ratio = (1 - 10/c3_max)^alpha
    c3_max = 10.0 / (1.0 - ratio ** 0.5) if ratio < 1.0 else 200.0
    c3_max = min(max(c3_max, 30.0), 300.0)
    points = []
    for c3 in range(0, int(c3_max) + 1, 5):
        frac = 1.0 - c3 / c3_max
        if frac <= 0:
            break
        m = leo_kg * frac ** 2
        if m < 0:
            break
        points.append((float(c3), m))
    if not points or points[-1][1] > 0:
        points.append((c3_max, 0.0))
    return points


def _build_vehicles() -> dict:
    vehicles_data = [
        ("Falcon 9", "SpaceX", 22800, 8300, 4500, 5.2, 13.1, 67, 0.98, 2010, VehicleStatus.ACTIVE),
        ("Falcon Heavy", "SpaceX", 63800, 26700, None, 5.2, 13.1, 150, 0.97, 2018, VehicleStatus.ACTIVE),
        ("Ariane 62", "ArianeGroup", 10350, 4500, None, 5.4, 20.0, 80, 0.95, 2024, VehicleStatus.ACTIVE),
        ("Ariane 64", "ArianeGroup", 21600, 11500, None, 5.4, 20.0, 130, 0.95, 2024, VehicleStatus.ACTIVE),
        ("Vega-C", "Avio", 2300, None, 1500, 3.3, 8.6, 40, 0.93, 2022, VehicleStatus.ACTIVE),
        ("Soyuz-2", "Roscosmos", 8200, 3250, None, 4.1, 11.4, 50, 0.97, 2004, VehicleStatus.ACTIVE),
        ("Atlas V 551", "ULA", 18850, 8900, None, 5.4, 12.2, 153, 0.99, 2002, VehicleStatus.ACTIVE),
        ("Vulcan Centaur", "ULA", 27200, 14400, None, 5.4, 15.5, 110, 0.95, 2024, VehicleStatus.ACTIVE),
        ("H3-24", "JAXA/MHI", 6500, 3400, None, 5.2, 16.0, 50, 0.95, 2024, VehicleStatus.ACTIVE),
        ("PSLV-XL", "ISRO", 3800, 1300, 1750, 3.2, 8.0, 21, 0.95, 1993, VehicleStatus.ACTIVE),
        ("Long March 5", "CASC", 25000, 14000, None, 5.2, 12.3, 60, 0.93, 2016, VehicleStatus.ACTIVE),
        ("Electron", "Rocket Lab", 300, None, 200, 1.2, 2.0, 7.5, 0.95, 2017, VehicleStatus.ACTIVE),
        ("LauncherOne", "Virgin Orbit", 500, None, 300, 1.3, 2.0, 12, 0.80, 2021, VehicleStatus.RETIRED),
        ("New Glenn", "Blue Origin", 45000, 13000, None, 7.0, 21.9, 100, 0.95, 2025, VehicleStatus.ACTIVE),
        ("Starship", "SpaceX", 150000, 50000, None, 9.0, 22.0, 90, 0.90, 2025, VehicleStatus.DEVELOPMENT),
        ("GSLV Mk III", "ISRO", 10000, 4000, None, 5.0, 10.0, 35, 0.93, 2017, VehicleStatus.ACTIVE),
    ]
    db = {}
    for name, provider, leo, gto_raw, sso, fd, fh, cost, rel, yr, status in vehicles_data:
        gto = gto_raw if gto_raw else int(leo * 0.35)
        v = LaunchVehicle(
            name=name,
            provider=provider,
            payload_leo_kg=leo,
            payload_gto_kg=gto,
            payload_sso_kg=sso,
            fairing_diameter_m=fd,
            fairing_height_m=fh,
            cost_musd=cost,
            reliability=rel,
            first_flight_year=yr,
            status=status,
        )
        v.c3_curve = _make_c3_curve(leo, gto)
        db[name] = v
    return db


LAUNCH_VEHICLES: dict[str, LaunchVehicle] = _build_vehicles()


def c3_capability(vehicle: LaunchVehicle, c3_km2s2: float) -> float:
    """Return payload mass (kg) at given C3 using linear interpolation."""
    if c3_km2s2 < 0:
        return vehicle.payload_leo_kg
    curve = vehicle.c3_curve
    if not curve:
        return 0.0
    if c3_km2s2 <= curve[0][0]:
        return curve[0][1]
    if c3_km2s2 >= curve[-1][0]:
        return max(0.0, curve[-1][1])
    for i in range(len(curve) - 1):
        c3_lo, m_lo = curve[i]
        c3_hi, m_hi = curve[i + 1]
        if c3_lo <= c3_km2s2 <= c3_hi:
            t = (c3_km2s2 - c3_lo) / (c3_hi - c3_lo) if c3_hi != c3_lo else 0
            return m_lo + t * (m_hi - m_lo)
    return 0.0


def escape_velocity(body: str, altitude_km: float = 0.0) -> float:
    """Return escape velocity (km/s) from body surface + altitude."""
    body = body.lower()
    mu = MU.get(body)
    r = BODY_RADIUS.get(body)
    if mu is None or r is None:
        raise ValueError(f"Unknown body: {body}. Available: {list(MU.keys())}")
    return math.sqrt(2 * mu / (r + altitude_km))


def select_vehicle(
    payload_kg: float,
    orbit_type: str = "LEO",
    c3: Optional[float] = None,
) -> list[LaunchVehicle]:
    """Return capable vehicles sorted by cost (cheapest first).

    For escape orbits, c3 must be provided.
    """
    orbit_type = orbit_type.upper()
    results = []
    for v in LAUNCH_VEHICLES.values():
        if v.status == VehicleStatus.RETIRED:
            continue
        if c3 is not None:
            cap = c3_capability(v, c3)
        elif orbit_type == "LEO":
            cap = v.payload_leo_kg
        elif orbit_type == "GTO":
            cap = v.payload_gto_kg
        elif orbit_type == "SSO":
            cap = v.payload_sso_kg if v.payload_sso_kg else v.payload_leo_kg * 0.6
        else:
            cap = v.payload_leo_kg
        if cap >= payload_kg:
            results.append(v)
    results.sort(key=lambda v: v.cost_musd if v.cost_musd else 9999)
    return results


def plot_c3_curves(vehicles: Optional[list[str]] = None) -> go.Figure:
    """Plot C3 vs payload for selected (or all major) vehicles."""
    if vehicles is None:
        vehicles = [
            "Falcon 9", "Falcon Heavy", "Ariane 64", "Vulcan Centaur",
            "New Glenn", "Starship", "Atlas V 551", "Long March 5",
        ]
    fig = go.Figure()
    for name in vehicles:
        v = LAUNCH_VEHICLES.get(name)
        if v is None or not v.c3_curve:
            continue
        c3_vals = [p[0] for p in v.c3_curve]
        mass_vals = [p[1] for p in v.c3_curve]
        fig.add_trace(go.Scatter(
            x=c3_vals, y=mass_vals,
            mode="lines+markers",
            name=v.name,
            hovertemplate="%{x:.0f} km²/s²<br>%{y:.0f} kg<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(
        title="Launch Vehicle C₃ Performance Curves",
        xaxis_title="C₃ (km²/s²)",
        yaxis_title="Payload Mass (kg)",
        hovermode="x unified",
        template="plotly_white",
    )
    return fig


def launch_window_geometry(
    departure_body: str,
    arrival_body: str,
    departure_date: str,
) -> dict:
    """Basic launch window geometry info.

    Returns approximate C3, transfer time, synodic period, and next window.
    This is a simplified model for preliminary mission planning.

    Args:
        departure_body: e.g. "earth"
        arrival_body: e.g. "mars"
        departure_date: ISO date string (YYYY-MM-DD), used as reference

    Returns:
        dict with transfer parameters
    """
    arrival = arrival_body.lower()
    departure = departure_body.lower()

    if departure != "earth":
        raise ValueError("Only Earth departures supported in this simplified model")

    c3_typ = TYPICAL_C3.get(arrival)
    if c3_typ is None:
        raise ValueError(f"No data for transfers to {arrival}. Available: {list(TYPICAL_C3.keys())}")

    synodic = SYNODIC_PERIOD.get(arrival, 365)

    # Approximate Hohmann transfer semi-major axes (AU)
    orbit_radii = {
        "mercury": (1.0, 0.387),
        "venus": (1.0, 0.723),
        "mars": (1.0, 1.524),
        "jupiter": (1.0, 5.203),
        "saturn": (1.0, 9.537),
        "moon": None,
    }

    transfer_days = None
    delta_v_approx = None

    if arrival == "moon":
        transfer_days = 3.5
        delta_v_approx = 3.13  # km/s TLI from LEO
    elif arrival in orbit_radii and orbit_radii[arrival] is not None:
        r1_au, r2_au = orbit_radii[arrival]
        # Hohmann transfer time: T/2 = pi * sqrt(a^3 / mu_sun)
        a_au = (r1_au + r2_au) / 2.0
        # Period in years: T = 2*pi*sqrt(a^3) with a in AU, T in years
        t_transfer_years = 0.5 * math.sqrt(a_au ** 3)  # half period
        transfer_days = t_transfer_years * 365.25
        # Approximate departure delta-v from LEO (km/s)
        v_earth = 29.784  # km/s orbital speed
        v_transfer = v_earth * math.sqrt(2 * r2_au / (r1_au * (r1_au + r2_au)))
        delta_v_approx = abs(v_transfer - v_earth)

    # Vinf from C3
    v_inf = math.sqrt(c3_typ) if c3_typ > 0 else 0.0

    return {
        "departure_body": departure,
        "arrival_body": arrival,
        "departure_date": departure_date,
        "typical_c3_km2s2": c3_typ,
        "v_infinity_kms": round(v_inf, 3),
        "hohmann_transfer_days": round(transfer_days, 1) if transfer_days else None,
        "departure_delta_v_kms": round(delta_v_approx, 3) if delta_v_approx else None,
        "synodic_period_days": synodic,
        "window_recurrence_note": f"Optimal windows repeat approximately every {synodic} days",
        "capable_vehicles": [
            v.name for v in select_vehicle(0, "LEO", c3=c3_typ)
            if c3_capability(v, c3_typ) > 100
        ],
    }
