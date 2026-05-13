# Report di Sicurezza - BEPI Project

**Data analisi:** 2026-05-06
(IL TUTTO è RISOLVIBILE CON REDNER E CON FUNZIONE WEB SERVICE COSì DA POTER METTERE LE VARIABILI LI SENZA ESPORRE API O ALTRO NEL CODICE, IL RESTO è SPIEGATO QUI SOTTO):
**Ambito:** Backend Python/FastAPI, Frontend Next.js, Database Supabase PostgreSQL, Deploy Vercel/Streamlit Cloud  
**Livello rischio complessivo:** ALTO

---

## Executive Summary

L'analisi ha rilevato **vulnerabilità critiche** legate all'esposizione di credenziali di servizi cloud e **vulnerabilità medie** nel codice sorgente. Si raccomanda l'intervento immediato per mitigare i rischi identificati.

| Severità | Quantità | Stato |
|----------|----------|-------|
| Critico | 3 | Richiede azione immediata |
| Medio | 3 | Richiede remediation programmata |
| Basso | 2 | Monitoraggio consigliato |

---

## 1. Vulnerabilità Critiche

### 1.1 Esposizione Credenziali Cloud

Nel file `.claude/settings.local.json` sono state rilevate credenziali hardcoded nella cronologia dei permessi CLI.

**Token esposti:**

| Servizio | Tipo | Impatto |
|----------|------|---------|
| Supabase | JWT Anon Key | Accesso anonimo completo alle API REST/GraphQL del database |
| Vercel | API Token | Controllo completo su deploy, domini, environment variables, log |
| PostgreSQL | Password connessione | Accesso diretto al database con privilegi dell'utente specificato |

**Rischio:** Qualunque utente con accesso in lettura al repository o ai file di configurazione può ottenere controllo completo sull'infrastruttura cloud, con possibilità di esfiltrazione dati, modifica configurazioni, e interruzione del servizio.

**Locazione:**
- File: `.claude/settings.local.json`
- Righe interessate: 116-165 (cronologia comandi autorizzati)

### 1.2 Accesso Database Remoto

La configurazione permette connessioni dirette al database PostgreSQL ospitato su Supabase tramite endpoint pubblico (`*.pooler.supabase.com`), con credenziali autenticate tramite password in chiaro.

---

## 2. Vulnerabilità di Livello Medio

### 2.1 Cross-Site Scripting (XSS) Potenziale

**File:** `streamlit_app.py`  
**Pattern:** Uso estensivo di `unsafe_allow_html=True`

Il componente Streamlit `st.markdown()` viene utilizzato con il parametro `unsafe_allow_html=True` in numerosi punti del codice (linee 109, 263, 339, 764, 831, 854, 1189, 1205, 1320, 1335, 1453, 1473, 1499, 1603, 1805, 1963, 2096, 3272).

Questa configurazione disabilita la sanificazione HTML di default di Streamlit, esponendo l'applicazione a potenziali attacchi XSS se il contenuto visualizzato include input utente non validato.

### 2.2 Command Injection

**File:** `src/bepi/services/matlab_bridge.py`  
**Linea:** 126

La costruzione del comando per l'esecuzione di script MATLAB/Octave utilizza concatenazione di stringhe con percorsi potenzialmente influenzabili da input esterno:

```python
cmd = [engine_path, "-batch", f"run('{wrapper_path}')"]
```

Se il parametro `config.script_path` o il percorso `wrapper_path` possono essere controllati da input utente, esiste la possibilità di esecuzione arbitraria di comandi sul sistema host.

### 2.3 Autenticazione Inadeguata

**File:** `streamlit_app.py`  
**Linee:** 45-60

Il sistema di autenticazione implementa un meccanismo single-password basato su confronto stringa diretta:

```python
if pwd == st.secrets.get("passwords", {}).get("admin", ""):
    st.session_state.authenticated = True
```

**Criticità identificate:**
- Password in chiaro (o base64) senza hashing crittografico
- Assenza di rate limiting su tentativi di accesso
- Session management basato solo su variabili di stato Streamlit
- Nessun meccanismo di logout automatico o timeout sessione
- Logica di autorizzazione RBAC implementata client-side tramite dizionari Python

---

## 3. Configurazioni di Livello Basso

### 3.1 Validazione Input API

I endpoint FastAPI implementano validazione dei tipi tramite Pydantic schemas (`RequirementCreate`, `RequirementUpdate`, etc.), fornendo un livello base di protezione contro input malformati.

### 3.2 Prevenzione SQL Injection

L'uso pervasivo di SQLAlchemy ORM con query parametrizzate nelle API previene efficacemente attacchi SQL injection attraverso la gestione automatica del quoting dei parametri.

---

## 4. Superficie di Attacco

### Componenti Esposti

| Componente | Endpoint/Porta | Stato |
|------------|---------------|-------|
| Frontend Next.js | `https://*.vercel.app` | Pubblico |
| API FastAPI | `http://localhost:8000` | Locale (development) |
| Streamlit App | Locale/Demo | Non esposto pubblicamente |
| Database PostgreSQL | `aws-0-eu-west-1.pooler.supabase.co:6543` | Internet-routable |

### Dati Sensibili Potenzialmente Esposti

Attraverso le credenziali compromesse, un attaccante potrebbe accedere a:
- Mission data e configurazioni satellitari
- Product tree e specifiche tecniche
- Requirements database
- Risk registers e analisi FMECA
- Schedule e task assignments
- Team member information

---

## 5. Raccomandazioni Immediate

### Priorità 1 - Azione entro 24 ore
1. Revoca e rigenerazione di tutti i token API esposti
2. Rimozione del file `.claude/settings.local.json` dal repository
3. Aggiunta del pattern `*.local.json` a `.gitignore`

### Priorità 2 - Azione entro 7 giorni
1. Implementazione di rate limiting sull'autenticazione
2. Sanificazione di tutti gli input utente prima del rendering HTML
3. Validazione e sanitizzazione dei percorsi file prima dell'esecuzione subprocess

### Priorità 3 - Azione entro 30 giorni
1. Implementazione di autenticazione robusta (OAuth2/JWT con password hashing)
2. Abilitazione di Row Level Security (RLS) su Supabase
3. Implementazione di audit logging per operazioni critiche

---

## Appendice: Metodologia di Analisi

L'analisi è stata condotta tramite:
- Static Application Security Testing (SAST) tramite pattern matching
- Analisi manuale del codice sorgente Python/TypeScript
- Ispezione dei file di configurazione
- Review delle dipendenze e integrazioni esterne

**Limitazioni:** L'analisi non include penetration testing dinamico o fuzzing delle API.

---

*Report per BEPI Project*  
*Classificazione: CONFIDENZIALE*