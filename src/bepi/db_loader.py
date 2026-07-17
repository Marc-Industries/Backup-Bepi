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
            budgets_map[code] = {
                "mass": b["nominal_value"] if b["budget_type"] == "mass_kg" else budgets_map.get(code, {}).get("mass", 0),
                "power": b["nominal_value"] if b["budget_type"] == "power_w" else budgets_map.get(code, {}).get("power", 0),
                "qty": 1,
                "mat": b.get("maturity", "estimate"),
                "trl": 6,
            }

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
        "equip_budgets": budgets_map,
        "fmeca_entries": [_map_fmeca_entry(f, node_id_map) for f in fmeca_rows],
        "mission_phase": mission.get("phase", "0"),
        "mission_framework": (mission.get("metadata", {}) or {}).get("framework", "ESA"),
    }


def _map_fmeca_entry(row: dict, node_map: dict[str, str]) -> dict:
    return {
        "id": str(row["id"]),
        "node_id": str(row.get("node_id", "")),
        "node_code": node_map.get(row.get("node_id"), ""),
        "failure_mode": row.get("failure_mode", ""),
        "failure_cause": row.get("failure_cause", ""),
        "local_effect": row.get("local_effect", ""),
        "system_effect": row.get("system_effect", ""),
        "severity": row.get("severity", 1),
        "occurrence": row.get("occurrence", 1),
        "detection": row.get("detection", 1),
        "mitigation": row.get("mitigation", ""),
        "criticality": row.get("criticality"),
    }


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


def _map_requirement(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "req_id": row["req_id"],
        "level": row["level"],
        "category": row["category"],
        "title": row["title"],
        "text": row["text"],
        "rationale": row.get("rationale", ""),
        "priority": row.get("priority", "mandatory"),
        "status": row.get("status", "draft"),
        "ecss_ref": row.get("ecss_ref", ""),
        "source": row.get("source", ""),
        "verification_method": row.get("verification_method", "analysis"),
        "verification_status": row.get("verification_status", "not_started"),
        "verification_evidence": row.get("verification_evidence", ""),
        "parent_id": str(row["parent_id"]) if row.get("parent_id") else None,
    }


def _map_risk(row: dict) -> "RiskItemData":
    # Return a RiskItemData object, not a dict: the app accesses risks as
    # objects (r.risk_id, r.status, r.risk_level, ...) in ~50 places — mock
    # missions load objects, so DB missions must too, or those attribute
    # accesses raise AttributeError (as they did on the first mission that
    # actually had risks stored). risk_level is a computed property on the
    # model; DB `mitigation_strategy` maps to the model's `mitigation`.
    from bepi.mock_data import RiskItemData
    return RiskItemData(
        id=str(row["id"]),
        risk_id=row["risk_id"],
        title=row.get("title") or "",
        description=row.get("description") or "",
        category=row.get("category") or "",
        likelihood=row.get("likelihood") or 1,
        consequence=row.get("consequence") or 1,
        status=row.get("status") or "open",
        owner=row.get("owner") or "",
        mitigation=row.get("mitigation_strategy") or "",
        residual_likelihood=row.get("residual_likelihood"),
        residual_consequence=row.get("residual_consequence"),
    )


def _map_task(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "start_date": row.get("start_date"),
        "end_date": row.get("end_date"),
        "duration_days": row.get("duration_days", 0),
        "progress_pct": row.get("progress_pct", 0.0),
        "assigned_to": row.get("assigned_to", ""),
        "status": row.get("status", "not_started"),
        "is_milestone": row.get("is_milestone", False),
        "notes": row.get("notes", ""),
        "wbs_code": "",
    }


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
