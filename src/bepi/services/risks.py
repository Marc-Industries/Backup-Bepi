"""Risk management: risk register, FMECA, FTA."""
from dataclasses import dataclass, field
import math


@dataclass
class RiskItemData:
    id: str
    risk_id: str  # "RSK-001"
    title: str
    description: str
    category: str
    likelihood: int  # 1-5
    consequence: int  # 1-5
    status: str = "open"
    owner: str = ""
    mitigation_strategy: str = ""
    residual_likelihood: int | None = None
    residual_consequence: int | None = None

    @property
    def risk_score(self) -> int:
        return self.likelihood * self.consequence

    @property
    def risk_level(self) -> str:
        s = self.risk_score
        if s >= 15:
            return "critical"
        elif s >= 9:
            return "high"
        elif s >= 4:
            return "medium"
        return "low"

    @property
    def residual_score(self) -> int | None:
        if self.residual_likelihood and self.residual_consequence:
            return self.residual_likelihood * self.residual_consequence
        return None


@dataclass
class FMECAEntryData:
    id: str
    node_code: str
    failure_mode: str
    failure_cause: str
    local_effect: str
    system_effect: str
    severity: int  # 1-5
    occurrence: int  # 1-5
    detection: int  # 1-5
    mitigation: str = ""
    criticality: str | None = None  # cat_1..cat_4
    # UUID of the product-tree node (for DB persistence). node_code is the human
    # code (e.g. "EPS-SA"); node_id is normalised to the node UUID before save
    # (see _normalize_fmeca_entries). Optional so mock rows without it load fine.
    node_id: str = ""

    @property
    def rpn(self) -> int:
        return self.severity * self.occurrence * self.detection


@dataclass
class FaultTreeNodeData:
    id: str
    name: str
    gate_type: str | None = None  # "and", "or", "vote_k_of_n", None=basic event
    probability: float | None = None  # For basic events
    k_of_n: int | None = None  # For vote gates
    children: list["FaultTreeNodeData"] = field(default_factory=list)


def risk_matrix(risks: list[RiskItemData]) -> dict:
    """Generate 5x5 risk matrix data.
    Returns {
        "matrix": [[count, ...], ...],  # 5x5, [likelihood][consequence]
        "cells": {(l,c): [risk_ids]},
        "summary": {"critical": n, "high": n, "medium": n, "low": n}
    }
    """
    matrix = [[0]*5 for _ in range(5)]
    cells = {}
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for r in risks:
        li, ci = r.likelihood - 1, r.consequence - 1
        matrix[li][ci] += 1
        cells.setdefault((r.likelihood, r.consequence), []).append(r.risk_id)
        summary[r.risk_level] += 1

    return {"matrix": matrix, "cells": cells, "summary": summary}


def fmeca_ranking(entries: list[FMECAEntryData]) -> list[FMECAEntryData]:
    """Sort FMECA entries by RPN descending."""
    return sorted(entries, key=lambda e: e.rpn, reverse=True)


def compute_criticality(severity: int, occurrence: int) -> str:
    """ECSS-Q-ST-30 criticality classification.
    Cat 1: Catastrophic (sev 5, occ >= 3)
    Cat 2: Critical (sev 4, occ >= 3 OR sev 5, occ < 3)
    Cat 3: Major (sev 3, occ >= 3 OR sev 4, occ < 3)
    Cat 4: Minor (everything else)
    """
    if severity == 5 and occurrence >= 3:
        return "cat_1"
    if (severity == 4 and occurrence >= 3) or (severity == 5 and occurrence < 3):
        return "cat_2"
    if (severity == 3 and occurrence >= 3) or (severity == 4 and occurrence < 3):
        return "cat_3"
    return "cat_4"


def compute_fta_probability(node: FaultTreeNodeData) -> float:
    """Recursively compute top event probability.
    AND gate: P = product of children probabilities
    OR gate: P = 1 - product of (1 - child_prob)
    VOTE k/n: P = sum of combinations (binomial)
    Basic event: return stored probability
    """
    if not node.gate_type:
        # Basic event
        return node.probability if node.probability is not None else 0.0

    child_probs = [compute_fta_probability(c) for c in node.children]

    if node.gate_type == "and":
        result = 1.0
        for p in child_probs:
            result *= p
        return result
    elif node.gate_type == "or":
        result = 1.0
        for p in child_probs:
            result *= (1 - p)
        return 1 - result
    elif node.gate_type == "vote_k_of_n":
        k = node.k_of_n or 1
        return _vote_probability(child_probs, k)
    return 0.0


def _vote_probability(probs: list[float], k: int) -> float:
    """Compute probability that at least k out of n events occur.
    Uses recursive enumeration (exact, works for small n).
    """
    n = len(probs)
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if n == 0:
        return 0.0
    p_n = probs[-1]
    rest = probs[:-1]
    return _vote_probability(rest, k) * (1 - p_n) + _vote_probability(rest, k - 1) * p_n
