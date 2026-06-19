"""BEPI-SAT Demo Dashboard — self-contained with mock data."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date, timedelta
from streamlit_option_menu import option_menu
import streamlit_antd_components as sac
from streamlit_extras.metric_cards import style_metric_cards
def colored_header(label="", description="", color_name="blue-70"):
    color_map = {"blue-70": "blue", "orange-70": "orange", "green-70": "green",
                 "violet-70": "violet", "red-70": "red", "light-blue-70": "blue", "gray-70": "gray"}
    st.header(label, divider=color_map.get(color_name, "blue"))
    if description:
        st.caption(description)

from bepi.services.budgets import (
    BudgetAllocationData, BudgetSummaryLine, compute_budget_summary,
)
from bepi.services.product_tree import ProductNodeData, build_tree, flatten_tree, compute_wbs_codes
from bepi.services.requirements import (
    RequirementData, verification_matrix, coverage_report,
)
from bepi.services.risks import (
    RiskItemData, FMECAEntryData, risk_matrix, fmeca_ranking, compute_criticality,
)
from bepi.services.scheduling import TaskData, compute_cpm, gantt_data
from bepi.ecss.margins import COMPONENT_MARGINS, SYSTEM_MARGINS, get_component_margin, get_system_margin
from bepi.ecss.phases import (PHASE_DEFINITIONS, PHASE_GATE_REVIEWS, PHASE_TRANSITIONS,
    NASA_PHASE_DEFINITIONS, NASA_PHASE_GATE_REVIEWS, NASA_PHASE_TRANSITIONS,
    ESA_TRL_TARGETS, NASA_TRL_TARGETS, ESA_PHASE_ACTIVITIES, NASA_PHASE_ACTIVITIES,
    ESA_MAIT_STATUS, FRAMEWORKS, get_framework)
from bepi.ecss.reviews import REVIEW_DEFINITIONS
from bepi.services.reports import generate_report
from bepi.auth import render_auth_ui, logout, get_current_user, check_password
from bepi.role_permissions import ROLES, ROLE_PERMISSION_LABELS, can, require, can_edit_node, can_modify_product_tree
from bepi.supabase_client import get_supabase, get_service_client
from bepi.db_loader import load_mission_data, load_missions_for_user, load_mission_members
from bepi.db_writer import (
    add_mission, delete_mission, add_requirement, update_requirement, delete_requirement,
    add_risk, update_risk, delete_risk, add_fmeca_entry, update_fmeca_entry, delete_fmeca_entry,
)
from bepi.seed import seed_demo_mission
from bepi.team_ops import invite_team_member
from bepi.onboarding import check_onboarding_needed, render_onboarding, _load_user_missions


def _process_product_tree_action(action: str, data: dict, flat: list, eb: dict):
    """Process product tree actions and save to DB."""
    from bepi.role_permissions import can
    
    client = get_service_client() or get_supabase()
    mission_id = st.session_state.get("active_mission_id")
    _role = st.session_state.get("user", {}).get("role", "USER")

    def _parent_uuid(parent_id: str | None) -> str | None:
        if not parent_id:
            return None
        for n in st.session_state.get("product_tree", []):
            if str(n.get("id")) == str(parent_id) or str(n.get("uuid")) == str(parent_id):
                return str(n.get("uuid") or n.get("id"))
        return str(parent_id)
    
    if action == "add_node":
        if _role == "ADMIN" or can("edit_subsystem") or can("edit_budget"):
            st.session_state["product_tree"].append(data)
            # Mark we just added locally so the next reload doesn't clobber it
            # before Supabase has a chance to return the new uuid.
            st.session_state["_pt_just_added"] = {
                "local_id": str(data.get("id", "")),
                "code": data.get("code", ""),
                "name": data.get("name", ""),
                "level": data.get("level", "subsystem"),
                "ts": __import__("time").time(),
            }
            if client and mission_id:
                try:
                    result = client.table("product_tree_nodes").insert({
                        "mission_id": mission_id,
                        "parent_id": _parent_uuid(data.get("parent_id")),
                        "level": data.get("level", "subsystem"),
                        "code": str(data.get("code", "")),
                        "name": str(data.get("name", "")),
                        "subsystem_type": data.get("subsystem_type"),
                        "is_leaf": bool(data.get("is_leaf", False)),
                        "quantity": int(data.get("quantity", 1)),
                        "trl": int(data.get("trl", 1)),
                        "status": data.get("status", "proposed"),
                    }).execute()
                    if result.data:
                        new_uuid = str(result.data[0].get("id", ""))
                        for n in st.session_state["product_tree"]:
                            if str(n.get("id")) == str(data.get("id")):
                                n["uuid"] = new_uuid
                                break
                        # Clear the "just added" marker — we have the real uuid now
                        st.session_state.pop("_pt_just_added", None)

                        # Add budgets for equipment
                        if data.get("level") == "equipment":
                            node_uuid = new_uuid
                            eb[data["code"]] = {"mass": 0.0, "power": 0, "qty": 1, "mat": "estimate", "trl": 1}
                            try:
                                client.table("budgets").insert({
                                    "node_id": node_uuid, "budget_type": "mass_kg", "nominal_value": 0.0, "unit": "kg", "maturity": "estimate"
                                }).execute()
                                client.table("budgets").insert({
                                    "node_id": node_uuid, "budget_type": "power_w", "nominal_value": 0.0, "unit": "W", "maturity": "estimate"
                                }).execute()
                            except Exception as e:
                                st.warning(f"Budget row insert failed: {e}")
                    else:
                        st.warning(f"⚠️ DB insert returned no rows for code={data.get('code')!r}. The node is kept locally but may not persist after refresh.")
                except Exception as e:
                    st.error(f"Add Error: {e}")
        else:
            st.warning("You don't have permission to add components to the product tree.")
    
    elif action == "update_item":
        if _role == "ADMIN" or can("edit_budget") or can("edit_subsystem"):
            code = data.get("code")
            if code:
                eb[code]["mass"] = float(data.get("mass", eb.get(code, {}).get("mass", 0)))
                eb[code]["power"] = float(data.get("power", eb.get(code, {}).get("power", 0)))
                eb[code]["qty"] = int(data.get("qty", eb.get(code, {}).get("qty", 1)))
                eb[code]["mat"] = data.get("maturity", eb.get(code, {}).get("mat", "estimate"))
                eb[code]["trl"] = int(data.get("trl", eb.get(code, {}).get("trl", 1)))
                
                if client:
                    try:
                        for n in st.session_state.get("product_tree", []):
                            if n.get("code") == code:
                                node_uuid = n.get("uuid") or n.get("id")
                                if node_uuid:
                                    for btype, field, unit in [("mass_kg", "mass", "kg"), ("power_w", "power", "W")]:
                                        res = client.table("budgets").update({
                                            "nominal_value": eb[code][field],
                                            "maturity": eb[code]["mat"],
                                        }).eq("node_id", node_uuid).eq("budget_type", btype).execute()
                                        if not res.data:
                                            client.table("budgets").insert({
                                                "node_id": node_uuid,
                                                "budget_type": btype,
                                                "nominal_value": eb[code][field],
                                                "unit": unit,
                                                "maturity": eb[code]["mat"],
                                            }).execute()
                                break
                    except Exception as e:
                        st.error(f"Update Error: {e}")
    
    # Clear query params after processing
    st.query_params.clear()


st.set_page_config(
    page_title="BEPI — Budget, Engineering & Project Integration",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Auth gate ---
if get_supabase():
    user = render_auth_ui()
    if not user:
        st.stop()
    has_local_mission = bool(st.session_state.get("active_mission_id")) and bool(st.session_state.get("missions"))
    onboarding_done = bool(st.session_state.get("_onboarding_completed")) or has_local_mission
    if st.session_state.get("ob_step") or (not onboarding_done and check_onboarding_needed(user.get("id"))):
        render_onboarding()
        st.stop()
    if not st.session_state.get("_missions_loaded"):
        _load_user_missions(user.get("id"))
else:
    if not check_password():
        st.stop()
    st.session_state["user"] = {"id": "U00", "full_name": "Admin", "role": "ADMIN", "email": "admin@bepi.eu"}

# Supabase config
HAS_SUPABASE = False
try:
    secrets = st.secrets.get("supabase", {})
    if secrets.get("url") and secrets.get("anon_key"):
        HAS_SUPABASE = get_supabase() is not None
except Exception:
    pass

# Enforce DB until policy is signed (check from secrets)
_policy_signed = False
try:
    _policy_signed = st.secrets.get("custom", {}).get("policy_signed", False)
except Exception:
    _policy_signed = False

DB_ENFORCED = HAS_SUPABASE and not _policy_signed


# Custom CSS
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        overflow-y: auto !important;
        max-height: 100vh !important;
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; font-size: 0.85rem !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.8rem !important; }
    .status-badge {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600; color: white;
    }
    .badge-green { background: #27ae60; }
    .badge-yellow { background: #f39c12; }
    .badge-red { background: #e74c3c; }
    .badge-blue { background: #3498db; }
    .badge-gray { background: #7f8c8d; }
    .tree-node {
        padding: 4px 8px; margin: 2px 0; border-radius: 6px;
        border-left: 3px solid #3498db; background: rgba(52,152,219,0.05);
    }
    .tree-node-sub { border-left-color: #e67e22; background: rgba(230,126,34,0.05); }
    .tree-node-equip { border-left-color: #27ae60; background: rgba(39,174,96,0.05); }
    .kpi-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155; border-radius: 16px;
        padding: 24px; text-align: center;
    }
    .phase-active { background: #f39c12; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
    .phase-done { background: #27ae60; color: white; padding: 4px 12px; border-radius: 20px; }
    .phase-future { background: #334155; color: #94a3b8; padding: 4px 12px; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Users, Roles & Approval System (must be before sidebar)
# ---------------------------------------------------------------------------

TEAM_MEMBERS = [
    {"id": "U00", "name": "Admin", "role": "ADMIN", "email": "admin@bepi.eu", "org": "Prime"},
    {"id": "U01", "name": "M. Rossi", "role": "PM", "email": "rossi@bepi.eu", "org": "Prime"},
    {"id": "U02", "name": "L. Bianchi", "role": "SE", "email": "bianchi@bepi.eu", "org": "Prime"},
    {"id": "U03", "name": "A. Ferrari", "role": "SSL", "email": "ferrari@bepi.eu", "org": "Prime", "subsystem": "EPS"},
    {"id": "U04", "name": "G. Conti", "role": "SSL", "email": "conti@bepi.eu", "org": "Prime", "subsystem": "AOCS"},
    {"id": "U05", "name": "S. Moretti", "role": "SSL", "email": "moretti@bepi.eu", "org": "SubCon-A", "subsystem": "COM"},
    {"id": "U06", "name": "P. Russo", "role": "SSL", "email": "russo@bepi.eu", "org": "Prime", "subsystem": "CDH"},
    {"id": "U07", "name": "F. Romano", "role": "SSL", "email": "romano@bepi.eu", "org": "Prime", "subsystem": "TCS"},
    {"id": "U08", "name": "D. Colombo", "role": "SSL", "email": "colombo@bepi.eu", "org": "Prime", "subsystem": "STR"},
    {"id": "U09", "name": "E. Ricci", "role": "SSL", "email": "ricci@bepi.eu", "org": "SubCon-B", "subsystem": "PROP"},
    {"id": "U10", "name": "C. Marino", "role": "SSL", "email": "marino@bepi.eu", "org": "SubCon-C", "subsystem": "PL"},
    {"id": "U11", "name": "R. Greco", "role": "QA", "email": "greco@bepi.eu", "org": "Prime"},
    {"id": "U12", "name": "N. Costa", "role": "CM", "email": "costa@bepi.eu", "org": "Prime"},
    {"id": "U13", "name": "V. Bruno", "role": "AIT", "email": "bruno@bepi.eu", "org": "Prime"},
]

def get_member(uid):
    tm = st.session_state.get("team_members", TEAM_MEMBERS)
    return next((m for m in tm if m["id"] == uid), None)

def member_badge(uid, show_role=True):
    m = get_member(uid)
    if not m:
        return ""
    role = ROLES[m["role"]]
    role_tag = f" <span class='status-badge' style='background:{role['color']};font-size:0.6rem;'>{m['role']}</span>" if show_role else ""
    return f"{role['icon']} {m['name']}{role_tag}"

def approval_badge(status):
    s = APPROVAL_STATUS.get(status, APPROVAL_STATUS["pending"])
    return f"<span class='status-badge' style='background:{s['color']};'>{s['icon']} {s['label']}</span>"

def get_latest_approval(entity, entity_id):
    log = st.session_state.get("approval_log", APPROVAL_LOG)
    matches = [a for a in log if a["entity"] == entity and a["entity_id"] == entity_id]
    return matches[-1] if matches else None

_MISSION_DATA_KEYS = [
    "tasks", "requirements", "risks", "approval_log", "req_ownership",
    "task_assignments", "risk_overrides", "product_tree", "equip_budgets",
    "warehouse_items", "procurement_orders", "mission_phase", "mission_framework",
    "orb_alt", "orb_inc", "orb_ecc", "orb_raan", "orb_aop", "orb_mass", "orb_area", "orb_epoch",
    "team_members", "fmeca_entries", "propellant_kg",
]
# Ensure mission state exists
if "missions" not in st.session_state:
    st.session_state.missions = {}
if not st.session_state.get("active_mission_id"):
    st.session_state.active_mission_id = None

# ---------------------------------------------------------------------------
# Mock data & Constants (used by _default_mission_data)
# ---------------------------------------------------------------------------

APPROVAL_STATUS = {
    "pending": {"label": "Pending", "color": "#f39c12", "icon": "⏳"},
    "approved": {"label": "Approved", "color": "#27ae60", "icon": "✅"},
    "rejected": {"label": "Rejected", "color": "#e74c3c", "icon": "❌"},
    "not_required": {"label": "—", "color": "#7f8c8d", "icon": ""},
}

APPROVAL_LOG = [
    {"entity": "task", "entity_id": "T01", "action": "progress_100%", "status": "approved",
     "approver": "U01", "approved_by_role": "PM", "date": "2025-12-01", "comment": "SRR baseline complete"},
    {"entity": "requirement", "entity_id": "1", "action": "status_passed", "status": "approved",
     "approver": "U02", "approved_by_role": "SE", "date": "2025-12-15", "comment": "Verified at SRR"},
    {"entity": "requirement", "entity_id": "2", "action": "status_passed", "status": "approved",
     "approver": "U02", "approved_by_role": "SE", "date": "2026-01-10", "comment": "Orbit analysis confirms compliance"},
    {"entity": "requirement", "entity_id": "7", "action": "status_passed", "status": "approved",
     "approver": "U02", "approved_by_role": "SE", "date": "2026-02-20", "comment": "Mass budget within limits"},
    {"entity": "requirement", "entity_id": "8", "action": "status_passed", "status": "approved",
     "approver": "U02", "approved_by_role": "SE", "date": "2026-02-20", "comment": "Power budget within limits"},
    {"entity": "requirement", "entity_id": "11", "action": "status_passed", "status": "approved",
     "approver": "U11", "approved_by_role": "QA", "date": "2026-03-01", "comment": "Safe mode demo successful"},
    {"entity": "requirement", "entity_id": "12", "action": "status_passed", "status": "approved",
     "approver": "U02", "approved_by_role": "SE", "date": "2026-02-28", "comment": "Link budget analysis confirms 8.2 dB margin"},
    {"entity": "requirement", "entity_id": "14", "action": "status_passed", "status": "approved",
     "approver": "U11", "approved_by_role": "QA", "date": "2026-03-05", "comment": "Datasheet inspection confirms 22x22 deg FOV"},
    {"entity": "task", "entity_id": "T02", "action": "progress_80%", "status": "approved",
     "approver": "U08", "approved_by_role": "SSL", "date": "2026-03-15", "comment": "STR FEM analysis complete"},
    {"entity": "task", "entity_id": "T03", "action": "progress_75%", "status": "approved",
     "approver": "U03", "approved_by_role": "SSL", "date": "2026-03-10", "comment": "EPS sizing converged"},
    {"entity": "task", "entity_id": "T04", "action": "progress_70%", "status": "pending",
     "approver": "U04", "approved_by_role": "SSL", "date": "2026-03-20", "comment": "AOCS mode analysis pending review"},
    {"entity": "task", "entity_id": "T07", "action": "progress_55%", "status": "pending",
     "approver": "U10", "approved_by_role": "SSL", "date": "2026-03-25", "comment": "Optical design TBR on aperture"},
    {"entity": "risk", "entity_id": "2", "action": "mitigation_update", "status": "approved",
     "approver": "U01", "approved_by_role": "PM", "date": "2026-02-15", "comment": "Rad-hard FPGA selected, watchdog implemented"},
    {"entity": "risk", "entity_id": "7", "action": "mitigation_update", "status": "approved",
     "approver": "U01", "approved_by_role": "PM", "date": "2026-01-20", "comment": "Cell-level fuses procured"},
    {"entity": "milestone", "entity_id": "M_SRR", "action": "passed", "status": "approved",
     "approver": "U01", "approved_by_role": "PM", "date": "2025-12-01", "comment": "SRR board: all criteria met"},
]

TASK_ASSIGNMENTS = {
    "T01": {"responsible": "U02", "approver": "U01", "contributors": ["U02", "U03", "U04", "U05"]},
    "T02": {"responsible": "U08", "approver": "U02", "contributors": ["U08"]},
    "T03": {"responsible": "U03", "approver": "U02", "contributors": ["U03"]},
    "T04": {"responsible": "U04", "approver": "U02", "contributors": ["U04"]},
    "T05": {"responsible": "U05", "approver": "U02", "contributors": ["U05"]},
    "T06": {"responsible": "U06", "approver": "U02", "contributors": ["U06"]},
    "T07": {"responsible": "U10", "approver": "U02", "contributors": ["U10"]},
    "T08": {"responsible": "U02", "approver": "U01", "contributors": ["U02", "U03", "U04"]},
    "T09": {"responsible": "U11", "approver": "U02", "contributors": ["U11", "U13"]},
    "T10": {"responsible": "U02", "approver": "U01", "contributors": ["U02", "U12"]},
    "T11": {"responsible": "U02", "approver": "U01", "contributors": ["U02", "U03", "U04", "U05", "U06", "U07"]},
    "T12": {"responsible": "U01", "approver": "U01", "contributors": ["U03", "U09", "U10"]},
    "T13": {"responsible": "U02", "approver": "U01", "contributors": ["U02", "U11", "U12"]},
    "M_SRR": {"responsible": "U01", "approver": "U01", "contributors": []},
    "M_PDR": {"responsible": "U01", "approver": "U01", "contributors": []},
    "M_CDR": {"responsible": "U01", "approver": "U01", "contributors": []},
}

REQ_OWNERSHIP = {
    "1": {"owner": "U01", "approver": "U02"},
    "2": {"owner": "U02", "approver": "U01"},
    "3": {"owner": "U05", "approver": "U02"},
    "4": {"owner": "U04", "approver": "U02"},
    "5": {"owner": "U04", "approver": "U02"},
    "6": {"owner": "U06", "approver": "U02"},
    "7": {"owner": "U02", "approver": "U01"},
    "8": {"owner": "U03", "approver": "U02"},
    "9": {"owner": "U02", "approver": "U01"},
    "10": {"owner": "U03", "approver": "U02"},
    "11": {"owner": "U04", "approver": "U02"},
    "12": {"owner": "U05", "approver": "U02"},
    "13": {"owner": "U06", "approver": "U02"},
    "14": {"owner": "U04", "approver": "U11"},
    "15": {"owner": "U02", "approver": "U01"},
}

EQUIP_BUDGETS = {
    "STR-PRI": {"mass": 35.0, "power": 0, "qty": 1, "mat": "measured", "trl": 8},
    "STR-SEC": {"mass": 8.0, "power": 0, "qty": 1, "mat": "measured", "trl": 7},
    "STR-IFR": {"mass": 4.5, "power": 0, "qty": 1, "mat": "qualified", "trl": 9},
    "EPS-SA":  {"mass": 12.0, "power": 0, "qty": 2, "mat": "measured", "trl": 7},
    "EPS-BAT": {"mass": 18.0, "power": 0, "qty": 1, "mat": "measured", "trl": 8},
    "EPS-PCDU":{"mass": 6.0, "power": 15, "qty": 1, "mat": "estimate", "trl": 5},
    "AOCS-STR":{"mass": 2.8, "power": 12, "qty": 2, "mat": "qualified", "trl": 9},
    "AOCS-SS": {"mass": 0.15, "power": 0.5, "qty": 4, "mat": "qualified", "trl": 9},
    "AOCS-RW": {"mass": 1.8, "power": 10, "qty": 4, "mat": "measured", "trl": 7},
    "AOCS-MT": {"mass": 0.6, "power": 3, "qty": 3, "mat": "measured", "trl": 7},
    "COM-SBT": {"mass": 3.5, "power": 25, "qty": 1, "mat": "estimate", "trl": 5},
    "COM-SBR": {"mass": 3.5, "power": 0, "qty": 1, "mat": "estimate", "trl": 5},
    "COM-SBA": {"mass": 0.4, "power": 0, "qty": 2, "mat": "qualified", "trl": 9},
    "COM-XBT": {"mass": 4.2, "power": 45, "qty": 1, "mat": "estimate", "trl": 4},
    "COM-XBA": {"mass": 1.8, "power": 0, "qty": 1, "mat": "measured", "trl": 6},
    "CDH-OBC": {"mass": 3.0, "power": 18, "qty": 1, "mat": "measured", "trl": 7},
    "CDH-MMU": {"mass": 1.5, "power": 8, "qty": 1, "mat": "measured", "trl": 7},
    "CDH-RTU": {"mass": 0.8, "power": 5, "qty": 2, "mat": "estimate", "trl": 5},
    "TCS-MLI": {"mass": 5.0, "power": 0, "qty": 1, "mat": "measured", "trl": 8},
    "TCS-HTR": {"mass": 1.2, "power": 30, "qty": 1, "mat": "estimate", "trl": 6},
    "TCS-RAD": {"mass": 3.5, "power": 0, "qty": 1, "mat": "measured", "trl": 7},
    "TCS-HP":  {"mass": 0.5, "power": 0, "qty": 4, "mat": "qualified", "trl": 9},
    "PROP-THR":{"mass": 0.8, "power": 15, "qty": 4, "mat": "estimate", "trl": 4},
    "PROP-TNK":{"mass": 8.0, "power": 0, "qty": 1, "mat": "measured", "trl": 7},
    "PROP-PR": {"mass": 0.6, "power": 0, "qty": 1, "mat": "qualified", "trl": 9},
    "PROP-FDV":{"mass": 0.3, "power": 0, "qty": 1, "mat": "qualified", "trl": 8},
    "PL-OPT":  {"mass": 25.0, "power": 60, "qty": 1, "mat": "estimate", "trl": 4},
    "PL-ELEC": {"mass": 8.0, "power": 35, "qty": 1, "mat": "estimate", "trl": 4},
    "HRN-ELC": {"mass": 15.0, "power": 0, "qty": 1, "mat": "estimate", "trl": 6},
}

# (Constant removed, propellant_kg is now mission-specific)

def mock_product_tree_flat():
    nodes = [
        {"id": "1", "code": "SAT", "name": "BEPI-SAT", "level": "satellite", "parent_id": None},
        {"id": "10", "code": "STR", "name": "Structure", "level": "subsystem", "parent_id": "1", "subsystem_type": "STR"},
        {"id": "20", "code": "EPS", "name": "Electrical Power", "level": "subsystem", "parent_id": "1", "subsystem_type": "EPS"},
        {"id": "30", "code": "AOCS", "name": "Attitude & Orbit Control", "level": "subsystem", "parent_id": "1", "subsystem_type": "AOCS"},
        {"id": "40", "code": "COM", "name": "Communications", "level": "subsystem", "parent_id": "1", "subsystem_type": "COM"},
        {"id": "50", "code": "CDH", "name": "Command & Data Handling", "level": "subsystem", "parent_id": "1", "subsystem_type": "CDH"},
        {"id": "60", "code": "TCS", "name": "Thermal Control", "level": "subsystem", "parent_id": "1", "subsystem_type": "TCS"},
        {"id": "70", "code": "PROP", "name": "Propulsion", "level": "subsystem", "parent_id": "1", "subsystem_type": "PROP"},
        {"id": "80", "code": "PL", "name": "Payload", "level": "subsystem", "parent_id": "1", "subsystem_type": "PL"},
        {"id": "90", "code": "HRN", "name": "Harness", "level": "subsystem", "parent_id": "1", "subsystem_type": "HRN"},
        {"id": "101", "code": "STR-PRI", "name": "Primary Structure", "level": "equipment", "parent_id": "10"},
        {"id": "102", "code": "STR-SEC", "name": "Secondary Structure", "level": "equipment", "parent_id": "10"},
        {"id": "103", "code": "STR-IFR", "name": "Interface Ring", "level": "equipment", "parent_id": "10"},
        {"id": "201", "code": "EPS-SA", "name": "Solar Array (6U)", "level": "equipment", "parent_id": "20"},
        {"id": "202", "code": "EPS-BAT", "name": "Li-ion Battery Pack", "level": "equipment", "parent_id": "20"},
        {"id": "203", "code": "EPS-PCDU", "name": "PCDU", "level": "equipment", "parent_id": "20"},
        {"id": "301", "code": "AOCS-STR", "name": "Star Tracker", "level": "equipment", "parent_id": "30"},
        {"id": "302", "code": "AOCS-SS", "name": "Sun Sensor", "level": "equipment", "parent_id": "30"},
        {"id": "303", "code": "AOCS-RW", "name": "Reaction Wheel", "level": "equipment", "parent_id": "30"},
        {"id": "304", "code": "AOCS-MT", "name": "Magnetorquer", "level": "equipment", "parent_id": "30"},
        {"id": "401", "code": "COM-SBT", "name": "S-Band Transponder (nom.)", "level": "equipment", "parent_id": "40"},
        {"id": "405", "code": "COM-SBR", "name": "S-Band Transponder (red.)", "level": "equipment", "parent_id": "40"},
        {"id": "402", "code": "COM-SBA", "name": "S-Band Antenna", "level": "equipment", "parent_id": "40"},
        {"id": "403", "code": "COM-XBT", "name": "X-Band Transmitter", "level": "equipment", "parent_id": "40"},
        {"id": "404", "code": "COM-XBA", "name": "X-Band Antenna", "level": "equipment", "parent_id": "40"},
        {"id": "501", "code": "CDH-OBC", "name": "On-Board Computer", "level": "equipment", "parent_id": "50"},
        {"id": "502", "code": "CDH-MMU", "name": "Mass Memory Unit", "level": "equipment", "parent_id": "50"},
        {"id": "503", "code": "CDH-RTU", "name": "Remote Terminal Unit", "level": "equipment", "parent_id": "50"},
        {"id": "601", "code": "TCS-MLI", "name": "MLI Blankets", "level": "equipment", "parent_id": "60"},
        {"id": "602", "code": "TCS-HTR", "name": "Heater Lines", "level": "equipment", "parent_id": "60"},
        {"id": "603", "code": "TCS-RAD", "name": "Radiator Panel", "level": "equipment", "parent_id": "60"},
        {"id": "604", "code": "TCS-HP", "name": "Heat Pipe", "level": "equipment", "parent_id": "60"},
        {"id": "701", "code": "PROP-THR", "name": "Thruster", "level": "equipment", "parent_id": "70"},
        {"id": "702", "code": "PROP-TNK", "name": "Propellant Tank", "level": "equipment", "parent_id": "70"},
        {"id": "703", "code": "PROP-PR", "name": "Pressure Regulator", "level": "equipment", "parent_id": "70"},
        {"id": "704", "code": "PROP-FDV", "name": "Fill & Drain Valve", "level": "equipment", "parent_id": "70"},
        {"id": "801", "code": "PL-OPT", "name": "Optical Instrument", "level": "equipment", "parent_id": "80"},
        {"id": "802", "code": "PL-ELEC", "name": "Payload Electronics", "level": "equipment", "parent_id": "80"},
        {"id": "901", "code": "HRN-ELC", "name": "Electrical Harness", "level": "equipment", "parent_id": "90"},
    ]
    return nodes

def mock_requirements():
    return [
        RequirementData("1", "SH-FUN-001", "stakeholder", "functional", "Earth observation imagery", "System shall provide optical imagery at 5 m GSD", verification_method="review", verification_status="passed"),
        RequirementData("2", "MIS-FUN-001", "mission", "functional", "Orbit maintenance", "Satellite shall maintain SSO at 550 km +/- 10 km", parent_id="1", verification_method="analysis", verification_status="passed"),
        RequirementData("3", "SYS-FUN-001", "system", "functional", "Payload data downlink", "System shall downlink 2 Gbit/orbit via X-band", parent_id="2", verification_method="test", verification_status="in_progress", allocated_to=["COM"]),
        RequirementData("4", "SYS-PER-001", "system", "performance", "Pointing accuracy", "System pointing accuracy shall be < 0.1 deg (3-sigma)", parent_id="1", verification_method="test", verification_status="in_progress", allocated_to=["AOCS"]),
        RequirementData("5", "SYS-PER-002", "system", "performance", "Pointing stability", "System shall provide < 5 arcsec jitter over 1 s integration", parent_id="4", verification_method="analysis", verification_status="not_started", allocated_to=["AOCS"]),
        RequirementData("6", "SYS-ENV-001", "system", "environmental", "Radiation tolerance", "All electronics shall withstand 20 krad TID", parent_id="1", verification_method="analysis", verification_status="not_started", allocated_to=["CDH", "EPS"]),
        RequirementData("7", "SYS-DES-001", "system", "design", "Mass budget", "Total wet mass shall not exceed 350 kg", parent_id="1", verification_method="analysis", verification_status="passed"),
        RequirementData("8", "SYS-DES-002", "system", "design", "Power budget", "Average power consumption shall not exceed 500 W", parent_id="1", verification_method="analysis", verification_status="passed", allocated_to=["EPS"]),
        RequirementData("9", "SYS-REL-001", "system", "reliability", "Mission lifetime", "Mission lifetime shall be >= 5 years", parent_id="1", verification_method="analysis", verification_status="in_progress"),
        RequirementData("10", "SUB-FUN-001", "subsystem", "functional", "EPS charge management", "EPS shall maintain battery SoC > 30%", parent_id="8", verification_method="test", verification_status="not_started", allocated_to=["EPS"]),
        RequirementData("11", "SUB-FUN-002", "subsystem", "functional", "AOCS safe mode", "AOCS shall transition to safe mode within 10 s of anomaly", parent_id="4", verification_method="demonstration", verification_status="passed", allocated_to=["AOCS"]),
        RequirementData("12", "SUB-PER-001", "subsystem", "performance", "S-Band link margin", "TTC link margin shall be >= 6 dB", parent_id="3", verification_method="analysis", verification_status="passed", allocated_to=["COM"]),
        RequirementData("13", "SUB-IFC-001", "subsystem", "interface", "SpaceWire bus", "CDH shall provide SpaceWire interface at 200 Mbps", parent_id="1", verification_method="test", verification_status="in_progress", allocated_to=["CDH"]),
        RequirementData("14", "EQP-DES-001", "equipment", "design", "Star tracker FOV", "Star tracker FOV shall be >= 20 x 20 deg", parent_id="4", verification_method="inspection", verification_status="passed", allocated_to=["AOCS-STR"]),
        RequirementData("15", "SYS-SAF-001", "system", "safety", "Passivation", "Satellite shall passivate all energy sources at EOL", parent_id="1", verification_method="review", verification_status="not_started"),
    ]

def mock_risks():
    return [
        RiskItemData("1", "RSK-001", "Solar array deployment failure", "Single-point failure on SA hinge mechanism", "technical", 2, 5, "open", "EPS Lead", "Redundant hinge + deployment test", 1, 4),
        RiskItemData("2", "RSK-002", "Radiation-induced latchup", "SEL on OBC FPGA in SAA region", "technical", 3, 4, "mitigating", "CDH Lead", "Rad-hard FPGA + watchdog", 2, 3),
        RiskItemData("3", "RSK-003", "Launch delay", "Launcher manifest slip > 6 months", "schedule", 3, 3, "open", "PM", "Backup launch slot reserved"),
        RiskItemData("4", "RSK-004", "Propulsion leak", "Propellant leak at fill/drain valve", "technical", 2, 5, "mitigating", "PROP Lead", "Redundant seals + leak test", 1, 4),
        RiskItemData("5", "RSK-005", "Star tracker blinding", "Sun intrusion in STR FOV during manoeuvre", "technical", 3, 3, "open", "AOCS Lead", "Sun exclusion angle + gyro propagation"),
        RiskItemData("6", "RSK-006", "Budget overrun", "Component cost increase > 15%", "cost", 2, 3, "accepted", "PM", "Cost contingency 20%"),
        RiskItemData("7", "RSK-007", "Thermal runaway in battery", "Li-ion cell thermal runaway", "technical", 1, 5, "mitigating", "EPS Lead", "Cell-level fuses + TCS monitoring", 1, 3),
        RiskItemData("8", "RSK-008", "Ground station unavailability", "Primary GS downtime > 24 h", "external", 2, 2, "open", "OPS Lead", "Backup GS agreement"),
    ]

def mock_fmeca():
    entries = [
        FMECAEntryData("1", "EPS-SA", "Cell string open circuit", "Micrometeorite impact", "Reduced power", "Degraded mission", 3, 2, 3, "String bypass diode"),
        FMECAEntryData("2", "EPS-BAT", "Cell thermal runaway", "Internal short", "Battery loss", "Mission loss (single battery)", 5, 1, 2, "Cell-level fuse, TCS monitoring"),
        FMECAEntryData("3", "AOCS-RW", "Bearing seizure", "Lubricant degradation", "Wheel loss", "Degraded pointing (3-wheel mode)", 3, 2, 4, "4th wheel redundancy"),
        FMECAEntryData("4", "COM-SBT", "Transponder failure", "Power amplifier burnout", "No TTC on nominal", "Switchover to COM-SBR", 4, 1, 3, "Redundant transponder (cold spare)"),
        FMECAEntryData("5", "CDH-OBC", "SEL latchup", "Heavy ion strike", "OBC reset", "Temporary loss of control", 4, 3, 2, "Watchdog + rad-hard design"),
        FMECAEntryData("6", "PROP-THR", "Valve stuck closed", "Contamination", "No thrust on 1 thruster", "Reduced delta-V capability", 3, 2, 3, "Quad redundancy"),
        FMECAEntryData("7", "TCS-HTR", "Heater line open", "Wire fatigue", "Cold spot", "Component below survival temp", 4, 2, 3, "Redundant heater circuit"),
        FMECAEntryData("8", "PL-OPT", "Detector degradation", "Radiation damage", "Noise increase", "Image quality degradation", 3, 3, 3, "Annealing cycle"),
        FMECAEntryData("9", "AOCS-STR", "Star tracker blinding", "Sun intrusion", "No attitude fix", "Safe mode entry", 3, 3, 2, "Sun exclusion + gyro backup"),
        FMECAEntryData("10", "EPS-PCDU", "MOSFET short", "Over-current", "Bus anomaly", "Partial power loss", 4, 2, 3, "Current limiters + redundant switches"),
    ]
    for e in entries:
        e.criticality = compute_criticality(e.severity, e.occurrence)
    return entries

def mock_tasks():
    return [
        TaskData("T01", "System Requirements Definition", 60, [], progress_pct=100, wbs_code="1.1", assigned_to="L. Bianchi (SE)"),
        TaskData("T02", "Preliminary Design - STR", 45, ["T01"], progress_pct=80, wbs_code="1.2.1", assigned_to="D. Colombo (STR)"),
        TaskData("T03", "Preliminary Design - EPS", 45, ["T01"], progress_pct=75, wbs_code="1.2.2", assigned_to="A. Ferrari (EPS)"),
        TaskData("T04", "Preliminary Design - AOCS", 40, ["T01"], progress_pct=70, wbs_code="1.2.3", assigned_to="G. Conti (AOCS)"),
        TaskData("T05", "Preliminary Design - COM", 40, ["T01"], progress_pct=65, wbs_code="1.2.4", assigned_to="S. Moretti (COM)"),
        TaskData("T06", "Preliminary Design - CDH", 35, ["T01"], progress_pct=60, wbs_code="1.2.5", assigned_to="P. Russo (CDH)"),
        TaskData("T07", "Preliminary Design - PL", 50, ["T01"], progress_pct=55, wbs_code="1.2.6", assigned_to="C. Marino (PL)"),
        TaskData("T08", "System-level Budgets & Margins", 30, ["T02", "T03", "T04", "T05", "T06", "T07"], progress_pct=20, wbs_code="1.3", assigned_to="L. Bianchi (SE)"),
        TaskData("T09", "Verification Plan", 25, ["T08"], progress_pct=0, wbs_code="1.4", assigned_to="R. Greco (QA)"),
        TaskData("T10", "PDR Preparation", 20, ["T08", "T09"], progress_pct=0, wbs_code="1.5", assigned_to="L. Bianchi (SE)"),
        TaskData("M_SRR", "SRR", 0, ["T01"], progress_pct=100, is_milestone=True, wbs_code="M1", assigned_to="M. Rossi (PM)"),
        TaskData("M_PDR", "PDR", 0, ["T10"], progress_pct=0, is_milestone=True, wbs_code="M2", assigned_to="M. Rossi (PM)"),
        TaskData("T11", "Detailed Design", 60, ["M_PDR"], progress_pct=0, wbs_code="2.1", assigned_to="L. Bianchi (SE)"),
        TaskData("T12", "QM Procurement", 45, ["T11"], progress_pct=0, wbs_code="2.2", assigned_to="M. Rossi (PM)"),
        TaskData("T13", "CDR Preparation", 25, ["T11", "T12"], progress_pct=0, wbs_code="2.3", assigned_to="L. Bianchi (SE)"),
        TaskData("M_CDR", "CDR", 0, ["T13"], progress_pct=0, is_milestone=True, wbs_code="M3", assigned_to="M. Rossi (PM)"),
    ]

    return nodes

def _get_product_tree(force_reload=False):
    """Read product tree from session_state; reload from DB only when needed
    (first load, mission switch, explicit force_reload, or a just-added node
    awaiting reconciliation). This is called ~18x per render, so serving the
    cached tree on the common read path avoids a full-table re-read each time."""
    if "product_tree" not in st.session_state:
        st.session_state["product_tree"] = []

    mission_id = st.session_state.get("active_mission_id")
    has_pending = "_pt_just_added" in st.session_state
    if (st.session_state["product_tree"] and not force_reload
            and not has_pending
            and st.session_state.get("_pt_loaded_for") == mission_id):
        return st.session_state["product_tree"]

    # User-scoped client so RLS enforces per-mission access (was the service
    # client, which bypassed RLS entirely — audit S4).
    client = get_supabase()

    if DB_ENFORCED and not client:
        st.error("🚫 Database connection required in this mode. Please configure Supabase credentials.")
        st.stop()

    if client and mission_id:
        try:
            result = client.table("product_tree_nodes").select("*").eq("mission_id", mission_id).execute()
            st.session_state["_pt_loaded_for"] = mission_id

            if result.data:
                # Build tree from DB data
                db_tree = []
                for node in result.data:
                    db_tree.append({
                        "id": str(node.get("id", "")),
                        "uuid": str(node.get("id", "")),
                        "parent_id": str(node.get("parent_id")) if node.get("parent_id") else None,
                        "level": node.get("level", "subsystem"),
                        "code": node.get("code", ""),
                        "name": node.get("name", ""),
                        "subsystem_type": node.get("subsystem_type"),
                        "is_leaf": node.get("is_leaf", False),
                        "quantity": node.get("quantity", 1),
                        "trl": node.get("trl", 1),
                        "status": node.get("status", "proposed"),
                    })
                
                # Only update if we have data from DB
                if db_tree:
                    # If we just added a node locally and the DB doesn't see it yet
                    # (e.g. RLS lag, replication, or the row was just inserted in
                    # the same rerun), preserve the local pending node instead of
                    # clobbering it.
                    pending = st.session_state.pop("_pt_just_added", None)
                    if pending:
                        local_ids = {str(n.get("id")) for n in st.session_state.get("product_tree", [])}
                        already_in_db = any(
                            str(n.get("code")) == pending.get("code")
                            for n in db_tree
                        )
                        if not already_in_db:
                            # keep the just-added local node on top of DB tree
                            new_node = {
                                "id": pending.get("local_id", ""),
                                "uuid": "",
                                "parent_id": None,
                                "level": pending.get("level", "subsystem"),
                                "code": pending.get("code", ""),
                                "name": pending.get("name", ""),
                                "subsystem_type": None,
                                "is_leaf": False,
                                "quantity": 1,
                                "trl": 1,
                                "status": "proposed",
                            }
                            db_tree.append(new_node)
                    st.session_state["product_tree"] = db_tree
                
        except Exception as e:
            st.error(f"🚫 Product tree DB load failed: {e}")
            st.stop()
    
    return st.session_state["product_tree"]

def _get_equip_budgets():
    """Read equip budgets from session_state, load from DB if empty."""
    if "equip_budgets" not in st.session_state:
        st.session_state["equip_budgets"] = {}
    
    # Load budgets from DB if session is empty
    if not st.session_state["equip_budgets"]:
        client = get_supabase()  # user-scoped: RLS enforces access (audit S4)
        mission_id = st.session_state.get("active_mission_id")
        
        if client and mission_id:
            try:
                # Get all equipment nodes for this mission
                nodes_result = client.table("product_tree_nodes").select("id, code, level").eq("mission_id", mission_id).eq("level", "equipment").execute()
                
                if nodes_result.data:
                    for node in nodes_result.data:
                        code = node.get("code", "")
                        node_id = node.get("id")
                        
                        # Get mass and power budgets for this node
                        budgets_result = client.table("budgets").select("budget_type, nominal_value").eq("node_id", node_id).execute()
                        
                        mass_val = 0.0
                        power_val = 0
                        
                        if budgets_result.data:
                            for b in budgets_result.data:
                                if b.get("budget_type") == "mass_kg":
                                    mass_val = float(b.get("nominal_value", 0))
                                elif b.get("budget_type") == "power_w":
                                    power_val = float(b.get("nominal_value", 0))
                        
                        if code:
                            st.session_state["equip_budgets"][code] = {
                                "mass": mass_val,
                                "power": power_val,
                                "qty": 1,
                                "mat": "estimate",
                                "trl": 1
                            }
            except Exception as e:
                st.error(f"Caricamento budget dal DB fallito: {e}")
    
    return st.session_state["equip_budgets"]


# --- Process product tree actions from the URL (legacy path, kept for
# backward compatibility with older clients that still navigate). The
# primary path now is the pt_bridge component (postMessage) handled inside
# page_product_tree(). ---
if "pt_action" in st.query_params:
    import json
    import urllib.parse
    import logging as _pt_log
    action = st.query_params.get("pt_action")
    try:
        data_str = st.query_params.get("pt_data", "{}")
        data = json.loads(urllib.parse.unquote(data_str))
    except Exception as _pt_ex:
        data = {}
        _pt_log.warning("pt_action: failed to parse pt_data: %s", _pt_ex)

    st.query_params.clear()
    _pt_log.info("pt_action=%s data=%s (legacy URL path)", action, data)

    flat = _get_product_tree()
    eb = _get_equip_budgets()
    _process_product_tree_action(action, data, flat, eb)
    st.rerun()


def _build_budget_tree():
    flat = _get_product_tree()
    eb = _get_equip_budgets()
    children_map: dict[str, list] = {}
    node_map: dict[str, dict] = {}
    for n in flat:
        node_map[n["id"]] = n
        pid = n.get("parent_id")
        if pid:
            children_map.setdefault(pid, []).append(n["id"])

    root_ids = [n["id"] for n in flat if n.get("parent_id") is None]

    def _subtree(nid):
        n = node_map[nid]
        cids = children_map.get(nid, [])
        allocs = []
        if not cids:
            b = eb.get(n["code"], {})
            if b:
                allocs.append(BudgetAllocationData(
                    node_id=nid, node_code=n["code"], node_name=n["name"],
                    budget_type="mass_kg", operating_mode=None,
                    nominal_value=b["mass"], quantity=b["qty"],
                    maturity=b["mat"], margin_pct=0,
                ))
                allocs.append(BudgetAllocationData(
                    node_id=nid, node_code=n["code"], node_name=n["name"],
                    budget_type="power_w", operating_mode="nominal",
                    nominal_value=b["power"], quantity=b["qty"],
                    maturity=b["mat"], margin_pct=0,
                ))
        return {
            "node": {"code": n["code"], "name": n["name"], "level": n["level"], "quantity": n.get("quantity", 1)},
            "allocations": allocs,
            "children": [_subtree(cid) for cid in cids],
        }

    if not root_ids:
        return {"node": {"code": "MISSION", "name": "Mission", "level": "mission", "quantity": 1}, "allocations": [], "children": []}
    if len(root_ids) == 1:
        return _subtree(root_ids[0])
    return {
        "node": {"code": "MISSION", "name": "Mission System", "level": "mission", "quantity": 1},
        "allocations": [],
        "children": [_subtree(rid) for rid in root_ids],
    }





def _normalize_fmeca_entries():
    """🔴 P3 FIX: Normalize FMECA node_id from code to UUID"""
    if "fmeca_entries" not in st.session_state or "product_tree" not in st.session_state:
        return
    
    entries = st.session_state["fmeca_entries"]
    tree = st.session_state["product_tree"]
    code_to_uuid = {n["code"]: n.get("id") for n in tree if n.get("code")}
    
    for e in entries:
        # If node_id looks like a code (contains dash or matches product_tree codes), convert to UUID
        if e.node_id in code_to_uuid:
            e.node_id = code_to_uuid[e.node_id]


def _get_mock_team():
    return [
        {"id": "U00", "name": "Admin", "role": "ADMIN", "email": "admin@bepi.eu", "org": "Prime"},
        {"id": "U01", "name": "M. Rossi", "role": "PM", "email": "rossi@bepi.eu", "org": "Prime"},
        {"id": "U02", "name": "L. Bianchi", "role": "SE", "email": "bianchi@bepi.eu", "org": "Prime"},
        {"id": "U03", "name": "A. Ferrari", "role": "SSL", "email": "ferrari@bepi.eu", "org": "Prime", "subsystem": "EPS"},
        {"id": "U04", "name": "G. Conti", "role": "SSL", "email": "conti@bepi.eu", "org": "Prime", "subsystem": "AOCS"},
        {"id": "U05", "name": "S. Moretti", "role": "SSL", "email": "moretti@bepi.eu", "org": "SubCon-A", "subsystem": "COM"},
        {"id": "U06", "name": "P. Russo", "role": "SSL", "email": "russo@bepi.eu", "org": "Prime", "subsystem": "CDH"},
        {"id": "U07", "name": "F. Romano", "role": "SSL", "email": "romano@bepi.eu", "org": "Prime", "subsystem": "TCS"},
        {"id": "U08", "name": "D. Colombo", "role": "SSL", "email": "colombo@bepi.eu", "org": "Prime", "subsystem": "STR"},
        {"id": "U09", "name": "E. Ricci", "role": "SSL", "email": "ricci@bepi.eu", "org": "SubCon-B", "subsystem": "PROP"},
        {"id": "U10", "name": "C. Marino", "role": "SSL", "email": "marino@bepi.eu", "org": "SubCon-C", "subsystem": "PL"},
        {"id": "U11", "name": "R. Greco", "role": "QA", "email": "greco@bepi.eu", "org": "Prime"},
        {"id": "U12", "name": "N. Costa", "role": "CM", "email": "costa@bepi.eu", "org": "Prime"},
        {"id": "U13", "name": "V. Bruno", "role": "AIT", "email": "bruno@bepi.eu", "org": "Prime"},
    ]


def _default_mission_data(name="BEPI-SAT", with_demo=True):
    if with_demo:
        return {
            "name": name, "description": "LEO Earth Observation SmallSat",
            "tasks": mock_tasks(), "requirements": mock_requirements(), "risks": mock_risks(),
            "approval_log": list(APPROVAL_LOG), "req_ownership": dict(REQ_OWNERSHIP),
            "task_assignments": dict(TASK_ASSIGNMENTS), "risk_overrides": {},
            "product_tree": mock_product_tree_flat(), "equip_budgets": dict(EQUIP_BUDGETS),
            "warehouse_items": None, "procurement_orders": None,
            "mission_phase": "B2", "mission_framework": "ESA",
            "team_members": _get_mock_team(),
            "fmeca_entries": mock_fmeca(),
            "propellant_kg": 25.0,
        }
    return {
        "name": name, "description": "",
        "tasks": [], "requirements": [], "risks": [],
        "approval_log": [], "req_ownership": {}, "task_assignments": {},
        "risk_overrides": {},
        "product_tree": [{"id": "0", "code": "SAT", "name": name, "level": "satellite", "parent_id": None}],
        "equip_budgets": {},
        "warehouse_items": None, "procurement_orders": None,
        "mission_phase": "0", "mission_framework": "ESA",
        "team_members": [],
        "fmeca_entries": [],
        "propellant_kg": 0.0,
    }


def _save_current_mission():
    mid = st.session_state.get("active_mission_id")
    if mid is None or "missions" not in st.session_state:
        return
    m = st.session_state.missions[mid]
    for key in _MISSION_DATA_KEYS:
        if key in st.session_state:
            m[key] = st.session_state[key]

def _map_mission(row: dict) -> dict:
    meta = row.get("metadata", {}) or {}
    return {
        "id": row["id"],
        "name": row["name"],
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


def _mission_from_db_row(row: dict) -> dict:
    mission = _default_mission_data(row.get("name", "Mission"), with_demo=False)
    mission.update(_map_mission(row))
    return mission


def _current_user_member() -> dict:
    user = st.session_state.get("user", {}) or {}
    return {
        "id": user.get("id", "U00"),
        "name": user.get("full_name") or user.get("email") or "You",
        "email": user.get("email", ""),
        "role": user.get("role", "PM") if user.get("role") in ROLES else "PM",
        "org": user.get("org", ""),
    }


def _activate_local_mission(mission_id: str, mission: dict) -> None:
    st.session_state.active_mission_id = mission_id
    st.session_state["_loaded_mission_id"] = mission_id
    st.session_state.missions[mission_id] = mission
    for key in _MISSION_DATA_KEYS:
        if key in mission:
            st.session_state[key] = mission[key]
        elif key in st.session_state:
            del st.session_state[key]

def _load_mission(mid: str):
    if not mid:
        return
    st.session_state.active_mission_id = mid
    
    # Try to load from DB if DB is enforced
    if DB_ENFORCED:
        try:
            data = load_mission_data(mid)
            if data:
                for key, val in data.items():
                    if key == "missions":
                        st.session_state.missions.update(val)
                    else:
                        st.session_state[key] = val
                st.session_state["_loaded_mission_id"] = mid
                return
            st.error("🚫 Database mission load failed: no mission data returned from DB.")
            st.stop()
        except Exception as exc:
            st.error(f"🚫 Database mission load failed: {exc}")
            st.stop()
# Onboarding check for new users
_has_local_mission = bool(st.session_state.get("active_mission_id")) and bool(st.session_state.get("missions"))
_onboarding_done = bool(st.session_state.get("_onboarding_completed")) or _has_local_mission
if HAS_SUPABASE and (st.session_state.get("ob_step") or (not _onboarding_done and check_onboarding_needed(user.get("id")))):
    render_onboarding()
    st.stop()

# Pre-init missions with minimal data only when offline / DB is not enforced
if not DB_ENFORCED:
    if "missions" not in st.session_state:
        st.session_state.missions = {"my-mission": {"name": "My Mission", "description": "New project"}}
        st.session_state.active_mission_id = "my-mission"
        st.session_state._missions_need_init = True

with st.sidebar:
    st.markdown(
        "<div style='text-align:center; padding: 10px 0 5px 0;'>"
        # Orbital ring SVG inspired by BepiColombo trajectory arcs
        "<svg width='90' height='90' viewBox='0 0 120 120' xmlns='http://www.w3.org/2000/svg'>"
        "<defs><linearGradient id='g1' x1='0%' y1='0%' x2='100%' y2='100%'>"
        "<stop offset='0%' style='stop-color:#4da6ff;stop-opacity:0.9'/>"
        "<stop offset='100%' style='stop-color:#2ecc71;stop-opacity:0.9'/>"
        "</linearGradient></defs>"
        # Elliptical orbit rings (BepiColombo transfer arcs feel)
        "<ellipse cx='60' cy='60' rx='52' ry='20' fill='none' stroke='url(#g1)' stroke-width='1.5' opacity='0.4' transform='rotate(-25 60 60)'/>"
        "<ellipse cx='60' cy='60' rx='52' ry='20' fill='none' stroke='url(#g1)' stroke-width='1.5' opacity='0.3' transform='rotate(25 60 60)'/>"
        "<ellipse cx='60' cy='60' rx='48' ry='16' fill='none' stroke='url(#g1)' stroke-width='1' opacity='0.2' transform='rotate(65 60 60)'/>"
        # Central body (planet/spacecraft)
        "<circle cx='60' cy='60' r='8' fill='url(#g1)' opacity='0.6'/>"
        "<circle cx='60' cy='60' r='4' fill='white' opacity='0.8'/>"
        # Small satellite dot on orbit
        "<circle cx='98' cy='48' r='3' fill='#4da6ff' opacity='0.9'/>"
        "<circle cx='98' cy='48' r='1.5' fill='white' opacity='0.7'/>"
        "</svg>"
        "<h1 style='font-size:2.2rem; margin:2px 0 0 0; letter-spacing: 5px; "
        "font-weight: 300; color: #e0e0e0;'>"
        "<span style='font-weight:600; color:#4da6ff;'>B</span>."
        "<span style='font-weight:600; color:#45b7d1;'>E</span>."
        "<span style='font-weight:600; color:#3bc49f;'>P</span>."
        "<span style='font-weight:600; color:#2ecc71;'>I</span>.</h1>"
        "<p style='font-size:0.55rem; opacity:0.45; margin-top:6px; letter-spacing: 2px; line-height:1.6;'>"
        "BUDGET &middot; ENGINEERING<br>PROJECT &middot; INTEGRATION</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    page = option_menu(
        None,
        ["Overview", "Product Tree", "Budgets", "Requirements", "Risks", "Schedule", "ECSS", "Reports", "Integrations", "Warehouse", "Team"],
        icons=["rocket-takeoff", "diagram-3", "bar-chart-fill", "list-check",
               "exclamation-triangle-fill", "calendar3", "book", "file-earmark-pdf-fill", "plug-fill", "box-seam", "people-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"color": "#3498db", "font-size": "16px"},
            "nav-link": {
                "font-size": "13px", "text-align": "left", "margin": "1px 0",
                "padding": "8px 12px", "border-radius": "8px", "--hover-color": "rgba(52,152,219,0.15)",
            },
            "nav-link-selected": {"background-color": "rgba(52,152,219,0.25)", "font-weight": "600"},
        },
    )

    # --- Mission selector ---
    if HAS_SUPABASE:
        user = st.session_state.get("user", {})
        user_id = user.get("id")
        if user_id and ("_missions_loaded" not in st.session_state or st.session_state.get("_current_user_id") != user_id):
            db_missions = load_missions_for_user(user_id)
            st.session_state.missions = {m["id"]: _mission_from_db_row(m) for m in db_missions}
            st.session_state["_missions_loaded"] = True
            st.session_state["_current_user_id"] = user_id

        missions = st.session_state.get("missions", {})
        mission_ids = list(missions.keys())
        active_mid = st.session_state.get("active_mission_id") or (mission_ids[0] if mission_ids else None)

        if not mission_ids:
            if DB_ENFORCED:
                st.warning("No missions found in the database. Create a mission from the Settings panel or complete onboarding.")
                st.stop()
            st.session_state.missions["my-mission"] = _default_mission_data("My Mission", with_demo=False)
            st.session_state.active_mission_id = "my-mission"
            missions = st.session_state.missions
            mission_ids = list(missions.keys())
            active_mid = "my-mission"

        mission_labels = {mid: missions[mid].get("name", mid) for mid in mission_ids}

    sac.divider(label="User", align="center", color="gray")
    if HAS_SUPABASE:
        user_session = st.session_state.get("user", {})
        user_session.setdefault("role", "ADMIN")
        current_user = user_session
        user_name = current_user.get("full_name", "User")
        user_email = current_user.get("email", "")
        st.markdown(f"<div style='text-align:center; font-size:0.8rem; color:#e0e0e0;'>{user_name}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center; font-size:0.6rem; opacity:0.6;'>{user_email}</div>", unsafe_allow_html=True)
        
        # Logout and Settings buttons in same row
        c_logout, c_settings = st.columns(2)
        with c_logout:
            if st.button("🚪 Logout", key="_logout_btn"):
                logout()
        with c_settings:
            if st.button("⚙️ Settings", key="btn_toggle_settings"):
                st.session_state.show_settings = not st.session_state.show_settings
    else:
        user_names = [f"{m['name']} ({m['role']})" for m in TEAM_MEMBERS]
        current_user_idx = st.selectbox("Logged in as", range(len(user_names)), format_func=lambda i: user_names[i], index=0, key="user_select")
        current_user = TEAM_MEMBERS[current_user_idx]

    if not HAS_SUPABASE and current_user.get("role") in ("ADMIN", "PM"):
        pass

# Main content starts here

# Initialize settings toggle state
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False

# Warning banner if DB is not working
if DB_ENFORCED and not HAS_SUPABASE:
    st.error("⚠️ **Database Connection Error**: Your current session is not saving data to the database. Changes will be lost when you refresh the page.")
elif DB_ENFORCED:
    pass  # DB is working

# Settings panel (main content)
if st.session_state.get("show_settings", False):
    with st.container(border=True):
        st.markdown("### ⚙️ Settings")
        
        st.markdown("#### Active Mission")
        all_mission_ids = list(missions.keys())
        mission_labels = {mid: missions[mid]["name"] for mid in all_mission_ids}
        
        sel_mid = st.selectbox(
            "Select Mission", all_mission_ids,
            index=all_mission_ids.index(active_mid) if active_mid in all_mission_ids else 0,
            format_func=lambda mid: mission_labels[mid], key="_settings_mission_select",
        )
        if sel_mid != active_mid:
            _save_current_mission()
            _load_mission(sel_mid)
            st.rerun()
        
        # Manage all missions button
        if "show_manage_missions" not in st.session_state:
            st.session_state.show_manage_missions = False
        
        if st.button("📋 Manage all missions", key="btn_manage_all_missions"):
            st.session_state.show_manage_missions = not st.session_state.show_manage_missions
        
        if st.session_state.show_manage_missions:
            st.markdown("##### All Missions")
            for mid in all_mission_ids:
                m_name = missions[mid].get("name", mid)
                is_active = mid == active_mid
                
                m_col1, m_col2, m_col3 = st.columns([3, 1, 1])
                with m_col1:
                    st.markdown(f"**{m_name}**" + (" *(active)*" if is_active else ""))
                with m_col2:
                    if st.button("✏️", key=f"edit_{mid}", help="Edit mission name"):
                        st.session_state.edit_mission_id = mid
                        st.rerun()
                with m_col3:
                    if len(all_mission_ids) > 1:
                        if st.button("🗑️", key=f"del_{mid}", help="Delete mission"):
                            st.session_state.delete_mission_id = mid
                            st.rerun()
                    else:
                        st.write("")
            
            # Edit mission modal
            if "edit_mission_id" in st.session_state and st.session_state.edit_mission_id:
                edit_mid = st.session_state.edit_mission_id
                with st.expander("✏️ Edit Mission", expanded=True):
                    new_name = st.text_input("Mission name", value=missions[edit_mid].get("name", ""), key=f"edit_name_{edit_mid}")
                    if st.button("Save", key=f"save_edit_{edit_mid}"):
                        if new_name and new_name != missions[edit_mid].get("name", ""):
                            missions[edit_mid]["name"] = new_name
                            st.session_state.edit_mission_id = None
                            st.session_state.show_manage_missions = False
                            st.rerun()
                    if st.button("Cancel", key=f"cancel_edit_{edit_mid}"):
                        st.session_state.edit_mission_id = None
                        st.rerun()
            
            # Delete mission modal
            if "delete_mission_id" in st.session_state and st.session_state.delete_mission_id:
                del_mid = st.session_state.delete_mission_id
                st.warning(f"Delete mission **{missions[del_mid].get('name', del_mid)}**? This cannot be undone.")
                c_del, c_canc = st.columns(2)
                with c_del:
                    if st.button("🗑️ Confirm Delete", key=f"confirm_del_{del_mid}", type="primary"):
                        if DB_ENFORCED:
                            delete_mission(del_mid)
                        if del_mid in missions:
                            del missions[del_mid]
                        remaining = list(missions.keys())
                        if remaining:
                            _load_mission(remaining[0])
                        st.session_state.delete_mission_id = None
                        st.session_state.show_manage_missions = False
                        st.rerun()
                with c_canc:
                    if st.button("Cancel", key=f"cancel_del_{del_mid}"):
                        st.session_state.delete_mission_id = None
                        st.rerun()
            
            # Delete All button - inside Manage all missions
            if "show_delete_all_confirm" not in st.session_state:
                st.session_state.show_delete_all_confirm = False
            
            if not st.session_state.show_delete_all_confirm:
                st.markdown("---")
                if st.button("🗑️ Delete All Missions", key="btn_delete_all", type="secondary"):
                    st.session_state.show_delete_all_confirm = True
                    st.rerun()
            else:
                st.markdown("---")
                st.markdown("<span style='color: #ff4b4b;'>⚠️ **This will delete ALL missions permanently!**</span>", unsafe_allow_html=True)
                confirm_text = st.text_input("Type 'Conferma' to confirm", key="confirm_delete_all_text")
                c_conf, c_abort = st.columns(2)
                with c_conf:
                    if st.button("✅ Confirm Delete All", key="btn_confirm_delete_all", type="primary"):
                        if confirm_text.strip().lower() == "conferma":
                            if DB_ENFORCED:
                                for mid in list(missions.keys()):
                                    delete_mission(mid)
                            missions.clear()
                            # Redirect to onboarding
                            st.session_state.ob_step = 1
                            st.session_state.ob_type = None
                            st.session_state.ob_name = ""
                            st.session_state.ob_desc = ""
                            st.session_state.ob_fw = "ESA"
                            st.session_state.ob_phase = "B2"
                            st.session_state.ob_alt = 550
                            st.session_state.ob_mass = 150
                            st.session_state.ob_prop = 0
                            st.session_state.ob_profile = "leo_eo"
                            st.session_state._onboarding_completed = False
                            st.session_state.show_delete_all_confirm = False
                            st.session_state.show_manage_missions = False
                            st.session_state.show_settings = False
                            st.rerun()
                        else:
                            st.error("You must type 'Conferma' exactly")
                with c_abort:
                    if st.button("Abort", key="btn_abort_delete_all"):
                        st.session_state.show_delete_all_confirm = False
                        st.rerun()

        st.markdown("---")
        st.markdown("#### ➕ Create New Mission")
        
        # Two options side by side
        c_step, c_fast = st.columns(2)
        
        with c_step:
            st.markdown("**Step by Step**")
            st.markdown("*Full onboarding wizard*")
            if st.button("📝 Create Mission step by step", key="btn_create_step_by_step", use_container_width=True):
                # Reset onboarding state to start from step 1
                st.session_state.ob_step = 1
                st.session_state.ob_type = None
                st.session_state.ob_name = ""
                st.session_state.ob_desc = ""
                st.session_state.ob_fw = "ESA"
                st.session_state.ob_phase = "B2"
                st.session_state.ob_alt = 550
                st.session_state.ob_mass = 150
                st.session_state.ob_prop = 0
                st.session_state.ob_profile = "leo_eo"
                st.session_state.onboarding_mission_type = "new"
                st.session_state.show_settings = False
                st.rerun()
        
        with c_fast:
            st.markdown("**Fast Create**")
            st.markdown("*Quick creation*")
            with st.form("create_mission_fast", clear_on_submit=True):
                new_name = st.text_input("Mission name", key="_new_mission_name_fast", placeholder="My Mission")
                c1, c2 = st.columns(2)
                with c1:
                    new_demo = st.checkbox("Demo data", value=False, key="_new_mission_demo_fast")
                with c2:
                    new_fw = st.selectbox("Framework", ["ESA", "NASA"], key="_new_mission_fw_fast")
                if st.form_submit_button("Create", type="primary"):
                    if new_name:
                        mid = new_name.lower().replace(" ", "-")
                        if DB_ENFORCED:
                            mission = add_mission(
                                name=new_name,
                                description="Created from Streamlit dashboard",
                                phase="0",
                                framework=new_fw,
                                owner_user_id=user.get("id"),
                            )
                            if mission and mission.get("id"):
                                st.session_state.active_mission_id = mission["id"]
                                _load_mission(mission["id"])
                                st.session_state.show_settings = False
                                st.rerun()
                            else:
                                st.error("Failed to create mission in database.")
                        else:
                            if mid in missions:
                                st.warning("Mission ID already exists")
                            else:
                                _save_current_mission()
                                new_data = _default_mission_data(new_name, with_demo=new_demo)
                                new_data["mission_framework"] = new_fw
                                missions[mid] = new_data
                                _load_mission(mid)
                                st.session_state.show_settings = False
                                st.rerun()
        
        if st.button("Close Settings", key="btn_close_settings"):
            st.session_state.show_settings = False
            st.rerun()
    
    # Hide main content when Settings is open
    if st.session_state.get("show_settings", False):
        st.stop()
    
    _phase = st.session_state.get("mission_phase", "B2")
    _mission = st.session_state.get("missions", {}).get(active_mid, {})
    _mission_name = _mission.get("name", "") if isinstance(_mission, dict) else missions.get(active_mid, {}).get("name", "")
    _role = current_user.get("role", "") if isinstance(current_user, dict) else ""
    _org = current_user.get("org", "") if isinstance(current_user, dict) else ""
    _role_icon = ROLES.get(_role, {}).get("icon", "")
    st.markdown(
        f"<div style='text-align:center; font-size:0.65rem; opacity:0.5; margin-top:8px;'>"
        f"{_role_icon} {_org} | {_mission_name} | Phase {_phase} | v0.2.0</div>",
        unsafe_allow_html=True,
    )

SUBSYSTEM_LEAD_MAP = {m["subsystem"]: m for m in TEAM_MEMBERS if m.get("subsystem")}

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

# Complete missions init with full data only when offline / DB is not enforced
if not DB_ENFORCED:
    if "missions" not in st.session_state:
        st.session_state.missions = {"my-mission": _default_mission_data("My Mission", with_demo=False)}
    if not st.session_state.get("active_mission_id"):
        st.session_state.active_mission_id = "my-mission"

# ---------------------------------------------------------------------------
# Session state — mutable copies for interactive editing
# ---------------------------------------------------------------------------
_active = st.session_state.missions.get(st.session_state.active_mission_id)
if not _active:
    st.warning("Please select or create a mission to get started.")
    st.stop()

if "tasks" not in st.session_state:
    st.session_state.tasks = _active.get("tasks", [])
if "requirements" not in st.session_state:
    st.session_state.requirements = _active.get("requirements", [])
if "risks" not in st.session_state:
    st.session_state.risks = _active.get("risks", [])
if "approval_log" not in st.session_state:
    st.session_state.approval_log = _active.get("approval_log", [])
if "req_ownership" not in st.session_state:
    st.session_state.req_ownership = _active.get("req_ownership", {})
if "task_assignments" not in st.session_state:
    st.session_state.task_assignments = _active.get("task_assignments", {})
if "risk_overrides" not in st.session_state:
    st.session_state.risk_overrides = _active.get("risk_overrides", {})
    st.session_state.risk_overrides = _active.get("risk_overrides", {})
if "team_members" not in st.session_state:
    st.session_state.team_members = _active.get("team_members", [])
if "fmeca_entries" not in st.session_state:
    st.session_state.fmeca_entries = _active.get("fmeca_entries", [])
if "product_tree" not in st.session_state:
    st.session_state.product_tree = _active.get("product_tree", [])

# 🔴 P3 FIX: Normalize FMECA node_id from code to UUID
_normalize_fmeca_entries()

def get_tasks():
    return st.session_state.tasks

def get_requirements():
    return st.session_state.requirements

def get_risks():
    return st.session_state.risks

def get_effective_risks():
    """Restituisce i rischi con gli override di stato/residual applicati.
    Usare questa funzione ovunque si vuole il dato aggiornato (es. Overview).
    """
    risks = st.session_state.risks
    overrides = st.session_state.get("risk_overrides", {})
    for r in risks:
        if r.risk_id in overrides:
            ov = overrides[r.risk_id]
            r.status = ov.get("status", r.status)
            r.residual_likelihood = ov.get("residual_l", r.residual_likelihood)
            r.residual_consequence = ov.get("residual_c", r.residual_consequence)
    return risks

def get_approval_log():
    return st.session_state.approval_log

def get_req_ownership():
    return st.session_state.req_ownership

def get_task_assignments():
    return st.session_state.task_assignments

def get_team():
    return st.session_state.team_members

# ===========================================================================
# PAGES
# ===========================================================================

def page_overview():
    if not st.session_state.get("missions"):
        st.info("No mission loaded. Create or join a mission first.")
        return
    
    _m = st.session_state.missions.get(st.session_state.get("active_mission_id"))
    if not _m:
        st.info("No active mission selected.")
        return
    colored_header(label="Mission Overview", description=f"{_m['name']} — {_m.get('description', '')}", color_name="blue-70")

    _phase = st.session_state.get("mission_phase", "B2")
    _mass_limit = st.session_state.get("_bud_mass_limit", 350.0)
    _power_limit = st.session_state.get("_bud_power_limit", 500.0)
    
    _prop_kg = st.session_state.get("propellant_kg", 0.0)
    
    mass_summary = compute_budget_summary(_build_budget_tree(), _phase, "mass_kg", budget_limit=_mass_limit - _prop_kg)
    power_summary = compute_budget_summary(_build_budget_tree(), _phase, "power_w", "nominal", budget_limit=_power_limit)
    wet_mass = mass_summary.total_with_system_margin + _prop_kg
    reqs = get_requirements()
    risks = get_effective_risks()  # applica override di stato/residual
    cov = coverage_report(reqs)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Wet Mass", f"{wet_mass:.1f} kg", f"{_mass_limit - wet_mass:.1f} kg margin")
    c2.metric("Total Power", f"{power_summary.total_with_system_margin:.1f} W", f"{power_summary.remaining:.1f} W margin")
    c3.metric("Requirements", len(reqs), f"{cov['overall_pct']:.0f}% verified")
    c4.metric("Open Risks", sum(1 for r in risks if r.status == "open"), f"{sum(1 for r in risks if r.risk_level in ('critical','high'))} high/critical")
    _fw_data = get_framework(st.session_state.get("mission_framework", "ESA"))
    _phase_defs = _fw_data["phases"]
    _gate_reviews = _fw_data["gate_reviews"]
    _next_review = next((rev for (pf, _), rev in _gate_reviews.items() if pf == _phase), "—") if _gate_reviews else "—"
    _phase_name = _phase_defs.get(_phase, {}).get("name", _phase)
    c5.metric("Next Review", _next_review, f"Phase {_phase}")

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1.2, 1, 1])
    with col_a:
        st.markdown("##### Mission Parameters")
        orb_alt = _m.get("orb_alt", 550)
        orb_inc = _m.get("orb_inc", 97.5)
        orb_mass = _m.get("orb_mass", 250)
        prop_kg = _m.get("propellant_kg", 0.0)
        target_launch = _m.get("target_launch_date", "TBD")
        lifetime = _m.get("lifetime_years", 5)
        params = {
            "Mission": _m.get("name", "BEPI-SAT"),
            "Phase": f"{_phase} — {_phase_name}",
            "Orbit": f"SSO {orb_alt} km, {orb_inc} deg",
            "Target Launch": target_launch,
            "Lifetime": f"{lifetime} years",
            "Dry Mass (with margin)": f"{mass_summary.total_with_system_margin:.1f} kg",
            "Propellant (AF-M315E)": f"{prop_kg:.1f} kg",
            "Wet Mass": f"{wet_mass:.1f} kg",
            "Launcher": _m.get("launcher", "TBD"),
        }
        st.dataframe(pd.DataFrame(params.items(), columns=["Parameter", "Value"]), hide_index=True, width=450)

    with col_b:
        st.markdown("##### Mass Budget (Wet)")
        status_color = {"green": "#27ae60", "yellow": "#f39c12", "red": "#e74c3c"}
        wet_remaining_pct = (350 - wet_mass) / 350 * 100
        color = "#27ae60" if wet_remaining_pct >= 20 else ("#f39c12" if wet_remaining_pct >= 10 else "#e74c3c")
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=wet_mass,
            delta={"reference": 350, "decreasing": {"color": "#27ae60"}},
            gauge={
                "axis": {"range": [0, 400], "tickcolor": "#666"},
                "bar": {"color": color},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 280], "color": "rgba(39,174,96,0.15)"},
                    {"range": [280, 315], "color": "rgba(243,156,18,0.15)"},
                    {"range": [315, 400], "color": "rgba(231,76,60,0.15)"},
                ],
                "threshold": {"line": {"color": "#e74c3c", "width": 3}, "value": 350},
            },
            number={"suffix": " kg", "font": {"size": 36}},
        ))
        fig.update_layout(height=250, margin=dict(t=40, b=10, l=30, r=30), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")

    with col_c:
        st.markdown("##### Power Budget")
        status_color_p = {"green": "#27ae60", "yellow": "#f39c12", "red": "#e74c3c"}
        color_p = status_color_p.get(power_summary.margin_status, "#27ae60")
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=power_summary.total_with_system_margin,
            delta={"reference": 500, "decreasing": {"color": "#27ae60"}},
            gauge={
                "axis": {"range": [0, 600], "tickcolor": "#666"},
                "bar": {"color": color_p},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 400], "color": "rgba(39,174,96,0.15)"},
                    {"range": [400, 450], "color": "rgba(243,156,18,0.15)"},
                    {"range": [450, 600], "color": "rgba(231,76,60,0.15)"},
                ],
                "threshold": {"line": {"color": "#e74c3c", "width": 3}, "value": 500},
            },
            number={"suffix": " W", "font": {"size": 36}},
        ))
        fig2.update_layout(height=250, margin=dict(t=40, b=10, l=30, r=30), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, width="stretch")

    # Review timeline with sac.steps
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### Review Timeline")
    review_order = [rev for (_, _), rev in _gate_reviews.items()]
    current_idx = review_order.index(_next_review) if _next_review in review_order else 0
    step_items = [sac.StepsItem(title=rev) for rev in review_order]
    sac.steps(step_items, index=current_idx, return_index=False)


def _render_pt_add_form(flat: list, eb: dict) -> None:
    """Render the 'Add Node' trigger and dialog for the Product Tree.

    Replaces the JS-driven modal that lived inside the components.html
    template. The JS modal could not communicate reliably with Python on
    Streamlit Cloud (srcdoc iframe, no setComponentValue, sandboxed
    navigation). The native dialog below writes directly to Supabase on
    submit, then triggers st.rerun() to redraw the tree.

    Visible only to roles that can edit the product tree (PM, SE, ADMIN,
    SSL), mirroring the gate in _process_product_tree_action.
    """
    from bepi.role_permissions import can

    user = st.session_state.get("user", {})
    role = user.get("role", "USER")
    if not (role == "ADMIN" or can("edit_subsystem") or can("edit_budget")):
        st.caption("🔒 You need PM/SE/ADMIN/SSL role to add nodes.")
        return

    mission_id = st.session_state.get("active_mission_id")
    if not mission_id:
        st.warning("No active mission selected.")
        return

    # The dialog reads the parent list from session_state because
    # @st.dialog-decorated functions cannot take arguments.
    st.session_state["_pt_add_parent_labels"] = ["(root)"] + [
        f"{n.get('code', '')} — {n.get('name', '')}" for n in flat
    ]
    st.session_state["_pt_add_parent_keys"] = [None] + [
        str(n.get("id")) for n in flat
    ]

    # Trigger button styled like the old "Add Component" header button.
    if st.button(
        "➕ Add Node",
        key="pt_open_add_dialog",
        type="primary",
        use_container_width=False,
    ):
        st.session_state["_pt_dialog_open"] = True
        st.rerun()

    if st.session_state.get("_pt_dialog_open"):
        _pt_add_node_dialog()


@st.dialog("Add Node", width="medium")
def _pt_add_node_dialog() -> None:
    """Streamlit-native modal for creating a product tree node.

    Mirrors the layout of the previous JS modal: Name + Code on the first
    row, Level + Parent on the second, TRL/Quantity/Mass on the third, with
    a Cancel/Add action row at the bottom. Submits directly to Supabase
    via the same client used by _process_product_tree_action.
    """
    parent_labels = st.session_state.get("_pt_add_parent_labels", ["(root)"])
    parent_keys = st.session_state.get("_pt_add_parent_keys", [None])
    mission_id = st.session_state.get("active_mission_id")

    # --- Header / intro ---
    st.caption("Define the specs of the new product tree element.")

    # --- Row 1: Name + Code ---
    c1, c2 = st.columns(2)
    with c1:
        new_name = st.text_input(
            "NAME",
            placeholder="e.g. ADCS Sensor",
            key="_pt_new_name",
        )
    with c2:
        new_code = st.text_input(
            "CODE",
            placeholder="e.g. ADCS-001",
            key="_pt_new_code",
        )

    # --- Row 2: Level + Parent ---
    c3, c4 = st.columns(2)
    with c3:
        level_options = ["spacecraft", "subsystem", "equipment", "component"]
        new_level = st.selectbox(
            "LEVEL",
            level_options,
            index=2,
            key="_pt_new_level",
        )
    with c4:
        parent_idx = st.selectbox(
            "PARENT",
            range(len(parent_labels)),
            format_func=lambda i: parent_labels[i],
            index=0,
            key="_pt_new_parent",
        )
        new_parent_id = parent_keys[parent_idx] if parent_idx else None

    # --- Row 3: TRL / Qty / Mass ---
    c5, c6, c7 = st.columns(3)
    with c5:
        new_trl = st.number_input(
            "TRL", min_value=1, max_value=9, value=5, step=1, key="_pt_new_trl"
        )
    with c6:
        new_qty = st.number_input(
            "QTY", min_value=1, value=1, step=1, key="_pt_new_qty"
        )
    with c7:
        new_mass = st.number_input(
            "MASS (kg)",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key="_pt_new_mass",
            help="Equipment-level only; stored in budgets table.",
        )

    st.divider()

    # --- Action row ---
    acol1, acol2 = st.columns([1, 1])
    with acol1:
        if st.button("Cancel", key="_pt_cancel", use_container_width=True):
            st.session_state["_pt_dialog_open"] = False
            st.rerun()
    with acol2:
        if st.button(
            "Add Node", key="_pt_submit", type="primary", use_container_width=True
        ):
            if not new_name.strip() or not new_code.strip():
                st.error("Name and Code are required.")
                st.stop()

            # User-scoped client: the product_tree_nodes INSERT RLS policy
            # (is_mission_member) authorises the write (audit S4).
            client = get_supabase()
            if not client:
                st.error("Database not configured. Cannot save.")
                st.stop()

            # Map "spacecraft" → "satellite" to match the legacy column
            # vocabulary used by the rest of the tree.
            db_level = "satellite" if new_level == "spacecraft" else new_level

            def _parent_uuid(parent_id):
                if not parent_id:
                    return None
                for n in st.session_state.get("product_tree", []):
                    if str(n.get("id")) == str(parent_id) or str(n.get("uuid")) == str(parent_id):
                        return str(n.get("uuid") or n.get("id"))
                return str(parent_id)

            payload = {
                "mission_id": mission_id,
                "parent_id": _parent_uuid(new_parent_id),
                "level": db_level,
                "code": new_code.strip(),
                "name": new_name.strip(),
                "quantity": int(new_qty),
                "trl": int(new_trl),
            }

            try:
                client.table("product_tree_nodes").insert(payload).execute()
                # Force the next _get_product_tree() to reload from DB so the new
                # node appears despite the read cache (reconciled at line ~994).
                st.session_state["_pt_just_added"] = {
                    "code": new_code.strip(), "name": new_name.strip(),
                    "level": db_level, "local_id": "",
                }
                st.session_state["_pt_dialog_open"] = False
                st.success(f"✅ Added **{new_name}** to the product tree.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
                # Keep the dialog open so the user can retry.


@st.dialog("Edit Node", width="medium")
def _pt_edit_node_dialog() -> None:
    """Streamlit-native modal for editing an existing product tree node.

    Pre-filled with the node's current data. Saves via UPDATE on
    `product_tree_nodes` (matched by id).
    """
    target_id = st.session_state.get("_pt_edit_target_id")
    flat = _get_product_tree()
    node = next((n for n in flat if str(n.get("id")) == str(target_id)), None)
    if node is None:
        st.error("Node not found — it may have been deleted.")
        if st.button("Close", key="_pt_edit_close_missing"):
            st.session_state["_pt_edit_dialog_open"] = False
            st.rerun()
        return

    st.caption(f"Editing **{node.get('code')}** — {node.get('name')}")

    parent_labels = ["(root)"] + [
        f"{n.get('code', '')} — {n.get('name', '')}"
        for n in flat if str(n.get("id")) != str(target_id)
    ]
    parent_keys = [None] + [
        str(n.get("id")) for n in flat if str(n.get("id")) != str(target_id)
    ]
    cur_parent = node.get("parent_id")
    try:
        parent_idx = parent_keys.index(str(cur_parent)) if cur_parent else 0
    except ValueError:
        parent_idx = 0

    level_options = ["satellite", "subsystem", "equipment", "component"]
    try:
        level_idx = level_options.index(node.get("level"))
    except ValueError:
        level_idx = 0

    c1, c2 = st.columns(2)
    with c1:
        new_name = st.text_input(
            "NAME", value=str(node.get("name", "")), key="_pt_edit_name"
        )
    with c2:
        new_code = st.text_input(
            "CODE", value=str(node.get("code", "")), key="_pt_edit_code"
        )

    c3, c4 = st.columns(2)
    with c3:
        new_level = st.selectbox(
            "LEVEL", level_options, index=level_idx, key="_pt_edit_level"
        )
    with c4:
        parent_pick = st.selectbox(
            "PARENT",
            range(len(parent_labels)),
            format_func=lambda i: parent_labels[i],
            index=parent_idx,
            key="_pt_edit_parent",
        )
        new_parent_id = parent_keys[parent_pick] if parent_pick else None

    c5, c6, c7 = st.columns(3)
    with c5:
        new_trl = st.number_input(
            "TRL", min_value=1, max_value=9,
            value=int(node.get("trl") or 5), step=1, key="_pt_edit_trl"
        )
    with c6:
        new_qty = st.number_input(
            "QTY", min_value=1,
            value=int(node.get("quantity") or 1), step=1, key="_pt_edit_qty"
        )
    with c7:
        new_mass = st.number_input(
            "MASS (kg)", min_value=0.0,
            value=float(node.get("mass_kg") or 0.0), step=0.1,
            key="_pt_edit_mass",
            help="Equipment-level only.",
        )

    st.divider()
    acol1, acol2 = st.columns([1, 1])
    with acol1:
        if st.button("Cancel", key="_pt_edit_cancel", use_container_width=True):
            st.session_state["_pt_edit_dialog_open"] = False
            st.session_state.pop("_pt_edit_target_id", None)
            st.rerun()
    with acol2:
        if st.button(
            "Save Changes", key="_pt_edit_save", type="primary", use_container_width=True
        ):
            if not new_name.strip() or not new_code.strip():
                st.error("Name and Code are required.")
                st.stop()

            client = get_service_client() or get_supabase()
            if not client:
                st.error("Database not configured. Cannot save.")
                st.stop()

            payload = {
                "parent_id": new_parent_id,
                "level": new_level,
                "code": new_code.strip(),
                "name": new_name.strip(),
                "quantity": int(new_qty),
                "trl": int(new_trl),
            }
            try:
                client.table("product_tree_nodes").update(payload).eq(
                    "id", str(target_id)
                ).execute()
                st.session_state["_pt_edit_dialog_open"] = False
                st.session_state.pop("_pt_edit_target_id", None)
                st.success(f"✅ Updated **{new_name}**.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")


@st.dialog("Delete Node", width="medium")
def _pt_delete_node_dialog() -> None:
    """Streamlit-native confirmation modal for deleting a product tree node."""
    target_id = st.session_state.get("_pt_delete_target_id")
    flat = _get_product_tree()
    node = next((n for n in flat if str(n.get("id")) == str(target_id)), None)
    if node is None:
        st.error("Node not found — it may have already been deleted.")
        if st.button("Close", key="_pt_delete_close_missing"):
            st.session_state["_pt_delete_dialog_open"] = False
            st.rerun()
        return

    # Count descendants so the user knows the blast radius.
    children = [n for n in flat if str(n.get("parent_id")) == str(target_id)]

    st.warning(
        f"⚠️ **Delete `{node.get('code')}` — {node.get('name')}?**\n\n"
        f"This will remove the node and all its descendants "
        f"({len(children)} direct children, plus their subtrees)."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancel", key="_pt_delete_cancel", use_container_width=True):
            st.session_state["_pt_delete_dialog_open"] = False
            st.session_state.pop("_pt_delete_target_id", None)
            st.rerun()
    with c2:
        if st.button(
            "Delete", key="_pt_delete_confirm", type="primary",
            use_container_width=True,
        ):
            client = get_service_client() or get_supabase()
            if not client:
                st.error("Database not configured. Cannot delete.")
                st.stop()
            try:
                # DB cascade handles descendants if FK ON DELETE CASCADE exists;
                # if not, we delete recursively in Python.
                _pt_recursive_delete(client, str(target_id))
                st.session_state["_pt_delete_dialog_open"] = False
                st.session_state.pop("_pt_delete_target_id", None)
                st.success(f"✅ Deleted **{node.get('code')}**.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete: {e}")


def _pt_recursive_delete(client, node_id: str) -> None:
    """Delete a node and all its descendants, bottom-up."""
    flat = _get_product_tree()
    children = [str(n["id"]) for n in flat if str(n.get("parent_id")) == str(node_id)]
    for cid in children:
        _pt_recursive_delete(client, cid)
    client.table("product_tree_nodes").delete().eq("id", str(node_id)).execute()


@st.dialog("Manage Nodes", width="large")
def _pt_manage_nodes_dialog() -> None:
    """Picker dialog: select a node, then choose Edit or Delete.

    The iframe table is read-only, so all row actions go through here.
    """
    flat = _get_product_tree()
    if not flat:
        st.info("No nodes yet. Use ➕ Add to create the first one.")
        if st.button("Close", key="_pt_manage_close_empty"):
            st.session_state["_pt_manage_dialog_open"] = False
            st.rerun()
        return

    options = [
        f"{n.get('code', '')} — {n.get('name', '')} [{n.get('level', '')}]"
        for n in flat
    ]
    keys = [str(n.get("id")) for n in flat]
    cur_idx = st.session_state.get("_pt_manage_idx", 0)
    if cur_idx >= len(options):
        cur_idx = 0
    pick = st.selectbox(
        "Select node",
        range(len(options)),
        format_func=lambda i: options[i],
        index=cur_idx,
        key="_pt_manage_pick",
    )
    st.session_state["_pt_manage_idx"] = pick
    target_id = keys[pick]

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "✏️ Edit", key="_pt_manage_edit_btn",
            type="primary", use_container_width=True,
        ):
            st.session_state["_pt_edit_target_id"] = target_id
            st.session_state["_pt_edit_dialog_open"] = True
            st.session_state["_pt_manage_dialog_open"] = False
            st.rerun()
    with c2:
        if st.button(
            "🗑️ Delete", key="_pt_manage_delete_btn",
            use_container_width=True,
        ):
            st.session_state["_pt_delete_target_id"] = target_id
            st.session_state["_pt_delete_dialog_open"] = True
            st.session_state["_pt_manage_dialog_open"] = False
            st.rerun()
    with c3:
        if st.button("Close", key="_pt_manage_close", use_container_width=True):
            st.session_state["_pt_manage_dialog_open"] = False
            st.rerun()


def page_product_tree():
    import json
    import urllib.parse
    import streamlit.components.v1 as components

    flat = _get_product_tree()
    eb = _get_equip_budgets()

    # --- Hide Streamlit chrome completely ---
    st.markdown("""
    <style>
        #root > div:first-child { margin-top: 0; }
        .stApp { margin: 0; padding: 0; }
        /* header[data-testid="stHeader"] restored */
        header[data-testid="stHeader"] { background: transparent !important; }
        .stAppDeployButton { display: none; }
        /* section[data-testid="stSidebar"] restored */
        .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
        .stApp > .main > .block-container { padding: 0 !important; }
        footer { display: none; }
        #MainMenu { display: none; }
    </style>
    """, unsafe_allow_html=True)

    # --- Prepare Data for JS ---
    items_for_js = []
    for n in flat:
        item = {
            "id": str(n["id"]), "code": n["code"], "name": n["name"], 
            "level": n["level"], "parentId": str(n.get("parent_id")) if n.get("parent_id") is not None else None
        }
        if item["level"] == "equipment":
            b = eb.get(n["code"], {"mass": 0.0, "power": 0, "qty": 1, "mat": "estimate", "trl": 5})
            item["mass"] = b.get("mass", 0.0)
            item["power"] = b.get("power", 0)
            item["qty"] = b.get("qty", 1)
            item["maturity"] = b.get("mat", "estimate")
            item["trl"] = b.get("trl", 5)
        items_for_js.append(item)

    items_json = json.dumps(items_for_js).replace("</", "<\\/")
    
    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  
  :root {
    --bg-main: #0f111a;
    --bg-sidebar: #161b22;
    --bg-card: #161b22;
    --bg-modal: #1c2128;
    --bg-input: #0d1117;
    --bg-header-modal: #24292f;
    --border: #21262d;
    --border-light: #30363d;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #484f58;
    --blue: #58a6ff;
    --blue-bg: rgba(88,166,255,0.1);
    --blue-border: rgba(88,166,255,0.3);
    --purple: #bc8cff;
    --purple-bg: rgba(188,140,255,0.1);
    --purple-border: rgba(188,140,255,0.3);
    --emerald: #3fb950;
    --emerald-bg: rgba(63,185,80,0.1);
    --emerald-border: rgba(63,185,80,0.3);
    --orange: #f0883e;
    --orange-bg: rgba(240,136,62,0.1);
    --orange-border: rgba(240,136,62,0.3);
    --blue-btn: #1f6feb;
  }

  body {
    background: var(--bg-main);
    color: var(--text-secondary);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    min-height: 100vh;
    overflow: hidden;
  }

  .app { display: flex; height: 100vh; overflow: hidden; }

  /* ── SIDEBAR ── */
  .sidebar {
    width: 256px;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    overflow: hidden;
  }

  .sidebar-logo {
    padding: 40px 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .logo-icon {
    width: 56px; height: 56px;
    background: rgba(31,111,235,0.2);
    border-radius: 16px;
    border: 1px solid rgba(31,111,235,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }

  .logo-icon svg { color: var(--blue); }

  .logo-title {
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.5px;
  }

  .logo-sub {
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 500;
    text-align: center;
  }

  .sidebar-nav { flex: 1; padding: 0 16px; display: flex; flex-direction: column; gap: 4px; }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.15s;
    color: var(--text-muted);
    font-size: 14px;
    font-weight: 600;
    border: 1px solid transparent;
  }
  .nav-item:hover { background: #21262d; color: var(--text-secondary); }
  .nav-item.active {
    background: rgba(31,111,235,0.2);
    color: var(--blue);
    border-color: rgba(31,111,235,0.2);
    box-shadow: 0 4px 24px rgba(31,111,235,0.1);
  }
  .nav-item svg { opacity: 0.7; flex-shrink: 0; }

  /* ── MAIN ── */
  .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

  .header {
    height: 64px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    background: rgba(15,17,26,0.8);
    backdrop-filter: blur(12px);
    flex-shrink: 0;
    z-index: 20;
  }

  .header-left { display: flex; align-items: center; gap: 24px; }

  .header-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }

  .view-switcher {
    display: flex;
    background: #1c2128;
    border: 1px solid var(--border-light);
    border-radius: 12px;
    padding: 4px;
    gap: 2px;
  }

  .view-btn {
    padding: 8px;
    border-radius: 8px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.15s;
    display: flex;
    align-items: center;
  }
  .view-btn:hover { color: var(--text-secondary); }
  .view-btn.active { background: #30363d; color: var(--blue); box-shadow: 0 1px 3px rgba(0,0,0,0.3); }

  .add-btn {
    background: var(--blue-btn);
    color: white;
    border: none;
    padding: 8px 24px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 12px rgba(31,111,235,0.3);
    letter-spacing: 0.02em;
  }
  .add-btn:hover { background: #388bfd; }

  /* ── CONTENT ── */
  .content { flex: 1; overflow-y: auto; padding: 32px; }
  .content::-webkit-scrollbar { width: 6px; }
  .content::-webkit-scrollbar-track { background: transparent; }
  .content::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 10px; }
  .content::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

  .content-inner { max-width: 960px; margin: 0 auto; }

  /* ── TREE VIEW ── */
  .tree-card {
    background: rgba(22,27,34,0.4);
    border: 1px solid rgba(33,38,45,0.6);
    border-radius: 32px;
    padding: 40px;
    box-shadow: 0 25px 50px rgba(0,0,0,0.4);
  }

  .tree-header { margin-bottom: 32px; }
  .tree-header h3 {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--blue);
    margin-bottom: 4px;
  }
  .tree-header p { font-size: 12px; font-weight: 500; color: var(--text-muted); }

  .tree-node { display: flex; flex-direction: column; }

  .node-row {
    display: flex;
    align-items: center;
    padding: 12px;
    margin: 4px 0;
    border-radius: 12px;
    border: 1px solid;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
  }
  .node-row:hover { transform: scale(1.005); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }

  .node-row.satellite { border-color: var(--blue-border); background: var(--blue-bg); color: var(--blue); }
  .node-row.subsystem  { border-color: var(--purple-border); background: var(--purple-bg); color: var(--purple); }
  .node-row.equipment  { border-color: var(--emerald-border); background: var(--emerald-bg); color: var(--emerald); }
  .node-row.mission    { border-color: var(--orange-border); background: var(--orange-bg); color: var(--orange); }

  .node-chevron { margin-right: 12px; color: var(--text-muted); flex-shrink: 0; width: 18px; }
  
  .node-icon-wrap {
    margin-right: 12px;
    padding: 8px;
    border-radius: 8px;
    background: rgba(13,17,23,0.6);
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }

  .node-info { display: flex; flex-direction: column; }
  .node-meta { display: flex; align-items: center; gap: 8px; }
  .node-id { font-size: 10px; font-family: monospace; opacity: 0.5; }
  .node-code { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.6; }
  .node-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }

  .node-add-btn {
    margin-left: auto;
    padding: 6px;
    border: none;
    background: transparent;
    cursor: pointer;
    border-radius: 6px;
    color: var(--text-secondary);
    opacity: 0;
    transition: all 0.15s;
    display: flex;
    align-items: center;
  }
  .node-row:hover .node-add-btn { opacity: 1; }
  .node-add-btn:hover { background: rgba(255,255,255,0.1); }

  .node-children {
    margin-left: 40px;
    border-left: 2px solid rgba(48,54,61,0.4);
    padding: 4px 0 4px 24px;
  }

  .connector-h {
    position: absolute;
    left: -24px;
    top: 50%;
    width: 24px;
    height: 2px;
    background: rgba(48,54,61,0.5);
  }

  /* ── TABLE VIEW ── */
  .table-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: visible; /* Changed from hidden to allow dropdowns to overflow */
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }

  thead { background: rgba(33,38,45,0.5); }
  thead th {
    padding: 20px 24px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border);
    text-align: left;
  }
  thead th:first-child { border-top-left-radius: 16px; }
  thead th:last-child { text-align: right; border-top-right-radius: 16px; }

  tbody tr {
    border-bottom: 1px solid rgba(33,38,45,0.5);
    transition: background 0.15s;
  }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:last-child td:first-child { border-bottom-left-radius: 16px; }
  tbody tr:last-child td:last-child { border-bottom-right-radius: 16px; }
  tbody tr:hover { background: rgba(88,166,255,0.03); }

  tbody td { padding: 16px 24px; }

  .cell-id { font-family: monospace; color: rgba(88,166,255,0.7); font-size: 12px; }
  .cell-code { font-weight: 700; color: var(--text-secondary); letter-spacing: -0.01em; }
  .cell-name { font-weight: 500; color: var(--text-primary); }

  .level-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    border: 1px solid;
    letter-spacing: 0.04em;
  }
  .badge-satellite { border-color: var(--blue-border); color: var(--blue); background: var(--blue-bg); }
  .badge-subsystem  { border-color: var(--purple-border); color: var(--purple); background: var(--purple-bg); }
  .badge-equipment  { border-color: var(--emerald-border); color: var(--emerald); background: var(--emerald-bg); }
  .badge-mission    { border-color: var(--orange-border); color: var(--orange); background: var(--orange-bg); }

  .action-btn { background: none; border: none; cursor: pointer; color: var(--text-muted); padding: 4px; border-radius: 4px; }
  .action-btn:hover { color: var(--text-primary); }
  td:last-child { text-align: right; }

  /* ── BUDGET VIEW ── */
  .budget-input {
    background: rgba(13,17,23,0.5);
    border: 1px solid rgba(48,54,61,0.5);
    border-radius: 8px;
    padding: 6px 12px;
    width: 80px;
    color: var(--text-secondary);
    font-size: 13px;
    outline: none;
    transition: border-color 0.15s;
    font-family: inherit;
  }
  .budget-input:focus { border-color: var(--emerald); }

  .maturity-select {
    background: rgba(13,17,23,0.5);
    border: 1px solid rgba(48,54,61,0.5);
    border-radius: 8px;
    padding: 6px 12px;
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    outline: none;
    cursor: pointer;
    font-family: inherit;
  }

  .cell-eq-code { font-family: monospace; color: var(--emerald); font-weight: 700; }
  .cell-trl { font-weight: 700; color: var(--blue); }
  tbody tr:hover td .budget-input { border-color: rgba(63,185,80,0.3); }

  /* ── MODAL ── */
  .modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 50;
    background: rgba(0,0,0,0.7);
    backdrop-filter: blur(8px);
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: fadeIn 0.2s ease-out;
  }
  .modal-overlay.open { display: flex; }

  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes scaleIn {
    from { transform: scale(0.95); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  .modal {
    background: var(--bg-modal);
    border: 1px solid var(--border-light);
    border-radius: 24px;
    width: 100%;
    max-width: 512px;
    box-shadow: 0 25px 50px rgba(0,0,0,0.6);
    overflow: hidden;
    animation: scaleIn 0.2s ease-out;
  }

  .modal-head {
    padding: 32px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(36,41,47,0.5);
  }

  .modal-head h3 { font-size: 20px; font-weight: 700; color: var(--text-primary); }
  .modal-head p { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

  .modal-close {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    padding: 8px;
    border-radius: 12px;
    transition: all 0.15s;
    display: flex;
    align-items: center;
  }
  .modal-close:hover { background: #21262d; color: var(--text-primary); }

  .modal-body { padding: 32px; display: flex; flex-direction: column; gap: 24px; }

  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

  .form-group { display: flex; flex-direction: column; gap: 8px; }
  .form-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    padding: 0 4px;
  }

  .form-input, .form-select {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px;
    color: var(--text-primary);
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s;
    font-family: inherit;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
    -webkit-appearance: none;
    appearance: none;
  }
  .form-input:focus, .form-select:focus { border-color: var(--blue-btn); }
  .form-input::placeholder { color: var(--text-muted); }

  .modal-foot {
    padding: 32px;
    background: rgba(36,41,47,0.5);
    border-top: 1px solid var(--border);
    display: flex;
    gap: 16px;
  }

  .cancel-btn {
    flex: 1;
    padding: 12px;
    background: none;
    border: none;
    color: var(--text-secondary);
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    cursor: pointer;
    transition: color 0.15s;
    font-family: inherit;
    letter-spacing: 0.04em;
  }
  .cancel-btn:hover { color: var(--text-primary); }

  .create-btn {
    flex: 2;
    padding: 12px;
    background: var(--blue-btn);
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.15s;
    box-shadow: 0 4px 12px rgba(31,111,235,0.4);
    letter-spacing: 0.04em;
    font-family: inherit;
  }
  .create-btn:hover { background: #388bfd; }

  /* SVG icons */
  svg { display: inline-block; vertical-align: middle; }
</style>
</head>
<body>
<div class="app">

  <!-- SIDEBAR -->
  <aside class="sidebar" style="display: none;">
    <div class="sidebar-logo">
      <div class="logo-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--blue)">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div class="logo-title">B.E.P.I.</div>
      <div class="logo-sub">Engineering Systems</div>
    </div>
    <nav class="sidebar-nav">
      <div class="nav-item" onclick="setPage(this,'Overview')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
        <span>Overview</span>
      </div>
      <div class="nav-item active" id="nav-product-tree" onclick="setPage(this,'Product Tree')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        <span>Product Tree</span>
      </div>
      <div class="nav-item" onclick="setPage(this,'Budgets')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        <span>Budgets</span>
      </div>
      <div class="nav-item" onclick="setPage(this,'Requirements')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
        <span>Requirements</span>
      </div>
      <div class="nav-item" onclick="setPage(this,'Schedule')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <span>Schedule</span>
      </div>
      <div class="nav-item" onclick="setPage(this,'Warehouse')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        <span>Warehouse</span>
      </div>
    </nav>
  </aside>

  <!-- MAIN -->
  <main class="main">
    <header class="header">
      <div class="header-left">
        <!-- Title is rendered by Streamlit above the iframe so the Add Node
             button can sit on the same row, aligned to the right. -->
        <div class="view-switcher">
          <button class="view-btn active" id="btn-tree" onclick="setView('tree')" title="Visualizzazione Albero">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 6h10M7 18h10M5 8v8"/></svg>
          </button>
          <button class="view-btn" id="btn-table" onclick="setView('table')" title="Tabella WBS">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
          </button>
          <button class="view-btn" id="btn-budget" onclick="setView('budget')" title="Budget Equipment">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
          </button>
        </div>
      </div>
      <!-- The "Add Node" trigger is rendered natively by Streamlit
           (see _render_pt_add_form), so the old HTML button is gone. -->
    </header>

    <div class="content">
      <div class="content-inner">
        <div id="view-tree"></div>
        <div id="view-table" style="display:none"></div>
        <div id="view-budget" style="display:none"></div>
      </div>
    </div>
  </main>
</div>

<script>
// ── DATA ──
let items = __INJECT_ITEMS_HERE__;

function triggerStreamlit(action, data) {
    console.log("[pt] triggerStreamlit", action, data);
    // We do NOT navigate the URL: the Streamlit `components.html` iframe is
    // rendered with `srcdoc`, so `window.location.href` resolves to
    // `about:srcdoc` and any `window.location.replace(...)` is a silent no-op.
    // We also do NOT call `setComponentValue` here: this iframe is not
    // directly wrapped by Streamlit, so the call is a no-op too.
    //
    // Instead, we postMessage the action to the parent window. A sibling
    // `components.html` (the "pt_bridge") is listening and calls
    // `Streamlit.setComponentValue` from inside its own iframe, which IS
    // wrapped by Streamlit and does trigger a rerun. `st_autorefresh`
    // guarantees that rerun fires even if the user is idle.
    try {
        sessionStorage.setItem('pt_action', action);
        sessionStorage.setItem('pt_data', JSON.stringify(data));
        localStorage.setItem('pt_pending_action', JSON.stringify({ action, data, ts: Date.now() }));
    } catch (e) {
        console.warn("[pt] storage write failed", e);
    }
    try {
        window.parent.postMessage(
            { type: 'pt_action', action, data, ts: Date.now() },
            '*'
        );
    } catch (e) {
        console.error("[pt] postMessage failed", e);
    }
}


let openNodes = {}; // id -> bool (collapsed)
let currentView = 'tree';

// ── ICONS ──
const icons = {
  mission:   `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`,
  satellite: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>`,
  subsystem: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07M8.46 8.46a5 5 0 0 0 0 7.07"/></svg>`,
  equipment: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="2" x2="9" y2="4"/><line x1="15" y1="2" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="22"/><line x1="15" y1="20" x2="15" y2="22"/><line x1="20" y1="9" x2="22" y2="9"/><line x1="20" y1="14" x2="22" y2="14"/><line x1="2" y1="9" x2="4" y2="9"/><line x1="2" y1="14" x2="4" y2="14"/></svg>`,
  chevron_right: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>`,
  chevron_down:  `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>`,
  plus: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
  dots: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>`,
};

// ── TREE BUILDING ──
function buildTree(parentId = null) {
  return items.filter(i => i.parentId === parentId);
}

function isDefaultOpen(id, depth) {
  if (id in openNodes) return openNodes[id];
  return depth < 2;
}

function toggleNode(id) {
  openNodes[id] = !isDefaultOpen(id, 99);
  renderTree();
}

function renderTreeNodes(parentId, depth, isChild) {
  const children = buildTree(parentId);
  if (!children.length) return '';
  
  let html = '';
  if (isChild) {
    html += `<div class="node-children">`;
  }
  
  children.forEach(node => {
    const subChildren = buildTree(node.id);
    const hasChildren = subChildren.length > 0;
    const open = isDefaultOpen(node.id, depth);
    
    html += `<div class="tree-node">
      <div class="node-row ${node.level}" onclick="toggleNode('${node.id}')">
        ${depth > 0 ? '<div class="connector-h"></div>' : ''}
        <div class="node-chevron">
          ${hasChildren ? (open ? icons.chevron_down : icons.chevron_right) : '<div style="width:18px"></div>'}
        </div>
        <div class="node-icon-wrap">${icons[node.level] || ''}</div>
        <div class="node-info">
          <div class="node-meta">
            <span class="node-id">${node.id}</span>
            <span class="node-code">${node.code}</span>
          </div>
          <span class="node-name">${node.name}</span>
        </div>
        <!-- The per-node "+" button used to open the old modal; the Streamlit
             Add Node dialog is now the only entry point. -->
      </div>
      ${(hasChildren && open) ? renderTreeNodes(node.id, depth + 1, true) : ''}
    </div>`;
  });
  
  if (isChild) html += `</div>`;
  return html;
}

function renderTree() {
  document.getElementById('view-tree').innerHTML = `
    <div class="tree-card">
      <div class="tree-header">
        <h3>Mission Structure</h3>
        <p>Functional breakdown of satellite equipment</p>
      </div>
      ${renderTreeNodes(null, 0, false)}
    </div>`;
}

function renderTable() {
  // Edit/Delete moved to a Streamlit-native dialog opened from the
  // page header (see `_pt_open_actions_dialog`). The iframe table is
  // intentionally read-only now.
  let rows = items.map(item => `
    <tr>
      <td class="cell-id">${item.id}</td>
      <td class="cell-code">${item.code}</td>
      <td class="cell-name">${item.name}</td>
      <td><span class="level-badge badge-${item.level}">${item.level}</span></td>
      <td style="text-align:right;color:var(--text-muted);font-size:12px;">Use toolbar →</td>
    </tr>`).join('');

  document.getElementById('view-table').innerHTML = `
    <div class="table-card">
      <table>
        <thead><tr>
          <th>WBS ID</th><th>Code</th><th>Name</th><th>Level</th><th>Actions</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function renderBudget() {
  const equip = items.filter(i => i.level === 'equipment');
  let rows = equip.map(item => `
    <tr>
      <td class="cell-eq-code">${item.code}</td>
      <td style="font-weight:600;color:var(--text-primary)">${item.name}</td>
      <td><input class="budget-input" type="number" value="${item.mass}" 
          onchange="updateItem('${item.id}','mass',parseFloat(this.value))"/></td>
      <td><input class="budget-input" type="number" value="${item.power}" 
          onchange="updateItem('${item.id}','power',parseFloat(this.value))"/></td>
      <td style="font-weight:700;color:var(--text-muted)">${item.qty}</td>
      <td>
        <select class="maturity-select" onchange="updateItem('${item.id}','maturity',this.value)">
          <option ${item.maturity==='estimate'?'selected':''}>estimate</option>
          <option ${item.maturity==='measured'?'selected':''}>measured</option>
          <option ${item.maturity==='qualified'?'selected':''}>qualified</option>
        </select>
      </td>
      <td class="cell-trl">${item.trl}</td>
    </tr>`).join('');

  document.getElementById('view-budget').innerHTML = `
    <div class="table-card" style="overflow-x:auto">
      <table style="white-space:nowrap">
        <thead><tr>
          <th>Equipment Code</th><th>Name</th><th>Mass (kg)</th>
          <th>Power (W)</th><th>Qty</th><th>Maturity</th><th>TRL</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function updateItem(id, field, value) {
  items = items.map(i => i.id === id ? {...i, [field]: value} : i);
  const updatedItem = items.find(i => i.id === id);
  triggerStreamlit("update_item", updatedItem);
}

// ── VIEW SWITCHING ──
function setView(v) {
  currentView = v;
  ['tree','table','budget'].forEach(name => {
    document.getElementById('view-' + name).style.display = (name === v) ? '' : 'none';
    document.getElementById('btn-' + name).classList.toggle('active', name === v);
  });
  if (v === 'tree') renderTree();
  else if (v === 'table') renderTable();
  else renderBudget();
}

// ── NAV ──
function setPage(el, name) {
  triggerStreamlit("nav_page", {page: name});
}

// ── INIT ──
setView('tree');
</script>
</body>
</html>
"""

    # --- Header bar (title left, Add/Manage buttons right) ---
    # The title lives here in Streamlit (not inside the iframe) so the buttons
    # can sit on the same row, aligned to the right. The iframe keeps its
    # own view-switcher (Tree/Table/Budget) below this header.
    hdr_l, hdr_r = st.columns([3, 1], vertical_alignment="center")
    with hdr_l:
        st.markdown(
            "<h2 style='margin:0;padding:8px 0;font-size:22px;"
            "font-weight:700;color:#e6edf3;'>Project Hierarchy</h2>",
            unsafe_allow_html=True,
        )
    with hdr_r:
        # Render the Add Node + Manage Nodes triggers inline. The dialogs are
        # opened via session_state and st.rerun.
        from bepi.role_permissions import can as _can
        _user = st.session_state.get("user", {})
        _role = _user.get("role", "USER")
        _can_edit = (_role == "ADMIN" or _can("edit_subsystem") or _can("edit_budget"))
        if _can_edit:
            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if st.button(
                    "➕ Add",
                    key="pt_open_add_dialog",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["_pt_add_parent_labels"] = ["(root)"] + [
                        f"{n.get('code', '')} — {n.get('name', '')}" for n in flat
                    ]
                    st.session_state["_pt_add_parent_keys"] = [None] + [
                        str(n.get("id")) for n in flat
                    ]
                    st.session_state["_pt_dialog_open"] = True
                    st.rerun()
            with btn_c2:
                if st.button(
                    "✏️ Manage",
                    key="pt_open_manage_dialog",
                    use_container_width=True,
                ):
                    st.session_state["_pt_manage_dialog_open"] = True
                    st.rerun()
        else:
            st.caption("🔒")

    if st.session_state.get("_pt_dialog_open"):
        _pt_add_node_dialog()

    # --- Manage Nodes: pick a node then Edit or Delete ---
    if st.session_state.get("_pt_manage_dialog_open"):
        _pt_manage_nodes_dialog()

    # --- Edit/Delete dialogs driven by the manage dialog ---
    if st.session_state.get("_pt_edit_dialog_open"):
        _pt_edit_node_dialog()

    if st.session_state.get("_pt_delete_dialog_open"):
        _pt_delete_node_dialog()


    html_content = HTML_TEMPLATE.replace("__INJECT_ITEMS_HERE__", items_json)
    components.html(html_content, height=1000, scrolling=True)

def page_budgets():
    phase = st.session_state.get("mission_phase", "B2")
    colored_header(label="Budget Dashboard", description=f"Mass & Power budgets with ECSS margins", color_name="green-70")

    # Budget controls
    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 1])
    with ctrl1:
        fw_data = get_framework(st.session_state.get("mission_framework", "ESA"))
        phase_ids = list(fw_data["phases"].keys())
        phase = st.selectbox("Phase for margins", phase_ids,
                             format_func=lambda p: f"{p} — {fw_data['phases'][p]['name']}",
                             index=phase_ids.index(phase) if phase in phase_ids else 0,
                             key="_bud_phase")
        # Fix P2: sincronizza fase con session_state + DB
        if phase != st.session_state.get("mission_phase"):
            st.session_state["mission_phase"] = phase
            # 🔴 P1 FIX: Persist phase to DB
            client = get_supabase()
            mission_id = st.session_state.get("active_mission_id")
            if client and mission_id:
                try:
                    client.table("missions").update({"phase": phase}).eq("id", mission_id).execute()
                    if mission_id in st.session_state.missions:
                        st.session_state.missions[mission_id]["mission_phase"] = phase
                except Exception as e:
                    st.warning(f"⚠️ Could not save phase to DB: {e}")
    with ctrl2:
        mass_limit = st.number_input("Mass limit (kg, wet)", min_value=0.0, value=350.0, step=10.0, key="_bud_mass_limit")
    with ctrl3:
        power_limit = st.number_input("Power limit (W)", min_value=0.0, value=500.0, step=10.0, key="_bud_power_limit")

    tree = _build_budget_tree()
    _prop_kg = st.session_state.get("propellant_kg", 0.0)
    dry_limit = mass_limit - _prop_kg

    tab_mass, tab_power, tab_equip_edit = st.tabs(["Mass Budget", "Power Budget", "Edit Equipment"])

    with tab_mass:
        summary = compute_budget_summary(tree, phase, "mass_kg", budget_limit=dry_limit)
        _render_budget(summary, "Mass (kg)", dry_limit, tree=tree)

    with tab_power:
        summary = compute_budget_summary(tree, phase, "power_w", "nominal", budget_limit=power_limit)
        _render_budget(summary, "Power (W)", power_limit, tree=tree)

    with tab_equip_edit:
        st.markdown("##### Equipment Budget Editor")
        eb = _get_equip_budgets()
        flat = _get_product_tree()
        equip_nodes = [n for n in flat if n["level"] == "equipment"]
        if equip_nodes:
            eq_rows = []
            for n in equip_nodes:
                b = eb.get(n["code"], {"mass": 0.0, "power": 0, "qty": 1, "mat": "estimate", "trl": 5})
                parent = next((p for p in flat if p["id"] == n.get("parent_id")), None)
                eq_rows.append({
                    "Subsystem": parent["code"] if parent else "—",
                    "Code": n["code"], "Name": n["name"],
                    "Mass (kg)": b.get("mass", 0.0), "Power (W)": b.get("power", 0),
                    "Qty": b.get("qty", 1), "Maturity": b.get("mat", "estimate"),
                })
            eq_df = pd.DataFrame(eq_rows)
            if can("edit_budget"):
                edited_eq = st.data_editor(
                    eq_df, key="_bud_equip_editor", hide_index=True, width="stretch",
                    column_config={
                        "Subsystem": st.column_config.TextColumn(disabled=True),
                        "Code": st.column_config.TextColumn(disabled=True),
                        "Name": st.column_config.TextColumn(),
                        "Mass (kg)": st.column_config.NumberColumn(min_value=0.0, step=0.1, format="%.2f"),
                        "Power (W)": st.column_config.NumberColumn(min_value=0, step=0.5, format="%.1f"),
                        "Qty": st.column_config.NumberColumn(min_value=1, step=1),
                        "Maturity": st.column_config.SelectboxColumn(options=["estimate", "measured", "qualified"]),
                    },
                )
            else:
                edited_eq = eq_df
                st.dataframe(eq_df, hide_index=True, width="stretch")
                st.caption("🔒 Read-only — `edit_budget` permission required")
            if st.button("Save & Recalculate", key="_bud_equip_save", type="primary", disabled=not can("edit_budget")):
                client = get_supabase()
                mission_id = st.session_state.get("active_mission_id")
                
                try:
                    for _, row in edited_eq.iterrows():
                        code = row["Code"]
                        mass_kg = float(row["Mass (kg)"])
                        power_w = float(row["Power (W)"])
                        qty = int(row["Qty"])
                        mat = row["Maturity"]
                        
                        # Update session_state
                        eb[code] = {
                            "mass": mass_kg, "power": power_w,
                            "qty": qty, "mat": mat,
                            "trl": eb.get(code, {}).get("trl", 5),
                        }
                        
                        # Find node by code and update name if changed
                        node = next((n for n in equip_nodes if n["code"] == code), None)
                        if node and node["name"] != row["Name"]:
                            node["name"] = row["Name"]
                        
                        # Persist to DB if client available.
                        # Update existing budget rows, insert only when none exist.
                        # NOTE: do NOT use .upsert() here — the budgets table has no
                        # UNIQUE(node_id, budget_type) constraint, so upsert resolves
                        # on the PK (id) and inserts a brand-new row every save,
                        # accumulating duplicates.
                        if client and node:
                            node_id = node.get("id")  # UUID
                            if node_id:
                                for btype, val, unit in [
                                    ("mass_kg", mass_kg, "kg"),
                                    ("power_w", power_w, "W"),
                                ]:
                                    res = client.table("budgets").update({
                                        "nominal_value": val,
                                        "quantity": qty,
                                        "maturity": mat,
                                        "source": "equipment_editor",
                                    }).eq("node_id", node_id).eq("budget_type", btype).execute()
                                    if not res.data:
                                        client.table("budgets").insert({
                                            "node_id": node_id,
                                            "budget_type": btype,
                                            "nominal_value": val,
                                            "unit": unit,
                                            "quantity": qty,
                                            "maturity": mat,
                                            "margin_pct": 0,
                                            "source": "equipment_editor",
                                        }).execute()
                    
                    st.success("✅ Budget saved to database!")
                except Exception as e:
                    st.error(f"❌ Error saving budget: {e}")
                
                st.rerun()
        else:
            st.info("No equipment nodes in the product tree.")


def _render_budget(summary, ylabel, limit, tree=None):
    # Detect if root is mission-level (multi-satellite) for deeper breakdown
    is_multi = tree and tree["node"]["level"] == "mission"

    # For multi-satellite: expand to subsystem level for the chart
    if is_multi and summary.lines:
        phase = summary.phase
        sub_lines = []
        for sat_line in summary.lines:
            # find satellite subtree and recompute per-subsystem
            sat_subtree = next((c for c in tree["children"] if c["node"]["code"] == sat_line.subsystem_code), None)
            if sat_subtree:
                sat_summary = compute_budget_summary(
                    sat_subtree, phase, summary.budget_type, summary.operating_mode, budget_limit=None)
                for sl in sat_summary.lines:
                    sub_lines.append(BudgetSummaryLine(
                        subsystem_code=f"{sat_line.subsystem_code}/{sl.subsystem_code}",
                        subsystem_name=f"{sat_line.subsystem_name} — {sl.subsystem_name}",
                        nominal=sl.nominal, with_margin=sl.with_margin, margin_pct=sl.margin_pct,
                    ))
        chart_lines = sub_lines if sub_lines else summary.lines
    else:
        chart_lines = summary.lines

    names = [l.subsystem_code for l in chart_lines]
    nominal = [l.nominal for l in chart_lines]
    with_margin = [l.with_margin for l in chart_lines]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Nominal", x=names, y=nominal, marker_color="#3498db",
                         marker_line=dict(width=0), opacity=0.9))
    fig.add_trace(go.Bar(name="With ECSS margin", x=names, y=with_margin, marker_color="#e67e22",
                         marker_line=dict(width=0), opacity=0.9))
    fig.update_layout(
        barmode="group", yaxis_title=ylabel, height=420,
        margin=dict(t=40, b=40), plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor="rgba(128,128,128,0.1)")
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.1)")
    st.plotly_chart(fig, width="stretch")

    status_color = {"green": "#27ae60", "yellow": "#f39c12", "red": "#e74c3c"}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nominal Total", f"{summary.subtotal_nominal:.1f}")
    c2.metric("With Component Margins", f"{summary.subtotal_with_margin:.1f}")
    c3.metric("With System Margin", f"{summary.total_with_system_margin:.1f}")
    remaining_pct = (summary.remaining / limit * 100) if limit else 0
    c4.metric("Remaining", f"{summary.remaining:.1f} ({remaining_pct:.1f}%)")

    st.markdown("<br>", unsafe_allow_html=True)
    first_col = "Element" if is_multi else "Subsystem"
    # Show satellite-level summary for multi, subsystem for single
    display_lines = summary.lines
    rows = [
        {first_col: l.subsystem_code, "Nominal": f"{l.nominal:.1f}",
         "With Margin": f"{l.with_margin:.1f}", "Margin": f"{l.margin_pct:.1f}%"}
        for l in display_lines
    ]
    rows.append({first_col: "**TOTAL**", "Nominal": f"{summary.subtotal_nominal:.1f}", "With Margin": f"{summary.subtotal_with_margin:.1f}", "Margin": ""})
    rows.append({first_col: f"+ System ({summary.system_margin_pct}%)", "Nominal": "", "With Margin": f"**{summary.total_with_system_margin:.1f}**", "Margin": ""})
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)

    # For multi-satellite: show per-satellite subsystem breakdown
    if is_multi and summary.lines:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### Per-Element Breakdown")
        for sat_line in summary.lines:
            sat_subtree = next((c for c in tree["children"] if c["node"]["code"] == sat_line.subsystem_code), None)
            if sat_subtree:
                with st.expander(f"{sat_line.subsystem_code} — {sat_line.subsystem_name} ({sat_line.with_margin:.1f} {ylabel.split('(')[-1].replace(')', '')})"):
                    sat_summary = compute_budget_summary(
                        sat_subtree, summary.phase, summary.budget_type, summary.operating_mode, budget_limit=None)
                    sub_df = pd.DataFrame([
                        {"Subsystem": sl.subsystem_code, "Nominal": f"{sl.nominal:.1f}",
                         "With Margin": f"{sl.with_margin:.1f}", "Margin": f"{sl.margin_pct:.1f}%"}
                        for sl in sat_summary.lines
                    ])
                    st.dataframe(sub_df, width="stretch", hide_index=True)


def page_requirements():
    colored_header(label="Requirements", description="Verification matrix, coverage tracking & management", color_name="violet-70")
    reqs = get_requirements()
    nodes = _get_product_tree()
    cov = coverage_report(reqs)
    ownership = get_req_ownership()

    # Filter bar
    col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
    with col_f1:
        filter_level = st.selectbox("Filter by Level", ["All"] + sorted(set(r.level for r in reqs)), key="req_flevel")
    with col_f2:
        filter_owner = st.selectbox("Filter by Owner", ["All"] + [m["name"] for m in get_team()], key="req_fowner")
    with col_f3:
        filter_status = st.selectbox("Filter by Status", ["All", "not_started", "in_progress", "passed", "failed", "waived"], key="req_fstatus")
    filtered_reqs = reqs
    if filter_level != "All":
        filtered_reqs = [r for r in filtered_reqs if r.level == filter_level]
    if filter_owner != "All":
        owner_ids = [m["id"] for m in get_team() if m["name"] == filter_owner]
        filtered_reqs = [r for r in filtered_reqs if ownership.get(r.id, {}).get("owner") in owner_ids]
    if filter_status != "All":
        filtered_reqs = [r for r in filtered_reqs if r.verification_status == filter_status]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", cov["total"])
    c2.metric("Verified", f"{cov['overall_pct']:.0f}%")
    c3.metric("Passed", cov["by_status"].get("passed", 0))
    c4.metric("In Progress", cov["by_status"].get("in_progress", 0))

    tab_matrix, tab_add, tab_edit_req, tab_assign = st.tabs(["Verification Matrix", "Add Requirement", "Edit / Delete", "Assign & Trace"])

    with tab_matrix:
        col_a, col_b = st.columns([2.5, 1])
        with col_a:
            vm = verification_matrix(filtered_reqs)
            df = pd.DataFrame(vm) if vm else pd.DataFrame(columns=["id", "title", "type", "priority", "status", "method"])
            status_map = {"passed": "✅ PASS", "in_progress": "🔄 WIP", "not_started": "⬜ TODO", "failed": "❌ FAIL", "waived": "⏭ WAIVED"}
            if not df.empty:
                df["status"] = df["status"].map(lambda s: status_map.get(s, s))
            if not df.empty:
                owners = []
                approvals = []
                allocated = []
                for r in filtered_reqs:
                    own = ownership.get(r.id, {})
                    owner_m = get_member(own.get("owner", ""))
                    owners.append(owner_m["name"] if owner_m else "—")
                    appr = get_latest_approval("requirement", r.id)
                    approvals.append(appr["status"].upper() if appr else ("—" if r.verification_status == "not_started" else "PENDING"))
                    allocated.append(", ".join(r.allocated_to) if r.allocated_to else "—")
                df["owner"] = owners
                df["allocated_to"] = allocated
                df["approval"] = approvals
            if can("edit_requirement") and not df.empty:
                status_opts = list(status_map.values())
                edited_req_df = st.data_editor(
                    df, key="_req_matrix_editor", hide_index=True, width="stretch", height=450,
                    column_config={
                        "id": st.column_config.TextColumn(disabled=True),
                        "title": st.column_config.TextColumn(disabled=True),
                        "type": st.column_config.TextColumn(disabled=True),
                        "priority": st.column_config.TextColumn(disabled=True),
                        "status": st.column_config.SelectboxColumn(options=status_opts, required=True),
                        "method": st.column_config.TextColumn(disabled=True),
                        "owner": st.column_config.TextColumn(disabled=True),
                        "allocated_to": st.column_config.TextColumn(disabled=True),
                        "approval": st.column_config.TextColumn(disabled=True),
                    },
                )
                rev_status_map = {v: k for k, v in status_map.items()}
                if not edited_req_df["status"].equals(df["status"]):
                    for i, row in edited_req_df.iterrows():
                        new_s = rev_status_map.get(row["status"], "not_started")
                        if i < len(filtered_reqs) and filtered_reqs[i].verification_status != new_s:
                            req_item = filtered_reqs[i]
                            req_item.verification_status = new_s
                            if DB_ENFORCED and getattr(req_item, "id", None):
                                update_requirement(req_item.id, {"verification_status": new_s})
                    st.rerun()
            else:
                st.dataframe(df, width="stretch", hide_index=True, height=450)

        with col_b:
            st.markdown("##### Coverage by Status")
            statuses = cov["by_status"]
            colors = {"passed": "#27ae60", "in_progress": "#f39c12", "not_started": "#636e72", "failed": "#e74c3c", "waived": "#3498db"}
            fig = go.Figure(go.Pie(
                labels=[s.replace("_", " ").title() for s in statuses.keys()],
                values=list(statuses.values()),
                marker=dict(colors=[colors.get(s, "#888") for s in statuses.keys()]),
                hole=0.5, textinfo="label+value", textfont_size=12,
            ))
            fig.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10),
                              paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig, width="stretch")
            st.markdown("##### By Level")
            for lvl, data in cov["by_level"].items():
                pct = data["pct"] / 100
                st.progress(pct, text=f"{lvl}: {data['verified']}/{data['total']} ({data['pct']:.0f}%)")
            st.markdown("##### By Method")
            for method, count in cov["by_method"].items():
                st.markdown(f"<span class='status-badge badge-blue'>{method.upper()}</span> {count}", unsafe_allow_html=True)

        # Update verification status
        st.divider()
        st.markdown("##### Update Verification Status")
        open_reqs = [r for r in reqs if r.verification_status != "passed"]
        if open_reqs:
            col_r, col_s, col_e, col_b = st.columns([2, 1, 2, 1])
            with col_r:
                sel_req = st.selectbox("Requirement", open_reqs, format_func=lambda r: f"{r.req_id} — {r.title}", key="req_sel")
            with col_s:
                new_status = st.selectbox("New Status", ["in_progress", "passed", "failed", "waived"], key="req_status")
            with col_e:
                evidence = st.text_input("Evidence / reference", key="req_evidence", placeholder="Test report TN-XXX...")
            with col_b:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Submit", type="primary", key="req_submit", disabled=not can("edit_requirement")):
                    own = ownership.get(sel_req.id, {})
                    approver_id = own.get("approver", "U02")
                    approver = get_member(approver_id)
                    approver_name = approver["name"] if approver else "SE"
                    sel_req.verification_status = new_status
                    if DB_ENFORCED and getattr(sel_req, "id", None):
                        update_requirement(sel_req.id, {"verification_status": new_status})
                    st.session_state.approval_log.append({
                        "entity": "requirement", "entity_id": sel_req.id,
                        "action": f"status_{new_status}",
                        "status": "pending", "approver": approver_id,
                        "approved_by_role": approver["role"] if approver else "SE",
                        "date": date.today().isoformat(),
                        "comment": evidence or f"Verification status → {new_status}",
                    })
                    st.rerun()

    with tab_add:
        st.markdown("##### Add New Requirement")
        with st.form("add_req_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                levels = ["stakeholder", "mission", "system", "subsystem", "equipment"]
                new_level = st.selectbox("Level", levels, index=2, key="new_req_level")
                categories = ["functional", "performance", "interface", "environmental", "design", "operational", "reliability", "safety"]
                new_cat = st.selectbox("Category", categories, key="new_req_cat")
                new_title = st.text_input("Title", key="new_req_title", placeholder="Short requirement title")
                new_text = st.text_area("Requirement Text", key="new_req_text", placeholder="The system shall...", height=100)
            with col2:
                methods = ["test", "analysis", "inspection", "review", "demonstration"]
                new_method = st.selectbox("Verification Method", methods, key="new_req_method")
                parent_options = [("", "— None —")] + [(r.id, f"{r.req_id} — {r.title}") for r in reqs]
                new_parent = st.selectbox("Parent Requirement", parent_options, format_func=lambda x: x[1], key="new_req_parent")
                subsys_codes = sorted(set(n["code"] for n in nodes if n["level"] in ("subsystem", "equipment")))
                new_alloc = st.multiselect("Allocate to Subsystem/Equipment", subsys_codes, key="new_req_alloc")
                new_owner = st.selectbox("Owner", get_team(), format_func=lambda m: f"{m['name']} ({m['role']})", key="new_req_owner")
                new_approver = st.selectbox("Approver", [m for m in get_team() if m["role"] in ("SE", "PM", "QA")],
                                            format_func=lambda m: f"{m['name']} ({m['role']})", key="new_req_approver")

            if st.form_submit_button("Add Requirement", type="primary"):
                if not require("edit_requirement"):
                    pass
                elif new_title and new_text:
                    # 🔴 P2 FIX: Validate allocations exist in current product tree
                    valid_codes = set(n["code"] for n in nodes if n["level"] in ("subsystem", "equipment"))
                    invalid_allocs = set(new_alloc) - valid_codes
                    if invalid_allocs:
                        st.error(f"❌ Invalid allocations: {', '.join(invalid_allocs)} not in current product tree")
                        st.stop()
                    
                    from bepi.services.requirements import generate_req_id
                    seq = len([r for r in reqs if r.level == new_level and r.category == new_cat]) + 1
                    req_id_str = generate_req_id(new_level, new_cat, seq)
                    new_id = ""
                    if not DB_ENFORCED:
                        new_id = str(max((int(r.id) for r in reqs if str(r.id).isdigit()), default=0) + 1)
                    new_req = RequirementData(
                        id=new_id, req_id=req_id_str, level=new_level, category=new_cat,
                        title=new_title, text=new_text,
                        parent_id=new_parent[0] if new_parent[0] else None,
                        verification_method=new_method, verification_status="not_started",
                        allocated_to=new_alloc,
                    )
                    if DB_ENFORCED and st.session_state.get("active_mission_id"):
                        created = add_requirement(st.session_state["active_mission_id"], {
                            "req_id": req_id_str,
                            "level": new_level,
                            "category": new_cat,
                            "title": new_title,
                            "text": new_text,
                            "priority": "mandatory",
                            "verification_method": new_method,
                            "verification_status": "not_started",
                        })
                        if created and created.get("id"):
                            new_req.id = str(created["id"])
                            new_req.req_id = created.get("req_id", req_id_str)
                    if not new_req.id:
                        new_req.id = str(max((int(r.id) for r in reqs if str(r.id).isdigit()), default=0) + 1)
                    st.session_state.requirements.append(new_req)
                    st.session_state.req_ownership[new_req.id] = {"owner": new_owner["id"], "approver": new_approver["id"]}
                    st.session_state.approval_log.append({
                        "entity": "requirement", "entity_id": new_req.id,
                        "action": "created", "status": "pending",
                        "approver": new_approver["id"], "approved_by_role": new_approver["role"],
                        "date": date.today().isoformat(),
                        "comment": f"New requirement: {new_req.req_id} — {new_title}",
                    })
                    st.toast(f"Requirement {new_req.req_id} created. Assigned to {new_owner['name']}, approval by {new_approver['name']}.", icon="✅")
                    st.rerun()
                else:
                    st.warning("Both Title and Requirement Text are required.")

    with tab_edit_req:
        st.markdown("##### Edit Requirement")
        if reqs:
            edit_req = st.selectbox("Select requirement", reqs, format_func=lambda r: f"{r.req_id} — {r.title}", key="_req_edit_sel")
            if edit_req:
                er1, er2 = st.columns(2)
                with er1:
                    er_title = st.text_input("Title", value=edit_req.title, key="_req_edit_title")
                    er_text = st.text_area("Text", value=edit_req.text, key="_req_edit_text", height=100)
                    er_level = st.selectbox("Level", ["stakeholder", "mission", "system", "subsystem", "equipment"],
                                            index=["stakeholder", "mission", "system", "subsystem", "equipment"].index(edit_req.level), key="_req_edit_level")
                with er2:
                    er_cat = st.selectbox("Category", ["functional", "performance", "interface", "environmental", "design", "operational", "reliability", "safety"],
                                          index=["functional", "performance", "interface", "environmental", "design", "operational", "reliability", "safety"].index(edit_req.category), key="_req_edit_cat")
                    er_method = st.selectbox("Verification Method", ["test", "analysis", "inspection", "review", "demonstration"],
                                             index=["test", "analysis", "inspection", "review", "demonstration"].index(edit_req.verification_method), key="_req_edit_method")
                    parent_options = [("", "— None —")] + [(r.id, f"{r.req_id} — {r.title}") for r in reqs if r.id != edit_req.id]
                    cur_parent_idx = next((i for i, p in enumerate(parent_options) if p[0] == (edit_req.parent_id or "")), 0)
                    er_parent = st.selectbox("Parent", parent_options, format_func=lambda x: x[1], index=cur_parent_idx, key="_req_edit_parent")
                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.button("Save Changes", type="primary", key="_req_edit_save", disabled=not can("edit_requirement")):
                        edit_req.title = er_title
                        edit_req.text = er_text
                        edit_req.level = er_level
                        edit_req.category = er_cat
                        edit_req.verification_method = er_method
                        edit_req.parent_id = er_parent[0] if er_parent[0] else None
                        if DB_ENFORCED and getattr(edit_req, "id", None):
                            update_requirement(edit_req.id, {
                                "title": er_title,
                                "description": er_text,
                                "level": er_level,
                                "category": er_cat,
                                "verification_method": er_method,
                                "parent_id": edit_req.parent_id,
                            })
                        st.toast(f"{edit_req.req_id} updated", icon="✅")
                        st.rerun()
                with ec2:
                    if st.button("Delete Requirement", key="_req_del_btn", disabled=not can("edit_requirement")):
                        if DB_ENFORCED and getattr(edit_req, "id", None):
                            delete_requirement(edit_req.id)
                        st.session_state.requirements = [r for r in st.session_state.requirements if r.id != edit_req.id]
                        st.session_state.req_ownership.pop(edit_req.id, None)
                        st.toast(f"{edit_req.req_id} deleted", icon="✅")
                        st.rerun()

    with tab_assign:
        if not reqs:
            st.info("No requirements yet. Add requirements first.")
        else:
            st.markdown("##### Assign Requirement to Subsystem")
            col_ar, col_an, col_ab = st.columns([2, 2, 1])
            with col_ar:
                sel_assign_req = st.selectbox("Requirement", reqs, format_func=lambda r: f"{r.req_id} — {r.title}", key="req_assign_sel")
            with col_an:
                subsys_codes = sorted(set(n["code"] for n in nodes if n["level"] in ("subsystem", "equipment")))
                current = sel_assign_req.allocated_to if sel_assign_req else []
                new_nodes = st.multiselect("Allocate to", subsys_codes, default=current, key="req_assign_nodes")
            with col_ab:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Update Allocation", type="primary", key="req_assign_btn"):
                    sel_assign_req.allocated_to = new_nodes
                    st.toast(f"{sel_assign_req.req_id} allocated to: {', '.join(new_nodes) or '—'}", icon="✅")
                    st.rerun()

            st.divider()
            st.markdown("##### Change Requirement Owner")
            col_or, col_oo, col_oa, col_ob = st.columns([2, 1.5, 1.5, 1])
            with col_or:
                sel_own_req = st.selectbox("Requirement", reqs, format_func=lambda r: f"{r.req_id} — {r.title}", key="req_own_sel")
            with col_oo:
                cur_own = ownership.get(sel_own_req.id, {})
                own_idx = next((i for i, m in enumerate(get_team()) if m["id"] == cur_own.get("owner")), 0)
                new_own = st.selectbox("Owner", get_team(), format_func=lambda m: f"{m['name']} ({m['role']})", index=own_idx, key="req_own_member")
            with col_oa:
                approvers = [m for m in get_team() if m["role"] in ("SE", "PM", "QA")]
                app_idx = next((i for i, m in enumerate(approvers) if m["id"] == cur_own.get("approver")), 0)
                new_app = st.selectbox("Approver", approvers, format_func=lambda m: f"{m['name']} ({m['role']})", index=app_idx, key="req_own_approver")
            with col_ob:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Update Owner", type="primary", key="req_own_btn"):
                    st.session_state.req_ownership[sel_own_req.id] = {"owner": new_own["id"], "approver": new_app["id"]}
                    st.toast(f"{sel_own_req.req_id}: owner → {new_own['name']}, approver → {new_app['name']}", icon="✅")
                    st.rerun()

            st.divider()
            st.markdown("##### Traceability Tree")
            sel_trace = st.selectbox("Select requirement", reqs, format_func=lambda r: f"{r.req_id} — {r.title}", key="req_trace_sel")
            if sel_trace:
                parent_chain = []
                r = sel_trace
                while r.parent_id:
                    parent = next((x for x in reqs if x.id == r.parent_id), None)
                    if parent:
                        parent_chain.insert(0, parent)
                        r = parent
                    else:
                        break
                children = [x for x in reqs if x.parent_id == sel_trace.id]
                tree_md = ""
                for i, p in enumerate(parent_chain):
                    tree_md += "&nbsp;" * (i * 4) + f"📄 **{p.req_id}** — {p.title}  \n"
                tree_md += "&nbsp;" * (len(parent_chain) * 4) + f"➡️ **{sel_trace.req_id}** — {sel_trace.title}  \n"
                for ch in children:
                    tree_md += "&nbsp;" * ((len(parent_chain) + 1) * 4) + f"📄 **{ch.req_id}** — {ch.title}  \n"
                st.markdown(tree_md, unsafe_allow_html=True)


def page_risks():
    colored_header(label="Risk Management", description="Risk matrix, register & FMECA", color_name="red-70")
    risks = get_risks()
    rm = risk_matrix(risks)

    tab_matrix, tab_register, tab_add_risk, tab_edit_risk, tab_fmeca = st.tabs(["Risk Matrix", "Risk Register", "Add Risk", "Edit / Delete", "FMECA"])

    with tab_matrix:
        matrix = rm["matrix"]
        cells = rm["cells"]
        z = [[0]*5 for _ in range(5)]
        text = [["" for _ in range(5)] for _ in range(5)]
        for li in range(5):
            for ci in range(5):
                z[li][ci] = matrix[li][ci]
                ids = cells.get((li+1, ci+1), [])
                text[li][ci] = "<br>".join(ids) if ids else ""

        score_z = [[(li+1)*(ci+1) for ci in range(5)] for li in range(5)]
        fig = go.Figure(go.Heatmap(
            z=score_z, text=text, texttemplate="%{text}",
            x=["1 - Negligible", "2 - Minor", "3 - Moderate", "4 - Major", "5 - Catastrophic"],
            y=["1 - Rare", "2 - Unlikely", "3 - Possible", "4 - Likely", "5 - Almost certain"],
            colorscale=[[0, "#1a5e1a"], [0.3, "#7fb800"], [0.55, "#f5a623"], [0.8, "#d0021b"], [1, "#8b0000"]],
            showscale=False, hoverinfo="text",
            textfont=dict(size=11, color="white"),
        ))
        fig.update_layout(
            xaxis_title="Consequence", yaxis_title="Likelihood",
            height=480, margin=dict(t=30, b=60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, width="stretch")

        c1, c2, c3, c4 = st.columns(4)
        colors_risk = {"critical": "red", "high": "orange", "medium": "yellow", "low": "green"}
        for col, (lvl, cnt) in zip([c1,c2,c3,c4], rm["summary"].items()):
            col.metric(lvl.capitalize(), cnt)

    with tab_register:
        # Apply risk overrides from session_state
        _ro = st.session_state.get("risk_overrides", {})
        for r in risks:
            if r.risk_id in _ro:
                ov = _ro[r.risk_id]
                r.status = ov.get("status", r.status)
                r.residual_likelihood = ov.get("residual_l", r.residual_likelihood)
                r.residual_consequence = ov.get("residual_c", r.residual_consequence)
        df_risk = pd.DataFrame([
            {"ID": r.risk_id, "Title": r.title, "Cat.": r.category.upper()[:4],
             "L": r.likelihood, "C": r.consequence, "Score": r.risk_score,
             "Level": r.risk_level.upper(), "Status": r.status, "Owner": r.owner,
             "Mitigation": r.mitigation_strategy[:40] + "..." if len(r.mitigation_strategy) > 40 else r.mitigation_strategy}
            for r in risks
        ])
        risk_status_opts = ["open", "mitigating", "accepted", "closed"]
        if can("edit_risk") and not df_risk.empty:
            edited_risk_df = st.data_editor(
                df_risk, key="_risk_reg_editor", hide_index=True, width="stretch", height=400,
                column_config={
                    "ID": st.column_config.TextColumn(disabled=True),
                    "Title": st.column_config.TextColumn(disabled=True),
                    "Cat.": st.column_config.TextColumn(disabled=True),
                    "L": st.column_config.NumberColumn(min_value=1, max_value=5),
                    "C": st.column_config.NumberColumn(min_value=1, max_value=5),
                    "Score": st.column_config.NumberColumn(disabled=True),
                    "Level": st.column_config.TextColumn(disabled=True),
                    "Status": st.column_config.SelectboxColumn(options=risk_status_opts, required=True),
                    "Owner": st.column_config.TextColumn(disabled=True),
                    "Mitigation": st.column_config.TextColumn(disabled=True),
                },
            )
            if not edited_risk_df[["L", "C", "Status"]].equals(df_risk[["L", "C", "Status"]]):
                for i, row in edited_risk_df.iterrows():
                    if i < len(risks):
                        r = risks[i]
                        new_l, new_c, new_s = int(row["L"]), int(row["C"]), row["Status"]
                        if new_l != r.likelihood or new_c != r.consequence or new_s != r.status:
                            st.session_state.risk_overrides[r.risk_id] = {
                                "status": new_s, "residual_l": new_l, "residual_c": new_c}
                            r.likelihood, r.consequence, r.status = new_l, new_c, new_s
                            r.risk_score = new_l * new_c
                            if DB_ENFORCED and getattr(r, "id", None):
                                update_risk(r.id, {"likelihood": new_l, "consequence": new_c, "status": new_s})
                st.rerun()
        else:
            st.dataframe(df_risk, width="stretch", hide_index=True, height=400)

        st.divider()
        st.markdown("##### Update Risk")
        open_risks = [r for r in risks if r.status in ("open", "mitigating")]
        if open_risks:
            col_r, col_l, col_c, col_s, col_b = st.columns([2, 1, 1, 1, 1])
            with col_r:
                sel_risk = st.selectbox("Risk", open_risks, format_func=lambda r: f"{r.risk_id} — {r.title}", key="risk_sel")
            with col_l:
                new_l = st.number_input("Residual L", 1, 5, value=sel_risk.residual_likelihood or sel_risk.likelihood, key="risk_l")
            with col_c:
                new_c = st.number_input("Residual C", 1, 5, value=sel_risk.residual_consequence or sel_risk.consequence, key="risk_c")
            with col_s:
                new_rs = st.selectbox("Status", ["open", "mitigating", "accepted", "closed"], key="risk_status",
                                      index=["open", "mitigating", "accepted", "closed"].index(sel_risk.status))
            with col_b:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Submit", type="primary", key="risk_submit", disabled=not can("edit_risk")):
                    st.session_state.risk_overrides[sel_risk.risk_id] = {
                        "status": new_rs, "residual_l": new_l, "residual_c": new_c}
                    if DB_ENFORCED and getattr(sel_risk, "id", None):
                        update_risk(sel_risk.id, {"likelihood": new_l, "consequence": new_c, "status": new_rs})
                    st.session_state.approval_log.append({
                        "entity": "risk", "entity_id": sel_risk.risk_id,
                        "action": f"update_L{new_l}C{new_c}_{new_rs}",
                        "status": "pending", "approver": "U01",
                        "approved_by_role": "PM",
                        "date": date.today().isoformat(),
                        "comment": f"Residual L={new_l}, C={new_c}, status→{new_rs}",
                    })
                    st.toast(f"Risk {sel_risk.risk_id} update submitted. Awaiting PM approval.", icon="✅")
                    st.rerun()

    with tab_add_risk:
        st.markdown("##### Add New Risk")
        with st.form("add_risk_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                risk_title = st.text_input("Risk Title", key="new_risk_title", placeholder="Short risk description")
                risk_desc = st.text_area("Description", key="new_risk_desc", placeholder="Detailed description...", height=100)
                risk_cat = st.selectbox("Category", ["technical", "schedule", "cost", "programmatic", "external"], key="new_risk_cat")
            with col2:
                risk_l = st.slider("Likelihood", 1, 5, 3, key="new_risk_l")
                risk_c = st.slider("Consequence", 1, 5, 3, key="new_risk_c")
                risk_owner = st.selectbox("Owner", get_team(), format_func=lambda m: f"{m['name']} ({m['role']})", key="new_risk_owner")
                risk_mitigation = st.text_area("Mitigation Strategy", key="new_risk_mit", placeholder="Describe mitigation...", height=80)
            if st.form_submit_button("Add Risk", type="primary"):
                if not require("edit_risk"):
                    pass
                elif risk_title:
                    _max_rid = max((int(r.risk_id.split("-")[1]) for r in risks if r.risk_id.startswith("RSK-")), default=0)
                    new_rid = f"RSK-{_max_rid+1:03d}"
                    new_id = ""
                    if not DB_ENFORCED:
                        new_id = str(_max_rid + 1)
                    new_risk = RiskItemData(
                        id=new_id, risk_id=new_rid, title=risk_title, description=risk_desc,
                        category=risk_cat, likelihood=risk_l, consequence=risk_c,
                        status="open", owner=risk_owner["name"],
                        mitigation_strategy=risk_mitigation,
                    )
                    if DB_ENFORCED and st.session_state.get("active_mission_id"):
                        created = add_risk(st.session_state["active_mission_id"], {
                            "risk_id": new_rid,
                            "title": risk_title,
                            "description": risk_desc,
                            "category": risk_cat,
                            "likelihood": risk_l,
                            "consequence": risk_c,
                            "risk_level": "medium",
                            "status": "open",
                            "owner": risk_owner["name"],
                            "mitigation_strategy": risk_mitigation,
                        })
                        if created and created.get("id"):
                            new_risk.id = str(created["id"])
                            new_risk.risk_id = created.get("risk_id", new_rid)
                    if not new_risk.id:
                        new_risk.id = str(_max_rid + 1)
                    st.session_state.risks.append(new_risk)
                    st.session_state.approval_log.append({
                        "entity": "risk", "entity_id": new_risk.id,
                        "action": "created", "status": "pending",
                        "approver": "U01", "approved_by_role": "PM",
                        "date": date.today().isoformat(),
                        "comment": f"New risk: {new_risk.risk_id} — {risk_title}",
                    })
                    st.toast(f"Risk {new_risk.risk_id} added (L={risk_l}, C={risk_c}, Score={risk_l*risk_c}). Awaiting PM approval.", icon="✅")
                    st.rerun()
                else:
                    st.warning("Risk title is required.")

    with tab_edit_risk:
        st.markdown("##### Edit / Delete Risk")
        if risks:
            edit_risk = st.selectbox("Select risk", risks, format_func=lambda r: f"{r.risk_id} — {r.title}", key="_risk_edit_sel")
            if edit_risk:
                re1, re2 = st.columns(2)
                with re1:
                    re_title = st.text_input("Title", value=edit_risk.title, key="_risk_edit_title")
                    re_desc = st.text_area("Description", value=edit_risk.description, key="_risk_edit_desc", height=80)
                    re_cat = st.selectbox("Category", ["technical", "schedule", "cost", "programmatic", "external"],
                                          index=["technical", "schedule", "cost", "programmatic", "external"].index(edit_risk.category), key="_risk_edit_cat")
                with re2:
                    re_owner = st.text_input("Owner", value=edit_risk.owner, key="_risk_edit_owner")
                    re_mit = st.text_area("Mitigation", value=edit_risk.mitigation_strategy, key="_risk_edit_mit", height=80)
                    re_l = st.slider("Likelihood", 1, 5, value=edit_risk.likelihood, key="_risk_edit_l")
                    re_c = st.slider("Consequence", 1, 5, value=edit_risk.consequence, key="_risk_edit_c")
                rb1, rb2 = st.columns(2)
                with rb1:
                    if st.button("Save Changes", type="primary", key="_risk_edit_save", disabled=not can("edit_risk")):
                        edit_risk.title = re_title
                        edit_risk.description = re_desc
                        edit_risk.category = re_cat
                        edit_risk.owner = re_owner
                        edit_risk.mitigation_strategy = re_mit
                        edit_risk.likelihood = re_l
                        edit_risk.consequence = re_c
                        if DB_ENFORCED and getattr(edit_risk, "id", None):
                            update_risk(edit_risk.id, {
                                "title": re_title,
                                "description": re_desc,
                                "category": re_cat,
                                "likelihood": re_l,
                                "consequence": re_c,
                                "owner": re_owner,
                                "mitigation_strategy": re_mit,
                            })
                        st.toast(f"{edit_risk.risk_id} updated", icon="✅")
                        st.rerun()
                with rb2:
                    if st.button("Delete Risk", key="_risk_del_btn", disabled=not can("edit_risk")):
                        if DB_ENFORCED and getattr(edit_risk, "id", None):
                            delete_risk(edit_risk.id)
                        st.session_state.risks = [r for r in st.session_state.risks if r.id != edit_risk.id]
                        st.toast(f"{edit_risk.risk_id} deleted", icon="✅")
                        st.rerun()

    with tab_fmeca:
        if "fmeca_entries" not in st.session_state:
            st.session_state.fmeca_entries = []
        entries = st.session_state.fmeca_entries
        ranked = fmeca_ranking(entries) if entries else []
        st.markdown("##### Failure Modes by RPN")
        if ranked:
            df_fm = pd.DataFrame([
                {"Node": e.node_code, "Failure Mode": e.failure_mode,
                 "S": e.severity, "O": e.occurrence, "D": e.detection,
                 "RPN": e.rpn, "Crit.": e.criticality or "", "Mitigation": e.mitigation}
                for e in ranked
            ])
            if can("edit_fmeca"):
                edited_fm = st.data_editor(
                    df_fm, key="_fmeca_editor", hide_index=True, width="stretch",
                    column_config={
                        "Node": st.column_config.TextColumn(disabled=True),
                        "Failure Mode": st.column_config.TextColumn(disabled=True),
                        "S": st.column_config.NumberColumn(min_value=1, max_value=5),
                        "O": st.column_config.NumberColumn(min_value=1, max_value=5),
                        "D": st.column_config.NumberColumn(min_value=1, max_value=5),
                        "RPN": st.column_config.NumberColumn(disabled=True),
                        "Crit.": st.column_config.TextColumn(disabled=True),
                        "Mitigation": st.column_config.TextColumn(),
                    },
                )
                if not edited_fm[["S", "O", "D", "Mitigation"]].equals(df_fm[["S", "O", "D", "Mitigation"]]):
                    for i, row in edited_fm.iterrows():
                        if i < len(ranked):
                            entry = ranked[i]
                            entry.severity = int(row["S"])
                            entry.occurrence = int(row["O"])
                            entry.detection = int(row["D"])
                            entry.mitigation = row["Mitigation"]
                            entry.criticality = compute_criticality(int(row["S"]), int(row["O"]))
                            if DB_ENFORCED and getattr(entry, "id", None):
                                node_map = {n["code"]: n.get("id") for n in _get_product_tree()}
                                node_id = node_map.get(entry.node_code)
                                if node_id:
                                    update_fmeca_entry(entry.id, {
                                        "node_id": node_id,
                                        "severity": entry.severity,
                                        "occurrence": entry.occurrence,
                                        "detection": entry.detection,
                                        "mitigation": entry.mitigation,
                                        "criticality": entry.criticality,
                                    })
                    st.rerun()
            else:
                st.dataframe(df_fm, width="stretch", hide_index=True)

            fig = go.Figure(go.Bar(
                x=[e.node_code + " — " + e.failure_mode[:20] for e in ranked[:10]],
                y=[e.rpn for e in ranked[:10]],
                marker_color=["#e74c3c" if e.rpn >= 40 else "#f39c12" if e.rpn >= 20 else "#27ae60" for e in ranked[:10]],
                marker_line=dict(width=0),
            ))
            fig.update_layout(yaxis_title="RPN", height=350, margin=dict(t=20, b=100),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig.update_xaxes(tickangle=-35, gridcolor="rgba(128,128,128,0.1)")
            fig.update_yaxes(gridcolor="rgba(128,128,128,0.1)")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No FMECA entries. Add failure modes below.")

        st.divider()
        st.markdown("##### Add Failure Mode")
        with st.form("add_fmeca_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            equip_nodes = [n for n in _get_product_tree() if n["level"] == "equipment"]
            with fc1:
                fm_node = st.selectbox("Component", [n["code"] for n in equip_nodes] if equip_nodes else ["N/A"], key="_fm_node")
                fm_mode = st.text_input("Failure Mode", key="_fm_mode", placeholder="e.g. Open circuit")
                fm_cause = st.text_input("Failure Cause", key="_fm_cause")
            with fc2:
                fm_s = st.slider("Severity (S)", 1, 5, 3, key="_fm_s")
                fm_o = st.slider("Occurrence (O)", 1, 5, 2, key="_fm_o")
                fm_d = st.slider("Detection (D)", 1, 5, 3, key="_fm_d")
                fm_mit = st.text_input("Mitigation", key="_fm_mit")
            if st.form_submit_button("Add Entry", type="primary"):
                if not require("edit_fmeca"):
                    pass
                elif fm_mode:
                    _max_fid = max((int(e.id) for e in entries if str(e.id).isdigit()), default=0)
                    new_entry = FMECAEntryData(
                        id=str(_max_fid + 1), node_code=fm_node, failure_mode=fm_mode,
                        failure_cause=fm_cause, local_effect="N/A", system_effect="N/A",
                        severity=fm_s, occurrence=fm_o, detection=fm_d,
                        mitigation=fm_mit, criticality=compute_criticality(fm_s, fm_o),
                    )
                    if DB_ENFORCED and st.session_state.get("active_mission_id"):
                        node_map = {n["code"]: n.get("id") for n in _get_product_tree()}
                        node_id = node_map.get(fm_node)
                        if node_id:
                            created = add_fmeca_entry({
                                "node_id": node_id,
                                "failure_mode": fm_mode,
                                "failure_cause": fm_cause,
                                "local_effect": new_entry.local_effect,
                                "system_effect": new_entry.system_effect,
                                "severity": fm_s,
                                "occurrence": fm_o,
                                "detection": fm_d,
                                "mitigation": fm_mit,
                                "criticality": new_entry.criticality,
                            })
                            if created and created.get("id"):
                                new_entry.id = str(created["id"])
                    entries.append(new_entry)
                    st.toast(f"FMECA entry added: {fm_node} — {fm_mode} (RPN={fm_s*fm_o*fm_d})", icon="✅")
                    st.rerun()
                else:
                    st.warning("Failure mode is required.")


def page_schedule():
    colored_header(label="Schedule", description="Gantt chart, critical path & milestones", color_name="light-blue-70")
    all_tasks = get_tasks()
    project_start = date(2025, 10, 1)
    cpm = compute_cpm(all_tasks, project_start)

    # Filter bar
    col_fp, col_fc = st.columns([1, 1])
    with col_fp:
        filter_person = st.selectbox("Filter by Person", ["All"] + [m["name"] for m in get_team()], key="sched_fperson")
    with col_fc:
        filter_crit = st.checkbox("Critical path only", key="sched_fcrit")
    ta = get_task_assignments()
    tasks = all_tasks
    if filter_person != "All":
        pid = next((m["id"] for m in get_team() if m["name"] == filter_person), None)
        if pid:
            tasks = [t for t in tasks if ta.get(t.id, {}).get("responsible") == pid
                     or pid in ta.get(t.id, {}).get("contributors", [])]
    if filter_crit:
        tasks = [t for t in tasks if t.id in cpm.critical_path]

    gdata = gantt_data(tasks, cpm, project_start)

    c1, c2, c3 = st.columns(3)
    c1.metric("Duration", f"{cpm.project_duration} days")
    c2.metric("End Date", str(cpm.project_end_date))
    c3.metric("Critical Tasks", sum(1 for t in all_tasks if t.id in cpm.critical_path and not t.is_milestone))

    st.markdown("<br>", unsafe_allow_html=True)

    _has_gantt = bool(gdata)
    if not _has_gantt:
        st.info("No tasks to display on the Gantt chart. Use **Add Task** below to create tasks.")
    else:
        df = pd.DataFrame(gdata)
        fig = go.Figure()

        task_names = list(reversed(df["Task"].tolist()))
        bar_h = 0.35

        for _, row in df.iterrows():
            is_milestone = row["Start"] == row["Finish"]
            is_critical = row["Critical"]
            progress = row["Progress"] / 100.0
            task_name = row["Task"]
            y_idx = task_names.index(task_name)

            if is_milestone:
                fig.add_trace(go.Scatter(
                    x=[pd.Timestamp(row["Start"])], y=[y_idx],
                    mode="markers", marker=dict(size=14, symbol="diamond", color="#9b59b6",
                                                line=dict(width=2, color="white")),
                    showlegend=False,
                    hovertext=f"{task_name}<br>{row['Start']}",
                    hoverinfo="text",
                ))
            else:
                bar_color = "#e74c3c" if is_critical else "#3498db"
                done_color = "#27ae60" if progress >= 1.0 else ("#c0392b" if is_critical else "#2980b9")
                remaining_color = "rgba(200,200,200,0.25)" if not is_critical else "rgba(231,76,60,0.15)"

                start_dt = pd.Timestamp(row["Start"])
                finish_dt = pd.Timestamp(row["Finish"])
                duration = finish_dt - start_dt
                done_end = start_dt + duration * progress

                fig.add_shape(type="rect", x0=start_dt, x1=finish_dt, y0=y_idx - bar_h, y1=y_idx + bar_h,
                              fillcolor=remaining_color, line=dict(color=bar_color, width=1.5))

                if progress > 0:
                    fig.add_shape(type="rect", x0=start_dt, x1=done_end, y0=y_idx - bar_h, y1=y_idx + bar_h,
                                  fillcolor=done_color, line=dict(width=0))

                mid_dt = start_dt + duration / 2
                fig.add_trace(go.Scatter(
                    x=[mid_dt], y=[y_idx], mode="markers",
                    marker=dict(size=0.1, opacity=0),
                    showlegend=False,
                    hovertext=f"<b>{task_name}</b><br>{row['Start']} → {row['Finish']}<br>Progress: {row['Progress']:.0f}%{'<br>⚠ CRITICAL' if is_critical else ''}",
                    hoverinfo="text",
                ))

                if 0 < progress < 1.0:
                    mid = start_dt + duration * progress / 2
                    fig.add_annotation(x=mid, y=y_idx, text=f"{row['Progress']:.0f}%",
                                       showarrow=False, font=dict(size=9, color="white"))

        today_str = date.today().isoformat()
        fig.add_shape(type="line", x0=today_str, x1=today_str,
                      y0=-0.5, y1=len(task_names) - 0.5,
                      line=dict(color="#f39c12", width=1.5, dash="dot"))
        fig.add_annotation(x=today_str, y=len(task_names) - 0.5, text="Today",
                           showarrow=False, font=dict(color="#f39c12", size=10),
                           yshift=12)

        fig.update_layout(
            height=520, xaxis_title="",
            xaxis=dict(type="date", tickformat="W%V\n%b %Y", dtick="M1"),
            yaxis=dict(tickmode="array", tickvals=list(range(len(task_names))), ticktext=task_names, fixedrange=True),
            margin=dict(t=30, b=40, l=240, r=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            hovermode="closest",
        )
        fig.update_xaxes(gridcolor="rgba(128,128,128,0.15)", showgrid=True)
        fig.update_yaxes(gridcolor="rgba(128,128,128,0.05)", showgrid=True, range=[-0.5, len(task_names) - 0.5])

        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color="#2980b9"),
                                 name="Completed", showlegend=True))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color="rgba(200,200,200,0.4)"),
                                 name="Remaining", showlegend=True))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color="#e74c3c"),
                                 name="Critical Path", showlegend=True))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, symbol="diamond", color="#9b59b6"),
                                 name="Milestone", showlegend=True))
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                      font=dict(size=11)))

        st.plotly_chart(fig, width="stretch")

        st.markdown("##### Critical Path")
        cp_names = [t.name for t in tasks if t.id in cpm.critical_path]
        if cp_names:
            sac.steps(
                [sac.StepsItem(title=n) for n in cp_names],
                index=len(cp_names)-1, return_index=False, size="sm",
            )

    st.markdown("##### Task Details & Assignments")
    detail_rows = []
    task_id_list = []
    for t in tasks:
        info = cpm.tasks.get(t.id, {"start_date": "", "end_date": "", "slack": 0})
        assign = get_task_assignments().get(t.id, {})
        resp = get_member(assign.get("responsible", ""))
        appr = get_member(assign.get("approver", ""))
        latest = get_latest_approval("task", t.id) or get_latest_approval("milestone", t.id)
        task_id_list.append(t.id)
        detail_rows.append({
            "WBS": t.wbs_code, "Task": t.name, "Duration": t.duration_days,
            "Start": str(info.get("start_date", "")), "End": str(info.get("end_date", "")),
            "Slack": info["slack"], "Progress (%)": int(t.progress_pct),
            "Predecessors": ", ".join(t.predecessors),
            "Responsible": resp["name"] if resp else "",
            "Critical": "⚠" if t.id in cpm.critical_path else "",
        })
    detail_df = pd.DataFrame(detail_rows)
    edited_sched = st.data_editor(
        detail_df, key="_sched_editor", hide_index=True, width="stretch",
        column_config={
            "WBS": st.column_config.TextColumn(disabled=True),
            "Task": st.column_config.TextColumn(),
            "Duration": st.column_config.NumberColumn(min_value=0, step=1),
            "Start": st.column_config.TextColumn(disabled=True, help="Computed by CPM"),
            "End": st.column_config.TextColumn(disabled=True, help="Computed by CPM"),
            "Slack": st.column_config.NumberColumn(disabled=True),
            "Progress (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=5),
            "Predecessors": st.column_config.TextColumn(help="Comma-separated task IDs (e.g. T01, T02)"),
            "Responsible": st.column_config.TextColumn(disabled=True),
            "Critical": st.column_config.TextColumn(disabled=True),
        },
    )
    if st.button("Save Schedule Changes", key="_sched_save", type="primary"):
        for i, tid in enumerate(task_id_list):
            t = next((tk for tk in st.session_state.tasks if tk.id == tid), None)
            if t:
                row = edited_sched.iloc[i]
                t.name = row["Task"]
                t.duration_days = int(row["Duration"])
                t.progress_pct = float(row["Progress (%)"])
                preds_str = str(row.get("Predecessors", "")).strip()
                t.predecessors = [p.strip() for p in preds_str.split(",") if p.strip()] if preds_str else []
        st.rerun()

    # Interactive: update progress & request approval
    st.divider()
    st.markdown("##### Update Task Progress")
    active_tasks = [t for t in tasks if not t.is_milestone and t.progress_pct < 100]
    if active_tasks:
        col_sel, col_prog, col_comm, col_btn = st.columns([2, 1, 2, 1])
        with col_sel:
            selected_task = st.selectbox("Task", active_tasks, format_func=lambda t: f"{t.wbs_code} — {t.name}", key="sched_task_sel")
        with col_prog:
            new_progress = st.number_input("New %", min_value=0, max_value=100, value=int(selected_task.progress_pct), step=5, key="sched_prog")
        with col_comm:
            comment = st.text_input("Comment", key="sched_comment", placeholder="Progress justification...")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Submit for Approval", type="primary", key="sched_submit", disabled=not (can("edit_schedule") or can("update_progress"))):
                assign = get_task_assignments().get(selected_task.id, {})
                approver_id = assign.get("approver", "U01")
                approver = get_member(approver_id)
                approver_name = approver["name"] if approver else "PM"
                selected_task.progress_pct = new_progress
                st.session_state.approval_log.append({
                    "entity": "task", "entity_id": selected_task.id,
                    "action": f"progress_{new_progress}%",
                    "status": "pending", "approver": approver_id,
                    "approved_by_role": approver["role"] if approver else "PM",
                    "date": date.today().isoformat(),
                    "comment": comment or f"Progress updated to {new_progress}%",
                })
                st.toast(f"Progress update ({new_progress}%) submitted. Awaiting approval from {approver_name}.", icon="✅")
                st.rerun()

    # Remove task
    st.divider()
    st.markdown("##### Remove Task")
    rm_task = st.selectbox("Select task", all_tasks, format_func=lambda t: f"{t.id} — {t.name}", key="_sched_rm_sel")
    if rm_task:
        deps = [t.name for t in all_tasks if rm_task.id in t.predecessors]
        if deps:
            st.warning(f"This task is a predecessor of: {', '.join(deps)}. Removing it will clear those dependencies.")
        if st.button("Remove Task", type="primary", key="_sched_rm_btn", disabled=not can("edit_schedule")):
            for t in st.session_state.tasks:
                if rm_task.id in t.predecessors:
                    t.predecessors.remove(rm_task.id)
            st.session_state.tasks = [t for t in st.session_state.tasks if t.id != rm_task.id]
            st.rerun()

    # Interactive: approve pending items
    pending = [a for a in get_approval_log() if a["status"] == "pending"]
    if pending:
        st.divider()
        st.markdown("##### Pending Approvals")
        for _ai, a in enumerate(pending):
            entity_label = f"{a['entity'].title()} {a['entity_id']}"
            approver = get_member(a["approver"])
            is_designated = a.get("approver") == current_user["id"]
            is_pm = current_user["role"] == "PM"
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            col1.markdown(f"**{entity_label}**: {a['action']}")
            col2.markdown(f"*{a['comment']}*")
            if is_designated or is_pm:
                with col3:
                    if st.button("✅ Approve", key=f"appr_{_ai}_{a['entity_id']}"):
                        a["status"] = "approved"
                        st.rerun()
                with col4:
                    if st.button("❌ Reject", key=f"rej_{_ai}_{a['entity_id']}"):
                        a["status"] = "rejected"
                        st.rerun()
            else:
                approver_name = approver["name"] if approver else "?"
                col3.caption(f"Awaiting {approver_name}")


    # Add task
    st.divider()
    st.markdown("##### Add Task")
    with st.form("add_task_form", clear_on_submit=True):
        col_n, col_d, col_w, col_p, col_r2 = st.columns([2, 0.8, 0.8, 2, 1.5])
        with col_n:
            task_name = st.text_input("Task Name", key="new_task_name", placeholder="Task description")
        with col_d:
            task_dur = st.number_input("Days", 1, 365, 30, key="new_task_dur")
        with col_w:
            task_wbs = st.text_input("WBS", key="new_task_wbs", placeholder="2.4")
        with col_p:
            pred_options = [t for t in tasks if not t.is_milestone]
            task_preds = st.multiselect("Predecessors", pred_options, format_func=lambda t: f"{t.wbs_code} — {t.name}", key="new_task_preds")
        with col_r2:
            task_resp = st.selectbox("Responsible", get_team(), format_func=lambda m: f"{m['name']} ({m['role']})", key="new_task_resp")
        if st.form_submit_button("Add Task", type="primary"):
            if not require("edit_schedule"):
                pass
            elif task_name:
                existing_nums = [int(t.id.replace("T", "").replace("M_", "")) for t in all_tasks if t.id.replace("T", "").replace("M_", "").isdigit()]
                new_id = f"T{max(existing_nums, default=0) + 1:02d}"
                pred_ids = [t.id for t in task_preds]
                new_task = TaskData(new_id, task_name, task_dur, pred_ids, wbs_code=task_wbs or new_id,
                                   assigned_to=f"{task_resp['name']} ({task_resp['role']})")
                st.session_state.tasks.append(new_task)
                st.session_state.task_assignments[new_id] = {
                    "responsible": task_resp["id"], "approver": "U01", "contributors": [task_resp["id"]]}
                st.toast(f"Task '{task_name}' added ({task_dur}d, WBS {task_wbs})", icon="✅")
                st.rerun()
            else:
                st.warning("Task name is required.")


def page_ecss():
    colored_header(label="ECSS Framework", description="Standards, phases, reviews & margin policy", color_name="gray-70")

    # Framework selector
    col_fw, col_phase = st.columns([1, 2])
    with col_fw:
        fw_name = st.selectbox("Framework", ["ESA", "NASA"], key="_ecss_fw")
    fw = get_framework(fw_name)
    phases_def = fw["phases"]
    gate_reviews = fw["gate_reviews"]
    trl_targets = fw["trl_targets"]
    activities = fw["activities"]
    phase_ids = list(phases_def.keys())

    with col_phase:
        current_phase = st.selectbox(
            "Current Project Phase",
            phase_ids,
            format_func=lambda p: f"{p} — {phases_def[p]['name']}",
            index=min(3, len(phase_ids) - 1),
            key="_ecss_phase",
        )

    st.session_state["mission_phase"] = current_phase
    st.session_state["mission_framework"] = fw_name
    
    # 🔴 P1 FIX: Persist framework + phase to DB
    client = get_supabase()
    mission_id = st.session_state.get("active_mission_id")
    if client and mission_id:
        try:
            existing_meta = st.session_state.missions.get(mission_id, {}).get("metadata", {}) or {}
            updated_meta = {**existing_meta, "framework": fw_name}
            client.table("missions").update({
                "phase": current_phase,
                "metadata": updated_meta,
            }).eq("id", mission_id).execute()
            st.session_state.missions[mission_id]["mission_phase"] = current_phase
            st.session_state.missions[mission_id]["mission_framework"] = fw_name
            st.session_state.missions[mission_id]["metadata"] = updated_meta
        except Exception as e:
            st.warning(f"⚠️ Could not save framework/phase to DB: {e}")

    # Phase info metrics
    p_info = phases_def[current_phase]
    gate = None
    for (p_from, _), rev in gate_reviews.items():
        if p_from == current_phase:
            gate = rev
            break
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Phase", current_phase)
    c2.metric("Key Activity", p_info["key_activity"])
    c3.metric("Typical Duration", f"{p_info['typical_duration_months']} mo")
    c4.metric("Gate Review", gate or "—")

    st.markdown("<br>", unsafe_allow_html=True)

    # Phase overview table
    st.markdown("##### Phase Overview")
    phase_data = []
    for pid, pdef in phases_def.items():
        g = None
        for (pf, _), rev in gate_reviews.items():
            if pf == pid:
                g = rev
                break
        trl = trl_targets.get(pid, {})
        phase_data.append({
            "Phase": pid, "Name": pdef["name"],
            "Duration (mo)": pdef["typical_duration_months"],
            "Key Activity": pdef["key_activity"],
            "Gate Review": g or "—",
            "TRL Target": f"{trl.get('min', '—')}–{trl.get('target', '—')}" if trl else "—",
        })
    df_phases = pd.DataFrame(phase_data)
    st.dataframe(df_phases, width="stretch", hide_index=True)

    st.divider()

    # Review timeline
    st.markdown("##### Review Timeline")
    review_list = []
    for pid in phase_ids:
        for (pf, _), rev in gate_reviews.items():
            if pf == pid and rev not in review_list:
                review_list.append(rev)
    current_gate_idx = 0
    for i, rev in enumerate(review_list):
        for (pf, _), r in gate_reviews.items():
            if r == rev and pf == current_phase:
                current_gate_idx = i
    step_items = [sac.StepsItem(title=rev) for rev in review_list]
    if step_items:
        sac.steps(step_items, index=current_gate_idx, return_index=False)

    st.divider()

    # Tabs for phase details
    tab_review, tab_margins, tab_trl, tab_act = st.tabs(["Gate Review Details", "Margin Policy", "TRL Tracking", "Phase Activities"])

    with tab_review:
        if gate and gate in REVIEW_DEFINITIONS:
            rev_def = REVIEW_DEFINITIONS[gate]
            st.markdown(f"##### {gate} — {rev_def['full_name']}")
            st.caption(rev_def["purpose"])
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Entry Criteria**")
                for cr in rev_def["entry_criteria"]:
                    st.markdown(f"- {cr}")
            with col_b:
                st.markdown("**Exit Criteria**")
                for cr in rev_def["exit_criteria"]:
                    st.markdown(f"- {cr}")
            st.markdown("**Required Documents**")
            st.dataframe(pd.DataFrame(rev_def["required_documents"]), width="stretch", hide_index=True)
        elif gate:
            st.info(f"Review **{gate}** — no detailed definition available for {fw_name} framework.")
        else:
            st.info("No gate review for this phase (terminal phase).")

    with tab_margins:
        st.markdown(f"##### Margin Policy — Phase {current_phase}")
        margin_data = []
        for mat in ["estimate", "measured", "qualified"]:
            val = COMPONENT_MARGINS.get((current_phase, mat), "—")
            margin_data.append({"Maturity": mat.capitalize(), "Component Margin (%)": f"{val}%" if val != "—" else "—"})
        sys_m = SYSTEM_MARGINS.get(current_phase, "—")
        margin_data.append({"Maturity": "System Margin", "Component Margin (%)": f"{sys_m}%" if sys_m != "—" else "—"})
        st.dataframe(pd.DataFrame(margin_data), width="stretch", hide_index=True)

        # Margin evolution chart
        st.markdown("##### Margin Evolution Across Phases")
        chart_data = []
        for pid in phase_ids:
            for mat in ["estimate", "measured", "qualified"]:
                val = COMPONENT_MARGINS.get((pid, mat))
                if val is not None:
                    chart_data.append({"Phase": pid, "Maturity": mat.capitalize(), "Margin (%)": val})
            sys_val = SYSTEM_MARGINS.get(pid)
            if sys_val is not None:
                chart_data.append({"Phase": pid, "Maturity": "System", "Margin (%)": sys_val})
        if chart_data:
            df_m = pd.DataFrame(chart_data)
            fig_m = px.line(df_m, x="Phase", y="Margin (%)", color="Maturity",
                           markers=True, category_orders={"Phase": phase_ids})
            fig_m.update_layout(height=350)
            st.plotly_chart(fig_m, width="stretch")

    with tab_trl:
        trl_info = trl_targets.get(current_phase, {})
        st.markdown(f"##### TRL Requirements — Phase {current_phase}")
        if trl_info:
            c1, c2, c3 = st.columns(3)
            c1.metric("Min TRL", trl_info["min"])
            c2.metric("Target TRL", trl_info["target"])
            c3.metric("Description", trl_info["description"])

        # TRL status of all equipment
        st.markdown("##### Component TRL Status")
        eb = _get_equip_budgets()
        equip_nodes = [n for n in _get_product_tree() if n["level"] == "equipment"]
        trl_data = []
        target = trl_info.get("target", 5) if trl_info else 5
        for n in equip_nodes:
            b = eb.get(n["code"], {})
            cur_trl = b.get("trl", 5)
            status = "✅ OK" if cur_trl >= target else ("⚠️ Below" if cur_trl >= target - 2 else "🔴 Critical")
            trl_data.append({
                "Code": n["code"], "Name": n["name"],
                "Current TRL": cur_trl, "Target TRL": target,
                "Gap": max(0, target - cur_trl), "Status": status,
            })
        if trl_data:
            df_trl = pd.DataFrame(trl_data)
            if can("edit_subsystem"):
                edited_trl = st.data_editor(
                    df_trl, key="_trl_editor", hide_index=True, width="stretch",
                    column_config={
                        "Code": st.column_config.TextColumn(disabled=True),
                        "Name": st.column_config.TextColumn(disabled=True),
                        "Current TRL": st.column_config.NumberColumn(min_value=1, max_value=9),
                        "Target TRL": st.column_config.NumberColumn(disabled=True),
                        "Gap": st.column_config.NumberColumn(disabled=True),
                        "Status": st.column_config.TextColumn(disabled=True),
                    },
                )
                if not edited_trl["Current TRL"].equals(df_trl["Current TRL"]):
                    eb = _get_equip_budgets()
                    for i, row in edited_trl.iterrows():
                        new_trl = int(row["Current TRL"])
                        code = row["Code"]
                        if code in eb and eb[code].get("trl", 5) != new_trl:
                            eb[code]["trl"] = new_trl
                    st.rerun()
            else:
                st.dataframe(df_trl, width="stretch", hide_index=True)

            # TRL bar chart
            fig_trl = go.Figure()
            codes = [d["Code"] for d in trl_data]
            trls = [d["Current TRL"] for d in trl_data]
            colors = ["#2ecc71" if d["Current TRL"] >= target else ("#f39c12" if d["Current TRL"] >= target - 2 else "#e74c3c") for d in trl_data]
            fig_trl.add_trace(go.Bar(x=codes, y=trls, marker_color=colors, name="Current TRL"))
            fig_trl.add_hline(y=target, line_dash="dash", line_color="red", annotation_text=f"Target TRL {target}")
            fig_trl.update_layout(height=350, yaxis_range=[0, 9.5], yaxis_title="TRL", xaxis_title="Component")
            st.plotly_chart(fig_trl, width="stretch")
        else:
            st.info("No equipment nodes in product tree.")

    with tab_act:
        st.markdown(f"##### Expected Activities — Phase {current_phase}")
        act_list = activities.get(current_phase, [])
        if act_list:
            for a in act_list:
                st.markdown(f"- {a}")
        else:
            st.info("No activities defined for this phase.")

        if fw_name == "ESA":
            mait = ESA_MAIT_STATUS.get(current_phase, "N/A")
            st.markdown(f"**MAIT Status:** {mait}")


def _base_context():
    return {
        "mission_name": st.session_state.get("missions", {}).get(st.session_state.get("active_mission_id", ""), {}).get("name", "BEPI-SAT"),
        "phase": st.session_state.get("mission_phase", "B2"),
        "phase_name": get_framework(st.session_state.get("mission_framework", "ESA"))["phases"].get(st.session_state.get("mission_phase", "B2"), {}).get("name", "Detailed Definition"),
        "orbit": "SSO 550 km, 97.6 deg i",
        "launch_date": "2027-06",
        "lifetime": "5 years",
        "customer": "ESA",
        "prime_contractor": "BEPI Aerospace",
        "prepared_by": "L. Bianchi (SE)",
        "reviewed_by": "R. Greco (QA)",
        "approved_by": "M. Rossi (PM)",
        "issue": "1",
        "revision": "0",
        "date": date.today().isoformat(),
        "doc_status": "Draft",
    }


def _budget_context():
    from bepi.ecss.margins import COMPONENT_MARGINS, SYSTEM_MARGINS
    nodes = _get_product_tree()
    equip_nodes = [n for n in nodes if n["level"] == "equipment"]
    subsys_nodes = [n for n in nodes if n["level"] == "subsystem"]

    _rpt_phase = st.session_state.get("mission_phase", "B2")
    sys_margin = get_system_margin(_rpt_phase)
    mass_by_sub = []
    power_by_sub = []
    mass_equip = []
    power_equip = []
    total_mass_nom = 0
    total_mass_mar = 0
    total_power_nom = 0
    total_power_mar = 0

    for sub in subsys_nodes:
        sub_mass_nom = 0
        sub_mass_mar = 0
        sub_power_nom = 0
        sub_power_mar = 0
        children = [n for n in equip_nodes if n.get("parent_id") == sub["id"]]
        for ch in children:
            b = _get_equip_budgets().get(ch["code"], {})
            if not b:
                continue
            m_pct = get_component_margin(_rpt_phase, b.get("mat", "estimate"))
            mass_nom = b.get("mass", 0) * b.get("qty", 1)
            mass_mar = mass_nom * (1 + m_pct / 100)
            pow_nom = b.get("power", 0) * b.get("qty", 1)
            pow_mar = pow_nom * (1 + m_pct / 100)
            sub_mass_nom += mass_nom
            sub_mass_mar += mass_mar
            sub_power_nom += pow_nom
            sub_power_mar += pow_mar
            if mass_nom > 0:
                mass_equip.append({"code": ch["code"], "name": ch["name"], "nominal": b["mass"],
                                   "qty": b.get("qty", 1), "margin_pct": m_pct, "total": mass_mar, "maturity": b["mat"]})
            if pow_nom > 0:
                power_equip.append({"code": ch["code"], "name": ch["name"], "nominal": b["power"],
                                    "qty": b.get("qty", 1), "margin_pct": m_pct, "total": pow_mar, "maturity": b["mat"]})
        if sub_mass_nom > 0:
            mass_by_sub.append({"name": sub["name"], "code": sub["code"], "nominal": sub_mass_nom,
                                "with_margin": sub_mass_mar, "margin_pct": (sub_mass_mar / sub_mass_nom - 1) * 100 if sub_mass_nom else 0,
                                "count": len(children)})
        if sub_power_nom > 0:
            power_by_sub.append({"name": sub["name"], "code": sub["code"], "nominal": sub_power_nom,
                                 "with_margin": sub_power_mar, "margin_pct": (sub_power_mar / sub_power_nom - 1) * 100 if sub_power_nom else 0})
        total_mass_nom += sub_mass_nom
        total_mass_mar += sub_mass_mar
        total_power_nom += sub_power_nom
        total_power_mar += sub_power_mar

    # recompute totals correctly
    total_mass_nom = sum(s["nominal"] for s in mass_by_sub)
    total_mass_mar = sum(s["with_margin"] for s in mass_by_sub)
    total_power_nom = sum(s["nominal"] for s in power_by_sub)
    total_power_mar = sum(s["with_margin"] for s in power_by_sub)

    sys_margin_kg = total_mass_mar * sys_margin / 100
    dry_with_sys = total_mass_mar + sys_margin_kg
    _prop_kg = st.session_state.get("propellant_kg", 0.0)
    wet = dry_with_sys + _prop_kg
    pow_sys_w = total_power_mar * sys_margin / 100
    pow_with_sys = total_power_mar + pow_sys_w

    return {
        "system_margin": sys_margin,
        "margin_table": [{"phase": _rpt_phase, "estimate": get_component_margin(_rpt_phase, "estimate"),
                          "measured": get_component_margin(_rpt_phase, "measured"),
                          "qualified": get_component_margin(_rpt_phase, "qualified")}],
        "mass_by_subsystem": mass_by_sub,
        "dry_nominal": total_mass_nom, "dry_with_margin": total_mass_mar,
        "system_margin_kg": sys_margin_kg, "dry_with_system": dry_with_sys,
        "propellant_kg": _prop_kg, "wet_mass": wet,
        "mass_limit": 350.0, "mass_remaining": 350.0 - wet,
        "mass_equipment": mass_equip,
        "power_by_subsystem": power_by_sub,
        "power_nominal": total_power_nom, "power_with_margin": total_power_mar,
        "power_system_margin_w": pow_sys_w, "power_with_system": pow_with_sys,
        "power_limit": 550.0, "power_remaining": 550.0 - pow_with_sys,
        "power_equipment": power_equip,
    }


def _requirements_context():
    reqs = get_requirements()
    cov = coverage_report(reqs)
    ownership = get_req_ownership()

    def req_dict(r):
        own = ownership.get(r.id, {})
        owner_m = get_member(own.get("owner", ""))
        parent_req = next((x for x in reqs if x.id == r.parent_id), None) if r.parent_id else None
        return {
            "req_id": r.req_id, "title": r.title, "text": r.text,
            "level": r.level, "category": r.category,
            "method": r.verification_method or "TBD",
            "status": r.verification_status,
            "allocated_to": ", ".join(r.allocated_to) if r.allocated_to else "",
            "owner": owner_m["name"] if owner_m else "",
            "parent_id": parent_req.req_id if parent_req else "",
        }

    all_req_dicts = [req_dict(r) for r in reqs]
    by_level = {}
    for lvl_name, data in cov["by_level"].items():
        by_level[lvl_name] = {"level": lvl_name, "total": data["total"], "verified": data["verified"],
                               "in_progress": data.get("in_progress", 0), "pct": data["pct"]}

    return {
        "total_reqs": cov["total"],
        "total_verified": sum(1 for r in reqs if r.verification_status == "passed"),
        "total_in_progress": sum(1 for r in reqs if r.verification_status == "in_progress"),
        "overall_pct": cov["overall_pct"],
        "coverage_by_level": list(by_level.values()),
        "reqs_stakeholder": [req_dict(r) for r in reqs if r.level == "stakeholder"],
        "reqs_mission": [req_dict(r) for r in reqs if r.level == "mission"],
        "reqs_system": [req_dict(r) for r in reqs if r.level == "system"],
        "reqs_subsystem": [req_dict(r) for r in reqs if r.level == "subsystem"],
        "reqs_equipment": [req_dict(r) for r in reqs if r.level == "equipment"],
        "all_reqs": all_req_dicts,
    }


def _risk_context():
    risks = get_effective_risks()
    rm = risk_matrix(risks)
    entries = st.session_state.get("fmeca_entries", [])
    ranked = fmeca_ranking(entries) if entries else []

    level_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    level_open = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    level_mitigating = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in risks:
        lvl = r.risk_level
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
        if r.status == "open":
            level_open[lvl] = level_open.get(lvl, 0) + 1
        elif r.status == "mitigating":
            level_mitigating[lvl] = level_mitigating.get(lvl, 0) + 1

    risk_summary = [{"level": k, "count": level_counts[k], "open": level_open[k], "mitigating": level_mitigating[k]}
                    for k in ["critical", "high", "medium", "low"]]

    return {
        "total_risks": len(risks),
        "total_open": sum(1 for r in risks if r.status == "open"),
        "total_mitigating": sum(1 for r in risks if r.status == "mitigating"),
        "risk_summary": risk_summary,
        "risks": [{"risk_id": r.risk_id, "title": r.title, "description": r.description,
                    "category": r.category, "likelihood": r.likelihood, "consequence": r.consequence,
                    "score": r.risk_score, "level": r.risk_level, "status": r.status,
                    "owner": r.owner, "mitigation": r.mitigation_strategy,
                    "residual_l": r.residual_likelihood, "residual_c": r.residual_consequence}
                   for r in risks],
        "fmeca": [{"node": e.node_code, "mode": e.failure_mode, "severity": e.severity,
                    "occurrence": e.occurrence, "detection": e.detection, "rpn": e.rpn,
                    "mitigation": e.mitigation} for e in ranked[:10]],
        "top_risks": [{"risk_id": r.risk_id, "title": r.title, "likelihood": r.likelihood,
                        "consequence": r.consequence, "score": r.risk_score, "status": r.status}
                       for r in sorted(risks, key=lambda x: x.risk_score, reverse=True)[:5]],
        "risk_critical": rm["summary"].get("critical", 0),
        "risk_high": rm["summary"].get("high", 0),
        "risk_medium": rm["summary"].get("medium", 0),
        "risk_low": rm["summary"].get("low", 0),
    }


REPORT_TYPES = {
    "Budget Report": {
        "template": "budget_report.tex",
        "doc_number": "BEPI-SAT-BUD-001",
        "doc_title": "Budget Report",
        "doc_subtitle": "Mass and Power Budget — Phase {phase}",
        "doc_title_short": "Budget Report",
        "description": "Mass and power budgets with ECSS margins, subsystem breakdown, and equipment-level detail.",
        "ecss_ref": "ECSS-E-HB-10-02A",
        "context_fn": _budget_context,
    },
    "System Requirements Document": {
        "template": "requirements_doc.tex",
        "doc_number": "BEPI-SAT-SRD-001",
        "doc_title": "System Requirements Document",
        "doc_subtitle": "Requirements Specification — Phase {phase}",
        "doc_title_short": "SRD",
        "description": "Full requirements tree with verification matrix, coverage analysis, and traceability.",
        "ecss_ref": "ECSS-E-ST-10-06C",
        "context_fn": _requirements_context,
    },
    "Risk Assessment": {
        "template": "risk_assessment.tex",
        "doc_number": "BEPI-SAT-RSK-001",
        "doc_title": "Risk Assessment Report",
        "doc_subtitle": "Risk Register, FMECA — Phase {phase}",
        "doc_title_short": "Risk Assessment",
        "description": "Risk register with 5x5 matrix assessment, FMECA summary, and mitigation tracking.",
        "ecss_ref": "ECSS-M-ST-80C",
        "context_fn": _risk_context,
    },
    "Design Definition File": {
        "template": "design_definition.tex",
        "doc_number": "BEPI-SAT-DDF-001",
        "doc_title": "Design Definition File",
        "doc_subtitle": "System Design — Phase {phase}",
        "doc_title_short": "DDF",
        "description": "Product tree, subsystem descriptions, budget summaries, and design drivers.",
        "ecss_ref": "ECSS-E-ST-10C",
        "context_fn": lambda: {
            **_budget_context(),
            "product_tree": [{"code": n["code"], "name": n["name"], "level": n["level"],
                              "parent": next((p["code"] for p in _get_product_tree() if p["id"] == n.get("parent_id")), ""),
                              "subsystem": n.get("subsystem_type", "")}
                             for n in _get_product_tree()],
            "subsystems": [
                {"name": n["name"], "code": n["code"],
                 "components": ", ".join(c["name"] for c in _get_product_tree() if c.get("parent_id") == n["id"]),
                 "mass": sum(_get_equip_budgets().get(c["code"], {}).get("mass", 0) * _get_equip_budgets().get(c["code"], {}).get("qty", 1)
                             for c in _get_product_tree() if c.get("parent_id") == n["id"]),
                 "power": sum(_get_equip_budgets().get(c["code"], {}).get("power", 0) * _get_equip_budgets().get(c["code"], {}).get("qty", 1)
                              for c in _get_product_tree() if c.get("parent_id") == n["id"]),
                 "ecss_standard": {"STR": "ECSS-E-ST-32", "EPS": "ECSS-E-ST-20", "AOCS": "ECSS-E-ST-60",
                                   "COM": "ECSS-E-ST-50", "CDH": "ECSS-E-ST-50", "TCS": "ECSS-E-ST-31",
                                   "PROP": "ECSS-E-ST-35", "PL": "Mission-specific", "HRN": "ECSS-E-ST-20"}.get(n["code"], ""),
                 "lead": SUBSYSTEM_LEAD_MAP.get(n["code"], {}).get("name", "TBD")}
                for n in _get_product_tree() if n["level"] == "subsystem"
            ],
            "design_drivers": [
                "SSO orbit at 550 km constrains launch mass to 350 kg (wet)",
                "5 m GSD payload drives pointing accuracy requirement (0.1 deg 3-sigma)",
                "5-year lifetime requires radiation-tolerant components (20 krad TID)",
                "Green propellant (AF-M315E) selected for ESA compliance",
                "Dual-band comms (S-band TTC + X-band payload data) for 2 Gbit/orbit downlink",
            ],
            "open_items": [
                {"type": "TBD", "description": "Star tracker sun exclusion angle — awaiting vendor data"},
                {"type": "TBD", "description": "Payload detector annealing cycle definition"},
                {"type": "TBC", "description": "Battery cell configuration (4s3p vs 4s4p)"},
                {"type": "TBC", "description": "S-band antenna pattern gain at +/- 60 deg"},
            ],
        },
    },
    "Review Data Package (PDR)": {
        "template": "review_data_package.tex",
        "doc_number": "BEPI-SAT-RDP-PDR-001",
        "doc_title": "Review Data Package — PDR",
        "doc_subtitle": "Preliminary Design Review — Phase {phase}",
        "doc_title_short": "RDP-PDR",
        "description": "Comprehensive review package for PDR: budgets, requirements coverage, risk status, schedule.",
        "ecss_ref": "ECSS-M-ST-10C",
        "context_fn": lambda: {
            **_budget_context(),
            **_risk_context(),
            "review_name": "PDR — Preliminary Design Review",
            "phase_before": st.session_state.get("mission_phase", "B2"), "phase_after": "C",
            "review_date": "2026-06-15", "review_status": "In Preparation",
            "entry_criteria": [
                {"text": "All system requirements defined and approved", "met": True},
                {"text": "Preliminary design complete for all subsystems", "met": False},
                {"text": "Mass budget margin > 20%", "met": True},
                {"text": "Power budget margin > 10%", "met": True},
                {"text": "All critical risks have mitigation plans", "met": True},
                {"text": "Verification plan approved", "met": False},
            ],
            "deliverables": [
                {"drd_code": "DRD-SRD", "title": "System Requirements Document", "status": "approved", "owner": "L. Bianchi", "due_date": "2026-05-01"},
                {"drd_code": "DRD-DDF", "title": "Design Definition File", "status": "in_progress", "owner": "L. Bianchi", "due_date": "2026-05-15"},
                {"drd_code": "DRD-BUD", "title": "Budget Report", "status": "draft", "owner": "L. Bianchi", "due_date": "2026-05-15"},
                {"drd_code": "DRD-VP", "title": "Verification Plan", "status": "not_started", "owner": "R. Greco", "due_date": "2026-06-01"},
                {"drd_code": "DRD-RSK", "title": "Risk Assessment", "status": "draft", "owner": "M. Rossi", "due_date": "2026-05-20"},
            ],
            "req_coverage": [{"level": k, "total": v["total"], "verified": v["verified"], "pct": v["pct"]}
                             for k, v in coverage_report(get_requirements())["by_level"].items()],
            "schedule_duration": compute_cpm(get_tasks(), date(2025, 10, 1)).project_duration,
            "schedule_end": str(compute_cpm(get_tasks(), date(2025, 10, 1)).project_end_date),
            "critical_tasks": sum(1 for t in get_tasks() if t.id in compute_cpm(get_tasks(), date(2025, 10, 1)).critical_path and not t.is_milestone),
            "overall_progress": (sum(t.progress_pct for t in get_tasks()) / len(get_tasks())) if get_tasks() else 0,
            "action_items": [
                {"type": "Design", "action": "Complete AOCS detailed mode analysis", "owner": "G. Conti", "due": "2026-05-01", "status": "Open"},
                {"type": "Budget", "action": "Update power budget after CDH vendor selection", "owner": "P. Russo", "due": "2026-05-10", "status": "Open"},
                {"type": "Test", "action": "Define PL optical test plan", "owner": "C. Marino", "due": "2026-05-15", "status": "Open"},
            ],
            "recommendation": "The review board recommends proceeding to Phase C (Detailed Definition) subject to closure of the 2 outstanding entry criteria and 3 open action items.",
        },
    },
}


def page_reports():
    colored_header(label="Report Generation", description="ECSS-compliant reports — PDF or DOCX", color_name="green-70")

    st.markdown("Select a report type, output format, and generate a professional ECSS-formatted document.")

    # ── Format Switch ──────────────────────────────────────────────
    col_format, col_sel, col_info = st.columns([1, 1, 2])

    with col_format:
        st.markdown("##### Output Format")
        output_format = st.segmented_control(
            "Format",
            options=["PDF", "DOCX"],
            default="DOCX",
            key="report_format"
        )
        st.caption("📄 DOCX required for ESA compliance")

    with col_sel:
        report_type = st.radio("Report Type", list(REPORT_TYPES.keys()), key="report_type")

    with col_info:
        rinfo = REPORT_TYPES[report_type]
        st.markdown(f"##### {report_type}")
        st.markdown(f"**Doc Number:** `{rinfo['doc_number']}`")
        st.markdown(f"**ECSS Reference:** {rinfo['ecss_ref']}")
        st.markdown(f"{rinfo['description']}")

    st.divider()

    col_o1, col_o2, col_o3 = st.columns(3)
    with col_o1:
        doc_issue = st.text_input("Issue", value="1", key="rpt_issue")
        doc_rev = st.text_input("Revision", value="0", key="rpt_rev")
    with col_o2:
        doc_status = st.selectbox("Status", ["Draft", "Under Review", "Approved", "Issued"], key="rpt_status")
        doc_date = st.date_input("Date", value=date.today(), key="rpt_date")
    with col_o3:
        prepared_by = st.selectbox("Prepared by", get_team(),
                                   format_func=lambda m: f"{m['name']} ({ROLES[m['role']]['name']})",
                                   index=1, key="rpt_prepared")
        approved_by = st.selectbox("Approved by", get_team(),
                                   format_func=lambda m: f"{m['name']} ({ROLES[m['role']]['name']})",
                                   index=0, key="rpt_approved")

    st.divider()

    # Generate button based on format
    gen_label = f"Generate {output_format}"
    gen_spinner = f"Compiling LaTeX → {output_format}..." if output_format == "PDF" else f"Generating {output_format} via docxtpl..."

    if st.button(gen_label, type="primary", key="rpt_generate", use_container_width=True):
        with st.spinner(gen_spinner):
            base = _base_context()
            base.update({
                "doc_title": rinfo["doc_title"],
                "doc_subtitle": rinfo["doc_subtitle"].format(phase=st.session_state.get("mission_phase", "B2")),
                "doc_title_short": rinfo["doc_title_short"],
                "doc_number": rinfo["doc_number"],
                "issue": doc_issue,
                "revision": doc_rev,
                "date": str(doc_date),
                "doc_status": doc_status,
                "prepared_by": f"{prepared_by['name']} ({ROLES[prepared_by['role']]['name']})",
                "approved_by": f"{approved_by['name']} ({ROLES[approved_by['role']]['name']})",
            })
            specific = rinfo["context_fn"]()
            base.update(specific)

            if output_format == "PDF":
                result = generate_report(rinfo["template"], base, rinfo["doc_number"])
            else:
                from bepi.services.reports import generate_docx_report
                result = generate_docx_report(rinfo["template"], base, rinfo["doc_number"])

        if result.success and result.pdf_path:
            file_ext = "pdf" if output_format == "PDF" else "docx"
            mime_type = "application/pdf" if output_format == "PDF" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

            st.success(f"{output_format} generated successfully: **{rinfo['doc_number']}.{file_ext}**")
            with open(result.pdf_path, "rb") as f:
                file_bytes = f.read()
            st.download_button(
                label=f"Download {rinfo['doc_number']}.{file_ext} ({len(file_bytes) // 1024} KB)",
                data=file_bytes,
                file_name=f"{rinfo['doc_number']}.{file_ext}",
                mime=mime_type,
                type="primary",
                use_container_width=True,
            )
            if output_format == "PDF" and result.log:
                st.caption(f"LaTeX compilation log available ({len(result.log)} chars)")
        else:
            st.error(f"{output_format} generation failed: {result.error}")
            if result.log:
                with st.expander("Compilation log"):
                    st.code(result.log[-2000:], language="text")

    # Show available reports overview
    st.divider()
    st.markdown("##### Available Report Templates")
    for name, info in REPORT_TYPES.items():
        st.markdown(f"- **{name}** (`{info['doc_number']}`) — {info['ecss_ref']} — {info['description'][:80]}...")

    # ── Excel Export ──────────────────────────────────────────────
    st.divider()
    st.markdown("##### Excel Export")
    st.markdown("Download mission data as formatted Excel spreadsheets.")

    from bepi.services.excel_io import (
        export_product_tree, export_requirements, export_risks,
        export_schedule, export_mission,
    )

    ex1, ex2, ex3, ex4, ex5 = st.columns(5)

    with ex1:
        nodes_flat = _get_product_tree()
        budgets_map = {}
        for n in nodes_flat:
            b = _get_equip_budgets().get(n["code"], {})
            if b:
                budgets_map[n["code"]] = {"mass": b.get("mass"), "power": b.get("power"),
                                           "mass_margin": get_component_margin(st.session_state.get("mission_phase", "B2"), b.get("mat", "estimate")),
                                           "power_margin": get_component_margin(st.session_state.get("mission_phase", "B2"), b.get("mat", "estimate")),
                                           "maturity": b.get("mat", "")}
        tree_bytes = export_product_tree(nodes_flat, budgets_map)
        st.download_button("📥 Product Tree", tree_bytes, "BEPI-SAT_product_tree.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with ex2:
        reqs = get_requirements()
        req_dicts = [{"req_id": r.req_id, "title": r.title, "text": r.text, "level": r.level,
                      "category": r.category, "verification_method": r.verification_method or "",
                      "verification_status": r.verification_status,
                      "owner": get_req_ownership().get(r.req_id, {}).get("owner", ""),
                      "allocated_to": ", ".join(r.allocated_to) if r.allocated_to else "",
                      "parent_id": r.parent_id or "", "priority": getattr(r, "priority", ""),
                      "status": getattr(r, "status", "")}
                     for r in reqs]
        req_bytes = export_requirements(req_dicts)
        st.download_button("📥 Requirements", req_bytes, "BEPI-SAT_requirements.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with ex3:
        risks = get_effective_risks()
        risk_dicts = [{"risk_id": r.risk_id, "title": r.title, "description": r.description,
                       "category": r.category, "likelihood": r.likelihood, "consequence": r.consequence,
                       "score": r.risk_score, "level": r.risk_level,
                       "status": r.status, "owner": r.owner,
                       "mitigation": r.mitigation_strategy} for r in risks]
        risk_bytes = export_risks(risk_dicts)
        st.download_button("📥 Risk Register", risk_bytes, "BEPI-SAT_risks.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with ex4:
        tasks = get_tasks()
        task_dicts = [{"wbs": t.wbs_code, "name": t.name,
                       "start": str(t.start_date) if t.start_date else "",
                       "end": str(t.end_date) if t.end_date else "",
                       "duration": t.duration_days, "responsible": t.assigned_to,
                       "progress": t.progress_pct, "predecessors": t.predecessors,
                       "status": "Complete" if t.progress_pct >= 100 else "In Progress" if t.progress_pct > 0 else "Not Started"}
                      for t in tasks]
        sched_bytes = export_schedule(task_dicts)
        st.download_button("📥 Schedule", sched_bytes, "BEPI-SAT_schedule.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with ex5:
        _mname = st.session_state.get("missions", {}).get(st.session_state.get("active_mission_id", ""), {}).get("name", "BEPI-SAT")
        mission_info = {"Mission": _mname, "Phase": st.session_state.get("mission_phase", "B2"), "Orbit": "SSO 550 km",
                        "Target Launch": "2027-06", "Lifetime": "5 years", "Customer": "ESA"}
        full_bytes = export_mission(nodes_flat, budgets_map, req_dicts, risk_dicts, task_dicts, mission_info)
        st.download_button("📥 Full Mission", full_bytes, f"{_mname}_full_export.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── Excel Import ──────────────────────────────────────────────
    st.divider()
    st.markdown("##### Excel Import")
    st.markdown("Upload an Excel file to import data into BEPI. The file must follow the expected column format.")

    import_type = st.selectbox("Import type", ["Requirements", "Risks", "Product Tree"], key="import_type")

    # Show expected format
    if import_type == "Requirements":
        st.markdown("""
**Expected columns** (first row = headers, case-insensitive):

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `Req ID` | ✅ | Unique identifier | `SYS-FUN-001` |
| `Title` | ✅ | Short title | `Pointing accuracy` |
| `Text` | | Full requirement text | `The satellite shall...` |
| `Level` | | `stakeholder`, `mission`, `system`, `subsystem`, `equipment` | `system` |
| `Category` | | `functional`, `performance`, `interface`, `environmental`, `design`, `operational`, `reliability`, `safety` | `performance` |
| `Verification Method` | | `test`, `analysis`, `inspection`, `review`, `demonstration` | `test` |
| `Verification Status` | | `not_started`, `in_progress`, `passed`, `failed`, `waived` | `not_started` |
| `Owner` | | Person responsible | `L. Bianchi` |
| `Allocated To` | | Subsystem codes (comma-separated) | `AOCS, EPS` |
| `Parent Req` | | Parent requirement ID | `SH-FUN-001` |
| `Priority` | | `mandatory`, `desirable`, `optional` | `mandatory` |
| `Status` | | `draft`, `under_review`, `approved`, `deleted` | `draft` |

💡 **Tip**: Export existing requirements first and use as template.
""")
    elif import_type == "Risks":
        st.markdown("""
**Expected columns** (first row = headers, case-insensitive):

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `Risk ID` | ✅ | Unique identifier | `RSK-001` |
| `Title` | ✅ | Short title | `Solar array degradation` |
| `Description` | | Detailed description | `SA output degrades...` |
| `Category` | | `technical`, `schedule`, `cost`, `programmatic`, `external` | `technical` |
| `Likelihood` | | 1-5 (1=rare, 5=almost certain) | `3` |
| `Consequence` | | 1-5 (1=negligible, 5=catastrophic) | `4` |
| `Status` | | `open`, `mitigating`, `accepted`, `closed`, `retired` | `open` |
| `Owner` | | Person responsible | `A. Ferrari` |
| `Mitigation` | | Mitigation strategy | `Oversized SA by 15%` |

💡 **Tip**: Export existing risks first and use as template.
""")
    else:
        st.markdown("""
**Expected columns** (first row = headers, case-insensitive):

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| `Code` | ✅ | Node code | `EPS-SA` |
| `Name` | ✅ | Component name | `Solar Array` |
| `Level` | | `satellite`, `subsystem`, `equipment`, `component` | `equipment` |
| `Subsystem` | | Subsystem type | `EPS` |
| `Parent Code` | | Code of parent node | `EPS` |
| `Qty` | | Quantity (default 1) | `2` |
| `Mass (kg)` | | Nominal mass per unit | `8.0` |
| `Power (W)` | | Nominal power per unit | `0` |
| `Maturity` | | `estimate`, `measured`, `qualified` | `measured` |
| `TRL` | | Technology Readiness Level 1-9 | `7` |

💡 **Tip**: Export existing product tree first and use as template.
""")

    uploaded = st.file_uploader("Upload Excel file", type=["xlsx", "xls"],
                                help="First row must be column headers matching the format above")
    if uploaded:
        from bepi.services.excel_io import (import_requirements_from_excel, import_risks_from_excel,
                                             import_product_tree_from_excel)
        file_bytes = uploaded.read()
        if st.button("Preview Import", type="primary"):
            if import_type == "Requirements":
                imported = import_requirements_from_excel(file_bytes)
            elif import_type == "Risks":
                imported = import_risks_from_excel(file_bytes)
            else:
                imported = import_product_tree_from_excel(file_bytes)
            if imported:
                st.success(f"Found **{len(imported)}** records ready to import")
                st.dataframe(imported[:30], width="stretch")
            else:
                st.warning("No valid records found. Check that column headers match the expected format.")


def page_warehouse():
    colored_header(label="Warehouse & MAIT", description="Component inventory, procurement, MAIT status tracking", color_name="orange-70")

    # --- Initialize warehouse data ---
    if "warehouse_items" not in st.session_state:
        eb = _get_equip_budgets()
        items = []
        for code, b in eb.items():
            trl = b.get("trl", 5)
            if trl >= 8:
                mait = "FM"
            elif trl >= 6:
                mait = "QM"
            elif trl >= 4:
                mait = "EM"
            else:
                mait = "BB"
            items.append({
                "code": code, "description": code.replace("-", " "),
                "mait_status": mait, "qty_required": b.get("qty", 1),
                "qty_in_stock": b.get("qty", 1) if trl >= 7 else 0,
                "supplier": "", "lead_time_weeks": 0,
                "order_status": "Delivered" if trl >= 7 else "Not Ordered",
                "unit_cost_eur": 0.0, "notes": "",
            })
        st.session_state["warehouse_items"] = items

    if "procurement_orders" not in st.session_state:
        st.session_state["procurement_orders"] = [
            {"order_id": "PO-001", "component": "EPS-PCDU", "supplier": "Terma A/S", "qty": 1,
             "unit_cost_eur": 85000.0, "order_date": "2025-09-15", "expected_delivery": "2026-03-15",
             "status": "In Production", "notes": "PCDU v3.2 custom config"},
            {"order_id": "PO-002", "component": "COM-XBT", "supplier": "Thales Alenia", "qty": 1,
             "unit_cost_eur": 120000.0, "order_date": "2025-10-01", "expected_delivery": "2026-06-01",
             "status": "Ordered", "notes": "X-band transponder 8W RF"},
            {"order_id": "PO-003", "component": "PL-OPT", "supplier": "Leonardo", "qty": 1,
             "unit_cost_eur": 350000.0, "order_date": "2025-06-01", "expected_delivery": "2026-09-01",
             "status": "In Production", "notes": "Optical payload EM"},
            {"order_id": "PO-004", "component": "PROP-THR", "supplier": "Bradford ECAPS", "qty": 4,
             "unit_cost_eur": 45000.0, "order_date": "2025-11-01", "expected_delivery": "2026-04-01",
             "status": "Ordered", "notes": "AF-M315E 1N thrusters"},
        ]

    # Reconcile warehouse with current product tree
    eb = _get_equip_budgets()
    wh_items = st.session_state["warehouse_items"]
    existing_map = {it["code"]: it for it in wh_items}
    
    for code, b in eb.items():
        qty = b.get("qty", 1)
        if code in existing_map:
            # Sync qty_required if changed in product tree
            existing_map[code]["qty_required"] = qty
        else:
            # Add new item
            trl = b.get("trl", 5)
            mait = "FM" if trl >= 8 else ("QM" if trl >= 6 else ("EM" if trl >= 4 else "BB"))
            wh_items.append({
                "code": code, "description": code.replace("-", " "),
                "mait_status": mait, "qty_required": qty,
                "qty_in_stock": qty if trl >= 7 else 0,
                "supplier": "", "lead_time_weeks": 0,
                "order_status": "Delivered" if trl >= 7 else "Not Ordered",
                "unit_cost_eur": 0.0, "notes": "",
            })

    items = st.session_state["warehouse_items"]
    orders = st.session_state["procurement_orders"]

    # --- MAIT summary metrics ---
    mait_counts = {"BB": 0, "EM": 0, "QM": 0, "FM": 0}
    for it in items:
        mait_counts[it["mait_status"]] = mait_counts.get(it["mait_status"], 0) + 1
    stock_ok = sum(1 for it in items if it["qty_in_stock"] >= it["qty_required"])
    stock_missing = len(items) - stock_ok

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Breadboard", mait_counts.get("BB", 0))
    c2.metric("Eng. Model", mait_counts.get("EM", 0))
    c3.metric("Qual. Model", mait_counts.get("QM", 0))
    c4.metric("Flight Model", mait_counts.get("FM", 0))
    c5.metric("In Stock", stock_ok, delta=None)
    c6.metric("Missing", stock_missing, delta=f"-{stock_missing}" if stock_missing else None, delta_color="inverse")

    tab_inv, tab_mait, tab_proc, tab_orders = st.tabs(["Inventory", "MAIT Tracker", "Procurement", "Orders"])

    # --- Inventory tab ---
    with tab_inv:
        st.markdown("##### Component Inventory")
        inv_data = []
        for it in items:
            gap = it["qty_required"] - it["qty_in_stock"]
            inv_data.append({
                "Code": it["code"],
                "MAIT": it["mait_status"],
                "Required": it["qty_required"],
                "In Stock": it["qty_in_stock"],
                "Gap": gap if gap > 0 else 0,
                "Order Status": it["order_status"],
                "Supplier": it["supplier"],
                "Lead Time (wk)": it["lead_time_weeks"],
                "Unit Cost (€)": it["unit_cost_eur"],
            })
        df_inv = pd.DataFrame(inv_data)
        edited_inv = st.data_editor(
            df_inv, key="_wh_inv_editor", hide_index=True, width="stretch",
            column_config={
                "Code": st.column_config.TextColumn(disabled=True),
                "MAIT": st.column_config.TextColumn(disabled=True),
                "Required": st.column_config.NumberColumn(min_value=0, step=1),
                "In Stock": st.column_config.NumberColumn(min_value=0, step=1),
                "Gap": st.column_config.NumberColumn(disabled=True),
                "Order Status": st.column_config.SelectboxColumn(options=["Not Ordered", "Ordered", "In Production", "Shipped", "Delivered"]),
                "Supplier": st.column_config.TextColumn(),
                "Lead Time (wk)": st.column_config.NumberColumn(min_value=0, step=1),
                "Unit Cost (€)": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.0f"),
            },
        )
        if st.button("Save Inventory Changes", key="_wh_inv_save", type="primary"):
            for i, it in enumerate(items):
                row = edited_inv.iloc[i]
                it["qty_required"] = int(row["Required"])
                it["qty_in_stock"] = int(row["In Stock"])
                it["order_status"] = row["Order Status"]
                it["supplier"] = row["Supplier"]
                it["lead_time_weeks"] = int(row["Lead Time (wk)"])
                it["unit_cost_eur"] = float(row["Unit Cost (€)"])
            st.rerun()

    # --- MAIT Tracker tab ---
    with tab_mait:
        st.markdown("##### MAIT Status Progression")
        st.caption("BB → EM → QM → FM")
        mait_levels = ["BB", "EM", "QM", "FM"]
        mait_data = []
        for it in items:
            cur_idx = mait_levels.index(it["mait_status"]) if it["mait_status"] in mait_levels else 0
            mait_data.append({
                "Code": it["code"],
                "Status": it["mait_status"],
                "Progress": f"{'█' * (cur_idx + 1)}{'░' * (3 - cur_idx)}",
            })
        df_mait = pd.DataFrame(mait_data)
        if can("edit_warehouse"):
            edited_mait = st.data_editor(
                df_mait, key="_mait_editor", hide_index=True, width="stretch",
                column_config={
                    "Code": st.column_config.TextColumn(disabled=True),
                    "Status": st.column_config.SelectboxColumn(options=mait_levels, required=True),
                    "Progress": st.column_config.TextColumn(disabled=True),
                },
            )
            if not edited_mait["Status"].equals(df_mait["Status"]):
                mait_to_trl = {"BB": 3, "EM": 5, "QM": 7, "FM": 9}
                eb = _get_equip_budgets()
                for i, row in edited_mait.iterrows():
                    new_st = row["Status"]
                    if i < len(items) and items[i]["mait_status"] != new_st:
                        items[i]["mait_status"] = new_st
                        code = items[i]["code"]
                        if code in eb:
                            eb[code]["trl"] = mait_to_trl.get(new_st, eb[code].get("trl", 5))
                st.rerun()
        else:
            st.dataframe(df_mait, width="stretch", hide_index=True)

        # MAIT bar chart
        fig_mait = go.Figure()
        for lvl in mait_levels:
            cnt = sum(1 for it in items if it["mait_status"] == lvl)
            fig_mait.add_trace(go.Bar(x=[lvl], y=[cnt], name=lvl))
        fig_mait.update_layout(height=300, showlegend=False, yaxis_title="Components", xaxis_title="MAIT Level")
        st.plotly_chart(fig_mait, width="stretch")

    # --- Procurement tab ---
    with tab_proc:
        st.markdown("##### Procurement Overview")
        total_cost = sum(o["unit_cost_eur"] * o["qty"] for o in orders)
        ordered = sum(1 for o in orders if o["status"] in ("Ordered", "In Production"))
        delivered = sum(1 for o in orders if o["status"] == "Delivered")

        p1, p2, p3 = st.columns(3)
        p1.metric("Total Orders", len(orders))
        p2.metric("Pending", ordered)
        p3.metric("Total Cost", f"€{total_cost:,.0f}")

        st.markdown("##### Supplier Summary")
        suppliers = {}
        for o in orders:
            s = o["supplier"]
            if s not in suppliers:
                suppliers[s] = {"orders": 0, "total_eur": 0.0}
            suppliers[s]["orders"] += 1
            suppliers[s]["total_eur"] += o["unit_cost_eur"] * o["qty"]
        supp_data = [{"Supplier": s, "Orders": d["orders"], "Total (€)": f"{d['total_eur']:,.0f}"} for s, d in suppliers.items()]
        if supp_data:
            st.dataframe(pd.DataFrame(supp_data), width="stretch", hide_index=True)

    # --- Orders tab ---
    with tab_orders:
        st.markdown("##### Purchase Orders")
        if orders:
            orders_df = pd.DataFrame(orders)
            orders_df.columns = ["Order ID", "Component", "Supplier", "Qty", "Unit Cost (€)", "Order Date", "Expected Delivery", "Status", "Notes"]
            edited_orders = st.data_editor(
                orders_df, key="_wh_orders_editor", hide_index=True, width="stretch",
                column_config={
                    "Order ID": st.column_config.TextColumn(disabled=True),
                    "Component": st.column_config.TextColumn(disabled=True),
                    "Supplier": st.column_config.TextColumn(),
                    "Qty": st.column_config.NumberColumn(min_value=1, step=1),
                    "Unit Cost (€)": st.column_config.NumberColumn(min_value=0.0, step=100.0),
                    "Order Date": st.column_config.TextColumn(),
                    "Expected Delivery": st.column_config.TextColumn(),
                    "Status": st.column_config.SelectboxColumn(options=["Ordered", "In Production", "Shipped", "Delivered", "Cancelled"]),
                    "Notes": st.column_config.TextColumn(),
                },
            )
            oc1, oc2 = st.columns([1, 3])
            with oc1:
                if st.button("Save Order Changes", key="_wh_ord_save", type="primary"):
                    for i, o in enumerate(orders):
                        row = edited_orders.iloc[i]
                        o["supplier"] = row["Supplier"]
                        o["qty"] = int(row["Qty"])
                        o["unit_cost_eur"] = float(row["Unit Cost (€)"])
                        o["order_date"] = row["Order Date"]
                        o["expected_delivery"] = row["Expected Delivery"]
                        o["status"] = row["Status"]
                        o["notes"] = row["Notes"]
                    st.rerun()
            with oc2:
                del_order = st.selectbox("Delete order", [o["order_id"] for o in orders], key="_wh_ord_del_sel")
                if st.button("Delete", key="_wh_ord_del_btn", disabled=not can("edit_warehouse")):
                    st.session_state["procurement_orders"] = [o for o in orders if o["order_id"] != del_order]
                    st.rerun()

        st.markdown("##### New Purchase Order")
        with st.form("new_order_form"):
            fo1, fo2 = st.columns(2)
            with fo1:
                no_comp = st.selectbox("Component", [it["code"] for it in items], key="_no_comp")
                no_supplier = st.text_input("Supplier", key="_no_supplier", placeholder="e.g. Airbus, Thales, OHB")
                no_qty = st.number_input("Quantity", min_value=1, value=1, key="_no_qty")
                no_cost = st.number_input("Unit Cost (€)", min_value=0.0, max_value=100_000_000.0, step=1000.0, key="_no_cost")
            with fo2:
                no_order_date = st.date_input("Order Date", key="_no_date")
                no_delivery = st.date_input("Expected Delivery", key="_no_delivery")
                no_status = st.selectbox("Status", ["Ordered", "In Production", "Shipped", "Delivered", "Cancelled"], key="_no_status")
                no_notes = st.text_input("Notes", key="_no_notes", placeholder="Optional notes")
            if st.form_submit_button("Create Order", type="primary"):
                if not require("edit_warehouse"):
                    pass
                else:
                    import re
                    po_nums = []
                    for o in orders:
                        match = re.search(r"PO-(\d+)", o["order_id"])
                        if match:
                            po_nums.append(int(match.group(1)))
                    _max_po = max(po_nums, default=0)
                    new_id = f"PO-{_max_po + 1:03d}"
                    orders.append({
                        "order_id": new_id, "component": no_comp, "supplier": no_supplier,
                        "qty": no_qty, "unit_cost_eur": no_cost,
                        "order_date": str(no_order_date), "expected_delivery": str(no_delivery),
                        "status": no_status, "notes": no_notes,
                    })
                    st.rerun()


def page_team():
    colored_header(label="Team & Roles", description="Team composition, assignments, approvals & workload", color_name="violet-70")

    tab_roster, tab_mywork, tab_workload, tab_approvals, tab_permissions = st.tabs(["Team Roster", "My Work", "Workload", "Approval Log", "Role Permissions"])

    with tab_roster:
        st.markdown("##### Mission Team")
        subsys_options = ["—", "STR", "EPS", "AOCS", "COM", "CDH", "TCS", "PROP", "PL", "HRN"]
        role_keys = list(ROLES.keys())
        role_names = [ROLES[r]["name"] for r in role_keys]
        roster_rows = []
        for m in get_team():
            task_count = sum(1 for a in get_task_assignments().values() if a.get("responsible") == m["id"])
            req_count = sum(1 for o in get_req_ownership().values() if o.get("owner") == m["id"])
            roster_rows.append({
                "ID": m["id"],
                "Name": m["name"],
                "Role": ROLES[m["role"]]["name"],
                "Subsystem": m.get("subsystem", "—"),
                "Org": m.get("org", "Prime"),
                "Tasks": task_count,
                "Requirements": req_count,
            })
        df_team = pd.DataFrame(roster_rows)
        if can("manage_team"):
            edited_team = st.data_editor(
                df_team, key="_team_roster_editor", hide_index=True, width="stretch",
                height=min(len(roster_rows) * 38 + 40, 400),
                column_config={
                    "ID": st.column_config.TextColumn(disabled=True),
                    "Name": st.column_config.TextColumn(),
                    "Role": st.column_config.SelectboxColumn(options=role_names, required=True),
                    "Subsystem": st.column_config.SelectboxColumn(options=subsys_options, required=True),
                    "Org": st.column_config.TextColumn(),
                    "Tasks": st.column_config.NumberColumn(disabled=True),
                    "Requirements": st.column_config.NumberColumn(disabled=True),
                },
            )
            if not edited_team.equals(df_team):
                from bepi.db_writer import update_mission_member
                _mid = st.session_state.get("active_mission_id")
                for i in range(len(edited_team)):
                    row = edited_team.iloc[i]
                    m = get_team()[i]
                    # Coerce pandas/numpy values to native Python types
                    new_name = str(row["Name"]) if row["Name"] is not None else m["name"]
                    new_role_name = str(row["Role"]) if row["Role"] is not None else m["role"]
                    new_org = str(row["Org"]) if row["Org"] is not None else m.get("org", "Prime")
                    new_sub = row["Subsystem"]
                    if new_sub is None or (isinstance(new_sub, float) and str(new_sub) == "nan"):
                        new_sub = "—"

                    m["name"] = new_name
                    m["role"] = next((k for k, v in ROLES.items() if v["name"] == new_role_name), m["role"])
                    m["org"] = new_org
                    if new_sub and new_sub != "—":
                        m["subsystem"] = str(new_sub)
                    else:
                        m.pop("subsystem", None)
                    if _mid and HAS_SUPABASE:
                        payload = {"role": str(m["role"])}
                        if "subsystem" in m:
                            payload["subsystem"] = str(m["subsystem"])
                        else:
                            payload["subsystem"] = None  # explicit clear
                        update_mission_member(_mid, str(m["id"]), payload)
                st.rerun()
        else:
            st.dataframe(df_team, width="stretch", hide_index=True, height=min(len(roster_rows) * 38 + 40, 400))

        st.divider()
        st.markdown("##### Add Team Member")
        if HAS_SUPABASE:
            mission_id = st.session_state.get("active_mission_id")
            with st.form("invite_team_form", clear_on_submit=True):
                col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1.5])
                with col1:
                    inv_name = st.text_input("Name", key="invite_name", placeholder="Full name")
                with col2:
                    inv_email = st.text_input("Email", key="invite_email", placeholder="colleague@unipd.it")
                with col3:
                    inv_role = st.selectbox("Role", role_keys, format_func=lambda r: ROLES[r]["name"], key="invite_role")
                with col4:
                    inv_subsys = st.selectbox("Subsystem", subsys_options, key="invite_subsys")
                if st.form_submit_button("Invite", type="primary"):
                    if not require("manage_team"):
                        pass
                    elif inv_name and inv_email and mission_id:
                        try:
                            result = invite_team_member(mission_id, inv_email, inv_name, inv_role, inv_subsys if inv_subsys != "—" else None)
                            invite_code = result.get("invite_code")
                            email_sent = result.get("email_sent", False)
                            email_result = result.get("email_result", {})
                            
                            st.success(f"✅ Invitation created for {inv_email}")
                            st.code(invite_code, language="text")
                            
                            if email_sent:
                                st.info(f"📧 Email sent! {inv_email} will receive the invitation code.")
                            else:
                                st.warning(f"⚠️ Email sending not configured or failed. Share this code manually with {inv_email}:")
                                st.info("📋 The user can join using: Settings → Join Mission → Paste code")
                                if email_result:
                                    error_detail = email_result.get("error") or email_result.get("response_text")
                                    if error_detail:
                                        with st.expander("Edge Function error details"):
                                            st.code(error_detail, language="text")
                        except Exception as e:
                            st.error(f"Invite failed: {e}")
                    else:
                        st.warning("Name and email are required.")
        else:
            with st.form("add_team_form", clear_on_submit=True):
                col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1.5])
                with col1:
                    new_name = st.text_input("Name", key="team_name", placeholder="Full name")
                with col2:
                    new_role = st.selectbox("Role", role_keys, format_func=lambda r: ROLES[r]["name"], key="team_role")
                with col3:
                    new_org = st.text_input("Organization", key="team_org", placeholder="Prime / SubCon")
                with col4:
                    new_subsys = st.selectbox("Subsystem", subsys_options, key="team_subsys")
                if st.form_submit_button("Add Member", type="primary"):
                    if not require("manage_team"):
                        pass
                    elif new_name:
                        _max_uid = max((int(m["id"][1:]) for m in get_team()), default=0)
                        new_id = f"U{_max_uid+1:02d}"
                        member = {"id": new_id, "name": new_name, "role": new_role,
                                  "email": f"{new_name.lower().replace(' ','.')}@bepi.eu", "org": new_org or "Prime"}
                        if new_subsys != "—":
                            member["subsystem"] = new_subsys
                        get_team().append(member)
                        st.toast(f"Added {new_name} as {ROLES[new_role]['name']}", icon="✅")
                        st.rerun()
                    else:
                        st.warning("Team member name is required.")

        if can("manage_team") and get_team():
            st.divider()
            rm_member = st.selectbox("Remove member", get_team(), format_func=lambda m: f"{m['name']} ({ROLES[m['role']]['name']})", key="_team_rm_sel")
            if rm_member and st.button("Remove Member", key="_team_del_btn", type="secondary"):
                get_team().remove(rm_member)
                st.toast(f"Removed {rm_member['name']}", icon="✅")
                st.rerun()

    with tab_mywork:
        team = get_team()
        if not team:
            st.info("No team members yet. Add a member from the Team Roster tab to see assigned work.")
            return
        sel_person = st.selectbox("Select Team Member", team,
                                  format_func=lambda m: f"{ROLES[m['role']]['icon']} {m['name']} ({ROLES[m['role']]['name']})",
                                  index=next((i for i, m in enumerate(team) if m["id"] == current_user["id"]), 0),
                                  key="mywork_person")
        if not sel_person:
            st.info("Select a team member to see assigned work.")
            return
        pid = sel_person["id"]
        tasks = get_tasks()
        reqs = get_requirements()
        ta = get_task_assignments()
        ro = get_req_ownership()

        st.markdown(f"##### Tasks — {sel_person['name']}")
        my_tasks = []
        for tid, assign in ta.items():
            t = next((t for t in tasks if t.id == tid), None)
            if not t:
                continue
            role_in_task = []
            if assign.get("responsible") == pid:
                role_in_task.append("Responsible")
            if assign.get("approver") == pid:
                role_in_task.append("Approver")
            if pid in assign.get("contributors", []) and "Responsible" not in role_in_task:
                role_in_task.append("Contributor")
            if role_in_task:
                my_tasks.append({"WBS": t.wbs_code, "Task": t.name, "Role": ", ".join(role_in_task),
                                 "Progress": f"{t.progress_pct:.0f}%", "Duration": f"{t.duration_days}d"})
        if my_tasks:
            st.dataframe(pd.DataFrame(my_tasks), width="stretch", hide_index=True)
        else:
            st.info("No tasks assigned")

        st.markdown(f"##### Requirements — {sel_person['name']}")
        my_reqs = []
        for rid, own in ro.items():
            r = next((r for r in reqs if r.id == rid), None)
            if not r:
                continue
            role_in_req = []
            if own.get("owner") == pid:
                role_in_req.append("Owner")
            if own.get("approver") == pid:
                role_in_req.append("Approver")
            if role_in_req:
                status_map = {"passed": "✅", "in_progress": "🔄", "not_started": "⬜", "failed": "❌", "waived": "⏭"}
                my_reqs.append({"ID": r.req_id, "Title": r.title, "Role": ", ".join(role_in_req),
                                "Status": f"{status_map.get(r.verification_status, '')} {r.verification_status}",
                                "Allocated": ", ".join(r.allocated_to) or "—"})
        if my_reqs:
            st.dataframe(pd.DataFrame(my_reqs), width="stretch", hide_index=True)
        else:
            st.info("No requirements assigned")

        st.markdown(f"##### Pending Approvals — {sel_person['name']}")
        my_pending = [a for a in get_approval_log() if a["status"] == "pending" and a.get("approver") == pid]
        if my_pending:
            for a in my_pending:
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                col1.markdown(f"**{a['entity'].title()} {a['entity_id']}**: {a['action']}")
                col2.markdown(f"*{a['comment']}*")
                with col3:
                    if st.button("✅ Approve", key=f"mw_appr_{a['entity_id']}_{a['action']}"):
                        a["status"] = "approved"
                        st.rerun()
                with col4:
                    if st.button("❌ Reject", key=f"mw_rej_{a['entity_id']}_{a['action']}"):
                        a["status"] = "rejected"
                        st.rerun()
        else:
            st.success("No pending approvals")

    with tab_workload:
        st.markdown("##### Task Assignments per Person")
        tasks = get_tasks()
        project_start = date(2025, 10, 1)
        cpm_result = compute_cpm(tasks, project_start)

        workload_data = []
        for m in get_team():
            assigned_tasks = [tid for tid, a in get_task_assignments().items() if a.get("responsible") == m["id"]]
            contributing_tasks = [tid for tid, a in get_task_assignments().items() if m["id"] in a.get("contributors", [])]
            total_days = sum(next((t.duration_days for t in tasks if t.id == tid), 0) for tid in assigned_tasks)
            if assigned_tasks or contributing_tasks:
                workload_data.append({
                    "Name": m["name"],
                    "Role": m["role"],
                    "Responsible For": len(assigned_tasks),
                    "Contributing To": len(contributing_tasks),
                    "Total Days (resp.)": total_days,
                })
        if workload_data:
            df_wl = pd.DataFrame(workload_data).sort_values("Total Days (resp.)", ascending=False)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Responsible", x=df_wl["Name"], y=df_wl["Responsible For"], marker_color="#3498db"))
            fig.add_trace(go.Bar(name="Contributing", x=df_wl["Name"], y=df_wl["Contributing To"], marker_color="#2ecc71", opacity=0.7))
            fig.update_layout(barmode="stack", height=350, margin=dict(t=30, b=40),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.update_xaxes(gridcolor="rgba(128,128,128,0.1)")
            fig.update_yaxes(gridcolor="rgba(128,128,128,0.1)", title="# Tasks")
            st.plotly_chart(fig, width="stretch")
            st.dataframe(df_wl, width="stretch", hide_index=True)

        st.divider()
        st.markdown("##### Reassign Task")
        all_tasks_list = [t for t in tasks if not t.is_milestone]
        if all_tasks_list:
            col_t, col_m, col_b = st.columns([2, 2, 1])
            with col_t:
                sel_task = st.selectbox("Task", all_tasks_list, format_func=lambda t: f"{t.wbs_code} — {t.name}", key="wl_task")
            with col_m:
                team = get_team()
                sel_member = st.selectbox("Assign to", team, format_func=lambda m: f"{m['name']} ({m['role']})", key="wl_member") if team else None
            with col_b:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Reassign", type="primary", key="wl_reassign", disabled=sel_member is None):
                    if sel_member is None:
                        st.warning("Add a team member before reassigning tasks.")
                        return
                    if sel_task.id in get_task_assignments():
                        get_task_assignments()[sel_task.id]["responsible"] = sel_member["id"]
                    sel_task.assigned_to = f"{sel_member['name']} ({sel_member['role']})"
                    st.toast(f"Task '{sel_task.name}' reassigned to {sel_member['name']}", icon="✅")
                    st.rerun()

    with tab_approvals:
        st.markdown("##### Approval History")
        log_rows = []
        for a in reversed(get_approval_log()):
            approver = get_member(a["approver"])
            status_icons = {"approved": "✅", "pending": "⏳", "rejected": "❌"}
            log_rows.append({
                "Date": a["date"],
                "Status": f"{status_icons.get(a['status'], '')} {a['status'].upper()}",
                "Entity": a["entity"].title(),
                "ID": a["entity_id"],
                "Action": a["action"],
                "Approver": f"{approver['name']} ({a['approved_by_role']})" if approver else "",
                "Comment": a["comment"],
            })
        st.dataframe(pd.DataFrame(log_rows), width="stretch", hide_index=True, height=500)

        # Stats
        st.divider()
        _log = get_approval_log()
        total_approvals = len(_log)
        approved = sum(1 for a in _log if a["status"] == "approved")
        pending = sum(1 for a in _log if a["status"] == "pending")
        rejected = sum(1 for a in _log if a["status"] == "rejected")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Actions", total_approvals)
        c2.metric("Approved", approved)
        c3.metric("Pending", pending)
        c4.metric("Rejected", rejected)

    with tab_permissions:
        st.markdown("##### Role Definitions & Permissions")
        for role_id, role_def in ROLES.items():
            with st.expander(f"{role_def['icon']} {role_def['name']} ({role_id})", expanded=role_id in ("PM", "SE")):
                members = [m for m in get_team() if m["role"] == role_id]
                if members:
                    st.markdown("**Members:** " + ", ".join(f"{m['name']}" + (f" ({m.get('subsystem', '')})" if m.get('subsystem') else "") for m in members))
                perms = role_def["permissions"]
                perm_labels = {
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
                    "update_verification": "Update verification test results",
                }
                for p in perms:
                    st.markdown(f"- ✓ {perm_labels.get(p, p)}")

        st.divider()
        st.markdown("##### Approval Workflow")
        st.markdown("""
| Change Type | Submitted By | Approved By | Escalation |
|-------------|-------------|-------------|------------|
| Task progress | SSL / AIT | SE (or PM for system tasks) | PM |
| Requirement status | SSL / SE | SE (or QA for inspections) | PM |
| Risk update | SSL / SE | PM (Risk Board) | — |
| Budget change | SSL / SE | SE + PM | — |
| Review gate | SE | PM (Review Board) | — |
| Document baseline | CM | QA + PM | — |
| Milestone completion | PM | Review Board | — |
""")


def page_integrations():
    colored_header(label="Integrations Hub", description="External tools, orbit analysis, environment models & data import", color_name="orange-70")

    # ── Phase-Centric Mission Parameters ─────────────────────────
    from bepi.integrations.mission_phases import (
        PhaseType, MissionPhase, MissionProfile, TEMPLATES,
        ALL_SUBSYSTEMS, DEFAULT_ACTIVE_SUBSYSTEMS,
        compute_phase_delta_v, generate_phase_summary_table,
    )

    # Initialize mission profile in session state
    if "mission_profile" not in st.session_state:
        st.session_state["mission_profile"] = None
    if "active_phase_index" not in st.session_state:
        st.session_state["active_phase_index"] = 0

    profile: MissionProfile | None = st.session_state["mission_profile"]

    # Phase manager expander
    with st.expander("🚀 **Mission Phases** — define mission phases or use manual orbit parameters", expanded=profile is None):
        _pm1, _pm2 = st.columns([2, 1])
        with _pm1:
            tmpl_name = st.selectbox("Load template", ["(none)"] + list(TEMPLATES.keys()),
                                      format_func=lambda x: {"(none)": "— Manual / Custom —", "LEO_ONLY": "LEO Only",
                                                              "GEO_TRANSFER": "GEO Transfer", "LUNAR_MISSION": "Lunar Mission",
                                                              "MARS_MISSION": "Mars Mission", "JUPITER_FLYBY": "Jupiter Flyby"}.get(x, x),
                                      key="_tmpl_sel")
        with _pm2:
            if st.button("Load", key="_tmpl_load") and tmpl_name != "(none)":
                st.session_state["mission_profile"] = MissionProfile(
                    name=TEMPLATES[tmpl_name].name,
                    phases=[MissionPhase(
                        name=p.name, phase_type=p.phase_type, body=p.body,
                        orbital_params=p.orbital_params, duration_days=p.duration_days,
                        delta_v_ms=p.delta_v_ms, notes=p.notes,
                        active_subsystems=DEFAULT_ACTIVE_SUBSYSTEMS.get(p.phase_type, ALL_SUBSYSTEMS.copy()),
                        full_orbital_params={"alt_km": p.orbital_params.get("alt_km", 550),
                                             "inc_deg": 97.6, "ecc": p.orbital_params.get("eccentricity", 0.001),
                                             "raan_deg": 0.0, "aop_deg": 0.0, "mass_kg": 285.0, "area_m2": 1.5},
                    ) for p in TEMPLATES[tmpl_name].phases]
                )
                st.session_state["active_phase_index"] = 0
                st.rerun()

        if profile and profile.phases:
            # Editable phase table via data_editor
            phase_df_data = []
            for i, p in enumerate(profile.phases):
                phase_df_data.append({
                    "#": i + 1,
                    "Name": p.name,
                    "Type": p.phase_type.value,
                    "Body": p.body,
                    "Alt (km)": p.full_orbital_params.get("alt_km", 550),
                    "Inc (°)": p.full_orbital_params.get("inc_deg", 97.6),
                    "Ecc": p.full_orbital_params.get("ecc", 0.001),
                    "Duration (d)": p.duration_days,
                    "ΔV (m/s)": p.delta_v_ms,
                })
            import pandas as pd
            edited = st.data_editor(pd.DataFrame(phase_df_data), hide_index=True, num_rows="dynamic",
                                     column_config={
                                         "#": st.column_config.NumberColumn(disabled=True, width="small"),
                                         "Type": st.column_config.SelectboxColumn(options=[e.value for e in PhaseType]),
                                         "Body": st.column_config.SelectboxColumn(options=["Earth", "Mars", "Moon", "Venus", "Jupiter", "Saturn", "Mercury", "Sun", "Deep Space"]),
                                     }, key="_phase_editor")

            # Sync edits back to profile
            new_phases = []
            for _, row in edited.iterrows():
                idx = int(row["#"]) - 1 if row["#"] == row["#"] else len(new_phases)
                pt = PhaseType(row["Type"]) if row["Type"] in [e.value for e in PhaseType] else PhaseType.PARKING_ORBIT
                old = profile.phases[idx] if idx < len(profile.phases) else None
                new_phases.append(MissionPhase(
                    name=row["Name"], phase_type=pt, body=row["Body"],
                    orbital_params=old.orbital_params if old else {},
                    duration_days=float(row["Duration (d)"]), delta_v_ms=float(row["ΔV (m/s)"]),
                    notes=old.notes if old else "",
                    active_subsystems=old.active_subsystems if old else DEFAULT_ACTIVE_SUBSYSTEMS.get(pt, ALL_SUBSYSTEMS.copy()),
                    full_orbital_params={"alt_km": float(row["Alt (km)"]), "inc_deg": float(row["Inc (°)"]),
                                         "ecc": float(row["Ecc"]), "raan_deg": old.full_orbital_params.get("raan_deg", 0.0) if old else 0.0,
                                         "aop_deg": old.full_orbital_params.get("aop_deg", 0.0) if old else 0.0,
                                         "mass_kg": old.full_orbital_params.get("mass_kg", 285.0) if old else 285.0,
                                         "area_m2": old.full_orbital_params.get("area_m2", 1.5) if old else 1.5},
                ))
            profile.phases = new_phases
            st.session_state["mission_profile"] = profile

            # Subsystem assignment per phase
            with st.expander("Subsystem assignment per phase"):
                sub_data = []
                for i, p in enumerate(profile.phases):
                    row = {"Phase": p.name}
                    for s in ALL_SUBSYSTEMS:
                        row[s] = s in p.active_subsystems
                    sub_data.append(row)
                sub_edited = st.data_editor(pd.DataFrame(sub_data), hide_index=True, disabled=["Phase"],
                                             column_config={"Phase": st.column_config.TextColumn(width="medium")},
                                             key="_sub_editor")
                # Sync back
                for i, (_, row) in enumerate(sub_edited.iterrows()):
                    if i < len(profile.phases):
                        profile.phases[i].active_subsystems = [s for s in ALL_SUBSYSTEMS if row.get(s, False)]
                st.session_state["mission_profile"] = profile

            # Action buttons row
            import json as _json
            _ab1, _ab2, _ab3, _ab4 = st.columns(4)
            with _ab1:
                if st.button("➕ Add Phase", key="_add_phase"):
                    profile.phases.append(MissionPhase(
                        name=f"Phase {len(profile.phases)+1}", phase_type=PhaseType.PARKING_ORBIT,
                        body="Earth", orbital_params={}, duration_days=30, delta_v_ms=0,
                        notes="", active_subsystems=ALL_SUBSYSTEMS.copy(),
                        full_orbital_params={"alt_km": 550, "inc_deg": 97.6, "ecc": 0.001,
                                             "raan_deg": 0.0, "aop_deg": 0.0, "mass_kg": 285.0, "area_m2": 1.5},
                    ))
                    st.session_state["mission_profile"] = profile
                    st.rerun()
            with _ab2:
                st.download_button("📥 Export JSON", data=_json.dumps(profile.to_dict(), indent=2),
                                   file_name=f"{profile.name or 'mission'}_profile.json",
                                   mime="application/json", key="_export_json")
            with _ab3:
                _uploaded = st.file_uploader("📤 Import JSON", type=["json"], key="_import_json", label_visibility="collapsed")
                if _uploaded is not None:
                    try:
                        loaded = MissionProfile.from_dict(_json.loads(_uploaded.read()))
                        st.session_state["mission_profile"] = loaded
                        st.rerun()
                    except Exception as e:
                        st.error(f"Import failed: {e}")
            with _ab4:
                if st.button("Clear all phases", key="_clear_phases"):
                    st.session_state["mission_profile"] = None
                    st.rerun()
        else:
            st.caption("No phases defined. Use manual orbit parameters below, or load a template above.")
            # Manual fallback
            _oc1, _oc2, _oc3, _oc4 = st.columns(4)
            with _oc1:
                st.session_state.setdefault("orb_alt", 550)
                st.session_state["orb_alt"] = st.number_input("Altitude (km)", 200, 40000, st.session_state["orb_alt"], key="_orb_alt")
                st.session_state.setdefault("orb_ecc", 0.001)
                st.session_state["orb_ecc"] = st.number_input("Eccentricity", 0.0, 0.99, st.session_state["orb_ecc"], format="%.4f", key="_orb_ecc")
            with _oc2:
                st.session_state.setdefault("orb_inc", 97.6)
                st.session_state["orb_inc"] = st.number_input("Inclination (°)", 0.0, 180.0, st.session_state["orb_inc"], key="_orb_inc")
                st.session_state.setdefault("orb_raan", 0.0)
                st.session_state["orb_raan"] = st.number_input("RAAN (°)", 0.0, 360.0, st.session_state["orb_raan"], key="_orb_raan")
            with _oc3:
                st.session_state.setdefault("orb_aop", 0.0)
                st.session_state["orb_aop"] = st.number_input("Arg. perigee (°)", 0.0, 360.0, st.session_state["orb_aop"], key="_orb_aop")
                st.session_state.setdefault("orb_mass", 285.0)
                st.session_state["orb_mass"] = st.number_input("S/C mass (kg)", 1.0, 10000.0, st.session_state["orb_mass"], key="_orb_mass")
            with _oc4:
                st.session_state.setdefault("orb_area", 1.5)
                st.session_state["orb_area"] = st.number_input("Cross section (m²)", 0.1, 100.0, st.session_state["orb_area"], key="_orb_area")
                st.session_state.setdefault("orb_epoch", "01 Jun 2027 12:00:00.000")
                st.session_state["orb_epoch"] = st.text_input("Epoch", st.session_state["orb_epoch"], key="_orb_epoch")

    # Active phase selector (always visible when phases exist)
    profile = st.session_state.get("mission_profile")
    if profile and profile.phases:
        phase_names = [p.name for p in profile.phases]
        options = phase_names + ["📊 All Phases (Aggregated)"]
        _sel_col1, _sel_col2 = st.columns([3, 1])
        with _sel_col1:
            active_sel = st.selectbox("🎯 Active Phase", options, index=st.session_state.get("active_phase_index", 0), key="_active_phase")
        with _sel_col2:
            active_phase = profile.phases[options.index(active_sel)] if active_sel != "📊 All Phases (Aggregated)" else None
            if active_phase:
                st.caption(f"**{active_phase.body}** · {active_phase.full_orbital_params.get('alt_km', 0):.0f} km · {active_phase.duration_days:.0f}d · {len(active_phase.active_subsystems)} subsys")
            else:
                st.caption(f"**{len(profile.phases)} phases** · {profile.total_duration():.0f} days total")

        if active_sel == "📊 All Phases (Aggregated)":
            st.session_state["active_phase_index"] = len(phase_names)
            # Use first phase params as defaults for tools that need single orbit
            fp = profile.phases[0].full_orbital_params
        else:
            idx = phase_names.index(active_sel)
            st.session_state["active_phase_index"] = idx
            fp = profile.phases[idx].full_orbital_params
            st.session_state["active_subsystems"] = profile.phases[idx].active_subsystems

        # Write selected phase params to shared session state
        st.session_state["orb_alt"] = fp.get("alt_km", 550)
        st.session_state["orb_inc"] = fp.get("inc_deg", 97.6)
        st.session_state["orb_ecc"] = fp.get("ecc", 0.001)
        st.session_state["orb_raan"] = fp.get("raan_deg", 0.0)
        st.session_state["orb_aop"] = fp.get("aop_deg", 0.0)
        st.session_state["orb_mass"] = fp.get("mass_kg", 285.0)
        st.session_state["orb_area"] = fp.get("area_m2", 1.5)
    else:
        active_sel = None
        active_phase = None
        st.session_state.setdefault("orb_alt", 550)
        st.session_state.setdefault("orb_inc", 97.6)
        st.session_state.setdefault("orb_ecc", 0.001)
        st.session_state.setdefault("orb_raan", 0.0)
        st.session_state.setdefault("orb_aop", 0.0)
        st.session_state.setdefault("orb_mass", 285.0)
        st.session_state.setdefault("orb_area", 1.5)
        st.session_state.setdefault("orb_epoch", "01 Jun 2027 12:00:00.000")

    # Shortcuts (used by all downstream tabs)
    _alt = st.session_state["orb_alt"]
    _inc = st.session_state["orb_inc"]
    _ecc = st.session_state["orb_ecc"]
    _raan = st.session_state["orb_raan"]
    _aop = st.session_state["orb_aop"]
    _mass = st.session_state["orb_mass"]
    _area = st.session_state["orb_area"]
    _epoch = st.session_state.get("orb_epoch", "01 Jun 2027 12:00:00.000")

    if active_sel and active_sel != "📊 All Phases (Aggregated)":
        st.caption(f"📍 **{active_sel}** — {active_phase.body} · {active_phase.full_orbital_params.get('alt_km', 0):.0f} km · {active_phase.phase_type.value} · {active_phase.duration_days:.0f}d")

    tab_gmat, tab_viz, tab_mission, tab_pwr, tab_env, tab_lca, tab_spice, tab_import = st.tabs([
        "🛰️ Orbit Analysis", "🌐 3D Visualizer", "🚀 Mission Design",
        "🔋 Power & Thermal", "🌍 Space Environment", "♻️ LCA / OpenLCA", "🔑 SPICE Kernels", "📥 External Import"])

    # ── Orbit Analysis ───────────────────────────────────────────
    with tab_gmat:
        from bepi.integrations.gmat import (
            SpacecraftParams, OrbitParams, PropagationConfig, GroundStation,
            COMMON_GROUND_STATIONS,
            generate_propagation_script as gmat_prop, generate_maneuver_script as gmat_mnvr, generate_stationkeeping_script as gmat_sk,
        )
        from bepi.integrations.freeflyer import (
            generate_propagation_script as ff_prop, generate_maneuver_script as ff_mnvr, generate_stationkeeping_script as ff_sk,
        )
        from bepi.integrations.matlab_gen import (
            generate_propagation_script as mat_prop, generate_maneuver_script as mat_mnvr, generate_stationkeeping_script as mat_sk,
        )
        from bepi.integrations.mission_script_gen import (
            generate_total_mission_gmat, generate_total_mission_freeflyer, generate_total_mission_matlab,
        )
        from bepi.integrations.celestial_bodies import body_names, planet_names

        _oa1, _oa2 = st.columns([2, 1])
        with _oa1:
            tool_choice = st.radio("Script target", ["GMAT", "FreeFlyer", "MATLAB"], horizontal=True, key="orbit_tool")
        with _oa2:
            _body_default = active_phase.body if active_phase else "Earth"
            _body_opts = body_names()
            _body_idx = _body_opts.index(_body_default) if _body_default in _body_opts else _body_opts.index("Earth")
            orbit_body = st.selectbox("Central body", _body_opts, index=_body_idx, key="orbit_body")
        if tool_choice == "GMAT":
            st.markdown("Generate [GMAT](https://sourceforge.net/projects/gmat/) `.script` files for high-fidelity orbit propagation and maneuver planning.")
        elif tool_choice == "FreeFlyer":
            st.markdown("Generate [FreeFlyer](https://ai-solutions.com/freeflyer/) `.MissionPlan` files for orbit propagation and maneuver planning.")
        else:
            st.markdown("Generate MATLAB scripts using **Satellite Communications Toolbox** / **Aerospace Toolbox** for 3D scenario, access analysis and ground track.")

        alt_km, inc_deg, ecc, epoch = _alt, _inc, _ecc, _epoch

        gc1, gc2 = st.columns(2)
        with gc1:
            st.markdown("**Spacecraft-specific**")
            dry_mass = st.number_input("Dry mass (kg)", 1.0, 10000.0, 260.0, key="gmat_dm")
            fuel_mass = st.number_input("Fuel mass (kg)", 0.0, 5000.0, 25.0, key="gmat_fm")
        with gc2:
            drag_area = st.number_input("Drag area (m²)", 0.1, 100.0, _area, key="gmat_da")
            srp_area = st.number_input("SRP area (m²)", 0.1, 100.0, 3.0, key="gmat_sa")

        from bepi.integrations.celestial_bodies import get_body as _get_body
        _ob = _get_body(orbit_body)
        orbit = OrbitParams(epoch=epoch, sma_km=_ob.radius_km + alt_km, ecc=ecc, inc_deg=inc_deg, body=orbit_body)
        sc_p = SpacecraftParams(dry_mass_kg=dry_mass, fuel_mass_kg=fuel_mass, drag_area_m2=drag_area, srp_area_m2=srp_area)

        if tool_choice == "MATLAB":
            st.markdown("---")
            mat_type = st.radio("MATLAB script type", ["Scenario Propagation", "Delta-V Maneuver", "Station-Keeping"], horizontal=True, key="mat_type")

            if mat_type == "Scenario Propagation":
                mat_gs = st.multiselect("Ground stations", list(COMMON_GROUND_STATIONS.keys()),
                                         default=["Svalbard", "Kiruna"], key="mat_sc_gs")
                mat_dur = st.number_input("Duration (days)", 0.1, 365.0, 1.0, key="mat_sc_dur2")
                if st.button("Generate MATLAB Script", type="primary", key="mat_sc_gen"):
                    gs_list = [COMMON_GROUND_STATIONS[n] for n in mat_gs]
                    config_mat = PropagationConfig(duration_days=mat_dur)
                    mat_script = mat_prop(sc_p, orbit, config_mat, gs_list, body=orbit_body)
                    st.code(mat_script, language="matlab")
                    st.download_button("📥 Download .m", mat_script, "BEPISAT_scenario.m", "text/plain")

            elif mat_type == "Delta-V Maneuver":
                mc1, mc2 = st.columns(2)
                with mc1:
                    mat_dv = st.number_input("Delta-V (m/s)", 0.01, 1000.0, 1.0, key="mat_dv")
                with mc2:
                    mat_dir = st.selectbox("Direction", ["velocity", "normal", "binormal"], key="mat_dir")
                if st.button("Generate MATLAB Script", type="primary", key="mat_gen_mnvr"):
                    mat_script = mat_mnvr(sc_p, orbit, mat_dv, mat_dir, body=orbit_body)
                    st.code(mat_script, language="matlab")
                    st.download_button("📥 Download .m", mat_script, "BEPISAT_maneuver.m", "text/plain")

            else:  # Station-Keeping
                sk1, sk2 = st.columns(2)
                with sk1:
                    mat_sk_alt = st.number_input("Target altitude (km)", 200, 2000, 550, key="mat_sk_alt")
                    mat_sk_tol = st.number_input("Tolerance (km)", 0.5, 50.0, 5.0, key="mat_sk_tol")
                with sk2:
                    mat_sk_days = st.number_input("Simulation (days)", 1, 365, 30, key="mat_sk_days")
                if st.button("Generate MATLAB Script", type="primary", key="mat_gen_sk"):
                    mat_script = mat_sk(sc_p, orbit, float(mat_sk_alt), mat_sk_tol, float(mat_sk_days), body=orbit_body)
                    st.code(mat_script, language="matlab")
                    st.download_button("📥 Download .m", mat_script, "BEPISAT_stationkeeping.m", "text/plain")

        else:
            gmat_type = st.radio("Script type", ["Orbit Propagation", "Delta-V Maneuver", "Station-Keeping"], horizontal=True, key="gmat_type")

        if tool_choice != "MATLAB":
            if gmat_type == "Orbit Propagation":
                pc1, pc2 = st.columns(2)
                with pc1:
                    duration = st.number_input("Duration (days)", 0.1, 365.0, 1.0, key="gmat_dur")
                    force = st.selectbox("Force model", ["full", "j2", "two_body"], key="gmat_force",
                                         help="full=all perturbations, j2=Earth oblateness only, two_body=Keplerian")
                with pc2:
                    gs_selected = st.multiselect("Ground stations", list(COMMON_GROUND_STATIONS.keys()),
                                                 default=["Svalbard", "Kiruna"], key="gmat_gs")
                gs_list = [COMMON_GROUND_STATIONS[n] for n in gs_selected]
                config = PropagationConfig(duration_days=duration, force_model=force)

                if st.button(f"Generate {tool_choice} Script", type="primary", key="gmat_gen_prop"):
                    if tool_choice == "GMAT":
                        script = gmat_prop(sc_p, orbit, config, gs_list)
                        ext, fname = ".script", "BEPISAT_propagation.script"
                    else:
                        script = ff_prop(sc_p, orbit, config, gs_list)
                        ext, fname = ".MissionPlan", "BEPISAT_propagation.MissionPlan"
                    st.code(script[:3000], language="matlab")
                    st.download_button(f"📥 Download {ext}", script, fname, "text/plain")

            elif gmat_type == "Delta-V Maneuver":
                mc1, mc2 = st.columns(2)
                with mc1:
                    dv = st.number_input("Delta-V (m/s)", 0.01, 1000.0, 1.0, key="gmat_dv")
                with mc2:
                    direction = st.selectbox("Direction", ["velocity", "normal", "binormal"], key="gmat_dir")

                if st.button(f"Generate {tool_choice} Script", type="primary", key="gmat_gen_mnvr"):
                    if tool_choice == "GMAT":
                        script = gmat_mnvr(sc_p, orbit, dv, direction)
                        ext, fname = ".script", "BEPISAT_maneuver.script"
                    else:
                        script = ff_mnvr(sc_p, orbit, dv, direction)
                        ext, fname = ".MissionPlan", "BEPISAT_maneuver.MissionPlan"
                    st.code(script[:3000], language="matlab")
                    st.download_button(f"📥 Download {ext}", script, fname, "text/plain")

            else:  # Station-Keeping
                sk1, sk2 = st.columns(2)
                with sk1:
                    target_alt = st.number_input("Target altitude (km)", 200, 2000, 550, key="gmat_sk_alt")
                    tolerance = st.number_input("Tolerance (km)", 0.5, 50.0, 5.0, key="gmat_sk_tol")
                with sk2:
                    sim_days = st.number_input("Simulation (days)", 1, 365, 30, key="gmat_sk_days")

                if st.button(f"Generate {tool_choice} Script", type="primary", key="gmat_gen_sk"):
                    if tool_choice == "GMAT":
                        script = gmat_sk(sc_p, orbit, target_alt, tolerance, float(sim_days))
                        ext, fname = ".script", "BEPISAT_stationkeeping.script"
                    else:
                        script = ff_sk(sc_p, orbit, target_alt, tolerance, float(sim_days))
                        ext, fname = ".MissionPlan", "BEPISAT_stationkeeping.MissionPlan"
                    st.code(script[:3000], language="matlab")
                    st.download_button(f"📥 Download {ext}", script, fname, "text/plain")

        # Total Mission Script (available when mission profile is loaded)
        _tm_profile = st.session_state.get("mission_profile")
        if _tm_profile and _tm_profile.phases:
            st.markdown("---")
            st.subheader("🚀 Total Mission Script")
            st.caption(f"Generate a single script covering all {len(_tm_profile.phases)} phases of **{_tm_profile.name}**")
            if st.button("Generate Complete Mission Script", type="primary", key="gen_total_mission"):
                if tool_choice == "GMAT":
                    tm_script = generate_total_mission_gmat(_tm_profile, sc_p)
                    tm_ext, tm_fname = ".script", f"{_tm_profile.name.replace(' ','_')}_total.script"
                elif tool_choice == "FreeFlyer":
                    tm_script = generate_total_mission_freeflyer(_tm_profile, sc_p)
                    tm_ext, tm_fname = ".MissionPlan", f"{_tm_profile.name.replace(' ','_')}_total.MissionPlan"
                else:
                    tm_script = generate_total_mission_matlab(_tm_profile, sc_p)
                    tm_ext, tm_fname = ".m", f"{_tm_profile.name.replace(' ','_')}_total.m"
                st.code(tm_script[:5000], language="matlab")
                st.download_button(f"📥 Download {tm_ext}", tm_script, tm_fname, "text/plain", key="dl_total_mission")

    # ── 3D Orbit Visualizer ─────────────────────────────────────
    with tab_viz:
        from bepi.integrations.orbit_viz import (
            plot_single_orbit, plot_hohmann_transfer, plot_interplanetary,
            interplanetary_data, plot_ground_track, plot_constellation,
        )
        try:
            from bepi.integrations.orbit_viz import plot_total_mission as _plot_total_mission
        except ImportError:
            _plot_total_mission = None

        _viz_opts = ["Single Orbit", "Hohmann Transfer", "Interplanetary", "Ground Track", "Constellation"]
        _tm_p = st.session_state.get("mission_profile")
        if _tm_p and _tm_p.phases and _plot_total_mission:
            _viz_opts.append("Total Mission")

        _vc1, _vc2 = st.columns([3, 1])
        with _vc1:
            viz_type = st.radio("Visualization", _viz_opts, horizontal=True, key="viz_type")
        with _vc2:
            viz_body = st.selectbox("Body", body_names(), index=body_names().index(active_phase.body if active_phase else "Earth"), key="viz_body")

        if viz_type == "Single Orbit":
            st.caption(f"Using shared orbit: {_alt} km, {_inc}° inc, e={_ecc}, Ω={_raan}°, ω={_aop}° around {viz_body}")
            fig = plot_single_orbit(_alt, _inc, raan_deg=_raan, ecc=_ecc, aop_deg=_aop, body=viz_body)
            st.plotly_chart(fig, width="stretch")

        elif viz_type == "Hohmann Transfer":
            hc1, hc2, hc3 = st.columns(3)
            with hc1:
                h_alt1 = st.number_input("Initial altitude (km)", 200, 40000, 400, key="viz_h1")
            with hc2:
                h_alt2 = st.number_input("Final altitude (km)", 200, 40000, 35786, key="viz_h2")
            with hc3:
                h_inc = st.number_input("Inclination (°)", 0.0, 180.0, 0.0, key="viz_h_inc")
            fig, hinfo = plot_hohmann_transfer(h_alt1, h_alt2, inclination_deg=h_inc, body=viz_body)
            st.plotly_chart(fig, width="stretch")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("ΔV₁ (km/s)", f"{hinfo['dv1_kms']:.4f}")
            mc2.metric("ΔV₂ (km/s)", f"{hinfo['dv2_kms']:.4f}")
            mc3.metric("ΔV total (km/s)", f"{hinfo['dv_total_kms']:.4f}")
            tof = hinfo['tof_minutes']
            mc4.metric("Transfer time", f"{tof:.1f} min" if tof < 120 else f"{hinfo['tof_hours']:.2f} h")

        elif viz_type == "Interplanetary":
            ip1, ip2 = st.columns(2)
            with ip1:
                ip_dep = st.selectbox("Departure", ["Earth", "Venus", "Mars"], key="viz_ip_dep")
            with ip2:
                ip_arr = st.selectbox("Arrival", ["Mars", "Venus", "Jupiter", "Saturn", "Mercury"], key="viz_ip_arr")
            fig = plot_interplanetary(ip_dep, ip_arr)
            st.plotly_chart(fig, width="stretch")

            ipd = interplanetary_data(ip_dep, ip_arr)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Transfer time", f"{ipd['tof_days']:.0f} days ({ipd['tof_days']/30.44:.1f} mo)")
            m2.metric("Total ΔV", f"{ipd['dv_total_kms']:.2f} km/s")
            m3.metric("C₃ departure", f"{ipd['c3_km2s2']:.1f} km²/s²")
            m4.metric("Synodic period", f"{ipd['synodic_period_years']:.1f} yr")
            st.caption(f"ΔV₁ (departure): {ipd['dv1_kms']:.3f} km/s | ΔV₂ (arrival): {ipd['dv2_kms']:.3f} km/s | "
                       f"V∞ dep: {ipd['v_inf_dep_kms']:.2f} km/s | V∞ arr: {ipd['v_inf_arr_kms']:.2f} km/s | "
                       f"Phase angle: {ipd['phase_angle_deg']:.1f}°")

        elif viz_type == "Ground Track":
            gt1, gt2, gt3 = st.columns(3)
            with gt1:
                gt_rev = st.number_input("Revolutions", 1, 20, 3, key="viz_gt_rev")
            with gt2:
                gt_swath = st.number_input("Swath half-angle (°)", 0.0, 90.0, 0.0, key="viz_gt_swath",
                                            help="0 = no swath overlay")
            with gt3:
                gt_gs_sel = st.multiselect("Ground stations", list(COMMON_GROUND_STATIONS.keys()), key="viz_gt_gs")
            gt_gs = [COMMON_GROUND_STATIONS[n] for n in gt_gs_sel] if gt_gs_sel else None
            st.caption(f"Using shared orbit: {_alt} km, {_inc}° inc, Ω={_raan}° around {viz_body}")
            fig = plot_ground_track(_alt, _inc, raan_deg=_raan, n_orbits=gt_rev, body=viz_body,
                                    ground_stations=gt_gs, swath_half_angle_deg=gt_swath)
            st.plotly_chart(fig, width="stretch")

        elif viz_type == "Constellation":
            _CONST_PRESETS = {
                "Custom": {"planes": 6, "sats": 11, "alt": 550, "inc": 86.4, "f": 0.0, "fov": 0.0},
                "Starlink Shell 1": {"planes": 72, "sats": 22, "alt": 550, "inc": 53.0, "f": 5.0, "fov": 22.5},
                "OneWeb": {"planes": 18, "sats": 40, "alt": 1200, "inc": 87.9, "f": 10.0, "fov": 25.0},
                "GPS (NAVSTAR)": {"planes": 6, "sats": 4, "alt": 20200, "inc": 55.0, "f": 60.0, "fov": 13.0},
                "Galileo": {"planes": 3, "sats": 10, "alt": 23222, "inc": 56.0, "f": 40.0, "fov": 12.5},
                "Iridium NEXT": {"planes": 6, "sats": 11, "alt": 780, "inc": 86.4, "f": 30.0, "fov": 24.0},
                "Globalstar": {"planes": 8, "sats": 6, "alt": 1414, "inc": 52.0, "f": 7.5, "fov": 26.0},
            }
            cp0, cp1 = st.columns([1, 2])
            with cp0:
                cn_preset = st.selectbox("Preset", list(_CONST_PRESETS.keys()), key="viz_cn_preset")
            _p = _CONST_PRESETS[cn_preset]
            # Reset number inputs when preset changes
            if st.session_state.get("_cn_last_preset") != cn_preset:
                st.session_state["_cn_last_preset"] = cn_preset
                if cn_preset != "Custom":
                    for _k, _v in [("viz_cn_planes", _p["planes"]), ("viz_cn_sats", _p["sats"]),
                                   ("viz_cn_alt", _p["alt"]), ("viz_cn_inc", _p["inc"]),
                                   ("viz_cn_f", _p["f"]), ("viz_cn_fov", _p["fov"])]:
                        st.session_state[_k] = _v
                    st.rerun()
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                cn_planes = st.number_input("Planes", 1, 100, _p["planes"], key="viz_cn_planes")
            with cc2:
                cn_sats = st.number_input("Sats/plane", 1, 50, _p["sats"], key="viz_cn_sats")
            with cc3:
                cn_alt = st.number_input("Altitude (km)", 200, 40000, _p["alt"], key="viz_cn_alt")
            cd1, cd2, cd3 = st.columns(3)
            with cd1:
                cn_inc = st.number_input("Inclination (°)", 0.0, 180.0, _p["inc"], key="viz_cn_inc")
            with cd2:
                cn_f = st.number_input("Phase offset F (°)", 0.0, 360.0, _p["f"], step=1.0, key="viz_cn_f",
                                       help="Walker Delta F parameter: inter-plane phase shift")
            with cd3:
                cn_fov = st.number_input("Sensor FOV half-angle (°)", 0.0, 90.0, _p["fov"], step=1.0, key="viz_cn_fov",
                                         help="Half-cone angle of instrument (comm/EO)")
            fig, cinfo = plot_constellation(cn_planes, cn_sats, cn_alt, cn_inc,
                                            phase_offset_deg=cn_f, fov_half_angle_deg=cn_fov, body=viz_body)
            st.plotly_chart(fig, width="stretch")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Total satellites", cinfo["total_sats"])
            mc2.metric("Orbital period", f"{cinfo['period_min']:.1f} min")
            mc3.metric("Max latitude", f"{cinfo['max_latitude_deg']:.1f}°")
            if cinfo["fov_ground_radius_km"] > 0:
                mc4.metric("FOV footprint", f"{cinfo['fov_ground_radius_km']:.0f} km")
            else:
                mc4.metric("Walker notation", cinfo["walker_notation"])

        elif viz_type == "Total Mission" and _plot_total_mission:
            st.caption(f"Total mission visualization for **{_tm_p.name}** ({len(_tm_p.phases)} phases)")
            fig = _plot_total_mission(_tm_p.phases)
            st.plotly_chart(fig, width="stretch")

    # ── Mission Design ────────────────────────────────────────────
    with tab_mission:
        from bepi.integrations.launch_vehicle import (
            LAUNCH_VEHICLES, select_vehicle, escape_velocity,
            c3_capability, plot_c3_curves,
        )
        from bepi.integrations.station_keeping import (
            SKParams, sk_delta_v_leo, sk_delta_v_geo, sk_delta_v_sso,
            compute_propellant_mass, total_mission_delta_v, PROPELLANT_ISP,
        )
        from bepi.integrations.reentry import (
            ReentryParams, compute_reentry_trajectory, compute_heat_shield_mass,
            plot_reentry_profile, mars_edl_sequence,
        )
        from bepi.integrations.phase_aggregation import PhaseOutput, aggregate

        md_sub = st.radio("Tool", ["Mission Overview", "Launch Vehicle", "Station Keeping & ΔV Budget",
                                     "Atmospheric Re-entry"], horizontal=True, key="md_sub")

        _profile = st.session_state.get("mission_profile")

        if md_sub == "Mission Overview":
            if not _profile or not _profile.phases:
                st.info("No mission phases defined. Use the **Mission Phases** expander above to load a template or create phases.")
            else:
                # Summary table
                summary = generate_phase_summary_table(_profile)
                import pandas as _pd_md
                summary_df = _pd_md.DataFrame(summary).rename(columns={
                    "name": "Phase", "type": "Type", "body": "Body",
                    "duration_days": "Duration (d)", "delta_v_ms": "ΔV (m/s)",
                    "cumulative_dv_ms": "Cumul. ΔV (m/s)", "cumulative_days": "Cumul. Days",
                    "notes": "Notes"})
                if "index" in summary_df.columns:
                    summary_df = summary_df.drop(columns=["index"])
                st.dataframe(summary_df, width="stretch", hide_index=True)

                m1, m2, m3 = st.columns(3)
                m1.metric("Total ΔV", f"{_profile.total_delta_v():.1f} m/s")
                m2.metric("Total duration", f"{_profile.total_duration():.0f} days ({_profile.total_duration()/365.25:.1f} yr)")
                m3.metric("Phases", str(len(_profile.phases)))

                # Timeline
                import plotly.graph_objects as go
                fig = go.Figure()
                cumulative = 0
                colors = {"parking_orbit": "#3498db", "transfer": "#e67e22", "capture_orbit": "#2ecc71",
                          "surface_ops": "#8e44ad", "escape": "#e74c3c", "reentry": "#c0392b",
                          "station_keeping": "#1abc9c", "flyby": "#f39c12"}
                for ph in _profile.phases:
                    fig.add_trace(go.Bar(x=[ph.duration_days], y=[0], orientation="h",
                                         base=cumulative, name=ph.name,
                                         marker_color=colors.get(ph.phase_type.value, "#95a5a6"),
                                         text=f"{ph.name}<br>{ph.body}<br>ΔV={ph.delta_v_ms:.0f} m/s<br>{', '.join(ph.active_subsystems)}",
                                         textposition="inside", hoverinfo="text"))
                    cumulative += ph.duration_days
                fig.update_layout(title="Mission Timeline", xaxis_title="Days", height=200,
                                  showlegend=False, barmode="stack",
                                  yaxis=dict(visible=False), margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, width="stretch")

                # Cumulative ΔV chart
                fig_dv = go.Figure()
                phase_labels = [p.name for p in _profile.phases]
                cumul_dv = []
                running = 0
                for p in _profile.phases:
                    running += p.delta_v_ms
                    cumul_dv.append(running)
                fig_dv.add_trace(go.Scatter(x=phase_labels, y=cumul_dv, mode="lines+markers+text",
                                             text=[f"{v:.0f}" for v in cumul_dv], textposition="top center",
                                             line=dict(width=3, color="#e74c3c"), marker=dict(size=10)))
                fig_dv.add_trace(go.Bar(x=phase_labels, y=[p.delta_v_ms for p in _profile.phases],
                                         name="Phase ΔV", marker_color="#3498db", opacity=0.5))
                fig_dv.update_layout(title="ΔV Budget", yaxis_title="ΔV (m/s)", height=300,
                                      showlegend=False, margin=dict(l=20, r=20, t=40, b=60))
                st.plotly_chart(fig_dv, width="stretch")

                # Subsystem activity matrix
                with st.expander("Subsystem Activity per Phase"):
                    sub_data = []
                    for ph in _profile.phases:
                        row = {"Phase": ph.name, "Body": ph.body}
                        for s in ALL_SUBSYSTEMS:
                            row[s] = "✅" if s in ph.active_subsystems else "—"
                        sub_data.append(row)
                    st.dataframe(sub_data, width="stretch", hide_index=True)

        elif md_sub == "Launch Vehicle":
            st.markdown("**Launch vehicle selection** — capability vs C₃, payload comparison.")

            lv1, lv2 = st.columns(2)
            with lv1:
                lv_payload = st.number_input("Payload mass (kg)", 1.0, 50000.0, _mass, key="lv_mass")
                lv_orbit = st.selectbox("Target orbit", ["LEO", "GTO", "SSO", "Escape"], key="lv_orbit")
            with lv2:
                lv_c3 = st.number_input("C₃ (km²/s²)", -10.0, 200.0, 0.0, key="lv_c3") if lv_orbit == "Escape" else 0.0

            capable = select_vehicle(lv_payload, lv_orbit, lv_c3 if lv_orbit == "Escape" else None)
            if capable:
                rows = []
                for v in capable:
                    cap = {"LEO": v.payload_leo_kg, "GTO": v.payload_gto_kg,
                           "SSO": v.payload_sso_kg or v.payload_leo_kg * 0.7}.get(lv_orbit, v.payload_leo_kg)
                    if lv_orbit == "Escape" and lv_c3 > 0:
                        cap = c3_capability(v, lv_c3)
                    margin = (cap - lv_payload) / cap * 100 if cap > 0 else 0
                    rows.append({"Vehicle": v.name, "Provider": v.provider,
                                 f"Capacity ({lv_orbit}, kg)": f"{cap:.0f}",
                                 "Margin": f"{margin:.1f}%",
                                 "Cost ($M)": f"{v.cost_musd:.0f}" if v.cost_musd else "N/A",
                                 "Fairing (m)": f"⌀{v.fairing_diameter_m}×{v.fairing_height_m}"})
                st.dataframe(rows, width="stretch", hide_index=True)
            else:
                st.warning("No vehicle found with sufficient capacity.")

            with st.expander("C₃ vs Payload Curves"):
                fig_c3 = plot_c3_curves()
                st.plotly_chart(fig_c3, width="stretch")

            with st.expander("Escape velocities"):
                bodies = ["Earth", "Mars", "Moon", "Venus", "Jupiter"]
                alts = [200, 200, 50, 200, 1000]
                ev_data = [{"Body": b, "Alt (km)": a, "V_esc (km/s)": f"{escape_velocity(b, a)/1000:.3f}"}
                           for b, a in zip(bodies, alts)]
                st.dataframe(ev_data, width="stretch", hide_index=True)

        elif md_sub == "Station Keeping & ΔV Budget":
            st.markdown("**Station keeping ΔV** and **total mission ΔV budget** with propellant sizing.")
            st.caption(f"Using shared orbit: {_alt} km, {_inc}° inc")

            sk_type = st.selectbox("Orbit type", ["LEO", "GEO", "SSO"], key="sk_type")
            sk_dur = st.number_input("Mission duration (years)", 0.5, 30.0, 5.0, key="sk_dur")

            if sk_type == "LEO":
                sk_p = SKParams(orbit_type="LEO", altitude_km=_alt, inclination_deg=_inc,
                                mission_duration_years=sk_dur, area_to_mass_ratio=_area / _mass)
                sk_result = sk_delta_v_leo(sk_p)
            elif sk_type == "GEO":
                sk_result = sk_delta_v_geo(0.05, True)
                sk_result = {k: v * sk_dur for k, v in sk_result.items()}
            else:
                sk_p = SKParams(orbit_type="SSO", altitude_km=_alt, inclination_deg=_inc,
                                mission_duration_years=sk_dur, area_to_mass_ratio=_area / _mass)
                sk_result = sk_delta_v_sso(sk_p)

            for k, v in sk_result.items():
                if isinstance(v, (int, float)):
                    st.metric(k, f"{v:.2f} m/s")

            st.markdown("---")
            st.markdown("**Propellant Sizing**")
            ps1, ps2 = st.columns(2)
            with ps1:
                prop_type = st.selectbox("Propellant", list(PROPELLANT_ISP.keys()), key="prop_type")
                total_dv = st.number_input("Total ΔV (m/s)", 0.0, 50000.0,
                                            float(sum(v for v in sk_result.values() if isinstance(v, (int, float)))),
                                            key="prop_dv")
            with ps2:
                dry_mass_prop = st.number_input("Dry mass (kg)", 1.0, 50000.0, _mass, key="prop_drym")

            isp = PROPELLANT_ISP[prop_type]
            prop = compute_propellant_mass(total_dv, dry_mass_prop, isp)
            p1, p2, p3 = st.columns(3)
            p1.metric("Propellant mass", f"{prop['propellant_mass_kg']:.2f} kg")
            p2.metric("Total wet mass", f"{prop['total_mass_kg']:.2f} kg")
            p3.metric("Mass ratio", f"{prop['mass_ratio']:.4f}")
            st.caption(f"Isp = {isp} s | ΔV = {total_dv:.1f} m/s")

            # Delta-V budget from mission profile
            if _profile and _profile.phases:
                with st.expander("Full Mission ΔV Budget (from Mission Profile)"):
                    dv_items = [{"phase": p.name, "delta_v_ms": p.delta_v_ms} for p in _profile.phases]
                    dv_items.append({"phase": f"Station keeping ({sk_dur:.0f} yr)", "delta_v_ms": total_dv})
                    budget = total_mission_delta_v(dv_items)
                    st.dataframe(budget["breakdown"], width="stretch", hide_index=True)
                    st.metric("Grand total ΔV", f"{budget['total_delta_v_ms']:.1f} m/s")

        else:  # Atmospheric Re-entry
            st.markdown("**Atmospheric re-entry analysis** — Earth and Mars entry, heating, deceleration, EDL.")

            re_body = st.selectbox("Body", ["Earth", "Mars", "Venus", "Titan"], key="re_body")
            rc1, rc2 = st.columns(2)
            with rc1:
                re_vel = st.number_input("Entry velocity (km/s)", 1.0, 50.0,
                                          {"Earth": 7.8, "Mars": 5.5, "Venus": 10.5, "Titan": 6.0}[re_body],
                                          key="re_vel")
                re_fpa = st.number_input("Flight path angle (°)", -90.0, -0.1, -5.0, key="re_fpa")
                re_bc = st.number_input("Ballistic coeff (kg/m²)", 10.0, 5000.0, 100.0, key="re_bc")
            with rc2:
                re_rn = st.number_input("Nose radius (m)", 0.01, 5.0, 0.5, key="re_rn")
                re_mass_v = st.number_input("Vehicle mass (kg)", 1.0, 50000.0, _mass, key="re_mass")
                re_shield = st.selectbox("Heat shield", ["ablative", "reusable", "none"], key="re_shield")

            re_params = ReentryParams(body=re_body, entry_velocity_kms=re_vel, entry_angle_deg=re_fpa,
                                       ballistic_coefficient_kg_m2=re_bc, nose_radius_m=re_rn,
                                       vehicle_mass_kg=re_mass_v, heat_shield_type=re_shield)
            traj = compute_reentry_trajectory(re_params)

            t1, t2, t3 = st.columns(3)
            t1.metric("Peak deceleration", f"{traj['peak_deceleration_g']:.1f} g")
            t2.metric("Peak heat flux", f"{traj['peak_heat_flux_w_cm2']:.1f} W/cm²")
            t3.metric("Total heat load", f"{traj['total_heat_load_j_cm2']:.0f} J/cm²")

            t4, t5, t6 = st.columns(3)
            t4.metric("Peak heating alt", f"{traj['altitude_peak_heating_km']:.1f} km")
            t5.metric("Time to peak", f"{traj['time_to_peak_heating_s']:.0f} s")
            t6.metric("Terminal velocity", f"{traj['terminal_velocity_ms']:.1f} m/s")

            fig_re = plot_reentry_profile(traj)
            st.plotly_chart(fig_re, width="stretch")

            with st.expander("Heat Shield Sizing"):
                hs = compute_heat_shield_mass(re_params, traj["total_heat_load_j_cm2"])
                for k, v in hs.items():
                    if isinstance(v, (int, float)):
                        st.metric(k.replace("_", " ").title(), f"{v:.2f}")

            if re_body == "Mars":
                with st.expander("Mars EDL Sequence"):
                    edl = mars_edl_sequence(re_params, parachute_deploy_mach=1.8, retro_thrust=True)
                    for phase_name, phase_data in edl.items():
                        if isinstance(phase_data, dict):
                            st.markdown(f"**{phase_name}**")
                            for k, v in phase_data.items():
                                st.caption(f"  {k}: {v}")

    # ── Power & Thermal ──────────────────────────────────────────
    with tab_pwr:
        from bepi.integrations.power_solar import (
            SolarArrayParams, OrbitLightingParams,
            compute_eclipse_fraction, compute_solar_power_profile,
            compute_battery_sizing, compute_power_budget_balance,
            export_systema_power_csv, plot_power_profile,
        )
        from bepi.integrations.thermal_model import (  # noqa: E402
            ThermalNode, ThermalCoupling, EnvironmentFluxes, ThermalModelParams,
            DEFAULT_SAT_NODES, solve_steady_state, solve_transient,
            export_systema_thermal_csv, export_esatan_input,
            plot_thermal_map, plot_transient,
            solve_worst_case, radiator_sizing, heater_sizing, make_sun_arrow,
        )
        from bepi.integrations.sat_3d_model import (
            SatelliteGeometry, SubsystemBlock, plot_satellite_3d, plot_satellite_with_orbit,
            create_face_to_node_mapping,
        )

        pwr_sub = st.radio("Analysis", ["Solar Array & Power", "Thermal Model", "3D Satellite Model"],
                           horizontal=True, key="pwr_sub")

        if pwr_sub == "Solar Array & Power":
            st.markdown("**Solar array power generation and battery sizing** using shared orbit parameters.")
            pc1, pc2 = st.columns(2)
            with pc1:
                sa_area = st.number_input("Array area (m²)", 0.1, 50.0, 2.0, key="sa_area")
                sa_eff = st.number_input("Cell efficiency", 0.1, 0.5, 0.30, format="%.2f", key="sa_eff")
                sa_wings = st.number_input("Wings", 1, 4, 2, key="sa_wings")
                sa_track = st.selectbox("Tracking", ["fixed", "1axis", "2axis"], key="sa_track",
                                       help="fixed=body-mounted, 1axis=single-axis SADM, 2axis=full sun-tracking")
            with pc2:
                sa_degrad = st.number_input("Degradation/yr", 0.0, 0.1, 0.02, format="%.3f", key="sa_degrad")
                sa_year = st.number_input("Mission year (EOL)", 1, 20, 5, key="sa_year")
                beta_deg = st.number_input("Beta angle (°)", -90.0, 90.0, 0.0, key="sa_beta")
                bus_v = st.number_input("Bus voltage (V)", 12, 100, 28, key="bus_v")

            sa_params = SolarArrayParams(area_m2=sa_area, efficiency=sa_eff, n_wings=sa_wings,
                                          tracking=sa_track, degradation_per_year=sa_degrad)
            _epoch_year = int(_epoch.split()[2]) if len(_epoch.split()) >= 3 else 2027
            orb_light = OrbitLightingParams(altitude_km=_alt, inclination_deg=_inc,
                                            beta_angle_deg=beta_deg, epoch_year=_epoch_year)

            pwr_profile = compute_solar_power_profile(sa_params, orb_light, sa_year)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Avg power (orbit)", f"{pwr_profile.avg_power_orbit_w:.1f} W")
            m2.metric("Peak power", f"{pwr_profile.peak_power_w:.1f} W")
            m3.metric("Eclipse fraction", f"{pwr_profile.eclipse_fraction:.1%}")
            m4.metric("Eclipse duration", f"{pwr_profile.eclipse_duration_min:.1f} min")

            fig_pwr = plot_power_profile(pwr_profile)
            st.plotly_chart(fig_pwr, width="stretch")

            with st.expander("Battery Sizing"):
                pwr_eclipse = st.number_input("Eclipse power demand (W)", 10.0, 5000.0, 200.0, key="pwr_ecl")
                bat = compute_battery_sizing(pwr_eclipse, pwr_profile.eclipse_duration_min,
                                              bus_voltage=float(bus_v))
                b1, b2, b3 = st.columns(3)
                b1.metric("Battery capacity", f"{bat.capacity_wh:.0f} Wh ({bat.capacity_ah:.1f} Ah)")
                b2.metric("Cycles/day", f"{bat.n_cycles_per_day:.1f}")
                b3.metric("EOL capacity", f"{bat.eol_capacity_wh:.0f} Wh")

            with st.expander("Power Budget Balance"):
                st.markdown("Compare generation vs consumption per operating mode.")
                modes = {}
                n_modes = st.number_input("Operating modes", 1, 8, 3, key="pwr_nmodes")
                for i in range(int(n_modes)):
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        mname = st.text_input(f"Mode {i+1}", ["Nominal", "Eclipse", "Safe", "Science", "Downlink", "Slew", "Peak", "Standby"][i] if i < 8 else f"Mode{i+1}", key=f"pwr_mname_{i}")
                    with mc2:
                        mval = st.number_input(f"Power (W) {i+1}", 0.0, 5000.0, [250.0, 200.0, 80.0, 400.0, 350.0, 300.0, 500.0, 50.0][i] if i < 8 else 100.0, key=f"pwr_mval_{i}")
                    modes[mname] = mval
                balance = compute_power_budget_balance(pwr_profile, modes)
                for mode, data in balance.items():
                    surplus = data.get("surplus_bol_w", data.get("surplus_w", 0))
                    if surplus >= 0:
                        st.success(f"**{mode}**: +{surplus:.0f} W surplus (BOL)")
                    else:
                        st.error(f"**{mode}**: {surplus:.0f} W deficit (BOL)")

            with st.expander("📤 Export for Systema"):
                csv_pwr = export_systema_power_csv(pwr_profile, sa_params)
                st.download_button("📥 Systema Power CSV", csv_pwr, "bepi_power_systema.csv", "text/csv")

            # ── Phase power summary for aggregated mode ──
            if active_sel == "📊 All Phases (Aggregated)" and st.session_state.get("mission_profile") and st.session_state["mission_profile"].phases:
                import pandas as pd
                mp = st.session_state["mission_profile"]
                pwr_rows = []
                for ph in mp.phases:
                    fp_ph = ph.full_orbital_params
                    ph_orb = OrbitLightingParams(altitude_km=fp_ph.get("alt_km", 550),
                                                 inclination_deg=fp_ph.get("inc_deg", 97.6),
                                                 beta_angle_deg=beta_deg, epoch_year=_epoch_year)
                    ph_profile = compute_solar_power_profile(sa_params, ph_orb, sa_year)
                    pwr_rows.append({
                        "Phase": ph.name,
                        "Active Subsystems": len(ph.active_subsystems),
                        "Duration (days)": round(ph.duration_days, 1),
                        "Avg Power (W)": round(ph_profile.avg_power_orbit_w, 1),
                        "Eclipse Frac": f"{ph_profile.eclipse_fraction:.1%}",
                    })
                with st.expander("📊 Phase Power Summary"):
                    st.dataframe(pd.DataFrame(pwr_rows), width="stretch", hide_index=True)

        elif pwr_sub == "Thermal Model":
            st.markdown("**Thermal node model** — nodes, couplings (GL/GR), radiator, optical properties, orbit-correlated.")

            # ── Phase & orbit context ──
            _th_body_name = active_phase.body if active_phase else "Earth"
            from bepi.integrations.celestial_bodies import get_body as _get_body_th, solar_flux_at_body as _solar_flux
            _th_body_obj = _get_body_th(_th_body_name)
            eclipse_frac = compute_eclipse_fraction(_alt, 0.0)
            T_orbit = 2 * 3.14159 * ((_th_body_obj.radius_km + _alt)**3 / _th_body_obj.mu_km3s2)**0.5

            oc1, oc2, oc3, oc4 = st.columns(4)
            oc1.metric("Body", _th_body_name)
            oc2.metric("Altitude", f"{_alt:.0f} km")
            oc3.metric("Eclipse fraction", f"{eclipse_frac:.1%}")
            oc4.metric("Orbit period", f"{T_orbit:.0f} s ({T_orbit/60:.1f} min)")

            th_mode = st.radio("Solver", ["Steady State", "Transient (3 orbits)", "Worst Case (Hot/Cold)"],
                              horizontal=True, key="th_mode")

            # ── Thermal nodes (full properties) ──
            with st.expander("🔵 Thermal nodes — mass, area, optical, dissipation, MLI, heaters", expanded=False):
                st.caption("Edit properties per node. MLI reduces effective ε. Heaters activate in cold case below setpoint.")
                import pandas as pd
                _node_rows = []
                for dn in DEFAULT_SAT_NODES:
                    _node_rows.append({
                        "Name": dn.name, "Mass (kg)": dn.mass_kg, "Area (m²)": dn.area_m2,
                        "α_s": dn.absorptivity, "ε_IR": dn.emissivity, "Q_int (W)": dn.internal_dissipation_w,
                        "MLI": False, "Heater (W)": 0.0, "Heater SP (K)": 263.0,
                        "T_hot (K)": 323.0, "T_cold (K)": 253.0,
                        "α_s EOL": dn.absorptivity * 1.3, "ε_IR EOL": dn.emissivity,
                    })
                if "th_node_rows" not in st.session_state:
                    st.session_state["th_node_rows"] = _node_rows
                _ndf = pd.DataFrame(st.session_state["th_node_rows"])
                edited_nodes = st.data_editor(
                    _ndf,
                    column_config={
                        "α_s": st.column_config.NumberColumn("α_s BOL", min_value=0.0, max_value=1.0, format="%.2f"),
                        "ε_IR": st.column_config.NumberColumn("ε_IR BOL", min_value=0.0, max_value=1.0, format="%.2f"),
                        "α_s EOL": st.column_config.NumberColumn("α_s EOL", min_value=0.0, max_value=1.0, format="%.2f"),
                        "ε_IR EOL": st.column_config.NumberColumn("ε_IR EOL", min_value=0.0, max_value=1.0, format="%.2f"),
                        "MLI": st.column_config.CheckboxColumn("MLI"),
                        "Heater (W)": st.column_config.NumberColumn(min_value=0.0, format="%.1f"),
                        "Heater SP (K)": st.column_config.NumberColumn(min_value=50.0, max_value=400.0, format="%.0f"),
                        "T_hot (K)": st.column_config.NumberColumn(min_value=200.0, max_value=500.0, format="%.0f"),
                        "T_cold (K)": st.column_config.NumberColumn(min_value=50.0, max_value=400.0, format="%.0f"),
                    },
                    num_rows="dynamic", hide_index=True, key="th_nodes_editor",
                )
                st.session_state["th_node_rows"] = edited_nodes.to_dict("records")

                nodes = []
                for row in st.session_state["th_node_rows"]:
                    nodes.append(ThermalNode(
                        name=row["Name"], mass_kg=row["Mass (kg)"], area_m2=row["Area (m²)"],
                        absorptivity=row["α_s"], emissivity=row["ε_IR"],
                        internal_dissipation_w=row["Q_int (W)"],
                        mli=bool(row.get("MLI", False)),
                        heater_power_w=row.get("Heater (W)", 0.0),
                        heater_setpoint_k=row.get("Heater SP (K)", 263.0),
                        temp_limit_hot_k=row.get("T_hot (K)", 323.0),
                        temp_limit_cold_k=row.get("T_cold (K)", 253.0),
                        absorptivity_eol=row.get("α_s EOL"),
                        emissivity_eol=row.get("ε_IR EOL"),
                    ))

            # ── Radiator configuration ──
            with st.expander("🧊 Radiator configuration", expanded=False):
                st.caption("Configure the radiator — connects to the thermal node named 'Radiator'.")
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    rad_area = st.number_input("Radiator area (m²)", 0.0, 5.0, 0.5, format="%.2f", key="th_rad_area")
                with rc2:
                    rad_face = st.selectbox("Mounting face", ["+X", "-X", "+Y", "-Y", "+Z", "-Z"], index=2, key="th_rad_face")
                with rc3:
                    rad_eps = st.number_input("Radiator ε_IR", 0.5, 1.0, 0.92, format="%.2f", key="th_rad_eps")
                rad_alpha = st.number_input("Radiator α_s", 0.0, 0.5, 0.15, format="%.2f", key="th_rad_alpha")
                # Update the Radiator node if it exists
                for nd in nodes:
                    if "radiator" in nd.name.lower():
                        nd.area_m2 = rad_area
                        nd.emissivity = rad_eps
                        nd.absorptivity = rad_alpha
                        break

            # ── Thermal couplings (GL conductive + GR radiative) ──
            with st.expander("🔗 Thermal couplings (GL conductive / GR radiative)", expanded=False):
                st.caption("Define heat paths between nodes. GL = conductive (W/K), GR = radiative view factor × area (m²).")
                import pandas as pd
                if "th_couplings" not in st.session_state:
                    # Default: chain coupling + radiator to battery and payload
                    _def_couplings = []
                    for ci in range(min(len(DEFAULT_SAT_NODES) - 1, 6)):
                        _def_couplings.append({"Node A": DEFAULT_SAT_NODES[ci].name,
                                               "Node B": DEFAULT_SAT_NODES[ci+1].name,
                                               "GL (W/K)": 1.0, "GR (m²)": 0.0})
                    # Radiator → Battery, Radiator → Payload
                    _def_couplings.append({"Node A": "Radiator", "Node B": "Battery Pack",
                                           "GL (W/K)": 5.0, "GR (m²)": 0.0})
                    _def_couplings.append({"Node A": "Radiator", "Node B": "Payload",
                                           "GL (W/K)": 3.0, "GR (m²)": 0.0})
                    # Internal radiative exchange body→radiator
                    _def_couplings.append({"Node A": "Body (+X)", "Node B": "Radiator",
                                           "GL (W/K)": 0.0, "GR (m²)": 0.02})
                    st.session_state["th_couplings"] = _def_couplings

                _c_df = pd.DataFrame(st.session_state["th_couplings"])
                node_names = [n.name for n in nodes]
                edited_c = st.data_editor(
                    _c_df,
                    column_config={
                        "Node A": st.column_config.SelectboxColumn("Node A", options=node_names),
                        "Node B": st.column_config.SelectboxColumn("Node B", options=node_names),
                        "GL (W/K)": st.column_config.NumberColumn("GL (W/K)", min_value=0.0, format="%.2f"),
                        "GR (m²)": st.column_config.NumberColumn("GR (m²)", min_value=0.0, format="%.4f"),
                    },
                    num_rows="dynamic", hide_index=True, key="th_couplings_editor",
                )
                st.session_state["th_couplings"] = edited_c.to_dict("records")

            # Build couplings from edited table
            couplings = []
            for row in st.session_state.get("th_couplings", []):
                na, nb = row.get("Node A", ""), row.get("Node B", "")
                gl = row.get("GL (W/K)", 0.0) or 0.0
                gr = row.get("GR (m²)", 0.0) or 0.0
                if na and nb and na != nb and (gl > 0 or gr > 0):
                    couplings.append(ThermalCoupling(na, nb, gl, radiative_gr_m2=gr))

            # ── Sun direction from beta angle ──
            with st.expander("☀️ Sun direction & beta angle", expanded=False):
                import math as _math
                _beta_th = st.number_input("Beta angle (°)", -90.0, 90.0,
                                           st.session_state.get("sa_beta", 0.0), key="th_beta")
                _beta_rad = _math.radians(_beta_th)
                _sun_dir = [_math.cos(_beta_rad), _math.sin(_beta_rad), 0.0]
                st.caption(f"Sun vector: ({_sun_dir[0]:.3f}, {_sun_dir[1]:.3f}, {_sun_dir[2]:.3f})")

            # ── Environment ──
            env = EnvironmentFluxes(solar_w_m2=_solar_flux(_th_body_name),
                                    albedo_factor=_th_body_obj.albedo,
                                    earth_ir_w_m2=_th_body_obj.ir_flux_w_m2)
            params = ThermalModelParams(nodes=nodes, couplings=couplings, env=env,
                                         orbit_period_s=T_orbit, eclipse_fraction=eclipse_frac)

            # ── Solve ──
            if th_mode == "Steady State":
                temps = solve_steady_state(params)
                fig_th = plot_thermal_map(temps, nodes)
                st.plotly_chart(fig_th, width="stretch")

                tc1, tc2, tc3 = st.columns(3)
                tc1.metric("Hottest node", f"{max(temps.values()):.1f} K ({max(temps.values())-273.15:.1f} °C)")
                tc2.metric("Coldest node", f"{min(temps.values()):.1f} K ({min(temps.values())-273.15:.1f} °C)")
                _delta = max(temps.values()) - min(temps.values())
                tc3.metric("ΔT max", f"{_delta:.1f} K")

                # Show per-node results table
                import pandas as pd
                _tres = [{"Node": n, "T (K)": f"{t:.1f}", "T (°C)": f"{t-273.15:.1f}"}
                         for n, t in temps.items()]
                st.dataframe(pd.DataFrame(_tres), hide_index=True)
            elif th_mode == "Transient (3 orbits)":
                n_orb = st.number_input("Orbits to simulate", 1, 20, 3, key="th_n_orbits")
                result = solve_transient(params, n_orbits=int(n_orb))
                fig_th = plot_transient(result, eclipse_fraction=eclipse_frac, orbit_period_s=T_orbit)
                st.plotly_chart(fig_th, width="stretch")

            else:  # Worst Case
                st.markdown("**Worst-case hot/cold** — β sweep, BOL/EOL optical props, dissipation ±margin")
                wc1, wc2, wc3 = st.columns(3)
                with wc1:
                    wc_beta_hot = st.number_input("Hot β (°)", -90.0, 90.0, 0.0, key="wc_beta_hot")
                with wc2:
                    wc_beta_cold = st.number_input("Cold β (°)", -90.0, 90.0, 75.0, key="wc_beta_cold")
                with wc3:
                    wc_diss_margin = st.number_input("Dissipation margin (%)", 0, 50, 10, key="wc_diss_margin")

                wc = solve_worst_case(params, beta_range=(wc_beta_hot, wc_beta_cold),
                                      dissipation_margin=wc_diss_margin / 100.0)

                if wc.violations:
                    for v in wc.violations:
                        st.error(v)
                else:
                    st.success("✅ All nodes within temperature limits")

                import pandas as pd
                wc_rows = []
                for name in wc.hot_case:
                    wc_rows.append({
                        "Node": name,
                        "T_hot (°C)": f"{wc.hot_case[name]-273.15:.1f}",
                        "Hot margin (K)": f"{wc.hot_margins[name]:+.1f}",
                        "T_cold (°C)": f"{wc.cold_case[name]-273.15:.1f}",
                        "Cold margin (K)": f"{wc.cold_margins[name]:+.1f}",
                    })
                st.dataframe(pd.DataFrame(wc_rows), hide_index=True)

                # Radiator auto-sizing
                st.markdown("---")
                rs1, rs2 = st.columns(2)
                rs1.metric("Radiator min area (auto-sized)", f"{wc.radiator_min_area_m2:.3f} m²")
                # Current radiator
                _cur_rad = next((n for n in nodes if "radiator" in n.name.lower()), None)
                if _cur_rad:
                    _rad_ok = _cur_rad.area_m2 >= wc.radiator_min_area_m2
                    rs2.metric("Current radiator", f"{_cur_rad.area_m2:.2f} m²",
                               delta=f"{'OK' if _rad_ok else 'UNDERSIZED'}",
                               delta_color="normal" if _rad_ok else "inverse")

                # Heater sizing
                htrs = heater_sizing(params)
                if htrs:
                    st.caption("**Survival heater power needed** (cold case, EOL)")
                    htr_rows = [{"Node": n, "Heater (W)": f"{p:.1f}"} for n, p in htrs.items()]
                    st.dataframe(pd.DataFrame(htr_rows), hide_index=True)

            with st.expander("📤 Export"):
                if th_mode == "Steady State":
                    csv_th = export_systema_thermal_csv(temps, nodes)
                    st.download_button("📥 Systema Thermal CSV", csv_th, "bepi_thermal_systema.csv", "text/csv")
                esatan = export_esatan_input(params)
                st.download_button("📥 ESATAN-TMS Input", esatan, "bepi_esatan.inp", "text/plain")

        else:  # 3D Satellite Model
            import math
            st.markdown("**Simplified 3D satellite model** with thermal overlay and Systema export.")
            try:
                from bepi.integrations.sat_3d_model import export_systema_geometry, export_systema_thermal_input
            except ImportError:
                export_systema_geometry = None
                export_systema_thermal_input = None

            sc0, sc1, sc2 = st.columns([1, 1, 1])
            with sc0:
                bus_shape = st.selectbox("Bus shape", ["box", "cylinder", "hexagonal_prism"],
                                          format_func=lambda x: {"box": "📦 Box", "cylinder": "🛢️ Cylinder",
                                                                  "hexagonal_prism": "⬡ Hexagonal Prism"}.get(x, x),
                                          key="sat3d_shape")
            with sc1:
                if bus_shape == "box":
                    bx = st.number_input("Body X (m)", 0.1, 3.0, 0.6, key="sat3d_bx")
                    by = st.number_input("Body Y (m)", 0.1, 3.0, 0.6, key="sat3d_by")
                else:
                    bx = st.number_input("Diameter (m)", 0.1, 3.0, 0.8, key="sat3d_diam")
                    by = bx
                bz = st.number_input("Body Z / Height (m)", 0.1, 3.0, 0.8, key="sat3d_bz")
            with sc2:
                panel_mount = st.selectbox("Solar panels", ["deployed_both", "deployed_+y", "deployed_-y",
                                                             "body_mounted", "both", "none"],
                                            format_func=lambda x: {"deployed_both": "🔲 Wing ±Y", "deployed_+y": "🔲 Wing +Y only",
                                                                    "deployed_-y": "🔲 Wing -Y only", "body_mounted": "📐 Body-mounted (±Z)",
                                                                    "both": "🔲+📐 Wing + Body", "none": "❌ None"}.get(x, x),
                                            key="sat3d_panel_mount")
                if panel_mount != "none":
                    sp_len = st.number_input("Panel length (m)", 0.1, 10.0, 1.5, key="sat3d_sp")
                    sp_wid = st.number_input("Panel width (m)", 0.1, 5.0, 0.6, key="sat3d_pw")
                    n_panels = st.selectbox("N. panels", [1, 2], index=1, key="sat3d_npanels")
                else:
                    sp_len, sp_wid, n_panels = 0.0, 0.0, 0
                has_ant = st.checkbox("Antenna", True, key="sat3d_ant")

            # ── Radiator on 3D model ──
            with st.expander("🧊 Radiator (3D)", expanded=False):
                _3d_rc1, _3d_rc2 = st.columns(2)
                with _3d_rc1:
                    _3d_rad_area = st.number_input("Radiator area (m²)", 0.0, 5.0,
                                                    st.session_state.get("th_rad_area", 0.5),
                                                    format="%.2f", key="sat3d_rad_area")
                with _3d_rc2:
                    _3d_rad_face = st.selectbox("Radiator face", ["+X", "-X", "+Y", "-Y", "+Z", "-Z"],
                                                 index=["+X", "-X", "+Y", "-Y", "+Z", "-Z"].index(
                                                     st.session_state.get("th_rad_face", "+Y")),
                                                 key="sat3d_rad_face")

            # ── Subsystem blocks ──
            _SUBSYS_COLORS = {"OBC": "#e74c3c", "AOCS": "#3498db", "COMM": "#2ecc71",
                              "EPS": "#f39c12", "Payload": "#9b59b6", "Propulsion": "#1abc9c",
                              "Thermal": "#e67e22", "Harness": "#95a5a6"}
            if "sat3d_blocks" not in st.session_state:
                st.session_state["sat3d_blocks"] = []

            with st.expander("📦 Subsystem blocks (box / cylinder)", expanded=False):
                st.caption("Add internal equipment to the 3D model — box or cylinder shape")
                sb1, sb2, sb3 = st.columns(3)
                with sb1:
                    blk_name = st.selectbox("Subsystem", list(_SUBSYS_COLORS.keys()) + ["Custom"], key="sat3d_blk_name")
                    if blk_name == "Custom":
                        blk_name = st.text_input("Name", "MyBlock", key="sat3d_blk_custom")
                    blk_shape = st.selectbox("Shape", ["box", "cylinder"],
                                              format_func=lambda x: "📦 Box" if x == "box" else "🛢️ Cylinder",
                                              key="sat3d_blk_shape")
                with sb2:
                    if blk_shape == "cylinder":
                        blk_sx = st.number_input("Diameter (m)", 0.02, 1.0, 0.12, key="sat3d_blk_sx")
                        blk_sy = blk_sx
                    else:
                        blk_sx = st.number_input("Size X (m)", 0.02, 1.0, 0.12, key="sat3d_blk_sx")
                        blk_sy = st.number_input("Size Y (m)", 0.02, 1.0, 0.12, key="sat3d_blk_sy")
                    blk_sz = st.number_input("Height (m)" if blk_shape == "cylinder" else "Size Z (m)",
                                              0.02, 1.0, 0.08, key="sat3d_blk_sz")
                with sb3:
                    blk_ox = st.number_input("Offset X (m)", -1.0, 1.0, 0.0, key="sat3d_blk_ox")
                    blk_oy = st.number_input("Offset Y (m)", -1.0, 1.0, 0.0, key="sat3d_blk_oy")
                    blk_oz = st.number_input("Offset Z (m)", -1.0, 1.0, 0.0, key="sat3d_blk_oz")
                blk_color = _SUBSYS_COLORS.get(blk_name, "#e74c3c")
                if st.button("➕ Add block", key="sat3d_add_blk"):
                    st.session_state["sat3d_blocks"].append(
                        {"name": blk_name, "x": blk_sx, "y": blk_sy, "z": blk_sz,
                         "ox": blk_ox, "oy": blk_oy, "oz": blk_oz, "color": blk_color,
                         "shape": blk_shape})
                    st.rerun()
                if st.session_state["sat3d_blocks"]:
                    for idx, b in enumerate(st.session_state["sat3d_blocks"]):
                        bc1, bc2 = st.columns([4, 1])
                        _sh = "🛢️" if b.get("shape") == "cylinder" else "📦"
                        bc1.caption(f"{_sh} **{b['name']}** — {b['x']:.2f}×{b['y']:.2f}×{b['z']:.2f} m @ ({b['ox']:.2f}, {b['oy']:.2f}, {b['oz']:.2f})")
                        if bc2.button("🗑️", key=f"sat3d_rm_blk_{idx}"):
                            st.session_state["sat3d_blocks"].pop(idx)
                            st.rerun()

            custom_blocks = [SubsystemBlock(name=b["name"], x_m=b["x"], y_m=b["y"], z_m=b["z"],
                                            offset_x=b["ox"], offset_y=b["oy"], offset_z=b["oz"],
                                            color=b["color"], shape=b.get("shape", "box"))
                             for b in st.session_state["sat3d_blocks"]]

            geom = SatelliteGeometry(body_x_m=bx, body_y_m=by, body_z_m=bz,
                                      solar_panel_length_m=sp_len, solar_panel_width_m=sp_wid,
                                      n_panels=n_panels, panel_mounting=panel_mount,
                                      has_antenna=has_ant, bus_shape=bus_shape,
                                      bus_diameter_m=bx if bus_shape != "box" else 0.0,
                                      radiator_area_m2=_3d_rad_area, radiator_face=_3d_rad_face,
                                      custom_blocks=custom_blocks)

            show_thermal = st.checkbox("Show thermal overlay", False, key="sat3d_thermal")
            show_thermal_nodes = st.checkbox("Show thermal nodes", False, key="sat3d_th_nodes")
            thermal_colors = None
            thermal_temps = None
            if show_thermal or show_thermal_nodes:
                eclipse_frac = compute_eclipse_fraction(_alt, 0.0)
                _th3d_body = active_phase.body if active_phase else "Earth"
                from bepi.integrations.celestial_bodies import get_body as _gb3d, solar_flux_at_body as _sf3d
                _b3d = _gb3d(_th3d_body)
                T_orbit = 2 * 3.14159 * ((_b3d.radius_km + _alt)**3 / _b3d.mu_km3s2)**0.5
                env = EnvironmentFluxes(solar_w_m2=_sf3d(_th3d_body),
                                        albedo_factor=_b3d.albedo, earth_ir_w_m2=_b3d.ir_flux_w_m2)
                # Reuse couplings from thermal model tab if available
                _3d_couplings = []
                for row in st.session_state.get("th_couplings", []):
                    na, nb = row.get("Node A", ""), row.get("Node B", "")
                    gl = row.get("GL (W/K)", 0.0) or 0.0
                    gr = row.get("GR (m²)", 0.0) or 0.0
                    if na and nb and na != nb and (gl > 0 or gr > 0):
                        _3d_couplings.append(ThermalCoupling(na, nb, gl, radiative_gr_m2=gr))
                params = ThermalModelParams(nodes=DEFAULT_SAT_NODES, couplings=_3d_couplings,
                                             env=env, orbit_period_s=T_orbit, eclipse_fraction=eclipse_frac)
                temps = solve_steady_state(params)
                if show_thermal:
                    mapping = create_face_to_node_mapping(geom)
                    thermal_colors = {}
                    for face, node_name in mapping.items():
                        if node_name in temps:
                            thermal_colors[face] = temps[node_name]
                if show_thermal_nodes:
                    thermal_temps = temps

            _beta_3d = math.radians(st.session_state.get("th_beta", st.session_state.get("sa_beta", 0.0)))
            _sun3d = (math.cos(_beta_3d), math.sin(_beta_3d), 0.0)
            show_sun_arrow = st.checkbox("Show sun direction arrow", True, key="sat3d_sun_arrow")
            fig_sat = plot_satellite_3d(geom, thermal_colors=thermal_colors,
                                        thermal_temps=thermal_temps, sun_direction=_sun3d)
            if show_sun_arrow:
                fig_sat.add_trace(make_sun_arrow(_sun3d, scale=max(bx, by, bz) * 2.5))
            st.plotly_chart(fig_sat, width="stretch")

            with st.expander("Satellite in orbit context"):
                fig_ctx = plot_satellite_with_orbit(geom, _alt, _inc)
                st.plotly_chart(fig_ctx, width="stretch")

            with st.expander("📤 Systema Export & Radiative Environment"):
                try:
                    from bepi.integrations.thermal_model import compute_view_factor_to_body, compute_face_fluxes, first_order_thermal
                    from bepi.integrations.celestial_bodies import get_body as _get_body_th

                    _re_body = active_phase.body if active_phase else "Earth"
                    _re_b = _get_body_th(_re_body)
                    vf = compute_view_factor_to_body(_alt, _re_b.radius_km)
                    m1, m2 = st.columns(2)
                    m1.metric("View factor to body", f"{vf:.4f}")
                    m2.metric("Body", _re_body)

                    _re_sun = list(_sun3d)
                    fluxes = compute_face_fluxes(geom, _re_body, _alt, sun_direction=_re_sun)
                    if fluxes:
                        import pandas as pd
                        flux_rows = []
                        for face, fd in fluxes.items():
                            flux_rows.append({"Face": face,
                                              "Solar (W/m²)": f"{fd.get('direct_solar_w_m2', 0):.1f}",
                                              "Albedo (W/m²)": f"{fd.get('albedo_w_m2', 0):.1f}",
                                              "IR (W/m²)": f"{fd.get('planetary_ir_w_m2', 0):.1f}",
                                              "Total (W/m²)": f"{fd.get('total_w_m2', 0):.1f}"})
                        st.dataframe(pd.DataFrame(flux_rows), hide_index=True)

                    _int_pwr = sum(n.internal_dissipation_w for n in DEFAULT_SAT_NODES)
                    temps_1st = first_order_thermal(geom, _re_body, _alt, internal_power_w=_int_pwr,
                                                    sun_direction=_re_sun)
                    if temps_1st:
                        st.caption(f"First-order equilibrium temperatures ({_int_pwr:.0f} W internal)")
                        temp_rows = [{"Face": f, "T (K)": f"{t:.1f}", "T (°C)": f"{t-273.15:.1f}"} for f, t in temps_1st.items()]
                        st.dataframe(pd.DataFrame(temp_rows), hide_index=True)

                except Exception as e:
                    st.warning(f"Radiative environment calculation not available: {e}")

                if export_systema_geometry:
                    systema_geom = export_systema_geometry(geom)
                    st.download_button("📥 Systema Geometry", systema_geom, "bepi_systema_geometry.txt", "text/plain", key="dl_systema_geom")

    # ── Space Environment ─────────────────────────────────────────
    with tab_env:
        from bepi.integrations.spenvis import estimate_radiation, generate_spenvis_input
        from bepi.integrations.drama import estimate_debris_flux, estimate_deorbit

        env_sub = st.radio("Analysis", ["Radiation (Earth)", "Radiation (Deep Space)", "Debris (MASTER)",
                                        "Deorbit (OSCAR)", "Compliance (DAS)", "Sustainability Indices"], horizontal=True, key="env_type")

        if env_sub == "Radiation (Earth)":
            from bepi.integrations.spenvis import has_spacepy, compute_radiation_spacepy

            if has_spacepy():
                st.success("**SpacePy/IRBEM detected** — using real AP-8/AE-8 trapped particle models (same as SPENVIS)")
            else:
                st.info("Using pre-computed lookup table. Install `spacepy` + IRBEM for full AP-8/AE-8 model calculations.")

            st.caption(f"Using shared orbit: {_alt} km, {_inc}° inc")
            r_alt, r_inc = _alt, _inc
            rc1, rc2 = st.columns(2)
            with rc1:
                r_years = st.number_input("Mission (years)", 0.5, 30.0, 5.0, key="rad_years")
            with rc2:
                r_shield = st.slider("Al shielding (mm)", 0.5, 20.0, 2.0, 0.5, key="rad_shield_earth")

            result = estimate_radiation(r_alt, r_inc, r_years, r_shield)

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Ionizing Dose", f"{result['tid_krad']:.1f} krad")
            c2.metric("Proton Fluence", f"{result['proton_fluence_cm2']:.1e} /cm²")
            c3.metric("Electron Fluence", f"{result['electron_fluence_cm2']:.1e} /cm²")

            st.info(f"**Recommendation:** {result['recommendation']}")
            st.caption(f"Reference orbit: {result['reference_orbit']} | Model: {result['model']} | {result['notes']}")

            # Dose-depth curve (SpacePy or analytical)
            with st.expander("Dose-Depth Curve"):
                import plotly.graph_objects as go
                shields = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0]
                tids = []
                for s in shields:
                    r = estimate_radiation(r_alt, r_inc, r_years, s)
                    tids.append(r["tid_krad"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=shields, y=tids, mode="lines+markers", name="TID"))
                fig.update_layout(
                    title="Dose vs Al Shielding Thickness",
                    xaxis_title="Al Shielding (mm)",
                    yaxis_title="TID (krad)",
                    yaxis_type="log",
                    height=350,
                )
                st.plotly_chart(fig, width="stretch")

            # Export in standard formats
            with st.expander("📤 Export radiation data (SPENVIS / OMERE / Systema / SHIELDOSE-2)"):
                from bepi.integrations.radiation_export import RadiationExportParams, EXPORT_FORMATS
                exp_params = RadiationExportParams(altitude_km=r_alt, inclination_deg=r_inc,
                                                    mission_years=r_years)
                fmt_cols = st.columns(len(EXPORT_FORMATS))
                for col, (key, (label, fn, ext)) in zip(fmt_cols, EXPORT_FORMATS.items()):
                    with col:
                        data = fn(exp_params)
                        st.download_button(f"📥 {label}", data,
                                           f"BEPI_radiation_{key}{ext}", "text/plain",
                                           key=f"rad_exp_{key}")

            # ── Phase breakdown for aggregated mode ──
            if active_sel == "📊 All Phases (Aggregated)" and profile and profile.phases:
                from bepi.integrations.phase_aggregation import PhaseOutput, AggregatedOutput, aggregate
                from bepi.integrations.spenvis import estimate_deepspace_radiation
                import pandas as pd
                import plotly.graph_objects as go_agg

                phase_outputs = []
                for ph in profile.phases:
                    fp_ph = ph.full_orbital_params
                    ph_alt = fp_ph.get("alt_km", 550)
                    ph_inc = fp_ph.get("inc_deg", 97.6)
                    ph_years = ph.duration_days / 365.25
                    dest = fp_ph.get("destination")
                    if dest:
                        r = estimate_deepspace_radiation(dest, ph_years, r_shield)
                        tid = r["total_tid_krad"]
                        pf = r.get("proton_fluence_cm2", 0.0)
                    else:
                        r = estimate_radiation(ph_alt, ph_inc, ph_years, r_shield)
                        tid = r["tid_krad"]
                        pf = r["proton_fluence_cm2"]
                    po = PhaseOutput(
                        phase_name=ph.name, body=ph.body,
                        duration_days=ph.duration_days,
                        radiation_tid_krad=tid,
                        proton_fluence_cm2=pf,
                        active_subsystems=ph.active_subsystems,
                    )
                    phase_outputs.append(po)

                agg = aggregate(phase_outputs)
                with st.expander("📊 Phase Breakdown", expanded=True):
                    st.dataframe(pd.DataFrame(agg.summary_table()), width="stretch", hide_index=True)

                    fig_tid = go_agg.Figure()
                    fig_tid.add_trace(go_agg.Bar(
                        x=[p.phase_name for p in agg.phases],
                        y=[p.radiation_tid_krad for p in agg.phases],
                        text=[f"{p.radiation_tid_krad:.2f}" for p in agg.phases],
                        textposition="auto",
                    ))
                    fig_tid.update_layout(title="TID Contribution per Phase",
                                          xaxis_title="Phase", yaxis_title="TID (krad)", height=350)
                    st.plotly_chart(fig_tid, width="stretch")

        elif env_sub == "Radiation (Deep Space)":
            from bepi.integrations.spenvis import DEEPSPACE_LOOKUP, estimate_deepspace_radiation

            st.markdown("Radiation for lunar, interplanetary and planetary missions (GCR + SPE + trapped).")

            dest_groups = {
                "Lunar": ["LUNAR-ORBIT", "LUNAR-SURFACE"],
                "Inner cruise / Venus / Mercury": ["CRUISE-INNER", "VENUS-ORBIT", "MERCURY-ORBIT"],
                "Mars": ["MARS-ORBIT", "MARS-SURFACE"],
                "Outer cruise": ["CRUISE-OUTER"],
                "Jupiter system": ["JUPITER-ORBIT-HIGH", "JUPITER-ORBIT-GANYMEDE",
                                   "JUPITER-ORBIT-EUROPA", "JUPITER-ORBIT-IO"],
                "Saturn": ["SATURN-ORBIT"],
                "Lagrange points": ["SEL2"],
            }
            flat_keys = [k for grp in dest_groups.values() for k in grp]
            dest_labels = {k: f"{DEEPSPACE_LOOKUP[k].destination}" for k in flat_keys}

            ds1, ds2 = st.columns(2)
            with ds1:
                dest_key = st.selectbox("Destination", flat_keys,
                                        format_func=lambda k: dest_labels[k], key="ds_dest")
                ds_years = st.number_input("Mission duration (years)", 0.5, 30.0, 5.0, key="ds_years")
            with ds2:
                ds_shield = st.slider("Al shielding (mm)", 0.5, 50.0, 2.0, 0.5, key="ds_shield")
                ds_solar = st.selectbox("Solar activity", ["solar_max", "solar_min", "mean"],
                                        format_func=lambda s: {"solar_max": "Solar Maximum (worst SPE)",
                                                                "solar_min": "Solar Minimum (worst GCR)",
                                                                "mean": "Cycle Average"}[s], key="ds_solar")

            env_info = DEEPSPACE_LOOKUP[dest_key]
            has_trapped = env_info.trapped_tid_krad_per_year > 0
            has_gcr = env_info.gcr_tid_krad_per_year > 0
            has_spe = env_info.spe_tid_krad_per_event > 0
            rad_sources = []
            if has_trapped:
                rad_sources.append(f"Trapped belts: **{env_info.trapped_tid_krad_per_year:.0f} krad/yr** behind 2 mm Al")
            if has_gcr:
                rad_sources.append(f"GCR: **{env_info.gcr_tid_krad_per_year:.1f} krad/yr** (solar min)")
            if has_spe:
                rad_sources.append(f"SPE: **{env_info.spe_tid_krad_per_event:.0f} krad** per worst-case event")
            dominant = "Trapped radiation" if env_info.trapped_tid_krad_per_year > env_info.gcr_tid_krad_per_year else "GCR + SPE"
            with st.expander(f"Destination info: {env_info.destination}", expanded=True):
                st.markdown(f"**Radiation models:** {env_info.models}")
                st.markdown("**Active sources:** " + " | ".join(rad_sources))
                st.markdown(f"**Dominant source:** {dominant}")
                if env_info.notes:
                    st.caption(env_info.notes)

            ds = estimate_deepspace_radiation(dest_key, ds_years, ds_shield, ds_solar)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total TID", f"{ds['total_tid_krad']:.1f} krad")
            c2.metric("GCR TID", f"{ds['gcr_tid_krad']:.1f} krad")
            c3.metric("SPE TID", f"{ds['spe_tid_krad']:.1f} krad")
            c4.metric("Trapped TID", f"{ds['trapped_tid_krad']:.1f} krad")

            st.info(f"**Recommendation:** {ds['recommendation']}")
            st.caption(f"Models: {ds['models']}")
            if ds["notes"]:
                st.caption(ds["notes"])

            # Dose-depth curve for deep space
            with st.expander("Dose-Depth Curve"):
                import plotly.graph_objects as go
                shields = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0]
                tids_ds = [estimate_deepspace_radiation(dest_key, ds_years, s, ds_solar)["total_tid_krad"] for s in shields]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=shields, y=tids_ds, mode="lines+markers", name="Total TID"))
                fig.update_layout(title="Dose vs Al Shielding", xaxis_title="Al Shielding (mm)",
                                  yaxis_title="TID (krad)", yaxis_type="log", height=350)
                st.plotly_chart(fig, width="stretch")

            # Comparison table
            with st.expander("All destinations comparison"):
                import pandas as pd
                rows = []
                for k, v in DEEPSPACE_LOOKUP.items():
                    r = estimate_deepspace_radiation(k, ds_years, ds_shield, ds_solar)
                    rows.append({"Destination": v.destination, "Total TID (krad)": r["total_tid_krad"],
                                 "GCR": r["gcr_tid_krad"], "SPE": r["spe_tid_krad"],
                                 "Trapped": r["trapped_tid_krad"], "Models": v.models})
                st.dataframe(pd.DataFrame(rows).sort_values("Total TID (krad)", ascending=False),
                             width="stretch", hide_index=True)

            # Export deep-space radiation
            with st.expander("📤 Export radiation data (SPENVIS / OMERE / Systema / SHIELDOSE-2)"):
                from bepi.integrations.radiation_export import RadiationExportParams, EXPORT_FORMATS
                exp_params = RadiationExportParams(destination=dest_key, mission_years=ds_years,
                                                    solar_activity=ds_solar)
                fmt_cols = st.columns(len(EXPORT_FORMATS))
                for col, (key, (label, fn, ext)) in zip(fmt_cols, EXPORT_FORMATS.items()):
                    with col:
                        data = fn(exp_params)
                        st.download_button(f"📥 {label}", data,
                                           f"BEPI_radiation_{key}{ext}", "text/plain",
                                           key=f"ds_rad_exp_{key}")

        elif env_sub == "Debris (MASTER)":
            st.markdown("Space debris flux estimate based on ESA MASTER model.")
            st.caption(f"Using shared orbit: {_alt} km, {_inc}° inc | Cross section: {_area} m²")
            dc1, dc2 = st.columns(2)
            with dc1:
                d_area = st.number_input("Cross section (m²)", 0.1, 50.0, _area, key="deb_area")
            with dc2:
                d_years = st.number_input("Mission (years)", 0.5, 30.0, 5.0, key="deb_years")

            deb = estimate_debris_flux(_alt, d_area, d_years)

            c1, c2, c3 = st.columns(3)
            c1.metric("Collision probability", f"{deb['collision_probability']:.2e}")
            c2.metric("Impacts >1cm (expected)", f"{deb['expected_impacts_gt_1cm']:.4f}")
            c3.metric("Impacts >1mm (expected)", f"{deb['expected_impacts_gt_1mm']:.2f}")

            st.caption(f"Flux >1cm: {deb['flux_gt_1cm_m2_year']:.1e} /m²/yr | "
                       f">1mm: {deb['flux_gt_1mm_m2_year']:.1e} /m²/yr | "
                       f">10cm (trackable): {deb['flux_gt_10cm_m2_year']:.1e} /m²/yr")

            # ── Debris phase breakdown for aggregated mode ──
            if active_sel == "📊 All Phases (Aggregated)" and profile and profile.phases:
                from bepi.integrations.phase_aggregation import PhaseOutput, AggregatedOutput, aggregate as agg_fn
                import pandas as pd
                phase_deb_outputs = []
                for ph in profile.phases:
                    fp_ph = ph.full_orbital_params
                    ph_alt = fp_ph.get("alt_km", 550)
                    ph_area = fp_ph.get("area_m2", _area)
                    ph_years = ph.duration_days / 365.25
                    dr = estimate_debris_flux(ph_alt, ph_area, ph_years)
                    po = PhaseOutput(
                        phase_name=ph.name, body=ph.body,
                        duration_days=ph.duration_days,
                        debris_collision_prob=dr["collision_probability"],
                        debris_impacts_gt_1mm=dr["expected_impacts_gt_1mm"],
                        active_subsystems=ph.active_subsystems,
                    )
                    phase_deb_outputs.append(po)
                agg_deb = agg_fn(phase_deb_outputs)
                with st.expander("📊 Phase Breakdown", expanded=True):
                    st.dataframe(pd.DataFrame(agg_deb.summary_table()), width="stretch", hide_index=True)

        elif env_sub == "Deorbit (OSCAR)":
            st.markdown("Orbital decay and deorbit analysis for 25-year rule compliance (IADC guidelines).")
            st.caption(f"Using shared orbit: {_alt} km | Mass: {_mass} kg | Area: {_area} m²")

            deorb = estimate_deorbit(_alt, _mass, _area)

            c1, c2, c3 = st.columns(3)
            c1.metric("Natural decay", f"{deorb.natural_decay_years} years",
                      delta="Compliant" if deorb.compliant_25yr else "NON-COMPLIANT",
                      delta_color="normal" if deorb.compliant_25yr else "inverse")
            c2.metric("Deorbit ΔV", f"{deorb.delta_v_deorbit_ms} m/s")
            c3.metric("Target perigee", f"{deorb.target_perigee_km} km")

            st.info(deorb.notes)

        elif env_sub == "Compliance (DAS)":
            from bepi.integrations.debris import (
                DebrisComplianceParams, check_debris_compliance,
                export_das_xml, export_drama_config, export_master_config,
                compute_ecob, nasa_standard_breakup_model,
            )

            st.markdown("**ESA Space Debris Mitigation Requirements** — full compliance check (DAS equivalent)")

            st.caption(f"Using shared orbit: {_alt} km, {_inc}° inc | Mass: {_mass} kg | Area: {_area} m²")
            das_alt, das_inc, das_mass, das_area = _alt, _inc, _mass, _area

            das1, das2 = st.columns(2)
            with das1:
                das_name = st.text_input("Mission name", "BEPI-SAT", key="das_name")
            with das2:
                das_dur = st.number_input("Mission duration (yr)", 0.5, 30.0, 5.0, key="das_dur")
                das_debris = st.number_input("Operational debris released", 0, 100, 0, key="das_deb")
                das_passiv = st.checkbox("Passivation planned", True, key="das_pass")
                das_avoid = st.checkbox("Collision avoidance capability", True, key="das_avoid")
                das_pmd = st.slider("PMD success probability", 0.0, 1.0, 0.9, 0.05, key="das_pmd")

            dp = DebrisComplianceParams(das_name, das_alt, das_inc, das_mass, das_area,
                                        mission_duration_years=das_dur,
                                        operational_debris_count=das_debris,
                                        passivation_planned=das_passiv,
                                        has_collision_avoidance=das_avoid,
                                        pmd_success_probability=das_pmd)
            rep = check_debris_compliance(dp)

            if rep.overall_compliant:
                st.success("✅ **COMPLIANT** — All 7 ESA SDM requirements met")
            else:
                st.error("❌ **NON-COMPLIANT** — One or more requirements failed")

            for item in rep.items:
                icon = "✅" if item.compliant else "❌"
                st.markdown(f"{icon} **{item.requirement}** — {item.description}")
                st.caption(f"   {item.details}")

            # ECOB index
            with st.expander("ECOB (Environmental Consequences of Orbital Breakups)"):
                ecob = compute_ecob(das_mass, max(das_area ** 0.5, 0.5), das_alt, das_inc)
                c1, c2, c3 = st.columns(3)
                c1.metric("ECOB Index", f"{ecob.ecob_index:.4f}")
                c2.metric("Rating", ecob.rating.upper())
                c3.metric("Fragments (if breakup)", f"{ecob.total_fragments:,}")
                st.caption(f"Mean fragment lifetime: {ecob.mean_lifetime_years:.1f} yr | "
                           f"Total cross-section: {ecob.total_cross_section_m2:.0f} m²")

            # SBM detail
            with st.expander("NASA Standard Breakup Model"):
                sbm_type = st.radio("Event type", ["collision", "explosion"], horizontal=True, key="sbm_type")
                sbm = nasa_standard_breakup_model(das_mass, max(das_area ** 0.5, 0.5), sbm_type)
                st.metric("Total fragments (>1mm)", f"{sbm.total_fragments:,}")
                import plotly.graph_objects as go
                fig = go.Figure()
                sizes = sorted(sbm.fragments_by_bin.keys())
                counts = [sbm.fragments_by_bin[s] for s in sizes]
                fig.add_trace(go.Bar(x=[f"{s*100:.1f}cm" for s in sizes], y=counts, name="Fragments"))
                fig.update_layout(title="Fragment Size Distribution", xaxis_title="Min size", yaxis_title="Count", yaxis_type="log", height=300)
                st.plotly_chart(fig, width="stretch")

            # Export DAS/DRAMA/MASTER files
            with st.expander("📤 Export (DAS XML / DRAMA / MASTER format)"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    das_xml = export_das_xml(dp)
                    st.download_button("📥 DAS XML", das_xml, "BEPI_DAS_compliance.xml", "text/xml", key="exp_das")
                with ec2:
                    drama_cfg = export_drama_config(dp)
                    st.download_button("📥 DRAMA config", drama_cfg, "BEPI_DRAMA_config.txt", "text/plain", key="exp_drama")
                with ec3:
                    master_cfg = export_master_config(das_alt, das_area)
                    st.download_button("📥 MASTER config", master_cfg, "BEPI_MASTER_config.txt", "text/plain", key="exp_master")

        elif env_sub == "Sustainability Indices":
            from bepi.integrations.debris import (
                SSRParams, compute_ssr, compute_niao, compute_collision_probability,
            )
            from bepi.integrations.nacrac import (
                RCParams, RIParams, MSParams, NACRACParams, compute_nacrac,
            )

            st.markdown("**Space sustainability & debris indices** — NACRAC, SSR, NIAO, collision probability")

            st.caption(f"Using shared orbit: {_alt} km, {_inc}° inc | Mass: {_mass} kg | Area: {_area} m²")
            si_alt, si_inc, si_mass, si_area = _alt, _inc, _mass, _area

            si1, si2 = st.columns(2)
            with si1:
                st.markdown("**Orbit & Spacecraft**")
                si_life = st.number_input("Residual lifetime (yr)", 0.1, 100.0, 3.0, key="si_life")
            with si2:
                st.markdown("**Mitigations**")
                si_avoid = st.checkbox("Collision avoidance", True, key="si_avoid")
                si_demise = st.checkbox("Design-for-demise", True, key="si_demise")
                si_pmd = st.slider("PMD success probability", 0.0, 1.0, 0.95, 0.05, key="si_pmd")
                si_reentry = st.selectbox("Re-entry strategy",
                    [4, 3, 2, 1], format_func=lambda x: {4:"Controlled", 3:"Fast (<1yr)", 2:"Slow (>1yr)", 1:"Uncontrolled"}[x],
                    key="si_reentry")
                si_share = st.checkbox("Shares orbital data (SSA)", True, key="si_share")

            st.markdown("---")

            # NACRAC
            rc = RCParams(perigee_km=si_alt, apogee_km=si_alt, mass_kg=si_mass, cross_section_m2=si_area)
            ri = RIParams(residual_lifetime_years=si_life)
            ms = MSParams(reentry_strategy=si_reentry, has_collision_avoidance=si_avoid, has_design_for_demise=si_demise)
            nacrac = compute_nacrac(NACRACParams(rc, ri, ms))

            st.markdown(f"### NACRAC: `{nacrac.full_code}`")
            nc1, nc2, nc3 = st.columns(3)
            nc1.metric("R_C (Collective Risk)", nacrac.full_code.split("|")[0].strip())
            nc2.metric("R_I (Individual Risk)", nacrac.full_code.split("|")[1].strip() if "|" in nacrac.full_code else "")
            nc3.metric("M_S (Mitigation)", nacrac.full_code.split("|")[2].strip() if nacrac.full_code.count("|") >= 2 else "")

            st.markdown("---")

            # SSR
            ssr = compute_ssr(SSRParams(altitude_km=si_alt, has_collision_avoidance=si_avoid,
                                        pmd_success_probability=si_pmd,
                                        shares_orbital_data=si_share))
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("SSR Total", f"{ssr.total_score:.0f}/{ssr.max_score:.0f}")
            sc2.metric("Mission", f"{ssr.mission_score:.0f}")
            sc3.metric("Debris", f"{ssr.debris_score:.0f}")
            sc4.metric("Grade", str(ssr.grade).split(".")[-1])

            # NIAO
            niao = compute_niao(si_area, si_alt, si_mass)
            st.metric("NIAO (Atmospheric Occupation)", f"{niao.niao:.4f}", delta=niao.rating)

            # Collision probability
            col_p = compute_collision_probability(si_alt, si_area, 5.0, si_mass)
            st.caption(f"Collision prob/yr: {col_p.probability:.2e} | "
                       f"Kinetic energy: {col_p.kinetic_energy_j:.0f} J | "
                       f"Catastrophic: {'Yes' if col_p.is_catastrophic else 'No'}")

    # ── LCA / OpenLCA ─────────────────────────────────────────────
    with tab_lca:
        from bepi.integrations.openlca_export import (
            LCAItem, LCAModel, SATELLITE_MATERIALS, SUBSYSTEM_MATERIAL_DEFAULTS,
            LAUNCH_VEHICLES_LCA, IMPACT_CATEGORIES,
            generate_lca_summary, export_openlca_jsonld, export_lca_csv,
        )
        import pandas as pd

        st.markdown("**Life Cycle Assessment** — material inventory, environmental impact estimation and OpenLCA export.")

        # Build LCA items from product tree
        _pt = st.session_state.get("product_tree", [])
        _eb = st.session_state.get("equip_budgets", {})

        lca_items: list[LCAItem] = []
        if _pt and _eb:
            for node in _pt:
                if node.get("level") == "equipment":
                    code = node.get("code", "")
                    subsys = node.get("subsystem_type", code[:3])
                    bud = _eb.get(code, {})
                    mass = bud.get("unit_mass_kg", 0)
                    qty = bud.get("quantity", 1)
                    if mass > 0:
                        mat = SUBSYSTEM_MATERIAL_DEFAULTS.get(subsys, "Electronic components (generic)")
                        lca_items.append(LCAItem(name=node.get("name", "?"), subsystem=subsys,
                                                  material=mat, mass_kg=mass, quantity=qty))

        if not lca_items:
            st.info("No product tree data found. Add items manually below or load a mission with equipment budgets.")

        # Manual item entry
        with st.expander("➕ Add / edit LCA items", expanded=not lca_items):
            if "lca_items_manual" not in st.session_state:
                st.session_state["lca_items_manual"] = [
                    {"Name": "Structure panels", "Subsystem": "STR", "Material": "Aluminium alloy (6061-T6)", "Mass (kg)": 35.0, "Qty": 1},
                    {"Name": "Solar array", "Subsystem": "SA", "Material": "GaAs triple-junction solar cell", "Mass (kg)": 8.0, "Qty": 2},
                    {"Name": "Battery pack", "Subsystem": "EPS", "Material": "Li-ion battery cells", "Mass (kg)": 12.0, "Qty": 1},
                    {"Name": "OBC + electronics", "Subsystem": "CDH", "Material": "PCB (FR4 + components)", "Mass (kg)": 4.5, "Qty": 2},
                    {"Name": "Reaction wheels", "Subsystem": "AOCS", "Material": "Electronic components (generic)", "Mass (kg)": 3.0, "Qty": 4},
                    {"Name": "S-band transceiver", "Subsystem": "COM", "Material": "Electronic components (generic)", "Mass (kg)": 2.5, "Qty": 2},
                    {"Name": "Thermal blankets", "Subsystem": "TCS", "Material": "Kapton (MLI / thermal blankets)", "Mass (kg)": 5.0, "Qty": 1},
                    {"Name": "Propellant tank", "Subsystem": "PROP", "Material": "Titanium alloy (Ti-6Al-4V)", "Mass (kg)": 4.0, "Qty": 1},
                    {"Name": "Harness", "Subsystem": "HRN", "Material": "Copper (harness/wiring)", "Mass (kg)": 8.0, "Qty": 1},
                    {"Name": "Payload instrument", "Subsystem": "PL", "Material": "Electronic components (generic)", "Mass (kg)": 15.0, "Qty": 1},
                ]

            edited_df = st.data_editor(
                pd.DataFrame(st.session_state["lca_items_manual"]),
                column_config={
                    "Material": st.column_config.SelectboxColumn("Material", options=list(SATELLITE_MATERIALS.keys()), required=True),
                    "Subsystem": st.column_config.SelectboxColumn("Subsystem", options=list(SUBSYSTEM_MATERIAL_DEFAULTS.keys()), required=True),
                    "Mass (kg)": st.column_config.NumberColumn("Mass (kg)", min_value=0.0, format="%.2f"),
                    "Qty": st.column_config.NumberColumn("Qty", min_value=1, step=1),
                },
                num_rows="dynamic", key="lca_editor", use_container_width=True,
            )
            st.session_state["lca_items_manual"] = edited_df.to_dict("records")

            # Convert edited table to LCA items
            lca_items = []
            for row in edited_df.to_dict("records"):
                if row.get("Mass (kg)", 0) > 0:
                    lca_items.append(LCAItem(
                        name=row.get("Name", "?"), subsystem=row.get("Subsystem", "STR"),
                        material=row.get("Material", "Aluminium alloy (6061-T6)"),
                        mass_kg=row.get("Mass (kg)", 0), quantity=int(row.get("Qty", 1)),
                    ))

        # Mission-level LCA parameters
        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            lca_vehicle = st.selectbox("Launch vehicle", list(LAUNCH_VEHICLES_LCA.keys()), key="lca_vehicle")
        with lc2:
            lca_prop_type = st.selectbox("Propellant", list(SATELLITE_MATERIALS.keys()),
                                          index=list(SATELLITE_MATERIALS.keys()).index("Hydrazine (N2H4)"),
                                          key="lca_prop_type")
            lca_prop_mass = st.number_input("Propellant mass (kg)", 0.0, 5000.0, 25.0, key="lca_prop_mass")
        with lc3:
            lca_mfg_energy = st.number_input("Mfg energy (MJ/kg)", 100.0, 2000.0, 500.0, key="lca_mfg_e",
                                              help="Manufacturing energy per kg of satellite dry mass")
            lca_ait_energy = st.number_input("AIT energy (MJ)", 1000.0, 500000.0, 50000.0, key="lca_ait_e",
                                              help="Assembly, Integration & Test total energy")

        _mission_name = st.session_state.get("mission_name", "BEPI Mission")
        lca_model = LCAModel(
            mission_name=_mission_name, items=lca_items, launch_vehicle=lca_vehicle,
            manufacturing_energy_mj_per_kg=lca_mfg_energy, ait_energy_mj=lca_ait_energy,
            propellant_type=lca_prop_type, propellant_mass_kg=lca_prop_mass,
        )

        if lca_items:
            summary = generate_lca_summary(lca_model)

            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Dry mass", f"{summary['total_dry_mass_kg']:.1f} kg")
            m2.metric("Wet mass", f"{summary['total_wet_mass_kg']:.1f} kg")
            m3.metric("Total CO₂", f"{summary['total_co2_kg']:.0f} kg", help="Manufacturing + Launch")
            m4.metric("Launch share", f"{summary['launch_share_pct']:.0f}%", help="Launch CO₂ as % of total")

            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("**Mass by material**")
                mat_df = pd.DataFrame([{"Material": k, "Mass (kg)": round(v, 2)} for k, v in summary["by_material"].items()])
                mat_df = mat_df.sort_values("Mass (kg)", ascending=False)
                st.dataframe(mat_df, hide_index=True, use_container_width=True)

            with mc2:
                st.markdown("**Mass by subsystem**")
                sub_df = pd.DataFrame([{"Subsystem": k, "Mass (kg)": round(v, 2)} for k, v in summary["by_subsystem"].items()])
                sub_df = sub_df.sort_values("Mass (kg)", ascending=False)
                st.dataframe(sub_df, hide_index=True, use_container_width=True)

            # CO2 breakdown
            st.markdown("**CO₂ breakdown**")
            co2_data = pd.DataFrame([
                {"Phase": "Manufacturing", "CO₂ (kg)": round(summary["manufacturing_co2_kg"], 0)},
                {"Phase": f"Launch ({lca_vehicle})", "CO₂ (kg)": round(summary["launch_co2_kg"], 0)},
            ])
            st.bar_chart(co2_data.set_index("Phase"), horizontal=True)

            st.markdown("**Relevant impact categories** (for detailed assessment in OpenLCA)")
            st.dataframe(pd.DataFrame(IMPACT_CATEGORIES), hide_index=True, use_container_width=True)

            # Export buttons
            st.markdown("---")
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                jsonld_zip = export_openlca_jsonld(lca_model)
                st.download_button("📥 OpenLCA JSON-LD (.zip)", jsonld_zip,
                                    f"{_mission_name.replace(' ','_')}_openlca.zip",
                                    "application/zip", key="dl_openlca")
            with ec2:
                csv_data = export_lca_csv(lca_model)
                st.download_button("📥 LCA Inventory CSV", csv_data,
                                    f"{_mission_name.replace(' ','_')}_lca.csv",
                                    "text/csv", key="dl_lca_csv")
            with ec3:
                import json as _json
                summary_json = _json.dumps(summary, indent=2)
                st.download_button("📥 LCA Summary JSON", summary_json,
                                    f"{_mission_name.replace(' ','_')}_lca_summary.json",
                                    "application/json", key="dl_lca_json")

    # ── SPICE Kernels ─────────────────────────────────────────────
    with tab_spice:
        from bepi.integrations.spice_kernels import (
            MissionKernelParams, InstrumentDef, OrbitState, generate_all_kernels,
        )

        st.markdown("Generate NAIF SPICE kernels for your mission. Download individually or as a bundle.")

        sk1, sk2 = st.columns(2)
        with sk1:
            sp_name = st.text_input("Spacecraft name", "BEPISAT", key="spice_name")
            sp_id = st.number_input("NAIF ID", -200000, -100, -999, key="spice_id")
            sp_epoch = st.text_input("Epoch (UTC)", "2027-06-01T12:00:00", key="spice_epoch")
        with sk2:
            sp_sma = st.number_input("SMA (km)", 6500.0, 50000.0, 6921.0, key="spice_sma")
            sp_ecc = st.number_input("Eccentricity", 0.0, 0.99, 0.001, format="%.4f", key="spice_ecc")
            sp_inc = st.number_input("Inclination (°)", 0.0, 180.0, 97.6, key="spice_inc")

        sp_att = st.selectbox("Attitude mode", ["NADIR", "INERTIAL", "SUN_POINTING"], key="spice_att")

        sp_instruments = []
        n_inst = st.number_input("Instruments", 0, 10, 1, key="spice_ninst")
        for i in range(int(n_inst)):
            ic1, ic2, ic3 = st.columns(3)
            with ic1:
                iname = st.text_input(f"Name #{i+1}", f"CAM{i+1}", key=f"spice_iname_{i}")
            with ic2:
                ifov = st.number_input(f"FOV (°) #{i+1}", 0.1, 90.0, 5.0, key=f"spice_ifov_{i}")
            with ic3:
                ishape = st.selectbox(f"Shape #{i+1}", ["CIRCLE", "RECTANGLE"], key=f"spice_ishape_{i}")
            sp_instruments.append(InstrumentDef(name=iname, abbrev=iname, naif_id_offset=100+i, fov_shape=ishape, fov_half_angle_deg=ifov/2))

        if st.button("Generate All Kernels", type="primary", key="spice_gen"):
            import math
            params = MissionKernelParams(
                mission_name=sp_name,
                spacecraft_name=sp_name,
                naif_id=int(sp_id),
                epoch_utc=sp_epoch,
                orbit=OrbitState(sma_km=sp_sma, ecc=sp_ecc, inc_deg=sp_inc, raan_deg=0.0, aop_deg=0.0, ta_deg=0.0),
                attitude_mode=sp_att,
                instruments=sp_instruments,
            )
            kernels = generate_all_kernels(params)

            st.success(f"Generated {len(kernels)} SPICE kernels")
            for kname, kcontent in sorted(kernels.items()):
                with st.expander(f"📄 {kname}"):
                    st.code(kcontent[:2000], language="text")
                    st.download_button(f"📥 {kname}", kcontent, kname, "text/plain", key=f"dl_{kname}")

    # ── External Import ───────────────────────────────────────────
    with tab_import:
        from bepi.integrations.importers import detect_and_import

        st.markdown("Import data from external engineering tools.")

        st.markdown("""
| Source | Format | Import As |
|--------|--------|-----------|
| **IBM DOORS** | CSV export | Requirements |
| **ReqIF** | XML (`.reqif`, `.xml`) | Requirements |
| **MS Project** | XML export (`.xml`) | Schedule / Tasks |
| **Altium Designer** | BOM CSV export | Product Tree (components) |
| **Valispace** | JSON API export | Product Tree |
| **Generic** | CSV / TSV | Auto-detected |
""")

        imp_type = st.radio("Source type", ["Engineering Tools", "Debris Analysis Tools"], horizontal=True, key="imp_type")

        if imp_type == "Engineering Tools":
            uploaded_ext = st.file_uploader("Upload file from external tool",
                                            type=["csv", "tsv", "xml", "json", "reqif"],
                                            key="ext_import")
            if uploaded_ext:
                file_bytes = uploaded_ext.read()
                result = detect_and_import(file_bytes, uploaded_ext.name)

                if result.success and result.record_count > 0:
                    st.success(f"Imported **{result.record_count}** records from **{result.source_format}**")
                    if result.warnings:
                        for w in result.warnings:
                            st.warning(w)
                    st.dataframe(result.records[:30], width="stretch")
                elif result.success and result.record_count == 0:
                    st.warning("File parsed successfully but no records found. Check the file content.")
                else:
                    st.error(f"Import failed: {', '.join(result.warnings)}")

        else:  # Debris Analysis Tools
            from bepi.integrations.das_importers import import_das_xml, import_drama_output, import_master_dat
            from bepi.integrations.validation import compare_internal_vs_imported

            st.markdown("""
| Source | Format | Import As |
|--------|--------|-----------|
| **ESA DAS** | XML compliance report | Debris compliance results |
| **DRAMA** | CSV/TXT reentry output | Reentry analysis data |
| **MASTER** | .dat flux files | Debris flux / impact data |
""")

            das_tool = st.selectbox("Tool", ["DAS (XML)", "DRAMA (CSV/TXT)", "MASTER (.dat)"], key="das_imp_tool")
            uploaded_das = st.file_uploader("Upload output file", type=["xml", "csv", "txt", "dat"], key="das_import")

            if uploaded_das:
                file_bytes = uploaded_das.read()
                if "DAS" in das_tool:
                    result = import_das_xml(file_bytes)
                elif "DRAMA" in das_tool:
                    result = import_drama_output(file_bytes)
                else:
                    result = import_master_dat(file_bytes)

                if result.success and result.record_count > 0:
                    st.success(f"Imported **{result.record_count}** records from **{result.source_format}**")
                    st.dataframe(result.records[:30], width="stretch")

                    with st.expander("Compare with BEPI internal calculation"):
                        st.info("Import your data above, then run the same analysis in BEPI's Space Environment tab to compare results side-by-side.")
                        if result.records:
                            imported_flat = result.records[0] if len(result.records) == 1 else result.records[0]
                            bepi_placeholder = {k: None for k in imported_flat}
                            comp = compare_internal_vs_imported(bepi_placeholder, imported_flat)
                            st.dataframe(comp["comparisons"][:20], width="stretch")
                else:
                    st.error(f"Import failed: {', '.join(result.warnings)}")


# ===========================================================================
# Router
# ===========================================================================
PAGE_MAP = {
    "Overview": page_overview,
    "Product Tree": page_product_tree,
    "Budgets": page_budgets,
    "Requirements": page_requirements,
    "Risks": page_risks,
    "Schedule": page_schedule,
    "ECSS": page_ecss,
    "Reports": page_reports,
    "Integrations": page_integrations,
    "Warehouse": page_warehouse,
    "Team": page_team,
}

PAGE_MAP[page]()
