"""Regression: risks loaded from the DB must be RiskItemData objects, not dicts.

The app accesses risks as objects (r.risk_id, r.status, r.risk_level, r.risk_score,
r.mitigation_strategy) in ~50 places. db_loader._map_risk used to return a dict, so
the first mission that actually had risks stored crashed the Overview with
AttributeError ('dict' object has no attribute 'risk_id'). The model was also
missing risk_score / mitigation_strategy that the Risks page reads.
"""
import sys
import types


def _load():
    # db_loader imports streamlit + the supabase client at module top; neither is
    # needed for _map_risk. Stub them (the repo's local supabase/ dir also shadows
    # the pip package). Force the stubs unconditionally — another test (e.g.
    # test_auth_role) may have installed a *partial* bepi.supabase_client stub
    # without get_service_client, so a guarded "if not in sys.modules" would leave
    # db_loader's top-level import broken depending on test order.
    st = types.ModuleType("streamlit"); st.session_state = {}
    sys.modules["streamlit"] = st
    pe = types.ModuleType("postgrest.exceptions"); pe.APIError = Exception
    sys.modules["postgrest"] = types.ModuleType("postgrest")
    sys.modules["postgrest.exceptions"] = pe
    sc = types.ModuleType("bepi.supabase_client")
    sc.get_supabase = lambda: None
    sc.get_service_client = lambda: None
    sys.modules["bepi.supabase_client"] = sc
    sys.modules.pop("bepi.db_loader", None)  # re-import against the fresh stub
    from bepi.db_loader import _map_risk
    from bepi.mock_data import RiskItemData
    return _map_risk, RiskItemData


_ROW = {
    "id": "uuid-1", "risk_id": "R-005", "title": "Battery degradation",
    "description": "Capacity fade over life", "category": "technical",
    "likelihood": 4, "consequence": 4, "risk_level": "high", "status": "open",
    "owner": "EPS", "mitigation_strategy": "Oversize BOL capacity",
}


def test_map_risk_returns_object_with_expected_attributes():
    _map_risk, RiskItemData = _load()
    r = _map_risk(_ROW)
    assert isinstance(r, RiskItemData)
    # the accesses that used to AttributeError on a dict
    assert r.risk_id == "R-005"
    assert r.status == "open"
    assert r.risk_level == "critical"          # computed: 4*4=16
    assert r.risk_score == 16                  # property read by the Risks page
    assert r.mitigation_strategy == "Oversize BOL capacity"  # alias of `mitigation`


def test_model_score_and_mitigation_alias():
    _map_risk, RiskItemData = _load()
    r = RiskItemData(id="1", risk_id="R-1", title="T", description="D",
                     category="technical", likelihood=3, consequence=5,
                     status="open", mitigation="Do X")
    assert r.risk_score == 15
    assert r.risk_level == "critical"
    assert r.mitigation_strategy == "Do X"
    r.mitigation = "Updated"                   # write goes to the real field
    assert r.mitigation_strategy == "Updated"  # read-only alias reflects it


def test_override_residual_fields_assignable():
    """get_effective_risks assigns residual_* — the fields must exist on the model."""
    _map_risk, RiskItemData = _load()
    r = _map_risk(_ROW)
    r.residual_likelihood = 2
    r.residual_consequence = 3
    assert (r.residual_likelihood, r.residual_consequence) == (2, 3)
