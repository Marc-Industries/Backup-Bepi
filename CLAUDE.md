# BEPI — Budget, Engineering & Project Integration

**Versione:** 0.2.0  
**Data:** Maggio 2026  
**Status:** Production Ready (Streamlit + Supabase DB)

---

## Cos'è BEPI

BEPI è una piattaforma completa per la gestione di progetti spaziali, focalizzata su:
- **Budget Engineering**: Calcolo automatico di budget massa/potenza con margini ECSS
- **Requirements Management**: Tracciamento requisiti con verifica e coverage
- **Risk Assessment**: Analisi rischi con FMECA e matrice di rischio
- **Project Scheduling**: Pianificazione con CPM e Gantt charts
- **Product Tree**: Albero prodotti multi-satellite con WBS codes
- **Report Generation**: Documenti LaTeX per PDR/CDR con template ECSS
- **Integrazioni**: GMAT, FreeFlyer, MATLAB, thermal models, LCA, SPICE kernels

### Architettura

- **Backend**: Python/FastAPI con SQLAlchemy + Supabase PostgreSQL
- **Frontend**: Streamlit (Streamlit Cloud) — unico runtime, Next.js rimosso 2026-06-10
- **Database**: Supabase con 20+ tabelle, RLS per multi-mission RBAC
- **Deploy**: Streamlit Cloud (app) + Supabase (DB/functions)

---

## Cosa esiste

### Core Engine (Python)
- ✅ Models/schemas per satelliti, requisiti, rischi, task, budget
- ✅ Services: budgets, requirements, risks, scheduling, reports
- ✅ CLI per seed/demo data e operazioni batch
- ✅ MATLAB bridge per sizing termico/strutturale
- ✅ Excel I/O per import/export dati

### Streamlit Dashboard
- ✅ App self-contained con mock data (password-protected)
- ✅ 11 pagine: Overview, Product Tree, Budgets, Requirements, Risks, Schedule, ECSS, Reports, Integrations, Warehouse, Team
- ✅ Multi-mission support con session state
- ✅ Product tree editor con drag&drop (JS integrato)
- ✅ Budget rollup con margini ECSS (massa/potenza)
- ✅ Requirements traceability con verification matrix
- ✅ Risk management con FMECA e criticality
- ✅ CPM scheduling con Gantt charts
- ✅ ECSS compliance checker e review templates
- ✅ Report generation (LaTeX/PDF) per PDR/CDR
- ✅ Integrazioni: GMAT/FreeFlyer/MATLAB scripts, 3D orbit viz, thermal/power models, LCA, SPICE kernels, space environment (radiation/debris)
- ✅ Warehouse management per procurement
- ✅ Team management con inviti email (Supabase Edge Functions + Resend)
- ✅ **Operating modes per equipment power**: ogni equipment ha UN power per mode (Commissioning, Recovery, Operation, …). Tabella `operating_modes` mission-scoped, hard cap 10 mode, gestita da Settings (add / delete / rename). Budget Editor mostra matrice power per equipment × mode via expander. Schema in `supabase/migrations/20260717170000_power_budget_operating_modes.sql`.

### Next.js Frontend (ARCHIVIATO 2026-06-10)
> Codice storico sul branch `archive/nextjs-frontend` (non più mantenuto, rimosso da `main`). Runtime attuale: solo Streamlit. (`git checkout archive/nextjs-frontend` per recuperarlo se serve solo lettura.)

### Database & Auth
- ✅ Supabase setup con 20 tabelle (missions, requirements, risks, etc.)
- ✅ Row Level Security per missioni
- ✅ Multi-mission RBAC (8 ruoli: ADMIN, PM, SE, SSL, QA, CM, AIT, USER)
- ✅ Email invitations con Edge Functions
- ✅ Real-time subscriptions

