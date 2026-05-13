import pytest
from bepi.services.risks import (
    RiskItemData, FMECAEntryData, FaultTreeNodeData,
    risk_matrix, fmeca_ranking, compute_criticality,
    compute_fta_probability,
)


class TestRiskScoring:
    def test_risk_level_critical(self):
        r = RiskItemData("1", "RSK-001", "T", "D", "technical", 5, 4)
        assert r.risk_score == 20
        assert r.risk_level == "critical"

    def test_risk_level_low(self):
        r = RiskItemData("1", "RSK-001", "T", "D", "technical", 1, 2)
        assert r.risk_score == 2
        assert r.risk_level == "low"

    def test_risk_matrix_counts(self):
        risks = [
            RiskItemData("1", "R1", "T", "D", "technical", 5, 5),
            RiskItemData("2", "R2", "T", "D", "technical", 5, 5),
            RiskItemData("3", "R3", "T", "D", "technical", 1, 1),
        ]
        result = risk_matrix(risks)
        assert result["matrix"][4][4] == 2  # Two risks at (5,5)
        assert result["summary"]["critical"] == 2
        assert result["summary"]["low"] == 1


class TestFMECA:
    def test_rpn_calculation(self):
        e = FMECAEntryData("1", "EPS", "Short", "Aging", "No power", "Mission loss", 5, 3, 2)
        assert e.rpn == 30

    def test_ranking(self):
        entries = [
            FMECAEntryData("1", "A", "F1", "", "", "", 2, 2, 2),  # RPN=8
            FMECAEntryData("2", "B", "F2", "", "", "", 5, 3, 2),  # RPN=30
            FMECAEntryData("3", "C", "F3", "", "", "", 3, 3, 3),  # RPN=27
        ]
        ranked = fmeca_ranking(entries)
        assert ranked[0].id == "2"  # RPN 30
        assert ranked[1].id == "3"  # RPN 27

    def test_criticality_cat1(self):
        assert compute_criticality(5, 3) == "cat_1"

    def test_criticality_cat4(self):
        assert compute_criticality(2, 2) == "cat_4"


class TestFTA:
    def test_basic_event(self):
        node = FaultTreeNodeData("1", "Failure", probability=0.01)
        assert compute_fta_probability(node) == pytest.approx(0.01)

    def test_and_gate(self):
        """AND: both must fail. P = 0.1 * 0.2 = 0.02"""
        root = FaultTreeNodeData("r", "Top", gate_type="and", children=[
            FaultTreeNodeData("a", "A", probability=0.1),
            FaultTreeNodeData("b", "B", probability=0.2),
        ])
        assert compute_fta_probability(root) == pytest.approx(0.02)

    def test_or_gate(self):
        """OR: either fails. P = 1 - (0.9 * 0.8) = 0.28"""
        root = FaultTreeNodeData("r", "Top", gate_type="or", children=[
            FaultTreeNodeData("a", "A", probability=0.1),
            FaultTreeNodeData("b", "B", probability=0.2),
        ])
        assert compute_fta_probability(root) == pytest.approx(0.28)

    def test_nested_gates(self):
        """AND(OR(A,B), C): P = (1-(0.9*0.8)) * 0.05 = 0.28 * 0.05 = 0.014"""
        root = FaultTreeNodeData("r", "Top", gate_type="and", children=[
            FaultTreeNodeData("or1", "SubOR", gate_type="or", children=[
                FaultTreeNodeData("a", "A", probability=0.1),
                FaultTreeNodeData("b", "B", probability=0.2),
            ]),
            FaultTreeNodeData("c", "C", probability=0.05),
        ])
        assert compute_fta_probability(root) == pytest.approx(0.014)

    def test_vote_2_of_3(self):
        """2-of-3 vote gate with equal probabilities.
        P(at least 2 of 3 fail) with p=0.1 each
        = 3*(0.1^2)*(0.9) + (0.1^3) = 0.027 + 0.001 = 0.028
        """
        root = FaultTreeNodeData("r", "Top", gate_type="vote_k_of_n", k_of_n=2, children=[
            FaultTreeNodeData("a", "A", probability=0.1),
            FaultTreeNodeData("b", "B", probability=0.1),
            FaultTreeNodeData("c", "C", probability=0.1),
        ])
        assert compute_fta_probability(root) == pytest.approx(0.028, rel=1e-3)
