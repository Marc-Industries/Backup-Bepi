import streamlit as st

ROLES = {
    "ADMIN": {"name": "Administrator", "color": "#2c3e50", "icon": "🛡️",
              "permissions": ["approve_milestone", "approve_risk", "approve_budget", "approve_requirement", "approve_deliverable", "approve_verification", "approve_document",
                              "edit_schedule", "edit_requirement", "edit_risk", "edit_subsystem", "edit_budget", "edit_fmeca", "edit_ncr", "edit_warehouse",
                              "manage_team", "manage_baseline", "update_progress", "update_verification", "view_all"]},
    "PM": {"name": "Project Manager", "color": "#e74c3c", "icon": "👔",
           "permissions": ["approve_milestone", "approve_risk", "approve_budget", "edit_schedule", "edit_requirement", "edit_risk", "edit_subsystem", "edit_budget", "manage_team", "view_all"]},
    "SE": {"name": "Systems Engineer", "color": "#3498db", "icon": "🔧",
           "permissions": ["approve_requirement", "approve_budget", "edit_requirement", "edit_budget", "edit_risk", "edit_schedule", "edit_subsystem", "view_all"]},
    "SSL": {"name": "Subsystem Lead", "color": "#e67e22", "icon": "⚙️",
            "permissions": ["edit_subsystem", "update_progress", "edit_fmeca", "view_subsystem"]},
    "QA": {"name": "Quality Assurance", "color": "#9b59b6", "icon": "✅",
           "permissions": ["approve_deliverable", "approve_verification", "edit_ncr", "view_all"]},
    "CM": {"name": "Configuration Manager", "color": "#1abc9c", "icon": "📋",
           "permissions": ["approve_document", "manage_baseline", "edit_warehouse", "view_all"]},
    "AIT": {"name": "AIT Engineer", "color": "#27ae60", "icon": "🧪",
            "permissions": ["update_verification", "update_progress", "edit_warehouse", "view_all"]},
    "USER": {"name": "User", "icon": "👤", "permissions": ["view_all"]},
}

ROLE_PERMISSION_LABELS = {
    "approve_milestone": "Approve milestones & review gates",
    "approve_risk": "Approve risk register changes",
    "approve_budget": "Approve budget allocations",
    "edit_schedule": "Edit project schedule",
    "view_all": "View all mission data",
    "approve_requirement": "Approve requirement status changes",
    "edit_requirement": "Create/edit requirements",
    "edit_budget": "Edit budget allocations",
    "edit_subsystem": "Edit own subsystem data",
    "update_progress": "Update task progress",
    "edit_fmeca": "Edit FMECA entries",
    "view_subsystem": "View own subsystem data",
    "approve_deliverable": "Approve review deliverables",
    "approve_verification": "Approve verification evidence",
    "edit_ncr": "Create/edit non-conformance reports",
    "approve_document": "Approve document baselines",
    "manage_baseline": "Manage configuration baselines",
    "edit_warehouse": "Edit warehouse data",
    "update_verification": "Update verification test results",
    "manage_team": "Manage mission team membership",
}


def _current_user() -> dict:
    return st.session_state.get("user", {}) or {}


def _current_role() -> str:
    return _current_user().get("role", "USER")


def can(action: str) -> bool:
    role = _current_role()
    return action in ROLES.get(role, ROLES.get("USER", {})).get("permissions", [])


def require(action: str) -> bool:
    if can(action):
        return True
    role = _current_role()
    role_info = ROLES.get(role, ROLES.get("USER", {"name": "Unknown"}))
    role_name = role_info.get("name", "Unknown")
    st.warning(f"🔒 {role_name} non ha il permesso `{action}`")
    return False


def _node_subsystem(node_id: str) -> str | None:
    flat = st.session_state.get("product_tree", [])
    node = next((n for n in flat if n["id"] == node_id), None)
    while node:
        if sst := node.get("subsystem_type"):
            return sst
        node = next((n for n in flat if n["id"] == node.get("parent_id")), None)
    return None


def can_edit_node(node_id: str) -> bool:
    current_role = _current_role()
    if current_role != "SSL":
        return can("edit_subsystem") or can("edit_budget")
    sst = _node_subsystem(node_id)
    current_user = _current_user()
    return sst is not None and current_user.get("subsystem") == sst


def can_modify_product_tree(action: str, payload: dict) -> bool:
    if action in ("add_node", "delete_node", "edit_node"):
        if _current_role() == "SSL":
            parent_id = payload.get("parent_id") or payload.get("parentId")
            return bool(parent_id and can_edit_node(parent_id))
        return can("edit_subsystem")
    if action == "update_item":
        return can("edit_budget")
    return False
