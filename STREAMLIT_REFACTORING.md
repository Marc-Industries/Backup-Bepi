# BEPI — Streamlit Refactoring Plan

> File: `STREAMLIT_REFACTORING.md`
> Data: 2026-06-20
> Scope: scomposizione di `streamlit_app.py` (6690 righe, 388 KB, 53 funzioni top-level) in moduli per sezione, con router centrale, helper condivisi e una sotto-struttura per la pagina `Integrations`.
> Status: proposta approvata — pronto per esecuzione.

---

## 1. Obiettivo

Alleggerire `streamlit_app.py` per renderlo ingestibile a colpo d'occhio, isolare le pagine in moduli indipendenti, e facilitare il debug futuro: un bug in `pages/team.py` non costringe più a scrollare 10k righe.

Il refactor deve:

- **non introdurre regressioni** (tutti i flussi esistenti restano funzionanti);
- **non rompere il runtime** (Streamlit Cloud continua a partire con `streamlit run streamlit_app.py`);
- **non duplicare logica** (helper globali estratti, non copiati);
- **non creare cicli di import** (le pagine non si importano fra loro, il router le importa tutte).

---

## 2. Mappa del file corrente

### 2.1 Statistiche globali

| Metrica | Valore |
|---|---:|
| Righe totali | **6 690** |
| Byte totali | **388 048** (388 KB) |
| Funzioni top-level (`def ...`) | 53 |
| `@st.cache_data` / `@st.cache_resource` nel file | **0** |
| Pagine (`page_*`) | 11 |
| Router (`PAGE_MAP[page]()`) | 1 blocco finale (righe 7300-7314) |
| `st.set_page_config` | 1 (riga 161) |
| Sidebar markup | 1 blocco (riga 898) |

I cache Streamlit vivono **fuori** da `streamlit_app.py` (in `bepi.services.*`, `bepi.db_loader`, ecc.). Questo è un vantaggio: il refactor non tocca la cache logic.

### 2.2 Sezioni per dimensione (righe)

| Sezione | Righe | Range | Note |
|---|---:|---|---|
| `page_integrations` | **1 961** | 5336-7296 | Il gigante: GMAT, FreeFlyer, MATLAB, thermal, power, orbit viz, LCA, SPENVIS, DRAMA, radiation, debris, deorbit, validation/import. Va spezzato in sotto-pagine. |
| `page_product_tree` | 882 | 1812-2693 | Include il dispatcher dialog (`_pt_action_dialog`) e i suoi 4 render. Tenere compatto. |
| `page_ecss` | 536 | 3887-4422 | Phases, gate reviews, tailoring. |
| `page_overview` | 504 | 1308-1811 | Mission cards + KPI. |
| `page_team` | 379 | 4957-5335 | Ha già `tab_permissions` con audit per-member. |
| `page_risks` | 341 | 3265-3605 | Include FMECA. |
| `page_requirements` | 322 | 2943-3264 | Verification matrix. |
| `page_schedule` | 281 | 3606-3886 | CPM/Gantt. |
| `page_warehouse` | 271 | 4686-4956 | Procurement. |
| `page_reports` | 263 | 4423-4685 | LaTeX/PDF. |
| `page_budgets` | 249 | 2694-2942 | ECSS rollup. |
| Router (`PAGE_MAP`) | 17 | 7297-7314 | La dispatch table finale. |

### 2.3 Sezioni non-pagina (helper globali) — da estrarre a prescindere

| Blocco | Range righe | Cosa fa | Destinazione proposta |
|---|---:|---|---|
| Imports top-level | 1-52 | `sys.path`, `import streamlit`, `import bepi.*` | restano in `streamlit_app.py` |
| `_process_product_tree_action` | 53-160 | Dispatcher write su `product_tree_nodes` + `budgets` | `streamlit/_pt_actions.py` |
| `get_member`, `member_badge`, `approval_badge`, `get_latest_approval` | 274-371 | Lookup utenti e badge | `streamlit/_badges.py` |
| Mock data (`mock_product_tree_flat`, `mock_requirements`, `mock_risks`, `mock_fmeca`, `mock_tasks`, `_get_mock_team`) | 423-759 | Dati offline per dev locale | `streamlit/_mock_data.py` (importato solo se `HAS_SUPABASE` è False) |
| `_get_product_tree`, `_get_equip_budgets`, `_build_budget_tree`, `_normalize_fmeca_entries` | 537-757 | Caching read dal DB | `streamlit/_loaders.py` |
| `_default_mission_data`, `_save_current_mission`, `_map_mission`, `_mission_from_db_row`, `_current_user_member`, `_activate_local_mission`, `_load_mission` | 778-1267 | Lifecycle missione | `streamlit/_mission.py` |
| `get_tasks`, `get_requirements`, `get_risks`, `get_effective_risks`, `get_approval_log`, `get_req_ownership`, `get_task_assignments`, `get_team` | 1269-1306 | Accessor session_state | `streamlit/_state.py` |
| Onboarding gate + state init | 1223-1307 | Decide se mostrare onboarding | `streamlit/_bootstrap.py` (chiamato PRIMA del router) |
| Sidebar (logo, nav, mission selector, user badge) | 898-1137 | Chrome layout | `streamlit/_layout.py` |
| Settings panel + manage missions | 1010-1222 | Pannello impostazioni, CRUD missioni, "Delete All" | `streamlit/_settings.py` |
| `st.set_page_config` | 161 | Config globale | resta in `streamlit_app.py` (prima di qualsiasi `st.*`) |

