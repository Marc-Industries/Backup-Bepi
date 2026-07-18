# Graph Report - BEPI  (2026-07-18)

## Corpus Check
- 144 files · ~136,630 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1329 nodes · 2747 edges · 82 communities (80 shown, 2 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 705 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ecd3d73d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Celestial Bodies Data
- Risks API (FMECA/FTA)
- Requirements API
- Debris & Atmospheric Risk
- Product Tree API
- Risk Services (FMECA, FTA)
- Budget Allocation & Rollup
- Radiation Export Models
- Missions API
- Budgets API
- Demo Mission Seeder
- NASA NAC/RAC Radiation
- DB Writer (mutations)
- DAS/DRAMA/MASTER Importer
- Mock Data (offline)
- Onboarding & Mission Helpers
- Requirements Services
- CLI (bepi.cli)
- Onboarding Flow (loaders)
- Thermal Model (ESATAN)
- Launch Vehicle Capability
- Station Keeping & Propellant
- SPICE Kernels (NAIF)
- Satellite 3D Model
- Audit Decisions & Schema
- Misc Utilities (cone, etc.)
- Product Tree UI (Streamlit)
- Bug & Audit Log (deferred)
- Environment Constants
- Excel I/O Services
- Cluster 30
- Cluster 31
- Cluster 32
- Cluster 33
- Cluster 34
- Cluster 35
- Cluster 36
- Cluster 37
- Cluster 38
- Cluster 39
- Cluster 40
- Cluster 41
- Cluster 42
- Cluster 43
- Cluster 44
- Cluster 45
- Cluster 46
- Cluster 47
- Cluster 48
- Cluster 49
- Cluster 50
- Cluster 51
- Cluster 52
- Cluster 53
- Cluster 54
- Punti di decisione per tipo di prodotto
- seed_demo_mission
- LL-001 — Hubble, aberrazione sferica
- LL-002 — Mars Climate Orbiter, mismatch di unità
- ECSS corpus — knowledge layer (docs-as-code)

## God Nodes (most connected - your core abstractions)
1. `page_integrations()` - 103 edges
2. `get_supabase()` - 47 edges
3. `get_body()` - 34 edges
4. `page_reports()` - 21 edges
5. `Supabase PostgreSQL` - 21 edges
6. `Base` - 19 edges
7. `get_service_client()` - 19 edges
8. `TimestampMixin` - 18 edges
9. `UUIDMixin` - 18 edges
10. `ProductNode` - 18 edges

## Surprising Connections (you probably didn't know these)
- `page_integrations()` --calls--> `LCAItem`  [INFERRED]
  streamlit_app.py → src/bepi/integrations/openlca_export.py
- `page_integrations()` --calls--> `has_spacepy()`  [INFERRED]
  streamlit_app.py → src/bepi/integrations/spenvis.py
- `page_integrations()` --calls--> `OrbitState`  [INFERRED]
  streamlit_app.py → src/bepi/integrations/spice_kernels.py
- `docker-compose (PostgreSQL locale)` ----> `Supabase PostgreSQL`  [INFERRED]
  docker-compose.yml → CLAUDE.md
- `_load_mission()` --calls--> `load_mission_data()`  [INFERRED]
  streamlit_app.py → src/bepi/db_loader.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Streamlit refactoring: helper modules** — streamlit-bootstrap, streamlit-layout, streamlit-settings, streamlit-pt-actions, streamlit-state, streamlit-loaders, streamlit-mock-data, streamlit-badges, streamlit-mission [EXTRACTED]
- **Bug Fixes & Root Causes (2026-05-29)** — bug-budget-duplicates, bug-logout-1h, fix-email-invitations-brevo [EXTRACTED]
- **System Audit & Fixes (2026-06-10)** — audit-s1-default-role, audit-s6-check-password, audit-s2-edge-function, audit-p1-product-tree-cache, audit-p2-supabase-client-cache, audit-c1-c3-dead-code, audit-i1-schema-snapshot, audit-i2-ci [EXTRACTED]
- **Security Report Findings** — vuln-credentials-exposure, vuln-xss-streamlit, vuln-command-injection, vuln-weak-auth [EXTRACTED]
- **Remember.md TODO snapshot 2026-06-20** — todo-budget-add-row, todo-product-tree-latency, todo-role-permission, todo-cookie-sso, todo-send-invitation-mail [EXTRACTED]
- **Supabase schema: core tables (CLAUDE.md list)** — table-missions, table-requirements, table-risks, table-tasks, table-product-tree-nodes, table-equip-budgets, table-approval-log, table-email-queue, table-team-members, table-warehouse-items, table-procurement-orders [EXTRACTED]
- **DevOps configuration files** — requirements-txt, requirements-dev-txt, github_workflows_ci_workflow, docker-compose [EXTRACTED]

## Communities (82 total, 2 thin omitted)

### Community 0 - "Celestial Bodies Data"
Cohesion: 0.07
Nodes (62): Any, CelestialBody, get_body(), _force_model(), generate_maneuver_script(), generate_propagation_script(), generate_stationkeeping_script(), FreeFlyer script generation — creates .MissionPlan files from BEPI parameters. (+54 more)

### Community 1 - "Risks API (FMECA/FTA)"
Cohesion: 0.06
Nodes (70): DeclarativeBase, FastAPI, bulk_import_requirements(), coverage_report(), create_requirement(), delete_requirement(), get_requirement(), get_requirement_trace() (+62 more)

### Community 2 - "Requirements API"
Cohesion: 0.09
Nodes (69): create_node(), create_operating_mode(), delete_node(), delete_operating_mode(), get_node(), get_node_tree(), get_operating_mode(), list_nodes() (+61 more)

### Community 3 - "Debris & Atmospheric Risk"
Cohesion: 0.08
Nodes (42): _atmospheric_density(), BreakupResult, BreakupType, CasualtyRiskResult, check_debris_compliance(), CollisionResult, ComplianceItem, ComplianceReport (+34 more)

### Community 4 - "Product Tree API"
Cohesion: 0.53
Nodes (15): Criticality, FTGateType, RiskCategory, RiskLevel, RiskStatus, FaultTreeNodeCreate, FaultTreeNodeRead, FMECAEntryCreate (+7 more)

### Community 5 - "Risk Services (FMECA, FTA)"
Cohesion: 0.08
Nodes (22): compute_criticality(), compute_fta_probability(), FaultTreeNodeData, fmeca_ranking(), FMECAEntryData, Risk management: risk register, FMECA, FTA., ECSS-Q-ST-30 criticality classification.     Cat 1: Catastrophic (sev 5, occ >=, Recursively compute top event probability.     AND gate: P = product of childre (+14 more)

### Community 6 - "Budget Allocation & Rollup"
Cohesion: 0.08
Nodes (33): budget_summary(), compute_value_with_margins(), get_component_margin(), get_system_margin(), ECSS margin policy tables from ECSS-E-HB-10-02., Compute value with component and optionally system margins.      Returns dict, _resolve_phase(), BudgetAllocationData (+25 more)

### Community 7 - "Radiation Export Models"
Cohesion: 0.11
Nodes (30): _compute_dose_depth(), _compute_electron_spectrum(), _compute_proton_spectrum(), export_electron_spectrum(), export_generic_csv(), export_omere_csv(), export_proton_spectrum(), export_shieldose2() (+22 more)

### Community 8 - "Missions API"
Cohesion: 0.26
Nodes (11): create_mission(), delete_mission(), get_mission(), list_missions(), AsyncSession, update_mission(), Mission, MissionCreate (+3 more)

### Community 9 - "Budgets API"
Cohesion: 0.20
Nodes (28): budget_rollup(), budget_summary(), _build_rollup_node(), create_allocation(), create_limit(), delete_allocation(), delete_limit(), get_allocation() (+20 more)

### Community 10 - "Demo Mission Seeder"
Cohesion: 0.08
Nodes (26): date, build_demo_product_tree(), build_demo_requirements(), build_demo_risks(), build_demo_tasks(), main(), ~15 tasks spanning 18 months., Build complete product tree for BEPI-SAT. (+18 more)

### Community 11 - "NASA NAC/RAC Radiation"
Cohesion: 0.12
Nodes (30): int, compute_ms(), compute_nacrac(), compute_rc(), compute_ri(), MSParams, MSResult, NACRACParams (+22 more)

### Community 12 - "DB Writer (mutations)"
Cohesion: 0.13
Nodes (27): add_fmeca_entry(), add_mission(), add_mission_member(), add_product_node(), add_requirement(), add_risk(), add_task(), _clean_updates() (+19 more)

### Community 13 - "DAS/DRAMA/MASTER Importer"
Cohesion: 0.14
Nodes (22): _detect_separator(), import_das_xml(), import_drama_output(), import_master_dat(), _is_numeric(), Importers for DAS, DRAMA and MASTER output files., _try_float(), detect_and_import() (+14 more)

### Community 14 - "Mock Data (offline)"
Cohesion: 0.17
Nodes (15): _code_by_id(), _compute_criticality(), FMECAEntryData, mock_fmeca(), mock_product_tree_flat(), mock_requirements(), mock_risks(), mock_tasks() (+7 more)

### Community 15 - "Onboarding & Mission Helpers"
Cohesion: 0.05
Nodes (90): get_framework(), _default_mission_data(), can(), can_edit_node(), can_modify_product_tree(), _current_role(), _current_user(), _node_subsystem() (+82 more)

### Community 16 - "Requirements Services"
Cohesion: 0.13
Nodes (17): coverage_report(), generate_req_id(), import_from_csv_rows(), Requirements management service., Import requirements from CSV-style rows.     Expected columns: ID (optional), L, Generate requirement ID.     Level: SH (stakeholder), MIS (mission), SYS (syste, Trace a requirement up (parents) and down (children).     Returns {"parents": [, Generate verification matrix.     Returns list of dicts: {req_id, title, level, (+9 more)

### Community 17 - "CLI (bepi.cli)"
Cohesion: 0.11
Nodes (18): mission_create(), _render_tree(), tree_show(), build_tree(), compute_wbs_codes(), find_node(), flatten_tree(), generate_node_code() (+10 more)

### Community 18 - "Onboarding Flow (loaders)"
Cohesion: 0.19
Nodes (18): load_missions_for_user(), _check_invitation(), check_onboarding_needed(), _create_invitation(), _generate_invite_code(), _load_user_missions(), Full-screen onboarding wizard for new users., Membership rows for the user, or None if the check could not run.      None (D (+10 more)

### Community 19 - "Thermal Model (ESATAN)"
Cohesion: 0.23
Nodes (21): _build_coupling_map(), compute_eclipse_fraction_from_beta(), _effective_props(), EnvironmentFluxes, export_esatan_input(), export_systema_thermal_csv(), heater_sizing(), plot_thermal_map() (+13 more)

### Community 20 - "Launch Vehicle Capability"
Cohesion: 0.14
Nodes (20): _build_vehicles(), c3_capability(), escape_velocity(), launch_window_geometry(), LaunchVehicle, _make_c3_curve(), OrbitType, plot_c3_curves() (+12 more)

### Community 21 - "Station Keeping & Propellant"
Cohesion: 0.12
Nodes (20): compute_propellant_mass(), _density_at_altitude(), _orbital_period(), _orbital_velocity(), Station-keeping and delta-V budget tool for orbital missions., Atmospheric drag compensation ΔV for LEO.      Uses exponential atmosphere mod, GEO station-keeping ΔV (N-S + E-W).      N-S: ~50 m/s/yr (luni-solar inclinati, Sun-synchronous orbit RAAN maintenance ΔV.      J2 secular drift naturally mai (+12 more)

### Community 22 - "SPICE Kernels (NAIF)"
Cohesion: 0.20
Nodes (17): BodyDef, _circle_boundary_vectors(), generate_all_kernels(), generate_ck_comment(), generate_dsk_input(), generate_fk(), generate_ik(), generate_mk() (+9 more)

### Community 23 - "Satellite 3D Model"
Cohesion: 0.17
Nodes (24): _add_antenna_realistic(), _add_bus_mesh(), _add_panels(), _add_radiator(), _add_subsystem_blocks(), _add_thermal_nodes_markers(), _box_faces(), create_face_to_node_mapping() (+16 more)

### Community 24 - "Audit Decisions & Schema"
Cohesion: 0.19
Nodes (16): I1: Schema SQL rigenerato, P2: Cache client Supabase, S2: Edge Function send-invitation validata, Email inviti su Brevo, Setup Email Invitations, streamlit/_state.py, Supabase PostgreSQL, Table: approval_log (+8 more)

### Community 25 - "Misc Utilities (cone, etc.)"
Cohesion: 0.28
Nodes (12): BatterySizing, compute_battery_sizing(), compute_eclipse_fraction(), compute_power_budget_balance(), compute_solar_power_profile(), export_systema_power_csv(), _orbit_period_min(), OrbitLightingParams (+4 more)

### Community 26 - "Product Tree UI (Streamlit)"
Cohesion: 0.08
Nodes (23): 1. Introduzione, 2. Documenti applicabili e di riferimento, 3.1 Obiettivi e vincoli di progetto, 3.2 Logica di evoluzione del prodotto, 3.3 Fasi, review e pianificazione, 3.4 Approccio all'approvvigionamento, 3.5 Criticità iniziali, 3. Project overview (+15 more)

### Community 27 - "Bug & Audit Log (deferred)"
Cohesion: 0.16
Nodes (14): C1/C3: Rimozione codice morto, Bug aperti (deliberato), I2: CI workflow, S6: check_password() gate, Bug: Logout/perdita dati dopo ~1h, Comandi locali, docker-compose (PostgreSQL locale), GitHub Actions CI (+6 more)

### Community 28 - "Environment Constants"
Cohesion: 0.24
Nodes (13): Environment, _build_docx_programmatically(), compile_pdf(), _escape_dict(), _escape_latex(), generate_docx_report(), generate_report(), _latex_env() (+5 more)

### Community 29 - "Excel I/O Services"
Cohesion: 0.10
Nodes (19): 1. Cos'è (in tre righe), 2. Il problema che risolve, 3. Architettura — tre assi più uno, 4. Contenuto del vault (stato attuale), 5. Il contratto — schema dei dati, 6. Portabilità — cosa è Obsidian e cosa no, 7. Limiti noti e debito tecnico, 8. Roadmap (+11 more)

### Community 30 - "Cluster 30"
Cohesion: 0.17
Nodes (19): available_baselines(), _baseline_ok(), current_revision(), deliverable_by_id(), deliverables(), deliverables_for_review(), drd_template(), lessons() (+11 more)

### Community 31 - "Cluster 31"
Cohesion: 0.18
Nodes (9): BaseSettings, Connection, do_run_migrations(), run_async_migrations(), run_migrations_online(), get_db(), AsyncSession, Config (+1 more)

### Community 32 - "Cluster 32"
Cohesion: 0.22
Nodes (12): _atmo_density(), compute_heat_shield_mass(), compute_reentry_trajectory(), mars_edl_sequence(), plot_reentry_profile(), Figure, Atmospheric re-entry trajectory and heat-shield sizing tool., TPS mass estimate from total heat load and shield type. (+4 more)

### Community 33 - "Cluster 33"
Cohesion: 0.16
Nodes (16): check_password(), _cookie_ctrl(), logout(), Local-dev / demo password gate, used ONLY when Supabase auth is not     configu, Persist the freshest session tokens to cookies. Supabase rotates refresh     to, Try to restore session from browser cookies. Returns True if restored., render_auth_ui(), _restore_from_cookie() (+8 more)

### Community 34 - "Cluster 34"
Cohesion: 0.30
Nodes (11): load_mission_data(), load_mission_members(), _map_budget_limit(), _map_fmeca_entry(), _map_member(), _map_mission(), _map_product_tree(), _map_requirement() (+3 more)

### Community 35 - "Cluster 35"
Cohesion: 0.22
Nodes (9): Client, Per-session anon client, created once and reused across reruns.      Cached in, _user_client(), _generate_invite_code(), invite_team_member(), Chiama una Supabase Edge Function per inviare l'email di invito.      Ritorna, Genera un codice di invito casuale., Invita un membro del team tramite codice di invito.          Flusso:     1. C (+1 more)

### Community 36 - "Cluster 36"
Cohesion: 0.13
Nodes (5): fake(), FakeClient, _Query, gates.py against an in-memory fake Supabase client (no live DB needed)., _Resp

### Community 37 - "Cluster 37"
Cohesion: 0.20
Nodes (10): scripts/check_streamlit_structure.py, streamlit/_badges.py, streamlit/_bootstrap.py, streamlit/_layout.py, streamlit/_mission.py, streamlit/_mock_data.py, streamlit/pages/, streamlit/_settings.py (+2 more)

### Community 38 - "Cluster 38"
Cohesion: 0.36
Nodes (9): _exchange(), export_lca_csv(), export_openlca_jsonld(), _flow_json(), generate_lca_summary(), LCAItem, LCAModel, OpenLCA JSON-LD export — generates .zip archives importable by OpenLCA 2.  Con (+1 more)

### Community 39 - "Cluster 39"
Cohesion: 0.36
Nodes (9): apply_outputs(), ParamMapping, prepare_inputs(), MATLAB/Octave bridge — execute scripts with parameter mapping., _resolve_engine(), run_script(), RunResult, ScriptConfig (+1 more)

### Community 40 - "Cluster 40"
Cohesion: 0.14
Nodes (15): P1: Cache product tree, S1: Ruolo default onboarding, bepi.services, Bug: Duplicati budget (Edit Equipment), Remember.md Snapshot 2026-06-20, RBAC 8 ruoli, streamlit/_loaders.py, streamlit/_pt_actions.py (+7 more)

### Community 41 - "Cluster 41"
Cohesion: 0.12
Nodes (15): CDR — Critical Design Review, Copertura — cosa esiste già, Deliverable in lavorazione, Design e giustificazione, Indice Lifecycle, PDR — Preliminary Design Review, Piani, Prossimi template da costruire (+7 more)

### Community 42 - "Cluster 42"
Cohesion: 0.12
Nodes (15): 1. L'idea e l'obiettivo, 2. Le idee emerse e la scrematura, 3. La libreria delle lessons learned, 4. Lo strumento: Obsidian + Dataview, 5. Implementazione — Scenario 1 (sistema base), 6. Il layer RAG (fase futura, opzionale), 7. Evoluzione futura — ambiente di formazione, 8. Sequenza consigliata (+7 more)

### Community 43 - "Cluster 43"
Cohesion: 0.20
Nodes (15): _client(), ensure_review(), excluded_requirements(), initialise_gate(), load_review_gates(), load_tailoring(), Per-mission ECSS project data: review gates, deliverable status, tailoring.  T, Return the stored tailoring object: {product_type, decisions:[{req,decision,rati (+7 more)

### Community 44 - "Cluster 44"
Cohesion: 0.36
Nodes (7): compare_internal_vs_imported(), DebrisBenchmark, _pct_deviation(), RadiationBenchmark, Benchmark validation for radiation and debris computations., validate_debris(), validate_radiation()

### Community 45 - "Cluster 45"
Cohesion: 0.25
Nodes (4): BREVO_API_KEY, corsHeaders, SERVICE_ROLE_KEY, SUPABASE_URL

### Community 46 - "Cluster 46"
Cohesion: 0.38
Nodes (6): DebrisEnvironment, DeorbitAnalysis, estimate_debris_flux(), estimate_deorbit(), DRAMA/MASTER interface — space debris and re-entry analysis.  ESA DRAMA (Debri, Estimate natural orbital decay time and delta-V for 25-year compliance.

### Community 47 - "Cluster 47"
Cohesion: 0.18
Nodes (10): 1. Scopo e applicabilità, 2. Documenti applicabili e di riferimento, 3. Strategia di verifica, 4. Metodi di verifica, 5. Livelli e stadi di verifica, 6. Model philosophy, 7. Verification matrix (tracciabilità), 8. Indipendenza delle verifiche critiche (+2 more)

### Community 48 - "Cluster 48"
Cohesion: 0.14
Nodes (6): BEPI Architecture, bepi.core, bepi.ecss, BEPI Platform, Roadmap Fasi BEPI, Setup Claude Code per Matteo

### Community 49 - "Cluster 49"
Cohesion: 0.33
Nodes (6): bepi.integrations, Report Sicurezza, streamlit/pages/integrations/, Vuln Media: Command injection matlab_bridge, Vuln Critica: Esposizione credenziali, Vuln Media: XSS potenziale in streamlit_app.py

### Community 50 - "Cluster 50"
Cohesion: 0.40
Nodes (3): _fmt(), generate_comparison_report_section(), Structured report section generators for radiation, debris, and comparison data.

### Community 51 - "Cluster 51"
Cohesion: 0.50
Nodes (4): print_summary(), Print a summary of all ECSS seed data., Seed ECSS data into PostgreSQL (async).     Requires running PostgreSQL and con, seed_db()

### Community 52 - "Cluster 52"
Cohesion: 0.19
Nodes (13): Cone, body_names(), solar_flux_at_body(), interplanetary_data(), plot_interplanetary(), aggregate(), AggregatedOutput, PhaseOutput (+5 more)

### Community 77 - "Punti di decisione per tipo di prodotto"
Cohesion: 0.22
Nodes (8): Il dato che conta: quanti punti decisionali hai, Launch segment element/sub-system — 44 decisioni, Launch segment equipment — 19 decisioni, Matrice completa (Table 7-2), Matrice di pre-tailoring — ECSS-E-ST-10C Rev.1, Punti di decisione per tipo di prodotto, Space segment element/sub-system — 15 decisioni, Space segment equipment — 66 decisioni

### Community 78 - "seed_demo_mission"
Cohesion: 0.42
Nodes (8): _code_by_id(), _criticality(), _model_data(), _risk_level(), _sample(), _sample_product_tree(), seed_demo_mission(), _task_status()

### Community 79 - "LL-001 — Hubble, aberrazione sferica"
Cohesion: 0.33
Nodes (5): Aggancio al deliverable, Catena causale, Fonte, LL-001 — Hubble, aberrazione sferica, Sintesi

### Community 80 - "LL-002 — Mars Climate Orbiter, mismatch di unità"
Cohesion: 0.33
Nodes (5): Aggancio al deliverable, Catena causale, Fonte, LL-002 — Mars Climate Orbiter, mismatch di unità, Sintesi

### Community 81 - "ECSS corpus — knowledge layer (docs-as-code)"
Cohesion: 0.33
Nodes (5): Aggiornare a una nuova revisione, Come arriva in BEPI (build → app), Cosa c'è qui, ECSS corpus — knowledge layer (docs-as-code), Versioning (ECSS invecchia)

## Knowledge Gaps
- **116 isolated node(s):** `RadiationEnvironment`, `DeepSpaceRadiation`, `RadiationBenchmark`, `DebrisBenchmark`, `ParamMapping` (+111 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `page_integrations()` connect `Cluster 52` to `Celestial Bodies Data`, `Cluster 32`, `Debris & Atmospheric Risk`, `Cluster 38`, `Radiation Export Models`, `NASA NAC/RAC Radiation`, `Cluster 44`, `DAS/DRAMA/MASTER Importer`, `Cluster 46`, `Onboarding & Mission Helpers`, `Thermal Model (ESATAN)`, `Launch Vehicle Capability`, `Station Keeping & Propellant`, `SPICE Kernels (NAIF)`, `Satellite 3D Model`, `Misc Utilities (cone, etc.)`?**
  _High betweenness centrality (0.427) - this node is a cross-community bridge._
- **Why does `bepi.ecss` connect `Cluster 48` to `Cluster 43`, `Cluster 36`, `Onboarding & Mission Helpers`?**
  _High betweenness centrality (0.212) - this node is a cross-community bridge._
- **Why does `budget_summary()` connect `Budget Allocation & Rollup` to `CLI (bepi.cli)`, `Budgets API`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Are the 101 inferred relationships involving `page_integrations()` (e.g. with `streamlit_app.py` and `body_names()`) actually correct?**
  _`page_integrations()` has 101 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `get_supabase()` (e.g. with `logout()` and `render_auth_ui()`) actually correct?**
  _`get_supabase()` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `page_reports()` (e.g. with `streamlit_app.py` and `get_component_margin()`) actually correct?**
  _`page_reports()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `RadiationEnvironment`, `DeepSpaceRadiation`, `RadiationBenchmark` to the rest of the system?**
  _116 weakly-connected nodes found - possible documentation gaps or missing edges._