### Deploy & DevOps
- ✅ Streamlit Cloud per app
- ✅ Supabase per DB + Edge Functions
- ✅ Docker compose per sviluppo locale
- ✅ Pytest suite
- ⚠️ Alembic configurato ma non usato (migration reali in `supabase/migrations/`)

---

## Stato Implementazione
- **Fase 1 completata**: Core engine (models, services, schemas, API, CLI, Streamlit MVP)
- **Fase 2 completata**: Report generation ✅, MATLAB bridge ✅, Excel I/O ✅, seed scripts ✅
- **Fase 3 completata**: Integrazioni esterne ✅, ESA/NASA framework ✅, full editability ✅, multi-satellite product tree ✅, empty-state robustness ✅
- **Fase 4 completata**: Next.js frontend ✅ (poi archiviato), Supabase DB ✅, Streamlit Cloud deploy ✅, Auth ✅, CRUD editing ✅
- **Fase 5 completata**: Multi-mission DB con RBAC ✅ (20 tabelle, RLS per missione, profili utente, ruoli)

---

## Come usare

### Sviluppo Locale

```bash
# Backend (FastAPI, opzionale in dev)
PYTHONPATH=src python -m uvicorn bepi.app:create_app --factory --reload

# Streamlit (runtime principale)
PYTHONPATH=src streamlit run streamlit_app.py
```

### Deploy

```bash
# Streamlit Cloud (auto-deploy dal branch main)
# Niente build locale necessario.

# Supabase
supabase db push
supabase functions deploy send-invitation
```

---

## Moduli Principali

### bepi.core
- `models.py`: SQLAlchemy models (Mission, Requirement, Risk, Task, etc.)
- `schemas.py`: Pydantic schemas per API
- `enums.py`: ECSS standards, risk levels, etc.

### bepi.services
- `budgets.py`: Budget allocation e rollup con margini
- `requirements.py`: Verification matrix e coverage
- `risks.py`: FMECA e risk matrix
- `scheduling.py`: CPM algorithm
- `reports.py`: LaTeX generation

### bepi.integrations
- `celestial_bodies.py`: Planetary data
- `gmat.py`: GMAT script generation
- `freeflyer.py`: FreeFlyer Mission Plan export
- `matlab_gen.py`: MATLAB sizing scripts
- `thermal_model.py`: Steady/transient thermal analysis
- `power_solar.py`: Solar array sizing
- `orbit_viz.py`: 3D orbit visualization
- `openlca_export.py`: LCA analysis
- `spenvis.py`: Radiation analysis
- `drama.py`: Debris analysis

### bepi.ecss
- `standards.py`: ECSS compliance checker
- `margins.py`: Component/system margins
- `phases.py`: ESA/NASA phase definitions
- `reviews.py`: Gate review templates
- `subsystems.py`: Subsystem definitions

---

## Database Schema

20+ tabelle con RLS:
- `missions`: Mission metadata
- `requirements`: Requirements con verification
- `risks`: Risk items con mitigation
- `tasks`: WBS tasks con CPM
- `product_tree_nodes`: Hierarchical product tree
- `equip_budgets`: Equipment mass/power budgets
- `operating_modes`: Operating mode definitions per mission (Commissioning, Recovery, Operation, …) — usata da `budgets.operating_mode_id` per memorizzare un power per equipment × mode
- `budgets`: Mass (mode-independent, `operating_mode_id IS NULL`) + Power (per mode, `operating_mode_id` non-null). Vincolo UNIQUE su `(node_id, budget_type, operating_mode_id)`.
- `budget_limits`: Power limit per missione e per mode
- `approval_log`: Change approval workflow
- `email_queue`: Email sending queue
- `team_members`: User roles per mission
- `warehouse_items`: Procurement tracking
- `procurement_orders`: Purchase orders

---

## API Endpoints

