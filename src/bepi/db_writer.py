from bepi.supabase_client import get_supabase, get_service_client


def update_mission_member(mission_id: str, user_id: str, updates: dict) -> None:
    client = get_service_client() or get_supabase()
    if not client or not mission_id or not user_id:
        return
    client.table("mission_members").update(updates).eq("mission_id", mission_id).eq("user_id", user_id).execute()


def add_mission_member(mission_id: str, user_id: str, role: str = "PM", subsystem: str | None = None) -> dict | None:
    client = get_service_client() or get_supabase()
    if not client or not mission_id or not user_id:
        return None
    payload = {
        "mission_id": mission_id,
        "user_id": user_id,
        "role": role,
    }
    if subsystem:
        payload["subsystem"] = subsystem
    result = client.table("mission_members").insert(payload).execute()
    return result.data[0] if result.data else None


def add_requirement(mission_id: str, req_data: dict) -> dict | None:
    client = get_supabase()
    if not client:
        return None
    result = client.table("requirements").insert({
        "mission_id": mission_id,
        "req_id": req_data.get("req_id", ""),
        "level": req_data.get("level", "subsystem"),
        "category": req_data.get("category", "functional"),
        "title": req_data.get("title", ""),
        "text": req_data.get("text", ""),
        "priority": req_data.get("priority", "mandatory"),
        "status": "draft",
        "verification_status": "not_started",
        "verification_method": "analysis",
    }).execute()
    return result.data[0] if result.data else None


def add_mission(
    name: str,
    description: str,
    phase: str,
    framework: str,
    *,
    owner_user_id: str | None = None,
    orbit_altitude_km: int | None = None,
    inclination_deg: int | None = None,
    dry_mass_kg: int | None = None,
    propellant_kg: int | None = None,
    sample_scope: str | None = None,
    profile_key: str | None = None,
) -> dict | None:
    client = get_service_client()
    if not client:
        client = get_supabase()
    if not client:
        return None
    metadata = {
        "framework": framework,
        "orbit_altitude_km": orbit_altitude_km,
        "inclination_deg": inclination_deg,
        "dry_mass_kg": dry_mass_kg,
        "propellant_kg": propellant_kg,
        "sample_scope": sample_scope,
        "profile_key": profile_key,
    }
    metadata = {k: v for k, v in metadata.items() if v is not None}
    result = client.table("missions").insert({
        "name": name,
        "description": description,
"phase": phase,
        "orbit_type": _orbit_type_from_altitude(orbit_altitude_km),
        "metadata": metadata,
    }).execute()
    mission = result.data[0] if result.data else None
    if mission and owner_user_id:
        add_mission_member(mission["id"], owner_user_id, "ADMIN")
    return mission


def _orbit_type_from_altitude(altitude_km: int | None) -> str | None:
    if altitude_km is None:
        return None
    if altitude_km < 2_000:
        return "LEO"
    if 30_000 <= altitude_km <= 42_500:
        return "GEO"
    return "MEO"


def update_requirement(req_id: str, updates: dict) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("requirements").update(updates).eq("id", req_id).execute()


def delete_requirement(req_id: str) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("requirements").delete().eq("id", req_id).execute()


def add_task(mission_id: str, task_data: dict) -> dict | None:
    client = get_supabase()
    if not client:
        return None
    result = client.table("schedule_tasks").insert({
        "mission_id": mission_id,
        "name": task_data.get("name", ""),
        "start_date": task_data.get("start_date"),
        "end_date": task_data.get("end_date"),
        "duration_days": task_data.get("duration_days", 0),
        "progress_pct": task_data.get("progress_pct", 0.0),
        "assigned_to": task_data.get("assigned_to", ""),
        "status": task_data.get("status", "not_started"),
        "is_milestone": task_data.get("is_milestone", False),
    }).execute()
    return result.data[0] if result.data else None


def update_task(task_id: str, updates: dict) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("schedule_tasks").update(updates).eq("id", task_id).execute()


def delete_task(task_id: str) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("schedule_tasks").delete().eq("id", task_id).execute()


def add_risk(mission_id: str, risk_data: dict) -> dict | None:
    client = get_supabase()
    if not client:
        return None
    result = client.table("risks").insert({
        "mission_id": mission_id,
        "risk_id": risk_data.get("risk_id", ""),
        "title": risk_data.get("title", ""),
        "description": risk_data.get("description", ""),
        "category": risk_data.get("category", "technical"),
        "likelihood": risk_data.get("likelihood", 3),
        "consequence": risk_data.get("consequence", 3),
        "risk_level": risk_data.get("risk_level", "medium"),
        "status": "open",
    }).execute()
    return result.data[0] if result.data else None


def update_risk(risk_id: str, updates: dict) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("risks").update(updates).eq("id", risk_id).execute()


def delete_risk(risk_id: str) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("risks").delete().eq("id", risk_id).execute()


def add_fmeca_entry(entry_data: dict) -> dict | None:
    client = get_supabase()
    if not client:
        return None
    result = client.table("fmeca_entries").insert(entry_data).execute()
    return result.data[0] if result.data else None


def update_fmeca_entry(entry_id: str, updates: dict) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("fmeca_entries").update(updates).eq("id", entry_id).execute()


def delete_fmeca_entry(entry_id: str) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("fmeca_entries").delete().eq("id", entry_id).execute()


def add_product_node(mission_id: str, node_data: dict) -> dict | None:
    client = get_supabase()
    if not client:
        return None
    result = client.table("product_tree_nodes").insert({
        "mission_id": mission_id,
        "parent_id": node_data.get("parent_id"),
        "level": node_data.get("level", "equipment"),
        "code": node_data.get("code", ""),
        "name": node_data.get("name", ""),
        "subsystem_type": node_data.get("subsystem_type"),
        "quantity": node_data.get("quantity", 1),
        "trl": node_data.get("trl", 1),
        "status": "proposed",
    }).execute()
    return result.data[0] if result.data else None


def update_product_node(node_id: str, updates: dict) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("product_tree_nodes").update(updates).eq("id", node_id).execute()


def delete_product_node(node_id: str) -> None:
    client = get_supabase()
    if not client:
        return
    client.table("product_tree_nodes").delete().eq("id", node_id).execute()


def delete_mission(mission_id: str) -> bool:
    """Delete a mission and all related data from the database."""
    service = get_service_client() or get_supabase()
    if not service or not mission_id:
        return False
    
    # Delete related data first (cascade)
    try:
        service.table("mission_members").delete().eq("mission_id", mission_id).execute()
    except Exception:
        pass
    
    try:
        service.table("requirements").delete().eq("mission_id", mission_id).execute()
    except Exception:
        pass
    
    try:
        service.table("risks").delete().eq("mission_id", mission_id).execute()
    except Exception:
        pass
    
    try:
        service.table("schedule_tasks").delete().eq("mission_id", mission_id).execute()
    except Exception:
        pass
    
    try:
        service.table("product_tree_nodes").delete().eq("mission_id", mission_id).execute()
    except Exception:
        pass
    
    try:
        service.table("fmeca_entries").delete().eq("mission_id", mission_id).execute()
    except Exception:
        pass
    
    try:
        service.table("reviews").delete().eq("mission_id", mission_id).execute()
    except Exception:
        pass
    
    try:
        service.table("budgets").delete().eq("mission_id", mission_id).execute()
    except Exception:
        pass
    
    # Finally delete the mission
    try:
        service.table("missions").delete().eq("id", mission_id).execute()
        return True
    except Exception:
        return False