### 2.4 Vincoli identificati

1. **`@st.dialog` rule (Streamlit 1.58)**: il decorator deve essere chiamato durante lo script run, non all'import. Il dispatcher `_pt_action_dialog` resta l'unico punto che apre un dialog, e viene chiamato dentro `page_product_tree.main()`.
2. **Side-effect all'import**: nessun modulo `streamlit/pages/*.py` deve avere `st.*` o accessi a `st.session_state` a livello top-level. Tutto dentro `def main(): ...`.
3. **Session state cross-page**: chiavi come `_pt_active`, `active_mission_id`, `missions`, `user` sono lette da più pagine. I default vanno centralizzati in `_bootstrap.py`.
4. **Path relativi**: template LaTeX (`reports.py`) e qualsiasi `open("templates/...")` vanno adattati a `Path(__file__).parent / "..."`.
5. **Nessun ciclo di import**: moduli in `streamlit/pages/*.py` non si importano fra loro. Solo `streamlit_app.py` li importa tutti in una volta.

---

## 3. Struttura target

```
BEPI/
├── streamlit_app.py                  ← thin entrypoint (stima: ~300 righe)
├── streamlit/
│   ├── __init__.py
│   ├── _bootstrap.py                 ← session_state init + onboarding gate
│   ├── _layout.py                    ← sidebar, logo, nav, mission selector, user badge
│   ├── _settings.py                  ← Settings panel + manage missions
│   ├── _pt_actions.py                ← dispatcher dialog product tree
│   ├── _state.py                     ← accessor session_state
│   ├── _loaders.py                   ← _get_product_tree, _get_equip_budgets, _build_budget_tree
│   ├── _mock_data.py                 ← tutti i mock_* (offline only)
│   ├── _badges.py                    ← badge helpers
│   ├── _mission.py                   ← mission lifecycle helpers
│   └── pages/
│       ├── __init__.py
│       ├── overview.py               ← page_overview (~500 righe)
│       ├── product_tree.py           ← page_product_tree + dialog helpers (~880 righe)
│       ├── budgets.py                ← page_budgets (~250 righe)
│       ├── requirements.py           ← page_requirements (~320 righe)
│       ├── risks.py                  ← page_risks (~340 righe)
│       ├── schedule.py               ← page_schedule (~280 righe)
│       ├── ecss.py                   ← page_ecss (~540 righe)
│       ├── reports.py                ← page_reports (~260 righe)
│       ├── warehouse.py              ← page_warehouse (~270 righe)
│       ├── team.py                   ← page_team (~380 righe)
│       └── integrations/
│           ├── __init__.py
│           ├── common.py             ← shell + shared orbit context
│           ├── gmat.py               ← GMAT script generation
│           ├── freeflyer.py          ← FreeFlyer mission plan
│           ├── matlab.py             ← MATLAB sizing scripts
│           ├── thermal.py            ← thermal model
│           ├── power.py              ← power_solar
│           ├── orbit_viz.py          ← 3D orbit visualization
│           ├── lca.py                ← OpenLCA export
│           ├── spenvis.py            ← radiation analysis
│           ├── drama.py              ← debris / deorbit
│           └── validation.py         ← import DAS/DRAMA/MASTER, compare
└── tests/
    └── test_streamlit_imports.py     ← smoke test: importa ogni modulo
```

### 3.1 Decisioni di layout

