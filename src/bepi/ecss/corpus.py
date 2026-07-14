"""ECSS knowledge corpus — the shared, versioned reference layer.

Docs-as-code: the source of truth is the JSON under ``data/`` (built from
J. Coccimiglio's ECSS second-brain: Table A-1 deliverables, Table 7-2 tailoring
matrix, lessons-learned). This module is framework-agnostic (no Streamlit
import) so it can be consumed by the app, the API, tests, or a build step.

Versioning: every record belongs to a standard ``revision``. Missions pin a
baseline (``mission.metadata.ecss_baseline``) and resolve against it, so
updating the corpus never mutates an in-flight mission. Today a single revision
is seeded; ``baseline`` is threaded through now so adding a revision later is
data, not a refactor.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

_DATA = os.path.join(os.path.dirname(__file__), "data")

REVIEW_ORDER = ["MDR", "PRR", "SRR", "PDR", "CDR", "QR", "AR",
                "ORR", "FRR", "LRR", "CRR", "ELR", "MCR"]


@lru_cache(maxsize=None)
def _load(name: str) -> dict:
    with open(os.path.join(_DATA, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def current_revision() -> str:
    return _load("deliverables").get("revision", "")


def available_baselines() -> list[str]:
    """Revisions present in the corpus (one today; ready for more)."""
    revs = {_load(n).get("revision") for n in ("deliverables", "tailoring_matrix", "lessons")}
    return sorted(r for r in revs if r)


def _baseline_ok(record_rev: str, baseline: str | None) -> bool:
    # Single-revision corpus: a record matches when no baseline is pinned or it
    # equals the record's revision. Extend here when multiple revisions coexist.
    return baseline is None or baseline == record_rev


# --- Deliverables (Table A-1) ---------------------------------------------

def deliverables(baseline: str | None = None) -> list[dict]:
    d = _load("deliverables")
    if not _baseline_ok(d.get("revision", ""), baseline):
        return []
    return d["deliverables"]


def deliverable_by_id(did: str, baseline: str | None = None) -> dict | None:
    return next((x for x in deliverables(baseline) if x["id"] == did), None)


def deliverables_for_review(review: str, baseline: str | None = None) -> list[dict]:
    """Deliverables expected at a given review (its last review = finalised)."""
    return [d for d in deliverables(baseline) if review in d.get("reviews", [])]


def reviews_in_corpus(baseline: str | None = None) -> list[str]:
    present = {r for d in deliverables(baseline) for r in d.get("reviews", [])}
    return [r for r in REVIEW_ORDER if r in present]


# --- Tailoring matrix (Table 7-2) -----------------------------------------

def product_types(baseline: str | None = None) -> list[str]:
    m = _load("tailoring_matrix")
    if not _baseline_ok(m.get("revision", ""), baseline):
        return []
    return list(m["product_types"].keys())


def tailoring_points(product_type: str, baseline: str | None = None) -> dict:
    """The `//` decision points + counts for a product type (empty if unknown)."""
    m = _load("tailoring_matrix")
    if not _baseline_ok(m.get("revision", ""), baseline):
        return {}
    return m["product_types"].get(product_type, {})


# --- Lessons learned -------------------------------------------------------

def lessons(baseline: str | None = None) -> list[dict]:
    d = _load("lessons")
    if not _baseline_ok(d.get("revision", ""), baseline):
        return []
    return d["lessons"]


def lessons_for_deliverable(deliverable_id: str, baseline: str | None = None) -> list[dict]:
    """Anti-patterns a deliverable is meant to prevent (Jacopo's drd↔lesson join,
    now on stable IDs instead of fragile title strings)."""
    return [ll for ll in lessons(baseline) if deliverable_id in ll.get("drd", [])]


def drd_template(deliverable_id: str) -> str | None:
    """Section-by-section DRD scaffold markdown, if one exists for this DRD."""
    path = os.path.join(_DATA, "drd_templates", f"{deliverable_id}.md")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return None
