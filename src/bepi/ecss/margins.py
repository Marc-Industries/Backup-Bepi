"""ECSS margin policy tables from ECSS-E-HB-10-02."""

COMPONENT_MARGINS = {
    ("0", "estimate"): 30, ("0", "measured"): 20, ("0", "qualified"): 10,
    ("A", "estimate"): 20, ("A", "measured"): 10, ("A", "qualified"): 5,
    ("B1", "estimate"): 20, ("B1", "measured"): 10, ("B1", "qualified"): 5,
    ("B2", "estimate"): 15, ("B2", "measured"): 10, ("B2", "qualified"): 5,
    ("C", "estimate"): 10, ("C", "measured"): 5, ("C", "qualified"): 3,
    ("D", "estimate"): 5, ("D", "measured"): 3, ("D", "qualified"): 0,
}

SYSTEM_MARGINS = {
    "0": 30,
    "A": 20,
    "B1": 20,
    "B2": 15,
    "C": 10,
    "D": 5,
    "E1": 0,
    "E2": 0,
    "F": 0,
}


NASA_TO_ESA_MARGIN_MAP = {
    "Pre-A": "0",
    "A": "A",
    "B": "B1",
    "C": "C",
    "D": "D",
    "E": "E1",
    "F": "F",
}


def _resolve_phase(phase: str) -> str:
    return NASA_TO_ESA_MARGIN_MAP.get(phase, phase)


def get_component_margin(phase: str, maturity: str) -> float:
    p = _resolve_phase(phase)
    return COMPONENT_MARGINS.get((p, maturity), 20)


def get_system_margin(phase: str) -> float:
    p = _resolve_phase(phase)
    return SYSTEM_MARGINS.get(p, 20)


def compute_value_with_margins(nominal: float, quantity: int, phase: str, maturity: str, include_system: bool = True) -> dict:
    """Compute value with component and optionally system margins.

    Returns dict with:
        nominal_total, component_margin_pct, value_with_component_margin,
        system_margin_pct, value_with_system_margin
    """
    comp_margin = get_component_margin(phase, maturity)
    val_with_comp = nominal * (1 + comp_margin / 100) * quantity

    result = {
        "nominal_total": nominal * quantity,
        "component_margin_pct": comp_margin,
        "value_with_component_margin": val_with_comp,
    }

    if include_system:
        sys_margin = get_system_margin(phase)
        result["system_margin_pct"] = sys_margin
        result["value_with_system_margin"] = val_with_comp * (1 + sys_margin / 100)

    return result
