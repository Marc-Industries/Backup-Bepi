import streamlit as st
from postgrest.exceptions import APIError
from bepi.supabase_client import get_supabase, get_service_client


def load_missions_for_user(user_id: str) -> list[dict]:
    if not user_id:
        return []

    service = get_service_client()
    if service:
        try:
            mm = (
                service.table("mission_members")
                .select("mission_id, role, subsystem")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            ).data or []
            mission_ids = [r.get("mission_id") for r in mm if r.get("mission_id")]
            if not mission_ids:
                return []
            missions = (
                service.table("missions")
                .select("*")
                .in_("id", mission_ids)
                .execute()
            ).data or []
            mm_by_id = {r.get("mission_id"): r for r in mm}
            for m in missions:
                member = mm_by_id.get(m.get("id")) or {}
                m["mission_members"] = [{"role": member.get("role"), "subsystem": member.get("subsystem")}]
            return missions
        except Exception:
            return []

    client = get_supabase()
    if not client:
        return []

    try:
        result = client.table("missions").select("*, mission_members(role, subsystem)").execute()
        return result.data or []
    except APIError as e:
        if (e.args and isinstance(e.args[0], dict) and e.args[0].get("code") == "42501"):
            st.error(
                "Supabase policy error: permission denied for function `is_mission_member`.\n\n"
                "Fix in Supabase SQL (example):\n"
                "- `grant execute on function public.is_mission_member(uuid, uuid) to authenticated;`"
            )
            return []
        raise


def load_mission_members(mission_id: str) -> list[dict]:
    client = get_supabase()
    if not client:
        return []

    result = client.table("mission_members").select("*, profiles(id, full_name, email, org)").eq("mission_id", mission_id).execute()
    return result.data or []


def load_mission_data(mission_id: str) -> dict:
    client = get_supabase()
    if not client:
        return {}

    # Load all tables in parallel (sequential for simplicity)
    nodes_result = client.table("product_tree_nodes").select("*").eq("mission_id", mission_id).execute()
    reqs_result = client.table("requirements").select("*").eq("mission_id", mission_id).execute()
    risks_result = client.table("risks").select("*").eq("mission_id", mission_id).execute()
    tasks_result = client.table("schedule_tasks").select("*").eq("mission_id", mission_id).execute()
    limits_result = client.table("budget_limits").select("*").eq("mission_id", mission_id).execute()
    modes_result = client.table("operating_modes").select("*").eq("mission_id", mission_id).order("created_at").execute()
    members_result = load_mission_members(mission_id)
    mission_result = client.table("missions").select("*").eq("id", mission_id).execute()

    mission = mission_result.data[0] if mission_result.data else {}
    if not mission:
        return {}

    # Build budgets map keyed by node code
    budgets_map: dict[str, dict] = {}
    all_nodes = nodes_result.data or []
    all_budgets = client.table("budgets").select("*, product_tree_nodes(code)").execute().data or []
    for b in all_budgets:
        code = b.get("product_tree_nodes", {}).get("code", "") if isinstance(b.get("product_tree_nodes"), dict) else ""
        if code:
            current = budgets_map.setdefault(code, {"mass": 0, "power": 0, "power_by_mode": {}, "qty": 1, "mat": "estimate", "trl": 6})
            if b["budget_type"] == "mass_kg":
                current["mass"] = b["nominal_value"]
            elif b["budget_type"] == "power_w":
                mode_id = b.get("operating_mode_id")
                if mode_id:
                    current["power_by_mode"][str(mode_id)] = b["nominal_value"]
                current["power"] = b["nominal_value"]
            current["qty"] = b.get("quantity") or current["qty"]
            current["mat"] = b.get("maturity", current["mat"])

    node_id_map = {n.get("id"): n.get("code") for n in all_nodes if n.get("id")}
    node_ids = [nid for nid in node_id_map.keys()]
    if node_ids:
        fmeca_result = client.table("fmeca_entries").select("*").in_("node_id", node_ids).execute()
        fmeca_rows = fmeca_result.data or []
    else:
        fmeca_rows = []

    return {
        "missions": {mission_id: _map_mission(mission)},
        "product_tree": _map_product_tree(all_nodes),
        "requirements": [_map_requirement(r) for r in reqs_result.data or []],
        "risks": [_map_risk(r) for r in risks_result.data or []],
        "tasks": [_map_task(t) for t in tasks_result.data or []],
        "team_members": [_map_member(m) for m in members_result],
        "budget_limits": [_map_budget_limit(l) for l in limits_result.data or []],
        "operating_modes": modes_result.data or [],
        "equip_budgets": budgets_map,
        "fmeca_entries": [_map_fmeca_entry(f, node_id_map) for f in fmeca_rows],
        "mission_phase": mission.get("phase", "0"),
        "mission_framework": (mission.get("metadata", {}) or {}).get("framework", "ESA"),
    }