FastAPI con auto-generated docs:
- `GET /missions`: List missions
- `POST /missions`: Create mission
- `GET /missions/{id}/requirements`: Get requirements
- `POST /missions/{id}/requirements`: Add requirement
- `PUT /missions/{id}/requirements/{req_id}`: Update requirement
- Similar per risks, tasks, budgets

---

## Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# Coverage
pytest --cov=bepi --cov-report=html
```

---

## Bug Fixes & Root Causes (2026-05-29)

- **Duplicati budget**: l'editor "Edit Equipment" salvava con `.upsert()` ma `budgets` non aveva vincolo UNIQUE → ogni Save inseriva una riga nuova invece di aggiornare. Fix: codice update-then-insert + vincolo `UNIQUE (node_id, budget_type)` su DB (migration in `supabase/migrations/`).
- **Logout / perdita dati dopo ~1h**: `get_supabase()` non risalvava i token rinnovati e usava il JWT scaduto per PostgREST → query DB fallivano in silenzio e l'F5 sloggava. Fix: token freschi persistiti in session_state + riscritti nel cookie (`auth.py`).
- **Logout su F5**: token ora salvati in cookie browser (`streamlit-cookies-controller`, 7gg) e ripristinati a ogni load.
- **Email inviti**: Edge Function `send-invitation` su **Brevo** (300 mail/gg free). Fallback graceful: se l'email fallisce, il codice invito è mostrato nell'UI. Caveat: Brevo filtra per IP, lasciare vuota la allowlist (Supabase Edge Functions usano IP dinamici).
- **Cleanup**: rimosse ~139 righe di codice morto (secondo handler product-tree mai eseguito).

## System Audit & Fixes (2026-06-10)

Audit multi-agente (sicurezza, performance, qualità, test/infra) + fix:

- **S1 — ruolo default**: l'onboarding non assegna più ADMIN di default a un utente senza membership (o su errore) → default `USER` (least privilege). Resta ADMIN della missione che crea. (`onboarding.py`)
- **S6 — `check_password()`**: era chiamata ma non definita (NameError nel branch senza Supabase). Ora è un vero gate password per dev locale, fail-closed. (`auth.py`)
- **S2 — Edge Function `send-invitation`**: era un relay email aperto. Ora valida server-side l'`invite_code` sulla tabella `invitations` e invia **solo** all'email registrata (non più a indirizzi arbitrari) + escape HTML + CORS ristretto. Redeployata.
- **P1 — cache product tree**: `_get_product_tree()` rileggeva l'intera tabella a ogni chiamata (~18×/render); ora serve la cache e ricarica solo su primo load / cambio missione / `force_reload` / nodo appena aggiunto.
- **P2 — cache client Supabase**: `get_service_client()` è `@st.cache_resource`; il client utente è creato una volta per sessione (era `create_client` 40-100×/render). `set_session` resta per-call → refresh token invariato.
- **C1/C3 — codice morto**: rimosse 416 righe di onboarding duplicato mai chiamato; frontend Next.js (~6k LOC) archiviato sul branch `archive/nextjs-frontend` e tolto da `main`.
- **I1 — `supabase/schema.sql`**: rigenerato dal DB live (mancava; c'era solo una copia stale di 10 tabelle). Snapshot generato: 22 tabelle, 25 enum, 79 policy RLS, 5 funzioni, 18 trigger. Cambiare via migration, poi rigenerare.
- **I2 — CI**: aggiunto `.github/workflows/ci.yml` (compileall + pytest) + `conftest.py` (pytest funziona senza `PYTHONPATH=src`) + `requirements-dev.txt`.

**Aperti (bucket "deliberato", non in questa sessione)**: S5 RLS split-brain `team_members` vs `mission_members` + S4 togliere il service client dalle azioni utente (il fix RLS "vero", da fare insieme e testare); C2 rimozione bridge JS / modal product-tree (è nei task aperti di Matteo in `task.txt`, lasciato a lui per non interferire con il suo lavoro in corso — ⚠️ edit/delete nodi non ha un path funzionante); P4 batch upsert budget; test sui bug fix.

## ECSS Compliance & Mission Progress (2026-07-14)

Integrato il lavoro di **Jacopo Coccimiglio** (ECSS "second brain", orientato alla produzione di deliverable) dentro BEPI. Chiave architetturale: la sua distinzione *conoscenza* (condivisa, in git) vs *dati di progetto* (per-tenant, DB+RLS) mappa 1:1 su BEPI, che aveva già gli "scaffali vuoti" — tabelle `reviews`/`review_deliverables` e campo `missions.ecss_tailoring` mai usati dall'app.

- **Corpus (conoscenza, docs-as-code)**: `src/bepi/ecss/data/` (JSON) + `corpus.py` (loader framework-agnostic, cache, versionato con `revision`). Sorgente human-readable in `docs/ecss-corpus/`. Contenuto: Table A-1 (37 deliverable, ID stabili `DRD-*` che riconciliano i 3 keyset in conflitto), Table 7-2 (punti di tailoring `//` per product type), 2 lessons, scaffold DRD (SEP, VP).
- **Layer dati-di-progetto**: `src/bepi/ecss/gates.py` — wire delle tabelle morte via **user client (RLS, audit S4)**. Review gate + stato deliverable su `reviews`/`review_deliverables`; tailoring su `missions.ecss_tailoring` jsonb. Zero nuovo schema.
- **UI**: 3 tab nuovi nella pagina ECSS — *Deliverables & Progress* (board "sono pronto per la PDR?", % completamento = mission-progress ECSS), *Tailoring* (decisioni per-clausola + razionale + impatto tailoring→deliverable via `called_by`), *Lessons Learned* (auto-surface sui deliverable agganciati).
- **Versioning ECSS**: ogni record porta `revision`; le missioni pinnano una baseline (`metadata.ecss_baseline`); si salvano mappature+metadati, non la prosa (link al PDF ufficiale). Change-advisory come evoluzione.
- **Test**: `test_ecss_corpus.py` + `test_ecss_gates.py` (fake client in-memory) — 11 test, gate/tailoring verificati contro lo schema (colonne, NOT NULL, idempotenza).
- **Aperti**: mappatura `called_by` seed solo per SEP (impatto tailoring completo quando estesa); `page_reports` usa ancora una lista DRD hardcoded (da migrare al corpus); libreria lessons 2/15-20 (roadmap Coccimiglio); RAG opzionale.

