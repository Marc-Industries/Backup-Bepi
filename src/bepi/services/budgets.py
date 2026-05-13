"""Budget roll-up engine for product tree."""
from dataclasses import dataclass
from bepi.ecss.margins import get_component_margin, get_system_margin


@dataclass
class BudgetAllocationData:
    """Represents a single budget allocation on a node."""
    node_id: str
    node_code: str
    node_name: str
    budget_type: str
    operating_mode: str | None
    nominal_value: float
    quantity: int
    maturity: str
    margin_pct: float  # Override margin; if 0, use ECSS default
    source: str = ""


@dataclass
class BudgetRollupResult:
    """Result of rolling up a budget through the tree."""
    node_code: str
    node_name: str
    level: str  # "satellite", "subsystem", "equipment", "component"
    nominal_total: float
    component_margin_pct: float
    value_with_component_margin: float
    children: list  # list of BudgetRollupResult


@dataclass
class BudgetSummaryLine:
    """One line in a budget summary table."""
    subsystem_code: str
    subsystem_name: str
    nominal: float
    with_margin: float
    margin_pct: float


@dataclass
class BudgetSummary:
    """Complete budget summary for a mission."""
    budget_type: str
    operating_mode: str | None
    phase: str
    lines: list[BudgetSummaryLine]
    subtotal_nominal: float
    subtotal_with_margin: float
    system_margin_pct: float
    total_with_system_margin: float
    budget_limit: float | None
    remaining: float | None
    margin_status: str  # "green", "yellow", "red"


def compute_node_budget(
    allocations: list[BudgetAllocationData],
    phase: str,
    budget_type: str,
    operating_mode: str | None = None,
) -> float:
    """Compute total budget for a single leaf node (with component margin)."""
    total = 0.0
    for alloc in allocations:
        if alloc.budget_type != budget_type:
            continue
        if operating_mode and alloc.operating_mode != operating_mode:
            continue

        if alloc.margin_pct > 0:
            margin = alloc.margin_pct
        else:
            margin = get_component_margin(phase, alloc.maturity)

        total += alloc.nominal_value * (1 + margin / 100) * alloc.quantity
    return total


def rollup_tree(
    tree: dict,  # {"node": {...}, "children": [...], "allocations": [...]}
    phase: str,
    budget_type: str,
    operating_mode: str | None = None,
    active_subsystems: list[str] | None = None,
) -> BudgetRollupResult:
    """
    Recursively roll up budget through product tree.

    tree structure:
    {
        "node": {"code": "SAT", "name": "Satellite", "level": "satellite", "quantity": 1},
        "allocations": [BudgetAllocationData, ...],  # leaf node allocations
        "children": [tree, ...]
    }

    If node has children: total = sum of children's value_with_component_margin
    If node is leaf: total = sum of allocations with margins applied
    """
    node = tree["node"]
    children_results = []

    if tree.get("children"):
        for child in tree["children"]:
            if active_subsystems is not None and child["node"]["code"] not in active_subsystems:
                continue
            child_result = rollup_tree(child, phase, budget_type, operating_mode, active_subsystems)
            children_results.append(child_result)

        nominal = sum(c.nominal_total for c in children_results)
        with_margin = sum(c.value_with_component_margin for c in children_results)
        margin_pct = ((with_margin / nominal - 1) * 100) if nominal > 0 else 0
    else:
        allocations = tree.get("allocations", [])
        nominal = sum(
            a.nominal_value * a.quantity
            for a in allocations
            if a.budget_type == budget_type and (not operating_mode or a.operating_mode == operating_mode)
        )
        with_margin = compute_node_budget(allocations, phase, budget_type, operating_mode)
        margin_pct = ((with_margin / nominal - 1) * 100) if nominal > 0 else 0

    return BudgetRollupResult(
        node_code=node["code"],
        node_name=node["name"],
        level=node["level"],
        nominal_total=nominal,
        component_margin_pct=round(margin_pct, 1),
        value_with_component_margin=round(with_margin, 2),
        children=children_results,
    )


def compute_budget_summary(
    tree: dict,
    phase: str,
    budget_type: str,
    operating_mode: str | None = None,
    budget_limit: float | None = None,
    active_subsystems: list[str] | None = None,
) -> BudgetSummary:
    """
    Compute full budget summary at mission level.
    Produces a table with one line per subsystem + system margin + limit check.
    """
    root_result = rollup_tree(tree, phase, budget_type, operating_mode, active_subsystems)

    lines = []
    for child in root_result.children:
        lines.append(BudgetSummaryLine(
            subsystem_code=child.node_code,
            subsystem_name=child.node_name,
            nominal=round(child.nominal_total, 2),
            with_margin=round(child.value_with_component_margin, 2),
            margin_pct=child.component_margin_pct,
        ))

    subtotal_nominal = root_result.nominal_total
    subtotal_with_margin = root_result.value_with_component_margin

    sys_margin = get_system_margin(phase)
    total = subtotal_with_margin * (1 + sys_margin / 100)

    remaining = None
    status = "green"
    if budget_limit and budget_limit > 0:
        remaining = budget_limit - total
        pct_remaining = (remaining / budget_limit) * 100
        if pct_remaining < 10:
            status = "red"
        elif pct_remaining < 20:
            status = "yellow"
        else:
            status = "green"

    return BudgetSummary(
        budget_type=budget_type,
        operating_mode=operating_mode,
        phase=phase,
        lines=lines,
        subtotal_nominal=round(subtotal_nominal, 2),
        subtotal_with_margin=round(subtotal_with_margin, 2),
        system_margin_pct=sys_margin,
        total_with_system_margin=round(total, 2),
        budget_limit=budget_limit,
        remaining=round(remaining, 2) if remaining is not None else None,
        margin_status=status,
    )
