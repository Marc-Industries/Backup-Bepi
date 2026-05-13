from supabase import create_client, Client
import streamlit as st


def get_supabase() -> Client | None:
    secrets = st.secrets.get("supabase", {})
    url = secrets.get("url", "")
    key = secrets.get("anon_key", "")
    if not url:
        return None
    client: Client = create_client(url, key)
    if "supabase_token" in st.session_state:
        client.session_token = st.session_state["supabase_token"]
    return client


def get_service_client() -> Client | None:
    secrets = st.secrets.get("supabase", {})
    url = secrets.get("url", "")
    key = secrets.get("service_role_key", "")
    if not url or not key:
        return None
    return create_client(url, key)