## Security & Infra Fixes (2026-07-17)

Verifica di sistema approfondita (Opus 4.8) + fix del debito emerso, per gravità:

- **🔴 Privilege escalation via `user_metadata` (`9f8eae7`)**: il ruolo di sessione (`session_state.user["role"]`, letto da `can()`/`require()`) era seminato da `user.user_metadata.role` e `onboarding._finalize_onboarding` ci scriveva `"ADMIN"`. Ma `user_metadata` è **scrivibile dall'utente** (GoTrue `update_user`) → chiunque poteva auto-promuoversi ADMIN, vanificando il fix S1. Altri 2 punti defaultavano a ruoli privilegiati (PM). Fix (least privilege, ruolo autorevole = `mission_members` sotto RLS): `auth._user_dict` parte `"USER"` e non legge più i metadata; rimossa la scrittura `update_user({role:ADMIN})`; `_current_user_member` default PM→USER. Il creatore resta ADMIN perché `add_mission` glielo concede in `mission_members`. Regression test `tests/unit/test_auth_role.py`. ⚠️ Utenti con `role:ADMIN` residuo nei metadata da vecchie sessioni: ora inerte (non più letto), volendo ripulibile con un admin-API pass.
- **🟠 Dipendenze non pinnate (`e5bf09e`)**: `requirements.txt` lasciava plotly/pandas/numpy/scipy senza versione e non c'era lock → ogni rebuild del Cloud pescava le ultime in autonomia. Aveva già rotto il venv locale (streamlit 1.56 + plotly 6.9: `go.layout.template.Data` rimosso in plotly 6.x → ImportError **al boot, prima del login**). Pinnati streamlit/plotly/pandas/numpy/scipy/openpyxl (+docxtpl/python-docx) a un set **verificato in venv pulito** (16 moduli chiave importano insieme). Supabase/transport restano floor `>=`.
- **🟡 Missioni duplicate (`00724fc`)**: `_user_has_missions` ritornava `[]` su errore DB (es. 42501 da GRANT mancante) e `check_onboarding_needed` lo leggeva come "nessuna missione" → onboarding → l'utente creava un duplicato (root cause dei 3× "CubeSat Demo" a secondi di distanza del 19/06, prima della migration `20260619140000` di Matteo delle 14:00). Difesa in profondità: ora ritorna `None` su errore (≠ `[]`), e l'onboarding non parte su errore. ⚠️ **Da confermare**: che la migration `20260619140000` sia applicata al DB live.
- **🟡 Reports DOCX (`936f18b`)**: `docxtpl`/`python-docx` usati da `reports.py` ma assenti da `requirements.txt` → "docxtpl not installed" sul Cloud. Dichiarati. **PDF (non risolto, deliberato)**: usa `pdflatex` (binario TeX Live assente sul Cloud, manca `packages.txt`) → il toggle PDF fallirà; deciso di lasciarlo al locale (il DOCX copre la ESA compliance). Nota minore: `gotrue` deprecato → `supabase_auth` (futuro).

