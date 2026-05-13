from bepi.supabase_client import get_service_client, get_supabase
from bepi.mock_data import (
    mock_tasks, mock_requirements, mock_risks,
    mock_product_tree_flat, mock_fmeca,
)


def _code_by_id(node_id: str) -> str:
    from bepi.mock_data import mock_product_tree_flat
    for n in mock_product_tree_flat():
        if n["id"] == node_id:
            return n["code"]
    return ""


def seed_demo_mission(
    mission_id: str,
    mission_name: str,
    framework: str = "ESA",
    *,
    sample_scope: str = "complete",
) -> None:
    client = get_service_client() or get_supabase()
    if not client:
        return

    nodes = _sample_product_tree(mock_product_tree_flat(), sample_scope)
    for node in nodes:
        parent_uuid = None
        if node.get("parent_id"):
            parent_row = next(
                (n for n in client.table("product_tree_nodes").select("id").eq("code", _code_by_id(node["parent_id"])).eq("mission_id", mission_id).execute().data or []),
                None,
            )
            if parent_row:
                parent_uuid = parent_row["id"]

        client.table("product_tree_nodes").insert({
            "mission_id": mission_id,
            "parent_id": parent_uuid,
            "level": node["level"],
            "code": node["code"],
            "name": node["name"],
            "subsystem_type": node.get("subsystem_type"),
            "quantity": node.get("quantity", 1),
            "trl": node.get("trl", 1),
            "status": "proposed",
        }).execute()

    for req in _sample(mock_requirements(), sample_scope, minimum=6):
        req_data = _model_data(req)
        client.table("requirements").insert({
            "mission_id": mission_id,
            "req_id": req_data["req_id"],
            "level": req_data["level"],
            "category": req_data["category"],
            "title": req_data["title"],
            "text": req_data["text"],
            "priority": req_data.get("priority", "mandatory"),
            "status": "draft",
            "verification_status": req_data.get("verification_status", "not_started"),
            "verification_method": req_data.get("verification_method", "analysis"),
        }).execute()

    for risk in _sample(mock_risks(), sample_scope, minimum=4):
        client.table("risks").insert({
            "mission_id": mission_id,
            "risk_id": risk.risk_id,
            "title": risk.title,
            "description": risk.description,
            "category": risk.category,
            "likelihood": risk.likelihood,
            "consequence": risk.consequence,
            "risk_level": _risk_level(risk.likelihood, risk.consequence),
            "status": risk.status or "open",
            "owner": risk.owner or "",
            "mitigation_strategy": risk.mitigation or "",
        }).execute()

    for task in _sample(mock_tasks(), sample_scope, minimum=8):
        client.table("schedule_tasks").insert({
            "mission_id": mission_id,
            "name": task.name,
            "start_date": str(task.start_date) if task.start_date else None,
            "end_date": str(task.end_date) if task.end_date else None,
            "duration_days": task.duration_days,
            "progress_pct": task.progress_pct,
            "assigned_to": task.assigned_to,
            "status": _task_status(task.status),
            "is_milestone": task.is_milestone,
            "notes": task.notes or "",
        }).execute()

    for entry in _sample(mock_fmeca(), sample_scope, minimum=4):
        node_row = next(
            (n for n in client.table("product_tree_nodes").select("id").eq("code", entry.node_id).eq("mission_id", mission_id).execute().data or []),
            None,
        )
        if not node_row:
            continue
        client.table("fmeca_entries").insert({
            "node_id": node_row["id"],
            "failure_mode": entry.failure_mode,
            "failure_cause": entry.failure_cause or "",
            "local_effect": entry.local_effect,
            "system_effect": entry.system_effect,
            "severity": entry.severity,
            "occurrence": entry.occurrence,
            "detection": entry.detection,
            "mitigation": entry.mitigation or "",
            "criticality": _criticality(entry.severity, entry.occurrence),
        }).execute()


def _sample(items: list, scope: str, minimum: int) -> list:
    if scope == "essential":
        return items[:minimum]
    return items


def _model_data(item) -> dict:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if hasattr(item, "dict"):
        return item.dict()
    return dict(item)


def _sample_product_tree(nodes: list[dict], scope: str) -> list[dict]:
    if scope != "essential":
        return nodes
    codes = {
        "SAT", "STR", "EPS", "AOCS", "COM", "CDH", "TCS", "PROP", "PL", "HRN",
        "STR-PRI", "EPS-SA", "EPS-BAT", "AOCS-RW", "COM-SBT", "CDH-OBC", "PL-OPT",
    }
    return [node for node in nodes if node["code"] in codes]


def _risk_level(likelihood: int, consequence: int) -> str:
    score = likelihood * consequence
    if score >= 15:
        return "critical"
    if score >= 9:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _criticality(severity: int, occurrence: int) -> str:
    if severity == 5 and occurrence >= 3:
        return "cat_1"
    if (severity == 4 and occurrence >= 3) or (severity == 5 and occurrence < 3):
        return "cat_2"
    if (severity == 3 and occurrence >= 3) or (severity == 4 and occurrence < 3):
        return "cat_3"
    return "cat_4"


def _task_status(status: str) -> str:
    if status == "pending":
        return "not_started"
    return status or "not_started"