- **`streamlit_app.py` resta in root**: il comando `streamlit run` punta lì. Spostarlo in `app/` richiederebbe di cambiare il comando ovunque (Streamlit Cloud config, README, CI).
- **`streamlit/pages/integrations/` ha granularità di "tab" attuale** (5-6 sotto-pagine), non di "dominio" (10+ file). Evita frammentazione eccessiva e mantiene la UX delle sub-tab esistenti.
- **Nomi prefissati con `_`** per i moduli helper (`_state.py`, `_layout.py`): convenzione Python per "internal", non importabili da `from streamlit._state import ...` da parte di terzi.
- **`@st.dialog` resta in `_pt_actions.py`**: singolo punto in tutto il progetto. Importare quel modulo non apre nulla; il decorator si attiva solo quando `main()` viene chiamato.

### 3.2 Firma standard di ogni pagina

Ogni modulo in `streamlit/pages/*.py` espone:

```python
# streamlit/pages/example.py
import streamlit as st

def main() -> None:
    """Render the Example page. No side effects on import."""
    ...  # tutto il codice UI qui dentro

main()  # chiamata a fine modulo — il router importa questo modulo
```

Niente `if __name__ == "__main__"`. Il router fa `import streamlit.pages.example` e l'`main()` a fine modulo si autoesegue. Se in futuro serve testing, si wrappa con `if __name__ == "__main__":`.

### 3.3 `streamlit_app.py` finale (stima ~300 righe)

```python
"""BEPI-SAT Demo Dashboard — thin entrypoint."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_antd_components import sac

# Config globale — DEVE restare prima di ogni st.*
st.set_page_config(...)

# Import dei moduli (solo per side-effect: registrano main())
from streamlit import _bootstrap, _layout
from streamlit.pages import (
    overview, product_tree, budgets, requirements, risks,
    schedule, ecss, reports, warehouse, team, integrations,
)

# Inizializzazione state
_bootstrap.init()

# Render chrome (sidebar con nav + mission selector)
page = _layout.render()

# Dispatch
PAGE_MAP = {
    "Overview":      overview.main,
    "Product Tree":  product_tree.main,
    "Budgets":       budgets.main,
    "Requirements":  requirements.main,
    "Risks":         risks.main,
    "Schedule":      schedule.main,
    "ECSS":          ecss.main,
    "Reports":       reports.main,
    "Integrations":  integrations.main,
    "Warehouse":     warehouse.main,
    "Team":          team.main,
}
PAGE_MAP[page]()
```

---

## 4. Rischi e mitigazioni

| # | Rischio | Mitigazione |
|---|---|---|
| R1 | Side-effect all'import (un `st.write` a top-level in una pagina rompe tutto) | Verifica `ast` pre-commit: nessun `st.*` o `st.session_state.*` al di fuori di `def main()`. Blocker pre-merge. |
| R2 | Session state non inizializzato (chiave mancante in pagina appena aperta) | `_bootstrap.py` setta tutti i default prima del dispatch. Test smoke: aprire ogni pagina in ordine casuale. |
| R3 | Path relativi rotti (template LaTeX, asset) | Grep pre-refactor: `open("..."`, `Path("..."`. Tutto convertito a `Path(__file__).parent / "..."`. |
| R4 | Cicli di import (pagina A importa pagina B) | AST check: `streamlit/pages/**/*.py` non può importare da `streamlit/pages/`. Solo `streamlit_app.py` importa le pagine. |
| R5 | `@st.dialog` rotto dopo lo split | Il decorator resta in `_pt_actions.py` importato da `product_tree.py`. Test: aprire Add / Edit / Delete / Manage dalla UI e verificare che nessuna dia `_assert_first_dialog_to_be_opened`. |
| R6 | `page_integrations` troppo grande (1961 righe) | Spezzato in `streamlit/pages/integrations/*.py` con un dispatcher interno. Le sub-tab esistenti restano il livello di navigazione. |
| R7 | `from bepi.X import Y` mancante dopo lo split | Tutti gli import sono top-level in `streamlit_app.py` e riesposti. Verifica con `python -c "import streamlit.pages.team"`. |
| R8 | Cache Streamlit invalidata per via del cold start dei moduli | Nessun `@st.cache_*` in `streamlit_app.py` (verificato: 0 occorrenze). I cache sono in `bepi.*` e non sono toccati. |

---

## 5. Ordine di esecuzione

> Una sessione ≈ 1 sotto-sezione. Ogni sotto-sezione termina con: smoke run + commit.

### Fase 0 — Discovery (15 min, no commit)

Grep sistematico per identificare:

