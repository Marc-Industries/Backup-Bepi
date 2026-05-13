"""GMAT script generation — creates .script files from BEPI mission parameters.

GMAT (General Mission Analysis Tool) is NASA's open-source orbit propagator.
This module generates GMAT scripts for common analyses:
- Orbit propagation
- Ground station contact windows
- Eclipse analysis
- Delta-V maneuver planning
- Orbit maintenance (station-keeping)
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import textwrap

from .celestial_bodies import get_body

# GMAT gravity model files per body
_GRAVITY_MODELS: dict[str, tuple[str, int, int]] = {
    "Earth": ("EGM96.cof", 20, 20),
    "Moon": ("LP165P.cof", 20, 20),
    "Mars": ("Mars50c.cof", 20, 20),
    "Venus": ("MGNP180U.cof", 20, 20),
    "Mercury": ("HgM005.cof", 10, 10),
    "Jupiter": ("JGM3.cof", 10, 10),
}

# GMAT names that differ from our canonical names
_GMAT_BODY_NAME: dict[str, str] = {
    "Moon": "Luna",
}


def _gmat_name(body: str) -> str:
    return _GMAT_BODY_NAME.get(body, body)


def _coord_system(body: str) -> str:
    return f"{_gmat_name(body)}MJ2000Eq"


@dataclass
class OrbitParams:
    epoch: str = "01 Jun 2027 12:00:00.000"
    sma_km: float = 6928.14  # 550 km altitude
    ecc: float = 0.001
    inc_deg: float = 97.6  # SSO
    raan_deg: float = 0.0
    aop_deg: float = 0.0
    ta_deg: float = 0.0
    body: str = "Earth"
    coord_system: str = ""

    def __post_init__(self):
        if not self.coord_system:
            self.coord_system = _coord_system(self.body)


@dataclass
class SpacecraftParams:
    name: str = "BEPISAT"
    dry_mass_kg: float = 260.0
    fuel_mass_kg: float = 25.0
    cd: float = 2.2  # Drag coefficient
    cr: float = 1.8  # Reflectivity coefficient
    drag_area_m2: float = 1.5
    srp_area_m2: float = 3.0


@dataclass
class GroundStation:
    name: str = "Svalbard"
    lat_deg: float = 78.23
    lon_deg: float = 15.39
    alt_m: float = 500.0
    min_elevation_deg: float = 5.0


@dataclass
class PropagationConfig:
    duration_days: float = 1.0
    step_size_s: float = 60.0
    force_model: str = "full"  # "full", "two_body", "j2"
    output_step_s: float = 60.0


COMMON_GROUND_STATIONS = {
    "Svalbard": GroundStation("Svalbard", 78.23, 15.39, 500),
    "Kiruna": GroundStation("Kiruna", 67.86, 20.96, 400),
    "Malindi": GroundStation("Malindi", -2.99, 40.19, 30),
    "Kourou": GroundStation("Kourou", 5.17, -52.68, 10),
    "Perth": GroundStation("Perth", -31.80, 115.89, 20),
    "Redu": GroundStation("Redu", 50.00, 5.15, 380),
    "Maspalomas": GroundStation("Maspalomas", 27.76, -15.63, 205),
    "Darmstadt": GroundStation("Darmstadt (ESOC)", 49.87, 8.63, 140),
}


def _force_model_block(config: PropagationConfig, body: str = "Earth") -> str:
    gname = _gmat_name(body)
    cb = get_body(body)

    if config.force_model == "two_body":
        return textwrap.dedent(f"""\
            Create ForceModel fm;
            fm.CentralBody = {gname};
            fm.PointMasses = {{{gname}}};
        """)
    elif config.force_model == "j2":
        return textwrap.dedent(f"""\
            Create ForceModel fm;
            fm.CentralBody = {gname};
            fm.PrimaryBodies = {{{gname}}};
            fm.GravityField.{gname}.Degree = 2;
            fm.GravityField.{gname}.Order = 0;
        """)
    else:
        grav = _GRAVITY_MODELS.get(body)
        if grav is None:
            # Unknown body — fall back to two-body
            return textwrap.dedent(f"""\
                Create ForceModel fm;
                fm.CentralBody = {gname};
                fm.PointMasses = {{{gname}}};
                fm.SRP = On;
                fm.SRP.Flux = 1367;
            """)

        pot_file, deg, order = grav
        lines = [
            "Create ForceModel fm;",
            f"fm.CentralBody = {gname};",
            f"fm.PrimaryBodies = {{{gname}}};",
            f"fm.GravityField.{gname}.Degree = {deg};",
            f"fm.GravityField.{gname}.Order = {order};",
            f"fm.GravityField.{gname}.PotentialFile = '{pot_file}';",
        ]

        # Drag only for bodies with atmosphere (Earth, Mars, Venus, Titan)
        if cb.has_atmosphere and body == "Earth":
            lines += [
                "fm.Drag.AtmosphereModel = MSISE90;",
                "fm.Drag.HistoricWeatherSource = 'ConstantFluxAndGeoMag';",
                "fm.Drag.F107 = 150;",
                "fm.Drag.F107A = 150;",
                "fm.Drag.MagneticIndex = 3;",
            ]
        elif cb.has_atmosphere and body == "Mars":
            lines += [
                "fm.Drag.AtmosphereModel = MarsGRAM2005;",
            ]

        lines += [
            "fm.SRP = On;",
            "fm.SRP.Flux = 1367;",
        ]

        # Third-body perturbations
        if body == "Earth":
            lines.append("fm.PointMasses = {Sun, Luna};")
        elif body == "Moon":
            lines.append("fm.PointMasses = {Sun, Earth};")
        elif cb.parent == "Sun":
            lines.append("fm.PointMasses = {Sun};")
        else:
            parent_gmat = _gmat_name(cb.parent)
            lines.append(f"fm.PointMasses = {{Sun, {parent_gmat}}};")

        return "\n".join(lines) + "\n"


def generate_propagation_script(
    sc: SpacecraftParams | None = None,
    orbit: OrbitParams | None = None,
    config: PropagationConfig | None = None,
    ground_stations: list[GroundStation] | None = None,
) -> str:
    sc = sc or SpacecraftParams()
    orbit = orbit or OrbitParams()
    config = config or PropagationConfig()
    gs_list = ground_stations or []

    gname = _gmat_name(orbit.body)

    gs_creates = ""
    gs_names = []
    for gs in gs_list:
        gs_creates += textwrap.dedent(f"""\
            Create GroundStation {gs.name};
            {gs.name}.CentralBody = {gname};
            {gs.name}.StateType = Spherical;
            {gs.name}.HorizonReference = Ellipsoid;
            {gs.name}.Location1 = {gs.lat_deg};
            {gs.name}.Location2 = {gs.lon_deg};
            {gs.name}.Location3 = {gs.alt_m / 1000:.3f};
            {gs.name}.MinimumElevationAngle = {gs.min_elevation_deg};

        """)
        gs_names.append(gs.name)

    contact_reports = ""
    if gs_names:
        contact_reports = textwrap.dedent(f"""\
            Create ContactLocator ContactLoc;
            ContactLoc.Target = {sc.name};
            ContactLoc.Observers = {{{', '.join(gs_names)}}};
            ContactLoc.LightTimeDirection = Transmit;
            ContactLoc.Filename = 'ContactReport.txt';
            ContactLoc.OccultingBodies = {{{gname}}};

        """)

    eclipse_locator = textwrap.dedent(f"""\
        Create EclipseLocator EclipseLoc;
        EclipseLoc.Spacecraft = {sc.name};
        EclipseLoc.Filename = 'EclipseReport.txt';
        EclipseLoc.OccultingBodies = {{{gname}}};
        EclipseLoc.EclipseTypes = {{'Umbra', 'Penumbra'}};

    """)

    script = textwrap.dedent(f"""\
        %% ============================================================
        %% BEPI-SAT GMAT Script — Auto-generated by BEPI
        %% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        %% ============================================================

        %% ---- Spacecraft ----
        Create Spacecraft {sc.name};
        {sc.name}.DateFormat = UTCGregorian;
        {sc.name}.Epoch = '{orbit.epoch}';
        {sc.name}.CoordinateSystem = {orbit.coord_system};
        {sc.name}.DisplayStateType = Keplerian;
        {sc.name}.SMA = {orbit.sma_km};
        {sc.name}.ECC = {orbit.ecc};
        {sc.name}.INC = {orbit.inc_deg};
        {sc.name}.RAAN = {orbit.raan_deg};
        {sc.name}.AOP = {orbit.aop_deg};
        {sc.name}.TA = {orbit.ta_deg};
        {sc.name}.DryMass = {sc.dry_mass_kg};
        {sc.name}.Cd = {sc.cd};
        {sc.name}.Cr = {sc.cr};
        {sc.name}.DragArea = {sc.drag_area_m2};
        {sc.name}.SRPArea = {sc.srp_area_m2};

        %% ---- Ground Stations ----
        {gs_creates}
        %% ---- Force Model ----
        {_force_model_block(config, orbit.body)}
        Create Propagator prop;
        prop.FM = fm;
        prop.Type = RungeKutta89;
        prop.InitialStepSize = {config.step_size_s};
        prop.MinStep = 0.001;
        prop.MaxStep = {config.step_size_s};

        %% ---- Subscribers ----
        Create OrbitView BodyView;
        BodyView.Add = {{{sc.name}, {gname}}};
        BodyView.CoordinateSystem = {orbit.coord_system};
        BodyView.ViewPointReference = {gname};
        BodyView.ViewDirection = {gname};
        BodyView.ViewScaleFactor = 3;

        Create ReportFile OrbitReport;
        OrbitReport.Filename = 'OrbitReport.txt';
        OrbitReport.Add = {{{sc.name}.UTCGregorian, {sc.name}.{orbit.coord_system}.X, {sc.name}.{orbit.coord_system}.Y, {sc.name}.{orbit.coord_system}.Z, {sc.name}.{gname}.Altitude, {sc.name}.{gname}.Latitude, {sc.name}.{gname}.Longitude}};

        Create GroundTrackPlot GroundTrack;
        GroundTrack.Add = {{{sc.name}}};
        GroundTrack.CentralBody = {gname};

        %% ---- Contact & Eclipse Locators ----
        {contact_reports}
        {eclipse_locator}

        %% ---- Mission Sequence ----
        BeginMissionSequence;
        Propagate prop({sc.name}) {{{sc.name}.ElapsedDays = {config.duration_days}}};
    """)
    return script


def generate_maneuver_script(
    sc: SpacecraftParams | None = None,
    orbit: OrbitParams | None = None,
    delta_v_ms: float = 1.0,
    direction: str = "velocity",  # "velocity", "normal", "binormal"
    maneuver_epoch: str | None = None,
) -> str:
    sc = sc or SpacecraftParams()
    orbit = orbit or OrbitParams()

    dv_x, dv_y, dv_z = 0.0, 0.0, 0.0
    delta_v_kms = delta_v_ms / 1000.0
    if direction == "velocity":
        dv_x = delta_v_kms
    elif direction == "normal":
        dv_y = delta_v_kms
    else:
        dv_z = delta_v_kms

    gname = _gmat_name(orbit.body)
    cb = get_body(orbit.body)

    # Build a simple force model for maneuver scripts
    fm_lines = [
        "Create ForceModel fm;",
        f"fm.CentralBody = {gname};",
        f"fm.PrimaryBodies = {{{gname}}};",
        f"fm.GravityField.{gname}.Degree = 10;",
        f"fm.GravityField.{gname}.Order = 10;",
    ]
    if cb.has_atmosphere and orbit.body == "Earth":
        fm_lines.append("fm.Drag.AtmosphereModel = MSISE90;")
    fm_lines.append("fm.SRP = On;")
    fm_block = "\n".join(fm_lines)

    script = textwrap.dedent(f"""\
        %% ============================================================
        %% BEPI-SAT Delta-V Maneuver — Auto-generated by BEPI
        %% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        %% Delta-V: {delta_v_ms:.3f} m/s ({direction})
        %% ============================================================

        Create Spacecraft {sc.name};
        {sc.name}.DateFormat = UTCGregorian;
        {sc.name}.Epoch = '{orbit.epoch}';
        {sc.name}.CoordinateSystem = {orbit.coord_system};
        {sc.name}.SMA = {orbit.sma_km};
        {sc.name}.ECC = {orbit.ecc};
        {sc.name}.INC = {orbit.inc_deg};
        {sc.name}.RAAN = {orbit.raan_deg};
        {sc.name}.AOP = {orbit.aop_deg};
        {sc.name}.TA = {orbit.ta_deg};
        {sc.name}.DryMass = {sc.dry_mass_kg};

        Create ChemicalTank MainTank;
        MainTank.FuelMass = {sc.fuel_mass_kg};
        MainTank.AllowNegativeFuelMass = false;
        {sc.name}.Tanks = {{MainTank}};

        Create ChemicalThruster MainThruster;
        MainThruster.Tank = {{MainTank}};
        MainThruster.C1 = {delta_v_kms};
        {sc.name}.Thrusters = {{MainThruster}};

        Create ImpulsiveBurn dv_burn;
        dv_burn.CoordinateSystem = Local;
        dv_burn.Origin = {gname};
        dv_burn.Axes = VNB;
        dv_burn.Element1 = {dv_x};
        dv_burn.Element2 = {dv_y};
        dv_burn.Element3 = {dv_z};

        {fm_block}

        Create Propagator prop;
        prop.FM = fm;

        Create ReportFile MnvrReport;
        MnvrReport.Filename = 'ManeuverReport.txt';
        MnvrReport.Add = {{{sc.name}.UTCGregorian, {sc.name}.{gname}.SMA, {sc.name}.{gname}.ECC, {sc.name}.{gname}.Altitude, {sc.name}.TotalMass}};

        BeginMissionSequence;
        Propagate prop({sc.name}) {{{sc.name}.ElapsedDays = 0.5}};
        Maneuver dv_burn({sc.name});
        Propagate prop({sc.name}) {{{sc.name}.ElapsedDays = 1.0}};
    """)
    return script


def generate_stationkeeping_script(
    sc: SpacecraftParams | None = None,
    orbit: OrbitParams | None = None,
    target_alt_km: float = 550.0,
    tolerance_km: float = 5.0,
    sim_days: float = 30.0,
) -> str:
    sc = sc or SpacecraftParams()
    orbit = orbit or OrbitParams()

    gname = _gmat_name(orbit.body)
    fm_block = _force_model_block(PropagationConfig(force_model="full"), orbit.body)

    script = textwrap.dedent(f"""\
        %% ============================================================
        %% BEPI-SAT Station-Keeping Analysis — Auto-generated by BEPI
        %% Target altitude: {target_alt_km} km +/- {tolerance_km} km
        %% Simulation: {sim_days} days
        %% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        %% ============================================================

        Create Spacecraft {sc.name};
        {sc.name}.DateFormat = UTCGregorian;
        {sc.name}.Epoch = '{orbit.epoch}';
        {sc.name}.SMA = {orbit.sma_km};
        {sc.name}.ECC = {orbit.ecc};
        {sc.name}.INC = {orbit.inc_deg};
        {sc.name}.RAAN = {orbit.raan_deg};
        {sc.name}.AOP = {orbit.aop_deg};
        {sc.name}.TA = {orbit.ta_deg};
        {sc.name}.DryMass = {sc.dry_mass_kg};
        {sc.name}.Cd = {sc.cd};
        {sc.name}.DragArea = {sc.drag_area_m2};

        Create ChemicalTank MainTank;
        MainTank.FuelMass = {sc.fuel_mass_kg};
        {sc.name}.Tanks = {{MainTank}};

        Create ImpulsiveBurn SK_Burn;
        SK_Burn.CoordinateSystem = Local;
        SK_Burn.Origin = {gname};
        SK_Burn.Axes = VNB;

        {fm_block}
        Create Propagator prop;
        prop.FM = fm;

        Create Variable alt dv_total n_burns;
        dv_total = 0;
        n_burns = 0;

        Create ReportFile SKReport;
        SKReport.Filename = 'StationKeepingReport.txt';
        SKReport.Add = {{{sc.name}.UTCGregorian, {sc.name}.{gname}.Altitude, dv_total, n_burns, {sc.name}.TotalMass}};

        BeginMissionSequence;

        While {sc.name}.ElapsedDays < {sim_days}
           Propagate prop({sc.name}) {{{sc.name}.ElapsedDays = 0.5}};

           %% Check altitude and apply correction burn if needed
           alt = {sc.name}.{gname}.Altitude;
           If alt < {target_alt_km - tolerance_km}
              SK_Burn.Element1 = 0.001;  %% Small prograde burn
              Maneuver SK_Burn({sc.name});
              dv_total = dv_total + 0.001;
              n_burns = n_burns + 1;
           EndIf;
        EndWhile;
    """)
    return script
