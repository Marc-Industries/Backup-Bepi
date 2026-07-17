"""Security regression — the session role must NEVER be sourced from the
user-writable Supabase Auth `user_metadata`.

The authoritative role is the per-mission `mission_members` row (RLS-protected),
resolved at mission load. Persisting/reading it from user_metadata was a
privilege-escalation vector: any account could call the GoTrue `update_user`
API to self-set `role: ADMIN`. See auth._user_dict and onboarding._finalize_onboarding.
"""
import sys
import types


def _load_user_dict():
    # auth.py imports streamlit (and, transitively, the supabase client) at module
    # top. The test env needs neither for the pure _user_dict function, and the
    # repo's local `supabase/` dir shadows the pip package anyway — so stub them.
    if "streamlit" not in sys.modules:
        st = types.ModuleType("streamlit")
        st.session_state = {}
        sys.modules["streamlit"] = st
    if "bepi.supabase_client" not in sys.modules:
        sc = types.ModuleType("bepi.supabase_client")
        sc.get_supabase = lambda: None
        sys.modules["bepi.supabase_client"] = sc
    from bepi.auth import _user_dict
    return _user_dict


class _FakeUser:
    def __init__(self, metadata):
        self.id = "uuid-1"
        self.email = "u@example.com"
        self.user_metadata = metadata


def test_role_is_not_taken_from_user_metadata():
    """An attacker self-sets role=ADMIN via update_user; it must be ignored."""
    _user_dict = _load_user_dict()
    d = _user_dict(_FakeUser({"full_name": "Mallory", "role": "ADMIN"}))
    assert d["role"] == "USER"          # escalation attempt ignored
    assert d["full_name"] == "Mallory"  # benign metadata still honoured


def test_role_defaults_to_user_without_metadata():
    _user_dict = _load_user_dict()
    d = _user_dict(_FakeUser(None))
    assert d["role"] == "USER"
    assert d["email"] == "u@example.com"
