from dataclasses import dataclass, field


@dataclass
class CelestialBody:
    name: str
    mu_km3s2: float
    radius_km: float
    j2: float = 0.0
    has_atmosphere: bool = False
    rotation_period_s: float = 86400.0
    parent: str = "Sun"
    sma_au: float = 0.0
    color: str = "gray"
    albedo: float = 0.3
    ir_flux_w_m2: float = 0.0
    soi_km: float = 0.0


BODIES: dict[str, CelestialBody] = {
    "Sun": CelestialBody(
        "Sun", 1.32712440018e11, 695700.0, parent="", sma_au=0.0,
        color="#FFD700", rotation_period_s=2.164e6,
    ),
    "Mercury": CelestialBody(
        "Mercury", 2.2032e4, 2439.7, j2=6.0e-5,
        sma_au=0.387, color="#A0A0A0", rotation_period_s=5.066e6,
        albedo=0.068, ir_flux_w_m2=0.0,
    ),
    "Venus": CelestialBody(
        "Venus", 3.24859e5, 6051.8, j2=4.458e-6,
        has_atmosphere=True, sma_au=0.723, color="#E8C56D",
        rotation_period_s=2.0997e7, albedo=0.77, ir_flux_w_m2=153.0,
    ),
    "Earth": CelestialBody(
        "Earth", 398600.4418, 6371.0, j2=1.08263e-3,
        has_atmosphere=True, rotation_period_s=86164.1,
        sma_au=1.0, color="#4488FF", albedo=0.30, ir_flux_w_m2=237.0,
        soi_km=924600.0,
    ),
    "Moon": CelestialBody(
        "Moon", 4902.8, 1737.4, j2=2.033e-4,
        parent="Earth", sma_au=0.00257, color="#AAAAAA",
        rotation_period_s=2.3606e6, albedo=0.12, ir_flux_w_m2=5.2,
    ),
    "Mars": CelestialBody(
        "Mars", 42828.37, 3389.5, j2=1.964e-3,
        has_atmosphere=True, rotation_period_s=88642.7,
        sma_au=1.524, color="#C1440E", albedo=0.25, ir_flux_w_m2=125.0,
        soi_km=577000.0,
    ),
    "Phobos": CelestialBody(
        "Phobos", 7.158e-4, 11.27, parent="Mars",
        color="#8B7355", rotation_period_s=27554.0,
    ),
    "Deimos": CelestialBody(
        "Deimos", 9.8e-5, 6.2, parent="Mars",
        color="#A0926B", rotation_period_s=109075.0,
    ),
    "Jupiter": CelestialBody(
        "Jupiter", 1.26687e8, 69911.0, j2=1.4736e-2,
        has_atmosphere=True, rotation_period_s=35730.0,
        sma_au=5.203, color="#C88B3A", albedo=0.34, ir_flux_w_m2=13.7,
        soi_km=48.2e6,
    ),
    "Europa": CelestialBody(
        "Europa", 3202.7, 1560.8, parent="Jupiter",
        color="#B8A88A", rotation_period_s=306822.0,
        albedo=0.67, ir_flux_w_m2=0.0,
    ),
    "Ganymede": CelestialBody(
        "Ganymede", 9887.8, 2634.1, parent="Jupiter",
        color="#8B8682", rotation_period_s=618153.0,
        albedo=0.43, ir_flux_w_m2=0.0,
    ),
    "Saturn": CelestialBody(
        "Saturn", 3.7931e7, 58232.0, j2=1.6298e-2,
        has_atmosphere=True, rotation_period_s=38018.0,
        sma_au=9.537, color="#E8D5A3", albedo=0.34, ir_flux_w_m2=4.7,
        soi_km=54.5e6,
    ),
    "Titan": CelestialBody(
        "Titan", 8978.1, 2574.7, parent="Saturn",
        has_atmosphere=True, color="#D4A017",
        rotation_period_s=1.378e6, albedo=0.22, ir_flux_w_m2=0.0,
    ),
    "Uranus": CelestialBody(
        "Uranus", 5.794e6, 25362.0, j2=3.343e-3,
        has_atmosphere=True, rotation_period_s=62064.0,
        sma_au=19.19, color="#72B5C4", albedo=0.30,
    ),
    "Neptune": CelestialBody(
        "Neptune", 6.836e6, 24622.0, j2=3.411e-3,
        has_atmosphere=True, rotation_period_s=58000.0,
        sma_au=30.07, color="#3F54BA", albedo=0.29,
    ),
}


def get_body(name: str) -> CelestialBody:
    if name in BODIES:
        return BODIES[name]
    for key, body in BODIES.items():
        if key.lower() == name.lower():
            return body
    return BODIES["Earth"]


def solar_flux_at_body(body_name: str) -> float:
    b = get_body(body_name)
    if b.sma_au <= 0:
        return 1361.0
    return 1361.0 / (b.sma_au ** 2)


def body_names() -> list[str]:
    return list(BODIES.keys())


def planet_names() -> list[str]:
    return [n for n, b in BODIES.items() if b.parent in ("Sun", "") and n != "Sun"]