- `open(` o `Path(` dentro `streamlit_app.py` (per path relativi da sistemare).
- `st.session_state` a top-level (non dentro `def`) → devono andare in `_bootstrap.py`.
- `import` condizionali dentro le funzioni (es. `import json` dentro `page_product_tree`) → vanno promossi a top-level del modulo di destinazione.
- `@st.dialog`, `@st.cache_*` (già verificato: 0 nel file).

Output: lista di fix meccanici da applicare durante le fasi successive.

### Fase 1 — Helper condivisi (~1 sessione)

Creare:

- `streamlit/__init__.py` (vuoto)
- `streamlit/_state.py` ← `get_tasks`, `get_requirements`, `get_risks`, `get_effective_risks`, `get_approval_log`, `get_req_ownership`, `get_task_assignments`, `get_team`
- `streamlit/_badges.py` ← `get_member`, `member_badge`, `approval_badge`, `get_latest_approval`
- `streamlit/_mock_data.py` ← tutti i `mock_*`, `TEAM_MEMBERS`, ecc.
- `streamlit/_loaders.py` ← `_get_product_tree`, `_get_equip_budgets`, `_build_budget_tree`, `_normalize_fmeca_entries`
- `streamlit/_mission.py` ← `_default_mission_data`, `_save_current_mission`, `_map_mission`, `_mission_from_db_row`, `_current_user_member`, `_activate_local_mission`, `_load_mission`
- `streamlit/_bootstrap.py` ← `init()` con default session_state + onboarding gate
- `streamlit/_pt_actions.py` ← `_process_product_tree_action` + dispatcher dialog

Risultato: nessuna `page_*` modificata, ma `streamlit_app.py` già alleggerito di ~1500 righe.

### Fase 2 — Pagine piccole e medie (~1 sessione)

Estrarre in `streamlit/pages/`:

- `overview.py` (504 righe)
- `budgets.py` (249 righe)
- `requirements.py` (322 righe)
- `risks.py` (341 righe)
- `schedule.py` (281 righe)
- `reports.py` (263 righe)
- `warehouse.py` (271 righe)
- `team.py` (379 righe)

Ordine: pagine con meno dipendenze condivise prima (overview, budgets), team/risks/ecss dopo.

Ogni modulo ha `def main(): ...` + `main()` a fondo file.

### Fase 3 — Product Tree + Layout + Settings (~1 sessione)

- `streamlit/_layout.py` ← sidebar markup (riga 898-1137)
- `streamlit/_settings.py` ← Settings panel + manage missions (1010-1222)
- `streamlit/pages/product_tree.py` ← 1812-2693

`product_tree.py` è la pagina più complessa: include il dialog dispatcher. Verificare con test specifico che le 4 azioni (Add/Edit/Delete/Manage) aprano il dialog senza `_assert_first_dialog_to_be_opened`.

### Fase 4 — `page_integrations` split (~1.5 sessioni, è il pezzo più grosso)

1961 righe → 6-7 sotto-pagine. Mantenere le sub-tab UX attuali:

- `streamlit/pages/integrations/__init__.py` ← `main()` con sub-tab dispatcher
- `common.py` ← shell + shared orbit context
- `gmat.py`, `freeflyer.py`, `matlab.py` ← generazione script
- `thermal.py`, `power.py`, `orbit_viz.py` ← modelli
- `lca.py`, `spenvis.py`, `drama.py` ← environment
- `validation.py` ← import DAS/DRAMA/MASTER + compare

Criterio di split: una sotto-pagina = una sub-tab visibile nell'UI corrente. Niente nuove sub-tab, niente rimozioni.

### Fase 5 — `streamlit_app.py` finale + Router (~30 min)

Riscrivere `streamlit_app.py` come thin entrypoint (~300 righe):

- Imports
- `st.set_page_config` (resta qui)
- `from streamlit import _bootstrap, _layout; _bootstrap.init(); page = _layout.render()`
- `from streamlit.pages import ...` (tutti i moduli)
- `PAGE_MAP[page]()`

### Fase 6 — Test + smoke (~30 min)

- `tests/test_streamlit_imports.py`: importa ogni modulo `streamlit/pages/*.py` e ne chiama `main()` con `streamlit.testing.v1.AppTest` (o MagicMock).
- AST check script: blocca commit se una pagina ha `st.*` fuori da `def main()`.
- Smoke run: `streamlit run streamlit_app.py --server.headless true`, click su ogni sidebar entry, verifica nessun `RuntimeError`.

### Fase 7 — Documentazione (~15 min)

