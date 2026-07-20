import streamlit as st
from bepi.supabase_client import get_supabase

_COOKIE_TOKEN = "bepi_token"
_COOKIE_REFRESH = "bepi_refresh"
_COOKIE_MAX_AGE = 86400 * 7  # 7 days


def _cookie_ctrl():
    try:
        from streamlit_cookies_controller import CookieController
        return CookieController(key="bepi_auth")
    except Exception:
        return None


def _user_dict(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.user_metadata.get("full_name", "") if user.user_metadata else "",
        # Authorization role is per-mission and lives in `mission_members` (RLS-
        # protected); it is resolved at mission load (_sync_team_members_from_db).
        # NEVER seed it from user_metadata: that field is user-writable via the
        # GoTrue update_user API, so trusting it here let any account self-promote
        # to ADMIN. Start least-privilege; the real role is filled in from the DB.
        "role": "USER",
    }


def _sync_cookie_from_state(cc) -> None:
    """Persist the freshest session tokens to cookies. Supabase rotates refresh
    tokens on every refresh, so the cookie must follow the rotation — otherwise
    the next hard refresh reads a stale/consumed token and logs the user out."""
    tok = st.session_state.get("supabase_token")
    ref = st.session_state.get("supabase_refresh_token")
    if not tok or not ref:
        return
    try:
        if cc.get(_COOKIE_TOKEN) != tok or cc.get(_COOKIE_REFRESH) != ref:
            cc.set(_COOKIE_TOKEN, tok, max_age=_COOKIE_MAX_AGE)
            cc.set(_COOKIE_REFRESH, ref, max_age=_COOKIE_MAX_AGE)
    except Exception:
        pass


def _restore_from_cookie(cc) -> bool:
    """Try to restore session from browser cookies. Returns True if restored."""
    if "user" in st.session_state:
        # Already authenticated this session — keep the cookie in sync with any
        # token rotation that happened during the previous run (get_supabase).
        _sync_cookie_from_state(cc)
        return True
    token = cc.get(_COOKIE_TOKEN)
    refresh = cc.get(_COOKIE_REFRESH)
    if not token or not refresh:
        return False
    client = get_supabase()
    if not client:
        return False
    try:
        result = client.auth.set_session(token, refresh)
        if result and result.user:
            st.session_state["user"] = _user_dict(result.user)
            st.session_state["supabase_token"] = result.session.access_token
            st.session_state["supabase_refresh_token"] = result.session.refresh_token
            # set_session may have refreshed/rotated the tokens — persist the new
            # ones back to the cookie so the session stays durable across refreshes.
            _sync_cookie_from_state(cc)
            return True
    except Exception:
        # Token expired or invalid — clear cookies and force login
        try:
            cc.remove(_COOKIE_TOKEN)
            cc.remove(_COOKIE_REFRESH)
        except Exception:
            pass
    return False


def _handle_sso_callback(cc) -> bool:
    """Consume the SSO callback redirected back from the sso-unipd Edge
    Function. The IdP-issued SAMLResponse was already verified server-side;
    here we just exchange the magic-link `token_hash` for a Supabase
    session and persist it the same way the password sign-in path does.

    Returns True if a session was established (caller should rerun).
    """
    qp = st.query_params
    token_hash = qp.get("sso_token_hash")
    email = qp.get("sso_email")
    if not token_hash or not email:
        return False
    client = get_supabase()
    if not client:
        st.error("❌ SSO callback received but Supabase is not configured.")
        st.query_params.clear()
        return False
    try:
        result = client.auth.verify_otp({
            "token_hash": str(token_hash),
            "type": "magiclink",
            "email": str(email),
        })
        if not result or not result.user or not result.session:
            st.error("❌ SSO callback: could not establish a session.")
            st.query_params.clear()
            return False
        st.session_state["user"] = _user_dict(result.user)
        st.session_state["supabase_token"] = result.session.access_token
        st.session_state["supabase_refresh_token"] = result.session.refresh_token
        if cc:
            cc.set(_COOKIE_TOKEN, result.session.access_token, max_age=_COOKIE_MAX_AGE)
            cc.set(_COOKIE_REFRESH, result.session.refresh_token, max_age=_COOKIE_MAX_AGE)
        st.query_params.clear()
        return True
    except Exception as e:
        st.error(f"❌ SSO callback failed: {e}")
        st.query_params.clear()
        return False


def _sso_button_url() -> str | None:
    """Build the Edge Function login URL from the Supabase project URL.
    Returns None if Supabase isn't configured (button is hidden)."""
    try:
        url = st.secrets.get("supabase", {}).get("url", "")
    except Exception:
        url = ""
    if not url:
        return None
    return f"{url.rstrip('/')}/functions/v1/sso-unipd?action=login"


