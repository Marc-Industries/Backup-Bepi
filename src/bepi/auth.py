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
        "role": user.user_metadata.get("role", "USER") if user.user_metadata else "USER",
    }


def _restore_from_cookie(cc) -> bool:
    """Try to restore session from browser cookies. Returns True if restored."""
    if "user" in st.session_state:
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
            return True
    except Exception:
        # Token expired or invalid — clear cookies and force login
        try:
            cc.remove(_COOKIE_TOKEN)
            cc.remove(_COOKIE_REFRESH)
        except Exception:
            pass
    return False


def render_auth_ui():
    cc = _cookie_ctrl()

    # Try cookie-based session restore (survives F5 / hard refresh)
    if cc and _restore_from_cookie(cc):
        return st.session_state.get("user")

    if "user" in st.session_state:
        return st.session_state["user"]

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
    for k in ["user", "supabase_token", "supabase_refresh_token"]:
        st.session_state.pop(k, None)
    st.rerun()


def get_current_user() -> dict | None:
    return st.session_state.get("user")
