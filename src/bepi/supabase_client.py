from supabase import create_client, Client
import streamlit as st


def get_supabase() -> Client | None:
    secrets = st.secrets.get("supabase", {})
    url = secrets.get("url", "")
    key = secrets.get("anon_key", "")
    if not url:
        return None
    client: Client = create_client(url, key)
    access_token = st.session_state.get("supabase_token")
    refresh_token = st.session_state.get("supabase_refresh_token")
    if access_token and refresh_token:
        # Ensure PostgREST requests are authenticated; setting `session_token`
        # is not enough for supabase-py >= 2.x.
        # set_session() auto-refreshes an expired access token and rotates the
        # refresh token — capture the result so we persist the fresh tokens and
        # use the fresh access token for PostgREST (otherwise queries silently
        # fail with a stale/expired JWT after ~1h).
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


def get_service_client() -> Client | None:
    secrets = st.secrets.get("supabase", {})
    url = secrets.get("url", "")
    key = secrets.get("service_role_key", "")
    if not url or not key:
        return None
    return create_client(url, key)
