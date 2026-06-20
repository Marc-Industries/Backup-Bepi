# Remember.md — Snapshot 2026-06-20

> File originale: `Remember.md` (rimosso il 2026-06-20 durante la pulizia dei residui del frontend Next.js archiviato).
> Contenuto invariato: è una to-do list di Matteo del 2026 circa, con note su bug e miglioramenti.
> **Stato di ogni punto (verificato 2026-06-20):**

---

## DB Budget - Edit Equipment (Mass & Power & Maturity) ADD ROW

> Nel Db in tabella budget, all'inserimento da frontend per l'edit degli equipment lo script non risce a trovare e modificare i vecchi valori quindi ne crea di nuovi creando un nuovo id e row ad ogni modifica.

**Stato 2026-06-20: ✅ RISOLTO.**
Fix documentato in `CLAUDE.md` sezione "Bug Fixes & Root Causes (2026-05-29)":
- `bepi/budgets.py` ora fa update-then-insert (non più solo `.upsert()`).
- Migration `supabase/migrations/*_budgets_unique.sql` aggiunge `UNIQUE (node_id, budget_type)`.

---

## Product Tree - Tabella Budget Equipment

> Visualizzazione corretta dei valori di massa, potenza e misurazione con risposta alla richiesta di edit, ma necessità di refresh della pagina a causa del db.

**Stato 2026-06-20: ✅ RISOLTO** (refresh non più necessario grazie a `P1` in `CLAUDE.md` sezione "System Audit & Fixes (2026-06-10)" — cache del product tree in `_get_product_tree()`).

---

## Product Tree: latenza creazione/modifica/cancellazione nodi

> Latenza di creazione, modifica e cancellazione nodi, la comunicazione con db è corretta ma vengono creati i nodi con qualche secondo di latenza quando richiesto, lato db e scripts py corretti, problema con prestazioni db (test fatti con ruolo admin).

**Stato 2026-06-20: ⚠️ PARZIALMENTE RISOLTO.** La latenza residua è normale (round-trip DB). Nessuna regressione in questa sessione.

---

## Role Permission

> Attualmente sono state implementate grandi modifiche alla role permission seguendo le linee guida nella sezione Team & Role, l'admin è sempre a pieni poteri non è stato modificato, mentre gli altri ruoli come User etc.. non possono invitare membri o creare pezzi sul product tree (*da rivedere*) o modificare ruoli.
> Il fattore da vedere oltre alle limitazioni imposte ai ruoli che sono assolutamente da visionare nel dettaglio, vanno anche corretti i frammenti di codice che consentono all'admin di modificare i ruoli degli utenti, dato che da front end può farlo ma ciò non va a cambiarsi da db.

**Stato 2026-06-20: ✅ RISOLTO.** Permission audit completato (vedi tab_permissions in `page_team` di `streamlit_app.py`).

---

## COOKIE - Connector Google, Microsoft, SSO, etc.

> Aggiunta necessaria di cookie per il login con successivo adempimento dei login con connector e build project in google cloud.

**Stato 2026-06-20: ❌ NON IMPLEMENTATO.** Fuori scope del refactor attuale. Le sessioni Streamlit usano già `streamlit-cookies-controller` per il refresh token (vedi `auth.py`).

---

## SEND INVITATION MAIL

> Rivedere la send verification mail, la function è creata, i codici di invito funzionano correttamente, le mail sono da rivedere dato che la api non è configurata correttamente nel portale SupaBase, il name deve essere RESEND_API_KEY.

**Stato 2026-06-20: ✅ RISOLTO.** Email inviti su Brevo (non Resend, era il refuso). Fix `S2` in `CLAUDE.md` sezione "System Audit & Fixes (2026-06-10)" — Edge Function `send-invitation` validata server-side e Brevo configurato.
