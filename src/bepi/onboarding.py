import streamlit as st
import hashlib
from postgrest.exceptions import APIError
from bepi.role_permissions import ROLES
from bepi.supabase_client import get_supabase, get_service_client
from bepi.db_loader import load_missions_for_user
from bepi.db_writer import add_mission
from bepi.seed import seed_demo_mission, mock_tasks, mock_requirements, mock_risks, mock_product_tree_flat, mock_fmeca


def _generate_invite_code(length=8):
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


MISSION_PROFILES = {
    "leo_eo": {
        "label": "LEO Earth Observation",
        "desc": "Sun-synchronous smallsat for optical payload operations.",
        "alt": 550,
        "inc": 97,
        "mass": 150,
        "prop": 25,
        "phase": "B2",
        "name": "BEPI-SAT EO",
    },
    "cubesat": {
        "label": "CubeSat Tech Demo",
        "desc": "Compact technology demonstrator with lean subsystem data.",
        "alt": 500,
        "inc": 51,
        "mass": 18,
        "prop": 0,
        "phase": "B1",
        "name": "CubeSat Demo",
    },
    "geo_com": {
        "label": "GEO Communications",
        "desc": "Telecom platform with higher mass and propellant envelope.",
        "alt": 35786,
        "inc": 0,
        "mass": 1800,
        "prop": 650,
        "phase": "A",
        "name": "GEO ComSat",
    },
}

DEMO_SAMPLE_SCOPES = {
    "essential": {
        "label": "Essential",
        "desc": "Smaller dataset for quick walkthroughs.",
        "stats": "17 nodes, 6 requirements, 4 risks",
    },
    "complete": {
        "label": "Complete",
        "desc": "Full BEPI-SAT dataset for dashboard exploration.",
        "stats": "39 nodes, 15 requirements, 8 risks",
    },
}


