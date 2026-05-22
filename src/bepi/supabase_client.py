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
        try:
            client.auth.set_session(access_token, refresh_token)
        except Exception:
            pass
        try:
            client.postgrest.auth(access_token)
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
