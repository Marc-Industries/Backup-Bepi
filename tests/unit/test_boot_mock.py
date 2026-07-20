"""Boot regression: local mock mode (no Supabase secrets) must seed a mission.

The early session-init block creates `missions` as an EMPTY dict; the mock-mode
seeders used to check `"missions" not in session_state`, so they never ran and
every page died on the select-a-mission banner. The seeders now treat a falsy
dict as "not initialized" — this test locks that in by booting the real app
headless via streamlit's AppTest.
"""
from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")

REPO_ROOT = Path(__file__).resolve().parents[2]
APP = REPO_ROOT / "streamlit_app.py"


def _supabase_configured() -> bool:
    secrets = REPO_ROOT / ".streamlit" / "secrets.toml"
    try:
        return "[supabase]" in secrets.read_text()
    except OSError:
        return False


@pytest.mark.skipif(
    _supabase_configured(),
    reason="local secrets configure Supabase: app boots in DB mode, not mock mode",
)
def test_mock_boot_seeds_mission():
    import sys

    from streamlit.testing.v1 import AppTest

    # test_auth_role stubs bepi.* modules in sys.modules and leaves them there;
    # purge so the app boots against the real modules regardless of test order.
    for name in [m for m in sys.modules if m == "bepi" or m.startswith("bepi.")]:
        sys.modules.pop(name, None)

    at = AppTest.from_file(str(APP), default_timeout=120)
    at.session_state["_pwd_ok"] = True  # test fixture: skip the dev password gate
    at.run()

    assert not at.exception, [str(e.value) for e in at.exception]
    assert "my-mission" in at.session_state["missions"]
    assert at.session_state["active_mission_id"] == "my-mission"
    banner = [w.value for w in at.warning if "select or create a mission" in w.value]
    assert not banner, "mock boot still stops on the select-a-mission banner"