def _user_has_missions(user_id: str) -> list[dict]:
    """Check if user is member of any mission. Returns list of (mission_id, role) pairs."""
    client = get_service_client() or get_supabase()
    if not client or not user_id:
        return []
    try:
        result = (
            client.table("mission_members")
            .select("mission_id, role")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        return result.data or []
    except APIError as e:
        # Common Supabase misconfiguration: RLS policy calls a helper function
        # without granting EXECUTE to the authenticated role.
        if (e.args and isinstance(e.args[0], dict) and e.args[0].get("code") == "42501"):
            st.error(
                "Supabase policy error: permission denied for function `is_mission_member`.\n\n"
                "Fix in Supabase SQL (example):\n"
                "- `grant execute on function public.is_mission_member(uuid, uuid) to authenticated;`\n"
                "Then re-run the app."
            )
            return []
        raise


def _check_invitation(code: str) -> dict | None:
    client = get_service_client() or get_supabase()
    if not client:
        return None
    result = client.table("invitations").select("*, missions(name)").eq("code", code).execute()
    if not result.data:
        return None
    inv = result.data[0]
    if inv.get("used_at"):
        return None
    return inv


def _redeem_invitation(inv: dict, user_id: str) -> bool:
    client = get_service_client() or get_supabase()
    if not client:
        return False
    client.table("invitations").update({"used_at": "now()", "used_by": user_id}).eq("id", inv["id"]).execute()
    client.table("mission_members").insert({
        "mission_id": inv["mission_id"],
        "user_id": user_id,
        "role": inv["role"],
        "subsystem": inv.get("subsystem"),
    }).execute()
    return True


def _create_invitation(mission_id: str, role: str, subsystem: str | None, email: str | None) -> str:
    code = _generate_invite_code()
    client = get_service_client() or get_supabase()
    if not client:
        return code
    client.table("invitations").insert({
        "mission_id": mission_id,
        "role": role,
        "subsystem": subsystem,
        "code": code,
        "invite_email": email,
    }).execute()
    return code


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_onboarding_needed(user_id: str | None) -> bool:
    if not user_id:
        return False
    memberships = _user_has_missions(user_id)
    return len(memberships) == 0


def render_onboarding():
    """Full-screen onboarding wizard for new users."""
    user = st.session_state.get("user", {})
    user_id = user.get("id")
    
    if user_id and not user.get("role"):
        client = get_service_client() or get_supabase()
        if client:
            try:
                result = client.table("mission_members").select("role").eq("user_id", user_id).execute()
                if result.data and result.data[0].get("role"):
                    st.session_state.user["role"] = result.data[0]["role"]
                else:
                    # No membership yet → least privilege. The user becomes ADMIN
                    # of any mission they create (add_mission grants it), and their
                    # real per-mission role is loaded from mission_members above.
                    st.session_state.user["role"] = "USER"
            except Exception:
                st.session_state.user["role"] = "USER"
        else:
            st.session_state.user["role"] = "USER"
    
    st.markdown("""
    <style>
        .onboard-root {
            min-height: 90vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px 20px;
        }
        .onboard-card {
            background: #111827;
            border: 1px solid #243044;
            border-radius: 8px;
            padding: 40px;
            width: 100%;
            max-width: 780px;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
        }
        .onboard-hero {
            text-align: center;
            margin-bottom: 40px;
        }
        .onboard-hero h2 {
            font-size: 2rem;
            font-weight: 300;
            color: #e0e0e0;
            margin-bottom: 8px;
        }
        .onboard-hero h2 span { font-weight: 700; color: #4da6ff; }
        .onboard-hero p {
            color: #7a8194;
            font-size: 1rem;
            margin: 0;
        }
        .onboard-progress {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 40px;
        }
        .progress-dot {
            width: 10px; height: 10px; border-radius: 50%;
            background: #2a2a4a;
            transition: all 0.3s ease;
        }
        .progress-dot.active { background: #4da6ff; box-shadow: 0 0 8px #4da6ff88; }
        .progress-dot.done { background: #2ecc71; }
        .type-card {
            background: #162033;
            border: 1px solid #2c3a51;
            border-radius: 8px;
            padding: 28px;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: center;
        }
        .type-card:hover { border-color: #60a5fa; background: #1a2638; }
        .type-card.selected { border-color: #60a5fa; background: #1a2638; box-shadow: 0 0 0 1px #60a5fa44; }
        .type-card .icon { font-size: 2.5rem; margin-bottom: 12px; }
        .type-card h3 { color: #e0e0e0; margin: 0 0 8px 0; font-weight: 600; }
        .type-card p { color: #7a8194; margin: 0; font-size: 0.85rem; }
        .field-label {
            color: #7a8194;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
            display: block;
        }
        .field-input input, .field-input select, .field-input textarea {
            background: #0f172a !important;
            border: 1px solid #2a2a4a !important;
            color: #e0e0e0 !important;
            border-radius: 8px !important;
            padding: 10px 14px !important;
            width: 100% !important;
        }
        .field-input input:focus, .field-input select:focus, .field-input textarea:focus {
            border-color: #4da6ff !important;
            outline: none !important;
        }
        .btn-primary {
            background: #4da6ff !important;
            color: #0f172a !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 12px 28px !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            width: 100%;
            cursor: pointer;
        }
        .btn-primary:hover { background: #6bb8ff !important; }
        .btn-ghost {
            background: transparent !important;
            color: #7a8194 !important;
            border: 1px solid #2a2a4a !important;
            border-radius: 8px !important;
            padding: 12px 28px !important;
            font-size: 0.95rem !important;
            cursor: pointer;
        }
        .btn-ghost:hover { border-color: #4da6ff !important; color: #e0e0e0 !important; }
        .btn-skip {
            background: transparent !important;
            color: #4da6ff88 !important;
            border: none !important;
            padding: 8px !important;
            font-size: 0.85rem !important;
            cursor: pointer;
        }
        .btn-skip:hover { color: #4da6ff !important; }
        .invite-box {
            background: #0f172a;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            padding: 24px;
            margin-top: 24px;
        }
        .invite-box h4 { color: #e0e0e0; margin: 0 0 16px 0; font-weight: 600; }
        .invite-success {
            background: #0f2a1a;
            border: 1px solid #2ecc71;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }
        .invite-success p { color: #2ecc71; margin: 0; }
        .team-row {
            background: #0f172a;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 8px;
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .team-row .role-badge {
            background: #4da6ff22;
            color: #4da6ff;
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 0.75rem;
            white-space: nowrap;
        }
        .profile-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 12px 0 18px;
        }
        .profile-card {
            min-height: 116px;
            background: #0f172a;
            border: 1px solid #2c3a51;
            border-radius: 8px;
            padding: 14px;
        }
        .profile-card.selected {
            border-color: #22c55e;
            box-shadow: 0 0 0 1px #22c55e55;
        }
        .profile-card h4 {
            color: #f8fafc;
            font-size: 0.9rem;
            margin: 0 0 6px;
        }
        .profile-card p {
            color: #94a3b8;
            font-size: 0.78rem;
            line-height: 1.35;
            margin: 0;
        }
        .sample-strip {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin: 12px 0 18px;
        }
        .sample-card {
            background: #0f172a;
            border: 1px solid #2c3a51;
            border-radius: 8px;
            padding: 12px 14px;
        }
        .sample-card.selected {
            border-color: #f59e0b;
            box-shadow: 0 0 0 1px #f59e0b55;
        }
        .sample-card b {
            color: #f8fafc;
            display: block;
            font-size: 0.9rem;
            margin-bottom: 4px;
        }
        .sample-card span {
            color: #94a3b8;
            display: block;
            font-size: 0.78rem;
            line-height: 1.3;
        }
        .sample-card small {
            color: #fbbf24;
            display: block;
            font-size: 0.72rem;
            margin-top: 8px;
        }
        .preview-card {
            background: #0f172a;
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
            border: 1px solid #2a2a4a;
        }
        .preview-card .row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #1a2744;
            font-size: 0.85rem;
        }
        .preview-card .row:last-child { border: none; }
        .preview-card .key { color: #7a8194; }
        .preview-card .val { color: #e0e0e0; font-weight: 600; }
        .setup-shell {
            width: min(1120px, calc(100vw - 40px));
            margin: 0 auto;
            display: grid;
            grid-template-columns: 300px minmax(0, 1fr);
            min-height: 640px;
            background: #101826;
            border: 1px solid #263244;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.38);
        }
        .setup-side {
            background: #0b1220;
            color: #e5e7eb;
            padding: 32px 28px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .setup-brand {
            font-size: 0.75rem;
            letter-spacing: 0.12em;
            color: #93c5fd;
            text-transform: uppercase;
            margin-bottom: 22px;
        }
        .setup-side h1 {
            font-size: 2.2rem;
            line-height: 1.05;
            margin: 0 0 14px;
            color: #f8fafc;
            letter-spacing: 0;
        }
        .setup-side p {
            color: #9ca3af;
            line-height: 1.5;
            margin: 0;
        }
        .setup-rail {
            display: grid;
            gap: 12px;
            margin-top: 36px;
        }
        .setup-rail-item {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #94a3b8;
            font-size: 0.9rem;
        }
        .setup-rail-dot {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            border: 1px solid #334155;
            color: #94a3b8;
            font-size: 0.75rem;
        }
        .setup-rail-item.active { color: #f8fafc; }
        .setup-rail-item.active .setup-rail-dot {
            background: #38bdf8;
            border-color: #38bdf8;
            color: #082f49;
            font-weight: 700;
        }
        .setup-note {
            border-top: 1px solid #1f2937;
            padding-top: 18px;
            font-size: 0.82rem;
            color: #94a3b8;
        }
        .setup-main {
            background: #111827;
            padding: 38px 42px;
            color: #e5e7eb;
        }
        .setup-kicker {
            color: #38bdf8;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .setup-title {
            font-size: 1.8rem;
            line-height: 1.15;
            color: #f8fafc;
            margin: 0 0 8px;
            letter-spacing: 0;
        }
        .setup-subtitle {
            color: #94a3b8;
            margin: 0 0 26px;
            line-height: 1.5;
        }
        .setup-main .field-label { color: #94a3b8; letter-spacing: 0.08em; }
        .setup-main .preview-card,
        .setup-main .invite-box {
            background: #0f172a;
            border-color: #263244;
        }
        .setup-main .preview-card .row { border-bottom-color: #1f2a3a; }
        .setup-main .preview-card .key { color: #94a3b8; }
        .setup-main .preview-card .val,
        .setup-main .invite-box h4 { color: #f8fafc; }
        .choice-panel {
            border: 1px solid #263244;
            background: #0f172a;
            border-radius: 8px;
            padding: 18px;
            min-height: 150px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.16);
        }
        .choice-panel.selected {
            border-color: #38bdf8;
            box-shadow: 0 0 0 1px #38bdf855;
        }
        .choice-panel strong {
            display: block;
            color: #f8fafc;
            margin-bottom: 6px;
        }
        .choice-panel span {
            color: #94a3b8;
            display: block;
            font-size: 0.86rem;
            line-height: 1.4;
            min-height: 48px;
        }
        .profile-card,
        .sample-card {
            background: #0f172a;
            border-color: #263244;
        }
        .profile-card.selected { border-color: #2dd4bf; box-shadow: 0 0 0 1px #2dd4bf55; }
        .profile-card h4,
        .sample-card b { color: #f8fafc; }
        .profile-card p,
        .sample-card span { color: #94a3b8; }
        .success-screen {
            text-align: center;
            padding: 60px 40px;
        }
        .success-screen .emoji { font-size: 4rem; margin-bottom: 16px; }
        .success-screen h2 { color: #2ecc71; font-weight: 700; margin-bottom: 8px; }
        .success-screen p { color: #7a8194; }
        @media (max-width: 640px) {
            .onboard-card { padding: 28px 20px; }
            .profile-grid, .sample-strip { grid-template-columns: 1fr; }
            .setup-shell { width: calc(100vw - 24px); grid-template-columns: 1fr; }
            .setup-side { padding: 24px; }
            .setup-main { padding: 26px 22px; }
        }
    </style>
    """, unsafe_allow_html=True)

    if "ob_step" not in st.session_state:
        st.session_state.ob_step = 1
        st.session_state.ob_type = None
        st.session_state.ob_name = ""
        st.session_state.ob_desc = ""
        st.session_state.ob_fw = "ESA"
        st.session_state.ob_phase = "B2"
        st.session_state.ob_alt = 550
        st.session_state.ob_inc = 97
        st.session_state.ob_mass = 150
        st.session_state.ob_prop = 0
        st.session_state.ob_profile = "leo_eo"
        st.session_state.ob_sample_scope = "complete"
        st.session_state.ob_team = []
        st.session_state.ob_invite_code = ""
        st.session_state.ob_invite_result = None

    step = st.session_state.ob_step
    user = st.session_state.get("user", {})

    def progress_dots(current: int, total: int):
        dots = ""
        for i in range(1, total + 1):
            cls = "active" if i == current else ("done" if i < current else "")
            dots += f"<div class='progress-dot {cls}'></div>"
        st.markdown(f"<div class='onboard-progress'>{dots}</div>", unsafe_allow_html=True)

    # ── STEP 1: Mission Type ────────────────────────────────────────────────
    if step == 1:
        st.markdown("""
        <div class="setup-shell">
          <aside class="setup-side">
            <div>
              <div class="setup-brand">BEPI Mission Workspace</div>
              <h1>Start from a clean engineering baseline.</h1>
              <p>{}, choose how this workspace should be initialized.</p>
              <div class="setup-rail">
                <div class="setup-rail-item active"><span class="setup-rail-dot">1</span><span>Workspace type</span></div>
                <div class="setup-rail-item"><span class="setup-rail-dot">2</span><span>Mission definition</span></div>
                <div class="setup-rail-item"><span class="setup-rail-dot">3</span><span>Team access</span></div>
              </div>
            </div>
            <div class="setup-note">A blank mission starts with no team, no product tree payload, no risks, no tasks, and 0 kg propellant.</div>
          </aside>
          <main class="setup-main">
            <div class="setup-kicker">Step 1</div>
            <h2 class="setup-title">Create or join a mission</h2>
            <p class="setup-subtitle">Use a blank workspace for real projects, or load demo data only when you want a guided sandbox.</p>
        """.format(user.get("full_name", "User")), unsafe_allow_html=True)

        cols = st.columns(3)
        selected = st.session_state.get("ob_type")
        for i, (icon, label, desc, key) in enumerate([
            ("🛰️", "New Mission", "Start from scratch with a blank product tree", "new"),
            ("🧪", "Demo Mission", "BEPI-SAT demo data pre-loaded to explore the platform", "demo"),
            ("🔗", "Join Existing", "Enter an invitation code from your team lead", "join"),
        ]):
            with cols[i]:
                cls = "selected" if selected == key else ""
                st.markdown(f"<div class='choice-panel {cls}'><strong>{icon} {label}</strong><span>{desc}</span>", unsafe_allow_html=True)
                if st.button(label, key=f"type_{key}", use_container_width=True):
                    st.session_state.ob_type = key
                    if key == "new":
                        st.session_state.ob_prop = 0
                    elif key == "demo":
                        st.session_state.ob_prop = MISSION_PROFILES["leo_eo"]["prop"]
                    if key == "join":
                        st.session_state.ob_step = 1.5
                    else:
                        st.session_state.ob_step = 2
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # Show invitation code section ONLY when Join Existing is selected
        if selected == "join":
            st.markdown("### 🔑 Enter Invitation Code")
            code_val = st.text_input("Invitation Code", placeholder="e.g. A7X9K2MZ", max_chars=10, key="invite_code_input")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Join Mission →", type="primary", use_container_width=True):
                    if code_val:
                        inv = _check_invitation(code_val.strip().upper())
                        if inv:
                            st.session_state.ob_invite_result = inv
                            st.session_state.ob_step = 1.5
                            st.rerun()
                        else:
                            st.error("Invalid or expired code. Ask your team lead for a new one.")
            with c2:
                st.button("Skip →", key="skip_to_missions", use_container_width=True, on_click=lambda: _skip_onboarding())
        else:
            st.button("Skip →", key="skip_to_missions", use_container_width=True, on_click=lambda: _skip_onboarding())

        st.markdown("</main></div>", unsafe_allow_html=True)

    # ── STEP 1.5: Confirm Join ─────────────────────────────────────────────
    elif step == 1.5:
        progress_dots(1, 3)
        inv = st.session_state.get("ob_invite_result")
        if inv:
            mission_name = inv.get("missions", {}).get("name", "their mission") if isinstance(inv.get("missions"), dict) else "the mission"
            st.markdown(f"""
            <div class="onboard-card">
              <div class="onboard-hero">
                <h2>🔗 Join Mission</h2>
                <p>You're about to join <strong style="color:#4da6ff">{mission_name}</strong> as <span class='team-badge'>{inv.get('role', '')}</span></p>
              </div>
              <div class='invite-success'>
                <p>✓ Invitation verified — you can access this mission after joining</p>
              </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⬅️ Go Back", use_container_width=True):
                    st.session_state.ob_step = 1
                    st.session_state.ob_invite_result = None
                    st.rerun()
            with c2:
                if st.button("Join Mission ✅", type="primary", use_container_width=True):
                    user_id = user.get("id")
                    if user_id and _redeem_invitation(inv, user_id):
                        _load_user_missions(user_id)
                        _finalize_onboarding(skipped=True)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.session_state.ob_step = 1
            st.rerun()

    # ── STEP 2: Mission Details ─────────────────────────────────────────────
    elif step == 2:
        is_demo = st.session_state.get("ob_type") == "demo"
        selected_profile = st.session_state.get("ob_profile", "leo_eo")
        sample_scope = st.session_state.get("ob_sample_scope", "complete")

        st.markdown("""
        <div class="setup-shell">
          <aside class="setup-side">
            <div>
              <div class="setup-brand">Mission Definition</div>
              <h1>{}</h1>
              <p>{}</p>
              <div class="setup-rail">
                <div class="setup-rail-item"><span class="setup-rail-dot">1</span><span>Workspace type</span></div>
                <div class="setup-rail-item active"><span class="setup-rail-dot">2</span><span>Mission definition</span></div>
                <div class="setup-rail-item"><span class="setup-rail-dot">3</span><span>Team access</span></div>
              </div>
            </div>
            <div class="setup-note">Mission parameters are editable later from settings and analysis tools.</div>
          </aside>
          <main class="setup-main">
            <div class="setup-kicker">Step 2</div>
            <h2 class="setup-title">{}</h2>
            <p class="setup-subtitle">{}</p>
        """.format(
            "Demo workspace" if is_demo else "Blank mission",
            "Preloaded data for exploration." if is_demo else "No demo data will be added.",
            "Configure demo data" if is_demo else "Define the mission shell",
            "Select a mission profile and adjust only the initial parameters you need."
        ), unsafe_allow_html=True)

        st.markdown("<label class='field-label'>Mission Profile</label>", unsafe_allow_html=True)
        profile_cols = st.columns(3)
        for idx, (profile_key, profile) in enumerate(MISSION_PROFILES.items()):
            with profile_cols[idx]:
                cls = "selected" if selected_profile == profile_key else ""
                st.markdown(
                    f"""
                    <div class="profile-card {cls}">
                      <h4>{profile["label"]}</h4>
                      <p>{profile["desc"]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Use profile", key=f"ob_profile_{profile_key}", use_container_width=True):
                    st.session_state.ob_profile = profile_key
                    st.session_state.ob_alt = profile["alt"]
                    st.session_state.ob_inc = profile["inc"]
                    st.session_state.ob_mass = profile["mass"]
                    st.session_state.ob_prop = profile["prop"] if is_demo else 0
                    st.session_state.ob_phase = profile["phase"]
                    if not st.session_state.get("ob_name_in"):
                        st.session_state.ob_name_in = profile["name"]
                    st.rerun()

        selected_profile_data = MISSION_PROFILES.get(selected_profile, MISSION_PROFILES["leo_eo"])
        if "ob_name_in" not in st.session_state and is_demo:
            st.session_state.ob_name_in = selected_profile_data["name"]

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("<label class='field-label'>Mission Name</label>", unsafe_allow_html=True)
            name = st.text_input("Mission Name", placeholder="My Satellite Mission", key="ob_name_in", label_visibility="collapsed")
        with c2:
            st.markdown("<label class='field-label'>Framework</label>", unsafe_allow_html=True)
            fw = st.selectbox("Framework", ["ESA", "NASA"], key="ob_fw_sel", label_visibility="collapsed")

        st.markdown("<label class='field-label' style='margin-top:16px'>Description</label>", unsafe_allow_html=True)
        desc = st.text_area("Description", placeholder=selected_profile_data["desc"], key="ob_desc_in", label_visibility="collapsed")

        if is_demo:
            st.markdown("<label class='field-label' style='margin-top:16px'>Starting Phase</label>", unsafe_allow_html=True)
            phase_values = ["A", "B1", "B2", "C", "D"]
            phase_default = st.session_state.get("ob_phase", selected_profile_data["phase"])
            phase_index = phase_values.index(phase_default) if phase_default in phase_values else 2
            phase = st.selectbox("Phase", phase_values, index=phase_index, key="ob_phase_sel", label_visibility="collapsed")

            st.markdown("<label class='field-label' style='margin-top:16px'>Demo Data Sampling</label>", unsafe_allow_html=True)
            sample_cols = st.columns(2)
            for idx, (scope_key, scope) in enumerate(DEMO_SAMPLE_SCOPES.items()):
                with sample_cols[idx]:
                    cls = "selected" if sample_scope == scope_key else ""
                    st.markdown(
                        f"""
                        <div class="sample-card {cls}">
                          <b>{scope["label"]}</b>
                          <span>{scope["desc"]}</span>
                          <small>{scope["stats"]}</small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("Select", key=f"ob_sample_{scope_key}", use_container_width=True):
                        st.session_state.ob_sample_scope = scope_key
                        st.rerun()
        else:
            phase = st.session_state.get("ob_phase", selected_profile_data["phase"])

        st.markdown("<label class='field-label' style='margin-top:16px'>Orbital Parameters</label>", unsafe_allow_html=True)
        c3, c4, c5, c6 = st.columns([1, 1, 1, 1])
        with c3:
            alt = st.number_input("Altitude (km)", 400, 36000, int(st.session_state.get("ob_alt", 550)), 50, key="ob_alt_in")
        with c4:
            inc = st.number_input("Inclination (°)", 0, 180, int(st.session_state.get("ob_inc", 97)), 1, key="ob_inc_in")
        with c5:
            mass = st.number_input("Dry Mass (kg)", 10, 5000, int(st.session_state.get("ob_mass", 150)), 10, key="ob_mass_in")
        with c6:
            prop = st.number_input("Propellant (kg)", 0, 1000, int(st.session_state.get("ob_prop", 0)), 5, key="ob_prop_in")

        # Preview card
        st.markdown("""
        <div class="preview-card">
            <div class="row"><span class="key">Mission</span><span class="val">{}</span></div>
            <div class="row"><span class="key">Profile</span><span class="val">{}</span></div>
            <div class="row"><span class="key">Framework</span><span class="val">{}</span></div>
            <div class="row"><span class="key">Phase</span><span class="val">{}</span></div>
            {}
            <div class="row"><span class="key">Altitude</span><span class="val">{} km</span></div>
            <div class="row"><span class="key">Inclination</span><span class="val">{}°</span></div>
            <div class="row"><span class="key">Dry Mass</span><span class="val">{} kg</span></div>
            <div class="row"><span class="key">Propellant</span><span class="val">{} kg</span></div>
        </div>
        """.format(
            name or "—",
            selected_profile_data["label"],
            fw or "ESA",
            phase,
            f"""<div class="row"><span class="key">Demo data</span><span class="val">{DEMO_SAMPLE_SCOPES[sample_scope]["label"]}</span></div>""" if is_demo else "",
            alt,
            inc,
            mass,
            prop,
        ), unsafe_allow_html=True)

        cbtn1, cbtn2 = st.columns([1, 2])
        with cbtn1:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.ob_step = 1
                st.rerun()
        with cbtn2:
            if st.button("Continue ➡️", type="primary", use_container_width=True):
                if not name:
                    st.error("Mission name is required")
                else:
                    st.session_state.ob_name = name
                    st.session_state.ob_desc = desc
                    st.session_state.ob_fw = fw
                    if is_demo:
                        st.session_state.ob_phase = phase
                        st.session_state.ob_sample_scope = sample_scope
                    else:
                        st.session_state.ob_phase = phase
                    st.session_state.ob_profile = selected_profile
                    st.session_state.ob_alt = alt
                    st.session_state.ob_inc = inc
                    st.session_state.ob_mass = mass
                    st.session_state.ob_prop = prop
                    st.session_state.ob_step = 3
                    st.rerun()

        st.markdown("</main></div>", unsafe_allow_html=True)

    # ── STEP 3: Team ────────────────────────────────────────────────────────
    elif step == 3:
        st.markdown("""
        <div class="setup-shell">
          <aside class="setup-side">
            <div>
              <div class="setup-brand">Team Access</div>
              <h1>Keep ownership explicit.</h1>
              <p>Add colleagues now, or start alone and invite the team later.</p>
              <div class="setup-rail">
                <div class="setup-rail-item"><span class="setup-rail-dot">1</span><span>Workspace type</span></div>
                <div class="setup-rail-item"><span class="setup-rail-dot">2</span><span>Mission definition</span></div>
                <div class="setup-rail-item active"><span class="setup-rail-dot">3</span><span>Team access</span></div>
              </div>
            </div>
            <div class="setup-note">Team setup is optional. A blank mission can launch with no extra team rows.</div>
          </aside>
          <main class="setup-main">
            <div class="setup-kicker">Step 3</div>
            <h2 class="setup-title">Team members</h2>
            <p class="setup-subtitle">Create the mission now, or add initial collaborators before entering the dashboard.</p>
        """, unsafe_allow_html=True)

        team = st.session_state.get("ob_team", [])

        for i, member in enumerate(team):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 0.5])
            with c1:
                st.text_input("Name", value=member.get("name", ""), key=f"ob_tname_{i}", label_visibility="collapsed")
            with c2:
                st.selectbox("Role", list(ROLES.keys()), index=list(ROLES.keys()).index(member.get("role", "SE")) if member.get("role", "SE") in ROLES else 0, key=f"ob_trole_{i}", format_func=lambda r: ROLES[r]["name"], label_visibility="collapsed")
            with c3:
                st.text_input("Email", value=member.get("email", ""), key=f"ob_temail_{i}", label_visibility="collapsed")
            with c4:
                if st.button("✕", key=f"ob_tdel_{i}"):
                    team.pop(i)
                    st.session_state.ob_team = team
                    st.rerun()

        if st.button("+ Add Team Member", use_container_width=True):
            team.append({"name": "", "role": "SE", "email": ""})
            st.session_state.ob_team = team
            st.rerun()

        cbtn1, cbtn2, cbtn3 = st.columns([1, 1, 2])
        with cbtn1:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.ob_step = 2
                st.rerun()
        with cbtn2:
            if st.button("Skip for now", use_container_width=True):
                _finalize_onboarding()
                st.rerun()
        with cbtn3:
            if st.button("Create Mission ✅", type="primary", use_container_width=True):
                _finalize_onboarding()
                st.rerun()

        st.markdown("</main></div>", unsafe_allow_html=True)


def _skip_onboarding():
    """Skip onboarding — load user's existing missions or create minimal mission."""
    user = st.session_state.get("user", {})
    user_id = user.get("id")
    if user_id:
        _load_user_missions(user_id)
    _finalize_onboarding(skipped=True)


def _load_user_missions(user_id: str):
    """Load all missions user is a member of."""
    missions = load_missions_for_user(user_id)
    all_missions = {m["id"]: m for m in missions if m.get("id")}
    st.session_state.missions = all_missions
    st.session_state.active_mission_id = next(iter(all_missions), None)

    client = get_service_client() or get_supabase()
    if client:
        _sync_team_members_from_db(client, user_id)


def _sync_team_members_from_db(client, user_id: str):
    """Sync team members from mission_members table to session state."""
    if not st.session_state.get("active_mission_id"):
        return
    
    mission_id = st.session_state.active_mission_id
    
    try:
        result = client.table("mission_members").select("*").eq("mission_id", mission_id).execute()
        members = result.data or []
        
        if members:
            profile_ids = [m.get("user_id") for m in members if m.get("user_id")]
            profile_map = {}
            if profile_ids:
                try:
                    prof_result = client.table("profiles").select("id, full_name").in_("id", profile_ids).execute()
                    profile_map = {p.get("id"): p.get("full_name") for p in (prof_result.data or [])}
                except Exception:
                    pass
            
            user_role_in_mission = None
            team_list = []
            for m in members:
                member_id = m.get("user_id", "")
                name = member_id
                
                if member_id == user_id:
                    name = st.session_state.get("user", {}).get("full_name", name)
                    user_role_in_mission = m.get("role", "SE")
                elif member_id in profile_map:
                    name = profile_map[member_id]
                
                team_list.append({
                    "id": member_id,
                    "role": m.get("role", "SE"),
                    "subsystem": m.get("subsystem"),
                    "name": name,
                })
            
            if user_role_in_mission:
                st.session_state.user["role"] = user_role_in_mission
            elif user_id and not st.session_state.user.get("role"):
                st.session_state.user["role"] = "ADMIN"
            
            st.session_state.team_members = team_list
            return
    except Exception:
        pass
    
    try:
        result = client.table("invitations").select("*").eq("mission_id", mission_id).execute()
        invites = result.data or []
        
        if invites:
            team_list = []
            for inv in invites:
                if inv.get("status") == "used" or inv.get("used_by"):
                    name = inv.get("invite_name", "")
                    if inv.get("used_by") == user_id:
                        name = st.session_state.get("user", {}).get("full_name", name)
                    team_list.append({
                        "id": inv.get("used_by", ""),
                        "role": inv.get("role", "SE"),
                        "subsystem": inv.get("subsystem"),
                        "name": name,
                        "email": inv.get("invite_email", ""),
                    })
            
            current_user = st.session_state.get("user", {})
            if current_user.get("id") and current_user.get("id") not in [t.get("id") for t in team_list]:
                team_list.insert(0, {
                    "id": current_user.get("id", ""),
                    "role": current_user.get("role", "USER"),
                    "name": current_user.get("full_name", "Me"),
                    "email": current_user.get("email", ""),
                })
            
            if not st.session_state.get("team_members"):
                st.session_state.team_members = team_list
    except Exception:
        pass


def _finalize_onboarding(skipped: bool = False):
    """Create mission and finalize onboarding."""
    user = st.session_state.get("user", {})
    user_id = user.get("id")
    ob = st.session_state
    client = get_supabase()

    if not skipped and ob.get("ob_type") in ("new", "demo"):
        m_name = ob.get("ob_name", "My Mission")
        m_desc = ob.get("ob_desc", "")
        m_fw = ob.get("ob_fw", "ESA")
        m_phase = ob.get("ob_phase", "0")
        m_alt = ob.get("ob_alt", 550)
        m_inc = ob.get("ob_inc", 97)
        m_mass = ob.get("ob_mass", 150)
        m_prop = ob.get("ob_prop", 0)
        m_profile = ob.get("ob_profile", "leo_eo")
        m_sample_scope = ob.get("ob_sample_scope", "complete")

        if client:
            db_mission = add_mission(
                m_name,
                m_desc,
                m_phase,
                m_fw,
                owner_user_id=user_id,
                orbit_altitude_km=m_alt,
                inclination_deg=m_inc,
                dry_mass_kg=m_mass,
                propellant_kg=m_prop,
                sample_scope=m_sample_scope if ob.get("ob_type") == "demo" else None,
                profile_key=m_profile,
            )
            if db_mission:
                mid = db_mission["id"]
                
                # For demo mission: use FULL mock data (exactly like Fast Mission)
                if ob.get("ob_type") == "demo":
                    db_mission.update({
                        "name": m_name,
                        "description": "LEO Earth Observation SmallSat",
                        "mission_phase": "B2",
                        "mission_framework": "ESA",
                        "propellant_kg": 25.0,
                        "tasks": mock_tasks(),
                        "requirements": mock_requirements(),
                        "risks": mock_risks(),
                        "product_tree": mock_product_tree_flat(),
                        "fmeca_entries": mock_fmeca(),
                        "team_members": [{
                            "id": user_id,
                            "name": user.get("full_name") or user.get("email") or "You",
                            "email": user.get("email", ""),
                            "role": "ADMIN",
                            "org": user.get("org", ""),
                        }],
                        "approval_log": [],
                        "req_ownership": {},
                        "task_assignments": {},
                        "risk_overrides": {},
                        "equip_budgets": {},
                        "warehouse_items": None,
                        "procurement_orders": None,
                    })
                else:
                    db_mission.update({
                        "name": m_name,
                        "description": "",
                        "mission_phase": m_phase,
                        "mission_framework": m_fw,
                        "orb_alt": m_alt,
                        "orb_inc": m_inc,
                        "orb_mass": m_mass,
                        "propellant_kg": m_prop,
                        "team_members": [{
                            "id": user_id,
                            "name": user.get("full_name") or user.get("email") or "You",
                            "email": user.get("email", ""),
                            "role": "ADMIN",
                            "org": user.get("org", ""),
                        }],
                        "tasks": [],
                        "requirements": [],
                        "risks": [],
                        "product_tree": [],
                        "equip_budgets": {},
                        "fmeca_entries": [],
                        "approval_log": [],
                        "req_ownership": {},
                        "task_assignments": {},
                        "risk_overrides": {},
                    })
                st.session_state.active_mission_id = mid
                st.session_state.missions = {mid: db_mission}
                for key in (
                    "mission_phase", "mission_framework", "orb_alt", "orb_inc",
                    "orb_mass", "propellant_kg", "team_members", "tasks",
                    "requirements", "risks", "product_tree", "equip_budgets",
                    "fmeca_entries", "approval_log", "req_ownership",
                    "task_assignments", "risk_overrides",
                ):
                    st.session_state[key] = db_mission[key]
                st.session_state._onboarding_completed = True
                st.session_state["_missions_loaded"] = True
                st.session_state["_current_user_id"] = user_id
                st.session_state["user"] = {
                    "id": user_id,
                    "email": user.get("email", ""),
                    "full_name": user.get("full_name") or user.get("email") or "You",
                    "role": "ADMIN",
                    "org": user.get("org", ""),
                }
            else:
                st.error("Failed to create mission. Running in offline mode.")
        else:
            mid = m_name.lower().replace(" ", "-")
            if ob.get("ob_type") == "demo":
                new_mission = {
                    "name": m_name,
                    "description": "LEO Earth Observation SmallSat",
                    "mission_phase": "B2",
                    "mission_framework": "ESA",
                    "propellant_kg": 25.0,
                    "tasks": mock_tasks(),
                    "requirements": mock_requirements(),
                    "risks": mock_risks(),
                    "product_tree": mock_product_tree_flat(),
                    "fmeca_entries": mock_fmeca(),
                    "team_members": [{
                        "id": user_id,
                        "name": user.get("full_name") or user.get("email") or "You",
                        "email": user.get("email", ""),
                        "role": "PM",
                        "org": user.get("org", ""),
                    }],
                    "approval_log": [],
                    "req_ownership": {},
                    "task_assignments": {},
                    "risk_overrides": {},
                    "equip_budgets": {},
                    "warehouse_items": None,
                    "procurement_orders": None,
                }
            else:
                new_mission = {
                    "name": m_name,
                    "description": "",
                    "mission_phase": m_phase,
                    "mission_framework": m_fw,
                    "orb_alt": m_alt,
                    "orb_inc": m_inc,
                    "orb_mass": m_mass,
                    "propellant_kg": m_prop,
                    "tasks": [],
                    "requirements": [],
                    "risks": [],
                    "product_tree": [],
                    "equip_budgets": {},
                    "fmeca_entries": [],
                    "approval_log": [],
                    "req_ownership": {},
                    "task_assignments": {},
                    "risk_overrides": {},
                    "team_members": [],
                    "warehouse_items": None,
                    "procurement_orders": None,
                }
            st.session_state.missions = {mid: new_mission}
            st.session_state.active_mission_id = mid
            st.session_state._onboarding_completed = True
            st.session_state["user"] = {
                "id": user_id,
                "email": user.get("email", ""),
                "full_name": user.get("full_name") or user.get("email") or "You",
                "role": "ADMIN" if ob.get("ob_type") in ("new", "demo") else "PM",
                "org": user.get("org", ""),
            }

    elif skipped:
        if client:
            _load_user_missions(user_id)
        else:
            mid = "my-mission"
            st.session_state.missions = {mid: {
                "name": "My Mission",
                "description": "LEO Earth Observation SmallSat",
                "mission_phase": "B2",
                "mission_framework": "ESA",
                "propellant_kg": 25.0,
                "tasks": mock_tasks(),
                "requirements": mock_requirements(),
                "risks": mock_risks(),
                "product_tree": mock_product_tree_flat(),
                "fmeca_entries": mock_fmeca(),
                "team_members": [{
                    "id": user_id,
                    "name": user.get("full_name") or user.get("email") or "You",
                    "email": user.get("email", ""),
                    "role": "ADMIN",
                    "org": user.get("org", ""),
                }],
                "approval_log": [],
                "req_ownership": {},
                "task_assignments": {},
                "risk_overrides": {},
                "equip_budgets": {},
                "warehouse_items": None,
                "procurement_orders": None,
            }}
            st.session_state.active_mission_id = mid
            st.session_state._onboarding_completed = True
            st.session_state["user"] = {
                "id": user_id,
                "email": user.get("email", ""),
                "full_name": user.get("full_name") or user.get("email") or "You",
                "role": "PM",
                "org": user.get("org", ""),
            }

    # Cleanup onboarding state
    for k in list(st.session_state.keys()):
        if k.startswith("ob_"):
            del st.session_state[k]
    st.session_state.pop("_onboarding_shown", None)

    # Update user role to ADMIN in Supabase Auth metadata
    try:
        client = get_supabase()
        if client and hasattr(client, 'auth') and client.auth.get_user():
            client.auth.update_user({
                "data": {
                    "role": "ADMIN"
                }
            })
    except Exception as e:
        st.warning(f"Could not update user role: {e}")

    st.balloons()
    st.rerun()


# Import needed for session-only mode
def _default_mission_data(name="My Mission", with_demo=True):
    from streamlit_app import _default_mission_data as _default
    return _default(name, with_demo)
