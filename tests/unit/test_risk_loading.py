"""Regression: entities loaded from the DB must be the services/ dataclasses the
app actually uses (not dicts, not mock_data), or attribute access across the UI
raises AttributeError. The first fully-populated mission exposed this on risks
(Overview), tasks (Schedule/Team CPM), requirements, and FMECA.
"""
import sys
import types


def _load():
    # db_loader imports streamlit + the supabase client at module top; neither is
    # needed for the pure _map_* functions. Force the stubs (another test may have
    # installed a partial bepi.supabase_client stub) and re-import db_loader.
    st = types.ModuleType("streamlit"); st.session_state = {}
    sys.modules["streamlit"] = st
    pe = types.ModuleType("postgrest.exceptions"); pe.APIError = Exception
    sys.modules["postgrest"] = types.ModuleType("postgrest")
    sys.modules["postgrest.exceptions"] = pe
    sc = types.ModuleType("bepi.supabase_client")
    sc.get_supabase = lambda: None
    sc.get_service_client = lambda: None
    sys.modules["bepi.supabase_client"] = sc
    sys.modules.pop("bepi.db_loader", None)
    from bepi import db_loader
    return db_loader


def test_risk_maps_to_service_object():
    dbl = _load()
    from bepi.services.risks import RiskItemData
    r = dbl._map_risk({"id": "u", "risk_id": "R-005", "title": "Batt", "description": "d",
                       "category": "technical", "likelihood": 4, "consequence": 4,
                       "status": "open", "owner": "EPS", "mitigation_strategy": "Oversize"})
    assert isinstance(r, RiskItemData)
    assert r.risk_id == "R-005" and r.status == "open"
    assert r.risk_level == "critical" and r.risk_score == 16   # computed properties
    assert r.mitigation_strategy == "Oversize"
    r.residual_likelihood = 2                                  # get_effective_risks assigns this
    assert r.residual_likelihood == 2


def test_task_maps_to_service_object_and_cpm_runs():
    dbl = _load()
    from bepi.services.scheduling import TaskData, compute_cpm
    t = dbl._map_task({"id": "u1", "name": "SRR", "duration_days": 30,
                       "progress_pct": 50.0, "assigned_to": "PM", "is_milestone": False})
    assert isinstance(t, TaskData)
    assert t.id == "u1"           # compute_cpm keys on t.id (not the mock's task_id)
    assert t.predecessors == []   # no deps stored -> parallel
    # the exact call that crashed page_schedule and page_team must now run
    cpm = compute_cpm([t])
    assert cpm.project_duration == 30


def test_requirement_maps_to_service_object_and_coverage_runs():
    dbl = _load()
    from bepi.services.requirements import RequirementData, coverage_report
    r = dbl._map_requirement({"id": "u", "req_id": "SYS-001", "level": "system",
                              "category": "functional", "title": "T", "text": "shall",
                              "verification_status": "passed"})
    assert isinstance(r, RequirementData)
    assert r.req_id == "SYS-001" and r.allocated_to == []
    coverage_report([r])          # must not raise


def test_fmeca_maps_to_service_object():
    dbl = _load()
    from bepi.services.risks import FMECAEntryData
    e = dbl._map_fmeca_entry({"id": "u", "node_id": "node-uuid", "failure_mode": "open",
                              "failure_cause": "x", "local_effect": "y", "system_effect": "z",
                              "severity": 4, "occurrence": 2, "detection": 3, "mitigation": "m"},
                             {"node-uuid": "EPS-SA"})
    assert isinstance(e, FMECAEntryData)
    assert e.node_code == "EPS-SA"     # human code for display
    assert e.node_id == "node-uuid"    # UUID for _normalize_fmeca_entries
    assert e.rpn == 24                 # 4*2*3 property
