"""Test budget roll-up engine."""
import pytest
from bepi.services.budgets import (
    BudgetAllocationData, compute_node_budget, rollup_tree, compute_budget_summary,
)


def make_leaf(code, name, allocations, level="component"):
    return {
        "node": {"code": code, "name": name, "level": level, "quantity": 1},
        "allocations": allocations,
        "children": [],
    }


def make_branch(code, name, children, level="subsystem"):
    return {
        "node": {"code": code, "name": name, "level": level, "quantity": 1},
        "allocations": [],
        "children": children,
    }


@pytest.fixture
def sample_tree():
    """
    SAT (satellite)
    ├── STR (subsystem) — leaf: 45 kg estimate
    ├── EPS (subsystem)
    │   ├── SA (equipment) — 8 kg measured, qty 2
    │   ├── BAT (equipment) — 12 kg qualified
    │   └── PCDU (equipment) — 5 kg estimate
    └── PL (subsystem) — leaf: 25 kg estimate
    """
    return make_branch("SAT", "Satellite", [
        make_leaf("STR", "Structure", [
            BudgetAllocationData("n1", "STR", "Structure", "mass_kg", None, 45.0, 1, "estimate", 0),
        ], level="subsystem"),
        make_branch("EPS", "Power Subsystem", [
            make_leaf("EPS-SA", "Solar Array", [
                BudgetAllocationData("n2", "EPS-SA", "Solar Array", "mass_kg", None, 8.0, 2, "measured", 0),
            ], level="equipment"),
            make_leaf("EPS-BAT", "Battery", [
                BudgetAllocationData("n3", "EPS-BAT", "Battery", "mass_kg", None, 12.0, 1, "qualified", 0),
            ], level="equipment"),
            make_leaf("EPS-PCDU", "PCDU", [
                BudgetAllocationData("n4", "EPS-PCDU", "PCDU", "mass_kg", None, 5.0, 1, "estimate", 0),
            ], level="equipment"),
        ]),
        make_leaf("PL", "Payload", [
            BudgetAllocationData("n5", "PL", "Payload", "mass_kg", None, 25.0, 1, "estimate", 0),
        ], level="subsystem"),
    ], level="satellite")


class TestComputeNodeBudget:
    def test_single_allocation_phase_b2(self):
        allocs = [BudgetAllocationData("n1", "X", "X", "mass_kg", None, 10.0, 1, "estimate", 0)]
        # Phase B2, estimate → 15% margin
        result = compute_node_budget(allocs, "B2", "mass_kg")
        assert result == pytest.approx(11.5, rel=1e-3)

    def test_quantity_multiplied(self):
        allocs = [BudgetAllocationData("n1", "X", "X", "mass_kg", None, 8.0, 2, "measured", 0)]
        # Phase B2, measured → 10%
        result = compute_node_budget(allocs, "B2", "mass_kg")
        assert result == pytest.approx(8 * 1.1 * 2, rel=1e-3)

    def test_override_margin(self):
        allocs = [BudgetAllocationData("n1", "X", "X", "mass_kg", None, 10.0, 1, "estimate", 25.0)]
        result = compute_node_budget(allocs, "B2", "mass_kg")
        assert result == pytest.approx(12.5, rel=1e-3)

    def test_filters_by_budget_type(self):
        allocs = [
            BudgetAllocationData("n1", "X", "X", "mass_kg", None, 10.0, 1, "estimate", 0),
            BudgetAllocationData("n2", "X", "X", "power_w", None, 50.0, 1, "estimate", 0),
        ]
        result = compute_node_budget(allocs, "B2", "mass_kg")
        assert result == pytest.approx(11.5, rel=1e-3)

    def test_filters_by_operating_mode(self):
        allocs = [
            BudgetAllocationData("n1", "X", "X", "power_w", "nominal", 10.0, 1, "estimate", 0),
            BudgetAllocationData("n2", "X", "X", "power_w", "eclipse", 5.0, 1, "estimate", 0),
        ]
        result = compute_node_budget(allocs, "B2", "power_w", "nominal")
        assert result == pytest.approx(11.5, rel=1e-3)


class TestRollupTree:
    def test_leaf_rollup(self):
        tree = make_leaf("X", "Leaf", [
            BudgetAllocationData("n1", "X", "Leaf", "mass_kg", None, 10.0, 1, "estimate", 0),
        ])
        result = rollup_tree(tree, "B2", "mass_kg")
        assert result.nominal_total == 10.0
        assert result.value_with_component_margin == pytest.approx(11.5, rel=1e-3)

    def test_three_level_rollup(self, sample_tree):
        """Test the full example from the plan:
        Phase B2:
          STR: 45 × 1.15 = 51.75 (estimate)
          EPS-SA: 8 × 1.1 × 2 = 17.6 (measured)
          EPS-BAT: 12 × 1.05 = 12.6 (qualified)
          EPS-PCDU: 5 × 1.15 = 5.75 (estimate)
          EPS total: 35.95
          PL: 25 × 1.15 = 28.75 (estimate)
          Subtotal with margin: 116.45
        """
        result = rollup_tree(sample_tree, "B2", "mass_kg")

        assert len(result.children) == 3
        str_result = result.children[0]
        eps_result = result.children[1]
        pl_result = result.children[2]

        assert str_result.value_with_component_margin == pytest.approx(51.75, rel=1e-2)
        assert eps_result.value_with_component_margin == pytest.approx(35.95, rel=1e-2)
        assert pl_result.value_with_component_margin == pytest.approx(28.75, rel=1e-2)

        assert result.value_with_component_margin == pytest.approx(116.45, rel=1e-2)


class TestBudgetSummary:
    def test_full_summary_with_limit(self, sample_tree):
        summary = compute_budget_summary(sample_tree, "B2", "mass_kg", budget_limit=180.0)

        assert len(summary.lines) == 3
        assert summary.system_margin_pct == 15  # Phase B2

        # Total with system margin = 116.45 * 1.15 = 133.92
        assert summary.total_with_system_margin == pytest.approx(133.92, rel=1e-2)
        assert summary.remaining == pytest.approx(180.0 - 133.92, rel=1e-2)
        assert summary.margin_status == "green"  # (180-134)/180 = 25.6%

    def test_red_status_tight_budget(self, sample_tree):
        summary = compute_budget_summary(sample_tree, "B2", "mass_kg", budget_limit=140.0)
        # 133.92 / 140 = 95.7% used → 4.3% remaining → RED
        assert summary.margin_status == "red"

    def test_yellow_status(self, sample_tree):
        summary = compute_budget_summary(sample_tree, "B2", "mass_kg", budget_limit=160.0)
        # 133.92 / 160 = 83.7% used → 16.3% remaining → YELLOW
        assert summary.margin_status == "yellow"

    def test_phase_d_lower_margins(self, sample_tree):
        """Phase D has lower margins: estimate=5%, measured=3%, qualified=0%"""
        result = rollup_tree(sample_tree, "D", "mass_kg")
        # STR: 45 × 1.05 = 47.25
        # EPS-SA: 8 × 1.03 × 2 = 16.48
        # EPS-BAT: 12 × 1.0 = 12.0
        # EPS-PCDU: 5 × 1.05 = 5.25
        # PL: 25 × 1.05 = 26.25
        assert result.value_with_component_margin == pytest.approx(107.23, rel=1e-2)