## Operating Modes Feature (2026-07-17)

- **Power per equipment × mode**: ogni equipment ha un `nominal_value` di power diverso per ogni `operating_mode` (Commissioning, Recovery, Operation, …). Schema: `budgets.operating_mode_id` + UNIQUE `(node_id, budget_type, operating_mode_id)`. Mass resta mode-independent (1 riga con `operating_mode_id IS NULL`).
- **Settings → Operating Modes**: editor con Add (riga vuota in fondo), Delete (colonna 🗑️), Rename, Default flag. Hard cap 10 mode per missione (`MAX_OPERATING_MODES_PER_MISSION` in `streamlit_app.py`); contatore `N/10` visibile. Cache `operating_modes` e `equip_budgets` invalidata dopo save.
- **Budget → Edit Equipment**: la tabella ha SOLO colonne non-power (Subsystem, Code, Name, Mass, Qty, Maturity). Il power è in un expander per ogni equipment, con N `number_input` (uno per mode). Save batch persiste N righe in `budgets`.
- **RLS**: INSERT/UPDATE/SELECT su `operating_modes` permesso a qualsiasi membro della missione (`is_mission_member`). DELETE solo a PM/SE (`has_mission_role(..., ARRAY['PM','SE'])`). Migration: `supabase/migrations/20260717170000_power_budget_operating_modes.sql`.
- **Power limit per mode**: out of scope (vedi `OPERATING_MODES_FEATURE.md` §6). Per ora il `power_limit` è scritto solo per il default mode.

---

## Roadmap Futuro

- **Fase 6**: Mobile app (React Native)
- **Fase 7**: AI assistants per sizing automatico
- **Fase 8**: Multi-organization support
- **Fase 9**: Plugin architecture per custom integrations

---

## Contributi

- **Federico Toson** — lead, systems engineering, architettura.
- **Matteo Marcon** — sviluppo (frontend/product tree, Streamlit).
- **Jacopo Coccimiglio** — ECSS compliance: corpus deliverable/tailoring/lessons ("second brain"), lifecycle Table A-1, matrice pre-tailoring Table 7-2. Vedi `docs/ecss-corpus/`.

Questo file DEVE essere aggiornato ad ogni cambiamento significativo.  
Ultimo aggiornamento: 17 Luglio 2026

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