def _map_fmeca_entry(row: dict, node_map: dict[str, str]):
    # services.risks.FMECAEntryData — page_risks reads e.node_code, e.rpn (property),
    # e.severity, ... and _normalize_fmeca_entries reads/writes e.node_id.
    from bepi.services.risks import FMECAEntryData
    return FMECAEntryData(
        id=str(row["id"]),
        node_code=node_map.get(row.get("node_id"), "") or "",
        failure_mode=row.get("failure_mode") or "",
        failure_cause=row.get("failure_cause") or "",
        local_effect=row.get("local_effect") or "",
        system_effect=row.get("system_effect") or "",
        severity=int(row.get("severity") or 1),
        occurrence=int(row.get("occurrence") or 1),
        detection=int(row.get("detection") or 1),
        mitigation=row.get("mitigation") or "",
        criticality=row.get("criticality"),
        node_id=str(row.get("node_id", "")),
    )


def _map_mission(row: dict) -> dict:
    meta = row.get("metadata", {}) or {}
    return {
        "id": row.get("id"),
        "name": row.get("name", "Mission"),
        "description": row.get("description", ""),
        "mission_phase": row.get("phase", "0"),
        "mission_framework": meta.get("framework", "ESA"),
        "orb_alt": meta.get("orb_alt", meta.get("orbit_altitude_km", 500)),
        "orb_inc": meta.get("orb_inc", meta.get("inclination_deg", 97.5)),
        "orb_ecc": meta.get("orb_ecc", 0.0),
        "orb_raan": meta.get("orb_raan", 0.0),
        "orb_aop": meta.get("orb_aop", 0.0),
        "orb_mass": meta.get("orb_mass", meta.get("dry_mass_kg", 250.0)),
        "orb_area": meta.get("orb_area", 0.5),
        "propellant_kg": meta.get("propellant_kg", 0.0),
    }


def _map_product_tree(rows: list[dict]) -> list[dict]:
    return [
        {
            "id": str(r["id"]),
            "code": r["code"],
            "name": r["name"],
            "level": r["level"],
            "subsystem_type": r.get("subsystem_type"),
            "parent_id": str(r["parent_id"]) if r.get("parent_id") else None,
            "quantity": r.get("quantity", 1),
            "trl": r.get("trl", 1),
            "status": r.get("status", "proposed"),
            "description": r.get("description", ""),
            "manufacturer": r.get("manufacturer", ""),
            "part_number": r.get("part_number", ""),
            "notes": r.get("notes", ""),
        }
        for r in rows
    ]


def _map_requirement(row: dict):
    # services.requirements.RequirementData — page_requirements and coverage_report
    # access r.req_id, r.verification_status, r.allocated_to, ... as attributes.
    from bepi.services.requirements import RequirementData
    return RequirementData(
        id=str(row["id"]),
        req_id=row["req_id"],
        level=row.get("level") or "system",
        category=row.get("category") or "functional",
        title=row.get("title") or "",
        text=row.get("text") or "",
        parent_id=str(row["parent_id"]) if row.get("parent_id") else None,
        verification_method=row.get("verification_method"),
        verification_status=row.get("verification_status") or "not_started",
        allocated_to=row.get("allocated_to") or [],
    )


def _map_risk(row: dict):
    # Return the SAME dataclass the app uses (services.risks.RiskItemData), not a
    # dict: streamlit_app accesses risks as objects (r.risk_id, r.status,
    # r.risk_level, r.risk_score, r.mitigation_strategy) in ~50 places. A dict
    # crashed the first mission that actually had risks stored. risk_level /
    # risk_score are computed properties on the dataclass.
    from bepi.services.risks import RiskItemData
    return RiskItemData(
        id=str(row["id"]),
        risk_id=row["risk_id"],
        title=row.get("title") or "",
        description=row.get("description") or "",
        category=row.get("category") or "",
        likelihood=int(row.get("likelihood") or 1),
        consequence=int(row.get("consequence") or 1),
        status=row.get("status") or "open",
        owner=row.get("owner") or "",
        mitigation_strategy=row.get("mitigation_strategy") or "",
        residual_likelihood=row.get("residual_likelihood"),
        residual_consequence=row.get("residual_consequence"),
    )


def _map_task(row: dict):
    # services.scheduling.TaskData — compute_cpm/gantt_data and page_schedule use
    # t.id and t.predecessors (NOT the mock model's task_id/predecessor_ids). The
    # schedule_tasks table stores no dependencies, so predecessors is empty (tasks
    # render in the Gantt as parallel; CPM still runs).
    from bepi.services.scheduling import TaskData
    return TaskData(
        id=str(row["id"]),
        name=row.get("name") or "",
        duration_days=int(row.get("duration_days") or 0),
        predecessors=row.get("predecessor_ids") or [],
        start_date=row.get("start_date"),
        end_date=row.get("end_date"),
        progress_pct=float(row.get("progress_pct") or 0),
        is_milestone=bool(row.get("is_milestone")),
        wbs_code=row.get("wbs_code") or "",
        assigned_to=row.get("assigned_to") or "",
    )


def _map_member(row: dict) -> dict:
    profile = row.get("profiles", {}) or {}
    return {
        "id": str(row["user_id"]),
        "name": profile.get("full_name") or profile.get("email") or "You",
        "email": profile.get("email", ""),
        "role": row["role"],
        "org": profile.get("org", ""),
        "subsystem": row.get("subsystem"),
    }


def _map_budget_limit(row: dict) -> dict:
    return {
        "budget_type": row["budget_type"],
        "limit_value": row["limit_value"],
        "unit": row["unit"],
    }