- Aggiornare `CLAUDE.md` (sezione "Moduli Principali" e "Bug Fixes"): aggiungere nota sul nuovo layout `streamlit/`.
- Aggiornare `README.md` se esiste: il comando di run non cambia.
- Aggiungere questo file come riferimento storico.

---

## 6. Stima tempi

| Fase | Durata stimata | Commit? |
|---|---:|---|
| 0 — Discovery | 15 min | no |
| 1 — Helper condivisi | 1 sessione (~45 min) | sì |
| 2 — Pagine piccole/medie | 1 sessione (~45 min) | sì (multi-commit, 1 per pagina) |
| 3 — Product Tree + Layout + Settings | 1 sessione (~45 min) | sì |
| 4 — `page_integrations` split | 1.5 sessioni (~70 min) | sì (multi-commit) |
| 5 — `streamlit_app.py` finale | 30 min | sì |
| 6 — Test + smoke | 30 min | sì |
| 7 — Doc | 15 min | sì |
| **Totale** | **~5 ore** | **~10 commit** |

Ogni commit: smoke run locale + push su `main` e `backup`.

---

## 7. Definizione di "fatto"

- [ ] `streamlit_app.py` è ≤ 350 righe.
- [ ] Ogni `streamlit/pages/*.py` è ≤ 1000 righe (soglia di guardia).
- [ ] Zero `st.*` o `st.session_state.*` a top-level nei moduli pagina (verificato da AST check).
- [ ] Nessun modulo pagina importa da `streamlit/pages/` (verificato da AST check).
- [ ] `streamlit run streamlit_app.py` parte senza errori.
- [ ] Ogni sidebar entry (11) renderizza senza `RuntimeError`.
- [ ] Le 4 azioni Product Tree (Add/Edit/Delete/Manage) aprono il dialog senza `_assert_first_dialog_to_be_opened`.
- [ ] `pytest tests/test_streamlit_imports.py` passa.
- [ ] Nessuna regressione funzionale rispetto a prima (smoke test manuale delle feature chiave: cambiare fase, aggiungere nodo product tree, invitare utente, generare report).
- [ ] `CLAUDE.md` aggiornato con la nuova struttura.

---

## 8. File di supporto da creare (durante la Fase 6)

### 8.1 `tests/test_streamlit_imports.py`

```python
"""Smoke test: importa ogni modulo streamlit/pages/*.py senza errori."""
import importlib
import pathlib
import pytest

PAGES_DIR = pathlib.Path(__file__).parent.parent / "streamlit" / "pages"

def _discover_pages():
    return [p.stem for p in PAGES_DIR.glob("*.py") if p.stem != "__init__"]

@pytest.mark.parametrize("page_name", _discover_pages())
def test_import_page(page_name):
    """Ogni modulo pagina deve importare senza side-effect."""
    if page_name == "integrations":
        # La pagina integrations è un package
        return
    mod = importlib.import_module(f"streamlit.pages.{page_name}")
    assert hasattr(mod, "main"), f"{page_name} must expose main()"
    assert callable(mod.main), f"{page_name}.main must be callable"
```

### 8.2 `scripts/check_streamlit_structure.py` (AST check pre-commit)

Pseudocodice:

```python
import ast, pathlib, sys

PAGES = pathlib.Path("streamlit/pages")
violations = []

for py in PAGES.rglob("*.py"):
    if py.name == "__init__.py":
        continue
    tree = ast.parse(py.read_text())
    # 1) Cerca st.* o st.session_state.* a top-level
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue  # OK: dentro def
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id == "st":
                    violations.append(f"{py}: st.* call at top level: line {node.lineno}")
    # 2) Cerca import da streamlit.pages (vietato)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("streamlit.pages"):
            violations.append(f"{py}: forbidden import from {node.module}")

if violations:
    print("\n".join(violations))
    sys.exit(1)
print("OK: streamlit structure invariants satisfied.")
```

---

## 9. Note finali

- Il refactor è **meccanico**: nessuna nuova logica, nessun cambio UX. Solo spostamento di codice esistente in moduli coerenti.
- Il rischio principale è **import circolari**: da evitare tassativamente. I moduli `streamlit/pages/*.py` non si importano fra loro.
- Il vantaggio principale è **debug velocity**: domani, se il Team page ha un bug, apri un file di 380 righe, non 6690.
- Tutte le cache (`@st.cache_*`) restano fuori da `streamlit_app.py` (e resteranno fuori dai moduli `streamlit/`). Le cache vivono in `bepi.services.*` e `bepi.db_loader` per design.

---

**Ultimo aggiornamento**: 2026-06-20
**Autore**: BEPI refactoring sessione
