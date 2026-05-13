"""Requirements management service."""
from dataclasses import dataclass, field


@dataclass
class RequirementData:
    id: str
    req_id: str  # "SYS-FUN-001"
    level: str
    category: str
    title: str
    text: str
    parent_id: str | None = None
    verification_method: str | None = None
    verification_status: str = "not_started"
    allocated_to: list[str] = field(default_factory=list)  # node codes


def generate_req_id(level: str, category: str, sequence: int) -> str:
    """Generate requirement ID.
    Level: SH (stakeholder), MIS (mission), SYS (system), SUB (subsystem), EQP (equipment)
    Category: FUN, PER, IFC, ENV, DES, OPS, REL, SAF, PA
    Example: SYS-FUN-001
    """
    level_map = {"stakeholder": "SH", "mission": "MIS", "system": "SYS", "subsystem": "SUB", "equipment": "EQP"}
    cat_map = {
        "functional": "FUN", "performance": "PER", "interface": "IFC",
        "environmental": "ENV", "design": "DES", "operational": "OPS",
        "reliability": "REL", "safety": "SAF", "product_assurance": "PA",
    }
    return f"{level_map.get(level, 'SYS')}-{cat_map.get(category, 'GEN')}-{sequence:03d}"


def trace_requirement(req_id: str, requirements: list[RequirementData]) -> dict:
    """Trace a requirement up (parents) and down (children).
    Returns {"parents": [...], "target": req, "children": [...]}
    """
    by_id = {r.id: r for r in requirements}
    by_req_id = {r.req_id: r for r in requirements}

    target = by_req_id.get(req_id)
    if target is None:
        return {"parents": [], "target": None, "children": []}

    # Walk up the parent chain
    parents: list[RequirementData] = []
    current = target
    while current.parent_id is not None:
        parent = by_id.get(current.parent_id)
        if parent is None:
            break
        parents.append(parent)
        current = parent
    parents.reverse()

    # Direct children only
    children = [r for r in requirements if r.parent_id == target.id]

    return {"parents": parents, "target": target, "children": children}


def verification_matrix(requirements: list[RequirementData]) -> list[dict]:
    """Generate verification matrix.
    Returns list of dicts: {req_id, title, level, method, status, allocated_to}
    """
    return [
        {
            "req_id": r.req_id,
            "title": r.title,
            "level": r.level,
            "method": r.verification_method,
            "status": r.verification_status,
            "allocated_to": r.allocated_to,
        }
        for r in requirements
    ]


def coverage_report(requirements: list[RequirementData]) -> dict:
    """Compute verification coverage.
    Returns {
        "total": int,
        "by_status": {"passed": int, "failed": int, "not_started": int, ...},
        "by_level": {"system": {"total": int, "verified": int, "pct": float}, ...},
        "by_method": {"test": int, "analysis": int, ...},
        "overall_pct": float,
    }
    """
    total = len(requirements)

    by_status: dict[str, int] = {}
    by_level: dict[str, dict] = {}
    by_method: dict[str, int] = {}

    verified_statuses = {"passed", "waived"}

    for r in requirements:
        # by_status
        by_status[r.verification_status] = by_status.get(r.verification_status, 0) + 1

        # by_level
        if r.level not in by_level:
            by_level[r.level] = {"total": 0, "verified": 0, "pct": 0.0}
        by_level[r.level]["total"] += 1
        if r.verification_status in verified_statuses:
            by_level[r.level]["verified"] += 1

        # by_method
        if r.verification_method:
            by_method[r.verification_method] = by_method.get(r.verification_method, 0) + 1

    for lvl_data in by_level.values():
        lvl_data["pct"] = (lvl_data["verified"] / lvl_data["total"] * 100.0) if lvl_data["total"] else 0.0

    verified_total = sum(1 for r in requirements if r.verification_status in verified_statuses)
    overall_pct = (verified_total / total * 100.0) if total else 0.0

    return {
        "total": total,
        "by_status": by_status,
        "by_level": by_level,
        "by_method": by_method,
        "overall_pct": overall_pct,
    }


def import_from_csv_rows(rows: list[dict]) -> list[RequirementData]:
    """Import requirements from CSV-style rows.
    Expected columns: ID (optional), Level, Category, Title, Text, Parent_ID, Verification_Method
    Auto-generates IDs if missing.
    """
    result: list[RequirementData] = []

    for i, row in enumerate(rows):
        level = row.get("Level", "system").lower()
        category = row.get("Category", "functional").lower()

        req_id = row.get("ID") or generate_req_id(level, category, i + 1)
        node_id = row.get("node_id") or str(i + 1)

        result.append(RequirementData(
            id=node_id,
            req_id=req_id,
            level=level,
            category=category,
            title=row.get("Title", ""),
            text=row.get("Text", ""),
            parent_id=row.get("Parent_ID") or None,
            verification_method=row.get("Verification_Method") or None,
            verification_status=row.get("Verification_Status", "not_started"),
        ))

    return result
