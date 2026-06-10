from supabase import create_client, Client
import streamlit as st


@st.cache_resource(show_spinner=False)
def get_service_client() -> Client | None:
    """Service-role client (bypasses RLS). It carries no per-user auth and is
    identical for everyone, so it is built once per process and cached."""
    secrets = st.secrets.get("supabase", {})
    url = secrets.get("url", "")
    key = secrets.get("service_role_key", "")
    if not url or not key:
        return None
    return create_client(url, key)


def _user_client() -> Client | None:
    """Per-session anon client, created once and reused across reruns.

    Cached in session_state (per-user) rather than via @st.cache_resource: the
    latter is process-global and would leak one user's auth header onto another
    user's client. create_client() builds several sub-clients (PostgREST, GoTrue,
    Realtime, Storage, Functions) — doing it 40-100x per render (every
    get_supabase() call) was the dominant cost, so we reuse one instance.
    """
    secrets = st.secrets.get("supabase", {})
    url = secrets.get("url", "")
    key = secrets.get("anon_key", "")
    if not url:
        return None
    client = st.session_state.get("_sb_user_client")
    if client is None:
        client = create_client(url, key)
        st.session_state["_sb_user_client"] = client
    return client


def get_supabase() -> Client | None:
    client = _user_client()
    if client is None:
        return None
    access_token = st.session_state.get("supabase_token")
    refresh_token = st.session_state.get("supabase_refresh_token")
    if access_token and refresh_token:
        # set_session() is local (just decodes/saves the JWT) unless the access
        # token has expired, in which case it does ONE network refresh and
        # rotates the refresh token — we capture and persist the fresh tokens
        # and authenticate PostgREST with the fresh access token. Keeping this
        # per-call (cheap on the cached client) preserves the long-session /
        # post-1h refresh behaviour.
        fresh_access = access_token
        try:
            res = client.auth.set_session(access_token, refresh_token)
            sess = getattr(res, "session", None)
            if sess:
                if sess.access_token:
                    fresh_access = sess.access_token
                    st.session_state["supabase_token"] = sess.access_token
                if sess.refresh_token:
                    st.session_state["supabase_refresh_token"] = sess.refresh_token
        except Exception:
            pass
        try:
            client.postgrest.auth(fresh_access)
        except Exception:
            pass
    return client
