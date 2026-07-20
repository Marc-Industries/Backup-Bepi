"""Tests for the SSO callback handler in src/bepi/auth.py.

The callback is the only piece of SSO that lives in the Streamlit app
itself. The Edge Function does the SAML validation and redirects the
user back with `?sso_token_hash=…&sso_email=…`. auth._handle_sso_callback
consumes those query params, calls Supabase's verify_otp to get a
session, and persists the session the same way the password sign-in path
does (session_state + cookies).

We mock the Supabase client + Streamlit bits to keep this test pure.
"""
import sys
import types


def _load_auth_with_stubs(monkeypatch, query_params: dict, session: dict):
    """Import auth.py with streamlit and supabase_client stubbed, and
    return the module + a fake supabase client + a fake cookie controller.
    """
    # Stub streamlit with the minimum surface auth.py touches during this
    # test: session_state, query_params, secrets, error, link_button is
    # not on the callback path.
    if "streamlit" not in sys.modules:
        st = types.ModuleType("streamlit")
        st.session_state = session
        st.query_params = query_params
        st.secrets = types.SimpleNamespace(get=lambda *_a, **_kw: "")
        st.error = lambda *a, **kw: None
        st.warning = lambda *a, **kw: None
        st.info = lambda *a, **kw: None
        st.stop = lambda: None
        st.rerun = lambda: None
        st.markdown = lambda *a, **kw: None
        st.tabs = lambda *_a, **_kw: (None, None)
        st.text_input = lambda *a, **kw: ""
        st.button = lambda *a, **kw: False
        st.link_button = lambda *a, **kw: None
        st.cache_resource = lambda f: f
        sys.modules["streamlit"] = st
    if "streamlit_cookies_controller" not in sys.modules:
        scc = types.ModuleType("streamlit_cookies_controller")
        scc.CookieController = lambda key=None: None
        sys.modules["streamlit_cookies_controller"] = scc
    if "bepi.supabase_client" not in sys.modules:
        sc = types.ModuleType("bepi.supabase_client")
        sc.get_supabase = lambda: None
        sys.modules["bepi.supabase_client"] = sc

    # Now reload auth fresh under the stubbed env.
    if "bepi.auth" in sys.modules:
        del sys.modules["bepi.auth"]
    from bepi import auth as auth_mod
    return auth_mod


def _make_fake_client(monkeypatch, *, user=None, session=None, raises=None):
    """Return a fake supabase client and patch get_supabase to return it."""
    fake = types.SimpleNamespace()
    captured = {}

    def verify_otp(payload):
        captured["verify_otp"] = payload
        if raises is not None:
            raise raises
        return types.SimpleNamespace(user=user, session=session)

    fake.auth = types.SimpleNamespace(verify_otp=verify_otp)
    captured["client"] = fake

    # Patch get_supabase inside auth module.
    import bepi.auth as auth_mod
    monkeypatch.setattr(auth_mod, "get_supabase", lambda: fake)
    return fake, captured


def test_callback_returns_false_when_no_token(monkeypatch):
    session = {}
    qp = {}  # no sso_token_hash, no sso_email
    auth_mod = _load_auth_with_stubs(monkeypatch, qp, session)
    _make_fake_client(monkeypatch, user=object(), session=object())

    cc = types.SimpleNamespace()
    assert auth_mod._handle_sso_callback(cc) is False
    assert "user" not in session


def test_callback_establishes_session_and_writes_cookies(monkeypatch):
    session = {}
    qp = {
        "sso_token_hash": "tok_abc123",
        "sso_email": "mario.rossi@studenti.unipd.it",
    }
    auth_mod = _load_auth_with_stubs(monkeypatch, qp, session)

    user = types.SimpleNamespace(
        id="uuid-mario",
        email="mario.rossi@studenti.unipd.it",
        user_metadata={"full_name": "Mario Rossi", "auth_provider": "unipd_sso"},
    )
    sess = types.SimpleNamespace(
        access_token="AT-123",
        refresh_token="RT-456",
    )
    fake, captured = _make_fake_client(monkeypatch, user=user, session=sess)

    cookie_writes: list[tuple[str, str, int]] = []
    cc = types.SimpleNamespace(set=lambda k, v, max_age: cookie_writes.append((k, v, max_age)))

    assert auth_mod._handle_sso_callback(cc) is True
    # verify_otp got the right args
    assert captured["verify_otp"] == {
        "token_hash": "tok_abc123",
        "type": "magiclink",
        "email": "mario.rossi@studenti.unipd.it",
    }
    # session_state populated
    assert session["user"]["id"] == "uuid-mario"
    assert session["user"]["email"] == "mario.rossi@studenti.unipd.it"
    assert session["user"]["role"] == "USER"  # least privilege (audit S1)
    assert session["supabase_token"] == "AT-123"
    assert session["supabase_refresh_token"] == "RT-456"
    # cookies written
    assert ("bepi_token", "AT-123", 86400 * 7) in cookie_writes
    assert ("bepi_refresh", "RT-456", 86400 * 7) in cookie_writes
    # query params cleared
    assert qp == {}


def test_callback_returns_false_when_no_supabase(monkeypatch):
    session = {}
    qp = {"sso_token_hash": "tok_abc", "sso_email": "x@y.it"}
    auth_mod = _load_auth_with_stubs(monkeypatch, qp, session)
    import bepi.auth as auth_mod_real
    monkeypatch.setattr(auth_mod_real, "get_supabase", lambda: None)

    cc = types.SimpleNamespace(set=lambda *a, **kw: None)
    assert auth_mod._handle_sso_callback(cc) is False
    assert qp == {}


def test_callback_handles_verify_otp_exception(monkeypatch):
    session = {}
    qp = {"sso_token_hash": "tok_bad", "sso_email": "x@y.it"}
    auth_mod = _load_auth_with_stubs(monkeypatch, qp, session)
    _make_fake_client(
        monkeypatch,
        raises=Exception("token has expired or is invalid"),
    )
    cc = types.SimpleNamespace(set=lambda *a, **kw: None)
    assert auth_mod._handle_sso_callback(cc) is False
    assert "user" not in session
    assert qp == {}  # params cleared even on failure


def test_callback_returns_false_when_session_missing(monkeypatch):
    """verify_otp returns something with no session — we treat as failure."""
    session = {}
    qp = {"sso_token_hash": "tok_abc", "sso_email": "x@y.it"}
    auth_mod = _load_auth_with_stubs(monkeypatch, qp, session)
    user = types.SimpleNamespace(id="u", email="x@y.it", user_metadata={})
    _make_fake_client(monkeypatch, user=user, session=None)
    cc = types.SimpleNamespace(set=lambda *a, **kw: None)
    assert auth_mod._handle_sso_callback(cc) is False
    assert "user" not in session
