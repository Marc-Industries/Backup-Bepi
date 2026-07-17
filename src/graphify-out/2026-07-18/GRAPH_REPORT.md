# Graph Report - src  (2026-07-17)

## Corpus Check
- 94 files · ~67,437 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 895 nodes · 2229 edges · 53 communities (52 shown, 1 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 337 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8d4463f7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- get_body
- budgets.py
- reviews.py
- thermal_model.py
- __init__.py
- debris.py
- __init__.py
- risks.py
- radiation_export.py
- nacrac.py
- enums.py
- get_supabase
- seed.py
- ImportResult
- budgets.py
- launch_vehicle.py
- station_keeping.py
- onboarding.py
- risks.py
- spice_kernels.py
- reports.py
- power_solar.py
- reentry.py
- excel_io.py
- requirements.py
- auth.py
- db_loader.py
- supabase_client.py
- env.py
- openlca_export.py
- matlab_bridge.py
- scheduling.py
- validation.py
- role_permissions.py
- drama.py
- report_sections.py
- phase_aggregation.py
- create_default_tailoring

## God Nodes (most connected - your core abstractions)
1. `get_supabase()` - 43 edges
2. `get_body()` - 34 edges
3. `Base` - 29 edges
4. `TimestampMixin` - 28 edges
5. `UUIDMixin` - 28 edges
6. `ProductNode` - 22 edges
7. `get_service_client()` - 21 edges
8. `BudgetType` - 20 edges
9. `BudgetAllocation` - 17 edges
10. `OrbitParams` - 17 edges

## Surprising Connections (you probably didn't know these)
- `budget_summary()` --indirect_call--> `ProductNode`  [INFERRED]
  src/bepi/api/v1/budgets.py → src/bepi/core/models/product_tree.py
- `budget_rollup()` --indirect_call--> `ProductNode`  [INFERRED]
  src/bepi/api/v1/budgets.py → src/bepi/core/models/product_tree.py
- `list_fmeca()` --indirect_call--> `FMECAEntry`  [INFERRED]
  src/bepi/api/v1/risks.py → src/bepi/core/models/risk.py
- `get_fmeca()` --indirect_call--> `FMECAEntry`  [INFERRED]
  src/bepi/api/v1/risks.py → src/bepi/core/models/risk.py
- `delete_fmeca()` --indirect_call--> `FMECAEntry`  [INFERRED]
  src/bepi/api/v1/risks.py → src/bepi/core/models/risk.py

## Import Cycles
- None detected.

## Communities (53 total, 1 thin omitted)

### Community 0 - "get_body"
Cohesion: 0.06
Nodes (64): Any, CelestialBody, get_body(), _force_model(), generate_maneuver_script(), generate_propagation_script(), generate_stationkeeping_script(), FreeFlyer script generation — creates .MissionPlan files from BEPI parameters. (+56 more)

### Community 1 - "budgets.py"
Cohesion: 0.10
Nodes (45): budget_rollup(), budget_summary(), _build_rollup_node(), create_allocation(), create_limit(), delete_allocation(), delete_limit(), get_allocation() (+37 more)

### Community 2 - "reviews.py"
Cohesion: 0.10
Nodes (44): get_db(), AsyncSession, create_mission(), delete_mission(), get_mission(), list_missions(), AsyncSession, update_mission() (+36 more)

### Community 3 - "thermal_model.py"
Cohesion: 0.09
Nodes (51): solar_flux_at_body(), _add_antenna_realistic(), _add_bus_mesh(), _add_panels(), _add_radiator(), _add_subsystem_blocks(), _add_thermal_nodes_markers(), _box_faces() (+43 more)

### Community 4 - "__init__.py"
Cohesion: 0.16
Nodes (32): create_node(), create_operating_mode(), delete_node(), delete_operating_mode(), get_node(), get_node_tree(), get_operating_mode(), list_nodes() (+24 more)

### Community 5 - "debris.py"
Cohesion: 0.08
Nodes (42): _atmospheric_density(), BreakupResult, BreakupType, CasualtyRiskResult, check_debris_compliance(), CollisionResult, ComplianceItem, ComplianceReport (+34 more)

### Community 6 - "__init__.py"
Cohesion: 0.20
Nodes (36): add_dependency(), cpm(), create_milestone(), create_task(), create_wbs(), delete_milestone(), delete_task(), delete_wbs() (+28 more)

### Community 7 - "risks.py"
Cohesion: 0.21
Nodes (32): create_fmeca(), create_fta_node(), create_risk(), delete_fmeca(), delete_fta_node(), delete_risk(), get_fmeca(), get_fta_node() (+24 more)

### Community 8 - "radiation_export.py"
Cohesion: 0.12
Nodes (29): _compute_dose_depth(), _compute_electron_spectrum(), _compute_proton_spectrum(), export_electron_spectrum(), export_generic_csv(), export_omere_csv(), export_proton_spectrum(), export_shieldose2() (+21 more)

### Community 9 - "nacrac.py"
Cohesion: 0.12
Nodes (30): compute_ms(), compute_nacrac(), compute_rc(), compute_ri(), MSParams, MSResult, NACRACParams, NACRACResult (+22 more)

### Community 10 - "enums.py"
Cohesion: 0.27
Nodes (26): bulk_import_requirements(), coverage_report(), create_requirement(), delete_requirement(), get_requirement(), get_requirement_trace(), list_requirements(), AsyncSession (+18 more)

### Community 11 - "get_supabase"
Cohesion: 0.13
Nodes (27): add_fmeca_entry(), add_mission(), add_mission_member(), add_product_node(), add_requirement(), add_risk(), add_task(), _clean_updates() (+19 more)

### Community 12 - "seed.py"
Cohesion: 0.17
Nodes (23): _code_by_id(), _compute_criticality(), FMECAEntryData, mock_fmeca(), mock_product_tree_flat(), mock_requirements(), mock_risks(), mock_tasks() (+15 more)

### Community 13 - "ImportResult"
Cohesion: 0.15
Nodes (22): _detect_separator(), import_das_xml(), import_drama_output(), import_master_dat(), _is_numeric(), Importers for DAS, DRAMA and MASTER output files., _try_float(), detect_and_import() (+14 more)

### Community 14 - "budgets.py"
Cohesion: 0.14
Nodes (22): budget_summary(), compute_value_with_margins(), get_component_margin(), get_system_margin(), ECSS margin policy tables from ECSS-E-HB-10-02., Compute value with component and optionally system margins.      Returns dict, _resolve_phase(), BudgetAllocationData (+14 more)

### Community 15 - "launch_vehicle.py"
Cohesion: 0.14
Nodes (20): _build_vehicles(), c3_capability(), escape_velocity(), launch_window_geometry(), LaunchVehicle, _make_c3_curve(), OrbitType, plot_c3_curves() (+12 more)

### Community 16 - "station_keeping.py"
Cohesion: 0.12
Nodes (20): compute_propellant_mass(), _density_at_altitude(), _orbital_period(), _orbital_velocity(), Station-keeping and delta-V budget tool for orbital missions., Atmospheric drag compensation ΔV for LEO.      Uses exponential atmosphere mod, GEO station-keeping ΔV (N-S + E-W).      N-S: ~50 m/s/yr (luni-solar inclinati, Sun-synchronous orbit RAAN maintenance ΔV.      J2 secular drift naturally mai (+12 more)

### Community 17 - "onboarding.py"
Cohesion: 0.18
Nodes (18): load_missions_for_user(), _check_invitation(), check_onboarding_needed(), _create_invitation(), _generate_invite_code(), _load_user_missions(), Full-screen onboarding wizard for new users., Check if user is member of any mission. Returns list of (mission_id, role) pairs (+10 more)

### Community 18 - "risks.py"
Cohesion: 0.13
Nodes (14): compute_criticality(), compute_fta_probability(), FaultTreeNodeData, fmeca_ranking(), FMECAEntryData, Risk management: risk register, FMECA, FTA., Recursively compute top event probability.     AND gate: P = product of childre, Compute probability that at least k out of n events occur.     Uses recursive e (+6 more)

### Community 19 - "spice_kernels.py"
Cohesion: 0.20
Nodes (17): BodyDef, _circle_boundary_vectors(), generate_all_kernels(), generate_ck_comment(), generate_dsk_input(), generate_fk(), generate_ik(), generate_mk() (+9 more)

### Community 20 - "reports.py"
Cohesion: 0.24
Nodes (13): _build_docx_programmatically(), compile_pdf(), _escape_dict(), _escape_latex(), generate_docx_report(), generate_report(), _latex_env(), Report generation service — LaTeX → PDF via pdflatex, DOCX via python-docx. (+5 more)

### Community 21 - "power_solar.py"
Cohesion: 0.28
Nodes (12): BatterySizing, compute_battery_sizing(), compute_eclipse_fraction(), compute_power_budget_balance(), compute_solar_power_profile(), export_systema_power_csv(), _orbit_period_min(), OrbitLightingParams (+4 more)

### Community 22 - "reentry.py"
Cohesion: 0.22
Nodes (12): _atmo_density(), compute_heat_shield_mass(), compute_reentry_trajectory(), mars_edl_sequence(), plot_reentry_profile(), Figure, Atmospheric re-entry trajectory and heat-shield sizing tool., TPS mass estimate from total heat load and shield type. (+4 more)

### Community 23 - "excel_io.py"
Cohesion: 0.35
Nodes (9): _auto_width(), export_mission(), export_product_tree(), export_requirements(), export_risks(), export_schedule(), Excel import/export service — openpyxl-based., _style_data() (+1 more)

### Community 24 - "requirements.py"
Cohesion: 0.22
Nodes (12): coverage_report(), generate_req_id(), import_from_csv_rows(), Requirements management service., Import requirements from CSV-style rows.     Expected columns: ID (optional), L, Generate requirement ID.     Level: SH (stakeholder), MIS (mission), SYS (syste, Trace a requirement up (parents) and down (children).     Returns {"parents": [, Generate verification matrix.     Returns list of dicts: {req_id, title, level, (+4 more)

### Community 25 - "auth.py"
Cohesion: 0.26
Nodes (10): check_password(), _cookie_ctrl(), logout(), Local-dev / demo password gate, used ONLY when Supabase auth is not     configu, Persist the freshest session tokens to cookies. Supabase rotates refresh     to, Try to restore session from browser cookies. Returns True if restored., render_auth_ui(), _restore_from_cookie() (+2 more)

### Community 26 - "db_loader.py"
Cohesion: 0.35
Nodes (10): load_mission_data(), load_mission_members(), _map_budget_limit(), _map_fmeca_entry(), _map_member(), _map_mission(), _map_product_tree(), _map_requirement() (+2 more)

### Community 27 - "supabase_client.py"
Cohesion: 0.22
Nodes (9): Per-session anon client, created once and reused across reruns.      Cached in, _user_client(), _generate_invite_code(), invite_team_member(), Chiama una Supabase Edge Function per inviare l'email di invito.      Ritorna, Genera un codice di invito casuale., Invita un membro del team tramite codice di invito.          Flusso:     1. C, _send_invitation_email() (+1 more)

### Community 28 - "env.py"
Cohesion: 0.24
Nodes (7): BaseSettings, do_run_migrations(), run_async_migrations(), run_migrations_online(), Config, Settings, Connection

### Community 29 - "openlca_export.py"
Cohesion: 0.36
Nodes (9): _exchange(), export_lca_csv(), export_openlca_jsonld(), _flow_json(), generate_lca_summary(), LCAItem, LCAModel, OpenLCA JSON-LD export — generates .zip archives importable by OpenLCA 2.  Con (+1 more)

### Community 30 - "matlab_bridge.py"
Cohesion: 0.36
Nodes (9): apply_outputs(), ParamMapping, prepare_inputs(), MATLAB/Octave bridge — execute scripts with parameter mapping., _resolve_engine(), run_script(), RunResult, ScriptConfig (+1 more)

### Community 31 - "scheduling.py"
Cohesion: 0.31
Nodes (9): compute_cpm(), CPMResult, gantt_data(), Scheduling: WBS, Gantt, CPM/PERT., Generate Gantt chart data for Plotly.     Returns list of dicts with: Task, Sta, Result of Critical Path Method analysis., Compute Critical Path Method.      Forward pass: compute ES (Early Start) and, TaskData (+1 more)

### Community 32 - "validation.py"
Cohesion: 0.36
Nodes (7): compare_internal_vs_imported(), DebrisBenchmark, _pct_deviation(), RadiationBenchmark, Benchmark validation for radiation and debris computations., validate_debris(), validate_radiation()

### Community 33 - "role_permissions.py"
Cohesion: 0.64
Nodes (7): can(), can_edit_node(), can_modify_product_tree(), _current_role(), _current_user(), _node_subsystem(), require()

### Community 34 - "drama.py"
Cohesion: 0.38
Nodes (6): DebrisEnvironment, DeorbitAnalysis, estimate_debris_flux(), estimate_deorbit(), DRAMA/MASTER interface — space debris and re-entry analysis.  ESA DRAMA (Debri, Estimate natural orbital decay time and delta-V for 25-year compliance.

### Community 35 - "report_sections.py"
Cohesion: 0.40
Nodes (3): _fmt(), generate_comparison_report_section(), Structured report section generators for radiation, debris, and comparison data.

### Community 36 - "phase_aggregation.py"
Cohesion: 0.60
Nodes (3): aggregate(), AggregatedOutput, PhaseOutput

## Knowledge Gaps
- **8 isolated node(s):** `LCAItem`, `RadiationEnvironment`, `DeepSpaceRadiation`, `OrbitState`, `RadiationBenchmark` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_body()` connect `get_body` to `thermal_model.py`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Why does `Document` connect `__init__.py` to `reports.py`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Why does `_build_docx_programmatically()` connect `reports.py` to `__init__.py`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Base` (e.g. with `BudgetAllocation` and `BudgetLimit`) actually correct?**
  _`Base` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `TimestampMixin` (e.g. with `BudgetAllocation` and `BudgetLimit`) actually correct?**
  _`TimestampMixin` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `UUIDMixin` (e.g. with `BudgetAllocation` and `BudgetLimit`) actually correct?**
  _`UUIDMixin` has 17 INFERRED edges - model-reasoned connections that need verification._
- **What connects `LCAItem`, `RadiationEnvironment`, `DeepSpaceRadiation` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._