def render_auth_ui():
    cc = _cookie_ctrl()

    # Try cookie-based session restore (survives F5 / hard refresh)
    if cc and _restore_from_cookie(cc):
        return st.session_state.get("user")

    if "user" in st.session_state:
        return st.session_state.get("user")

    # SSO callback from the sso-unipd Edge Function (?sso_token_hash=…&sso_email=…).
    # If present, exchange the magic-link token for a session, then rerun.
    if _handle_sso_callback(cc):
        st.rerun()

    st.markdown("""
    <style>
    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 40px 30px;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px;
        border: 1px solid #334155;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    .auth-header {
        text-align: center;
        margin-bottom: 30px;
    }
    .auth-header h1 {
        font-size: 2rem;
        font-weight: 300;
        color: #e0e0e0;
        margin: 0;
    }
    .auth-header h1 span {
        font-weight: 600;
        color: #4da6ff;
    }
    .auth-header p {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 8px;
    }
    .auth-footer {
        text-align: center;
        margin-top: 20px;
        color: #64748b;
        font-size: 0.85rem;
    }
    /* Hide Streamlit header anchor links */
    .stHeaderActionElements, [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    /* UniPD SSO button: rounded, full-width, brand icon left of the label.
       Anchor must be a direct child of a <p> or <div>; we render it inside
       a dedicated wrapper so the layout is consistent across Streamlit
       re-renders. */
    a.sso-unipd-btn {
        display: flex; align-items: center; justify-content: center;
        gap: 10px; width: 100%;
        padding: 10px 18px; margin: 0;
        background: linear-gradient(135deg, #a32638 0%, #7a1c2a 100%);
        color: #ffffff !important; text-decoration: none !important;
        font-size: 14px; font-weight: 700; letter-spacing: 0.02em;
        border: 1px solid #7a1c2a; border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25);
        transition: transform 0.12s ease, box-shadow 0.12s ease, filter 0.12s ease;
    }
    a.sso-unipd-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.35);
        filter: brightness(1.08);
    }
    a.sso-unipd-btn:active { transform: translateY(0); filter: brightness(0.95); }
    a.sso-unipd-btn img {
        height: 22px; width: auto; display: block;
        background: #ffffff; border-radius: 4px; padding: 2px 4px;
    }
    a.sso-unipd-btn .sso-unipd-label { line-height: 1; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; padding: 10px 0px 5px;">
        <svg width="90" height="90" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color: rgb(77, 166, 255); stop-opacity: 0.9;"></stop>
                    <stop offset="100%" style="stop-color: rgb(46, 204, 113); stop-opacity: 0.9;"></stop>
                </linearGradient>
            </defs>
            <ellipse cx="60" cy="60" rx="52" ry="20" fill="none" stroke="url(#g1)" stroke-width="1.5" opacity="0.4" transform="rotate(-25 60 60)"></ellipse>
            <ellipse cx="60" cy="60" rx="52" ry="20" fill="none" stroke="url(#g1)" stroke-width="1.5" opacity="0.3" transform="rotate(25 60 60)"></ellipse>
            <ellipse cx="60" cy="60" rx="48" ry="16" fill="none" stroke="url(#g1)" stroke-width="1" opacity="0.2" transform="rotate(65 60 60)"></ellipse>
            <circle cx="60" cy="60" r="8" fill="url(#g1)" opacity="0.6"></circle>
            <circle cx="60" cy="60" r="4" fill="white" opacity="0.8"></circle>
            <circle cx="98" cy="48" r="3" fill="#4da6ff" opacity="0.9"></circle>
            <circle cx="98" cy="48" r="1.5" fill="white" opacity="0.7"></circle>
        </svg>
        <h1 style="font-size: 2.2rem; margin: 2px 0px 0px; letter-spacing: 5px; font-weight: 300; color: rgb(224, 224, 224);">
            <span style="font-weight: 600; color: rgb(77, 166, 255);">B</span>.
            <span style="font-weight: 600; color: rgb(69, 183, 209);">E</span>.
            <span style="font-weight: 600; color: rgb(59, 196, 159);">P</span>.
            <span style="font-weight: 600; color: rgb(46, 204, 113);">I</span>.
        </h1>
        <p style="font-size: 0.55rem; opacity: 0.45; margin-top: 6px; letter-spacing: 2px; line-height: 1.6;">BUDGET · ENGINEERING<br>PROJECT · INTEGRATION</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔐 Sign In", "✨ Sign Up"])

    sso_url = _sso_button_url()

    with tab_login:
        st.markdown("---")
        email_input = st.text_input("Email Address", placeholder="name@example.com", key="_auth_email")
        password_input = st.text_input("Password", type="password", placeholder="Enter your password", key="_auth_pass")
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        if st.button("Sign In", use_container_width=True, type="primary"):
            email_str = str(email_input).strip() if email_input else ""
            password_str = str(password_input) if password_input else ""
            if email_str and password_str:
                client = get_supabase()
                try:
                    result = client.auth.sign_in_with_password({"email": email_str, "password": password_str})
                    if result.user:
                        st.session_state["user"] = _user_dict(result.user)
                        st.session_state["supabase_token"] = result.session.access_token
                        st.session_state["supabase_refresh_token"] = result.session.refresh_token
                        if cc:
                            cc.set(_COOKIE_TOKEN, result.session.access_token, max_age=_COOKIE_MAX_AGE)
                            cc.set(_COOKIE_REFRESH, result.session.refresh_token, max_age=_COOKIE_MAX_AGE)
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                except Exception as e:
                    st.error(f"❌ Login failed: {str(e)}")
            else:
                st.warning("⚠️ Please enter both email and password")

        # UniPD SSO — link button (renders as a styled <a> that does a
        # top-level navigation to the Edge Function, which then redirects
        # to the IdP). Hidden when Supabase isn't configured.
        if sso_url:
            st.markdown(
                "<div style='text-align:center;margin:18px 0 6px;"
                "font-size:11px;color:#64748b;letter-spacing:0.08em;"
                "text-transform:uppercase;'>— or —</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<a class="sso-unipd-btn" href="{sso_url}" target="_self" '
                f'rel="noopener">'
                f'<img src="https://stem.elearning.unipd.it/pluginfile.php/'
                f'1/auth_shibboleth/logo/SSO_unipd.png" alt="UniPD SSO"/>'
                f'<span class="sso-unipd-label">Login with UniPD SSO</span>'
                f'</a>',
                unsafe_allow_html=True,
            )

    with tab_signup:
        st.markdown("---")
        full_name = st.text_input("Full Name", placeholder="Your full name", key="_auth_name")
        email_input = st.text_input("Email Address", placeholder="name@example.com", key="_auth_signup_email")
        password_input = st.text_input("Password", type="password", placeholder="Create a password", key="_auth_signup_pass")
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        if st.button("Create Account", use_container_width=True, type="primary"):
            email_str = str(email_input).strip() if email_input else ""
            password_str = str(password_input) if password_input else ""
            if email_str and password_str:
                client = get_supabase()
                result = client.auth.sign_up({
                    "email": email_str,
                    "password": password_str,
                    "options": {"data": {"full_name": full_name}},
                })
                if result.user:
                    st.success("✅ Account created! Check your email to confirm, then sign in.")
                else:
                    st.error("❌ Sign-up failed. Email may already be registered.")
            else:
                st.warning("⚠️ Please enter both email and password")

        if sso_url:
            st.markdown(
                "<div style='text-align:center;margin:18px 0 6px;"
                "font-size:11px;color:#64748b;letter-spacing:0.08em;"
                "text-transform:uppercase;'>— or —</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<a class="sso-unipd-btn" href="{sso_url}" target="_self" '
                f'rel="noopener">'
                f'<img src="https://stem.elearning.unipd.it/pluginfile.php/'
                f'1/auth_shibboleth/logo/SSO_unipd.png" alt="UniPD SSO"/>'
                f'<span class="sso-unipd-label">Sign up with UniPD SSO</span>'
                f'</a>',
                unsafe_allow_html=True,
            )

    st.markdown("""
    <div class="auth-footer">
        By signing in, you agree to our Terms of Service and Privacy Policy
    </div>
    """, unsafe_allow_html=True)

    st.stop()


def logout():
    cc = _cookie_ctrl()
    if cc:
        try:
            cc.remove(_COOKIE_TOKEN)
            cc.remove(_COOKIE_REFRESH)
        except Exception:
            pass
    client = get_supabase()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    for k in ["user", "supabase_token", "supabase_refresh_token", "_sb_user_client"]:
        st.session_state.pop(k, None)
    st.rerun()


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def check_password() -> bool:
    """Local-dev / demo password gate, used ONLY when Supabase auth is not
    configured (no [supabase] secrets). On Streamlit Cloud the Supabase branch
    runs instead and this is never reached. Fails closed if nothing is set up."""
    if st.session_state.get("_pwd_ok"):
        return True
    try:
        expected = st.secrets["passwords"]["admin"]
    except Exception:
        st.error("🔒 Autenticazione non configurata: né Supabase né password locale (`[passwords].admin`).")
        return False
    pwd = st.text_input("Password", type="password", key="_local_pwd")
    if pwd:
        if pwd == expected:
            st.session_state["_pwd_ok"] = True
            return True
        st.error("❌ Password errata")
    return False
