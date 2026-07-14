# BRIEF — ECSS Second Brain
### Documento di handover · v1.0 · luglio 2026

---

## 1. Cos'è (in tre righe)

Un sistema di supporto alla **produzione di deliverable** conformi agli standard ECSS.
Non è un archivio di standard né uno strumento di studio: è una catena di montaggio che, dato un documento da consegnare, fornisce lo scaffold normato, il profilo di tailoring applicabile e i fallimenti storici che quel documento serve a prevenire.

Implementato come vault Obsidian (markdown + YAML + plugin Dataview), ma — punto centrale per chi lo riceve — **il dato è indipendente da Obsidian** (vedi §6).

---

## 2. Il problema che risolve

Un system engineer che deve produrre un deliverable ECSS affronta ogni volta tre domande, e nessuno strumento gliele risponde insieme:

1. **Cosa devo produrre, e per quando?** → sepolto nella Table A-1 di ECSS-E-ST-10C
2. **Cosa ci va dentro?** → sepolto nei DRD, sparsi come annessi di standard diversi
3. **Cosa si applica al *mio* progetto?** → il tailoring, sepolto nella Table 7-2

E una quarta domanda che nessuno pone esplicitamente: **perché questa clausola esiste?** Senza risposta, i deliverable si compilano in modo burocratico, e proprio le clausole che sembrano formalità sono quelle che storicamente hanno intercettato i fallimenti.

Il sistema risponde a tutte e quattro, e le collega.

---

## 3. Architettura — tre assi più uno

| Asse | Nota | Origine del dato |
|---|---|---|
| **Cosa produrre e quando** | `Indice Lifecycle` | ECSS-E-ST-10C Rev.1, Annex A, Table A-1 |
| **Cosa contiene un deliverable** | `Templates/Template - *` | DRD (annessi ECSS) |
| **Cosa si applica al mio progetto** | `Matrice Pre-Tailoring ECSS` + `Tailoring - Template Progetto` | ECSS-E-ST-10C Rev.1, clausola 7, Table 7-2 |
| **Perché esiste questa clausola** ⟂ | `Lessons/LL-*` | Report d'inchiesta ufficiali (mishap boards) |

I primi tre assi vengono dallo standard. Il quarto — le **lessons learned** — è trasversale e attraversa gli altri tre: è la parte non replicabile, e il vero valore aggiunto.

### Il meccanismo che rende il sistema attivo

Ogni template DRD dichiara nel frontmatter il proprio `deliverable`. Ogni lesson dichiara, nel campo `drd`, i deliverable che avrebbero potuto intercettare quel fallimento. Una query Dataview dentro ogni template fa il resto:

```
WHERE type = "lesson" AND contains(drd, this.deliverable)
```

Risultato: aprendo il Verification Plan compaiono **da soli** Hubble e Mars Climate Orbiter. Nessuna sincronizzazione manuale. Si scrive la conoscenza una volta, appare ovunque serva.

Lo stesso schema, su un asse diverso, collega i template all'Indice Lifecycle tramite il campo `review`.

### Il legame tailoring → deliverable

Ogni DRD è **invocato da un requisito specifico** dello standard (campo `chiamato_da` nei template; il SEP, per esempio, dai requisiti 5.1a e 5.3.4a). Se il tailoring esclude quel requisito, **cade anche il deliverable**. È il modo più rapido per determinare cosa vada davvero prodotto — e per difenderlo in review.

---

## 4. Contenuto del vault (stato attuale)

```
vault/
├── 00 - START HERE.md              ← tour guidato, ~30 min, produce un deliverable vero
├── Indice Lifecycle.md             ← ingresso: review → deliverable
├── Matrice Pre-Tailoring ECSS.md   ← Table 7-2 completa (100 req × 9 product type)
├── Templates/
│   ├── Template - Verification Plan.md        (ricostruito, da riallineare a E-ST-10-02)
│   ├── Template - System Engineering Plan.md  (fedele a E-ST-10C Annex D)
│   └── Tailoring - Template Progetto.md
└── Lessons/
    ├── LL-001 - Hubble.md                     (verifica senza cross-check indipendente)
    └── LL-002 - Mars Climate Orbiter.md       (interfaccia non controllata)
```

### Il dato più interessante estratto

Il parsing della Table 7-2 rivela quanto il carico di tailoring vari col livello di prodotto:

| Tipo di prodotto | Decisioni `//` da prendere |
|---|---|
| Space system | **0** — si applica tutto |
| Space segment element/sub-system | **15** |
| Space segment equipment | **66** |
| Launch segment element/sub-system | **43** |
| Ground segment, GSE, Software | — (coperti da E-ST-70, E-ST-40, Q-ST-80) |

Questo dato da solo giustifica il layer: a livello equipment il tailoring è quasi interamente lavoro discrezionale, e sapere *quali* 66 righe guardare invece di leggerne 100 è tempo risparmiato ogni volta.

---

## 5. Il contratto — schema dei dati

**Questa è la sezione che conta per chi estende il sistema.** Il valore non sta nei file, sta nelle convenzioni: se si rompono, le viste smettono silenziosamente di popolarsi.

### Tipi di nota

| `type` | Ruolo | Si duplica? |
|---|---|---|
| `lesson` | Anti-pattern storico | no, si accumula |
| `drd-template` | Scaffold di un deliverable | **sì** |
| `drd-doc` | Deliverable di progetto (template duplicato) | — |
| `tailoring` | Decisioni di tailoring per un progetto | **sì** |
| `indice` / `riferimento` / `guida` | Navigazione e consultazione | no |

### Campi per tipo

**`lesson`**
| Campo | Obbl. | Note |
|---|---|---|
| `id` | ✔ | `LL-00X`, progressivo |
| `caso`, `programma`, `cosa_successe` | ✔ | descrittivi |
| `causa_radice` | ✔ | **la radice REALE** — quasi sempre di processo, non tecnica |
| `ecss` | ✔ | lista di standard/clausole |
| `drd` | ✔ | **lista di deliverable** — è la chiave di aggancio |
| `lesson` | ✔ | principio operativo azionabile |
| `fonte` | ✔ | report d'inchiesta **ufficiale** |
| `tags` | ✔ | include sempre `lesson`, `anti-pattern` |

**`drd-template`**
| Campo | Obbl. | Note |
|---|---|---|
| `deliverable` | ✔ | **chiave di aggancio** — deve corrispondere ai `drd` delle lessons |
| `titolo`, `ecss_source`, `drd_ref` | ✔ | provenienza |
| `chiamato_da` | ○ | requisito ECSS che invoca il DRD → usato dal tailoring |
| `review` | ✔ | lista — alimenta l'Indice Lifecycle |
| `fase`, `status` | ✔ | |

**`drd-doc`** — template duplicato per un progetto. Servono **tre** modifiche:
`type: drd-doc` · `status: in-lavorazione` · **`progetto: "<nome>"`** ← la più dimenticata

### Le tre regole non negoziabili

1. **YAML valido, o la nota sparisce.** Il frontmatter è tutto-o-niente: **una riga rotta invalida l'intero blocco** e la nota diventa invisibile a Dataview, senza alcun messaggio d'errore. Colpevole n.1: virgolette che non racchiudono l'intero valore (`fonte: "Report" (NASA, 1999)` → invalido; `fonte: "Report (NASA, 1999)"` → valido).
2. **Match esatto tra `drd` e `deliverable`.** Dataview fa confronto letterale: maiuscole e spazi contano. `Verification plan` ≠ `Verification Plan`.
3. **Nomi dei deliverable = titoli esatti della Table A-1.** Non inventare varianti.

> **Nota per il porting (§6): la regola 2 è fragile per costruzione.** In un sistema multi-utente va sostituita da **ID stabili** (`DRD-VP`, `DRD-SEP`) con il nome leggibile come sola etichetta di visualizzazione. È la prima modifica da fare se il sistema esce da un uso personale.

---

## 6. Portabilità — cosa è Obsidian e cosa no

Distinzione cruciale per chi vuole derivare il lavoro su un'altra piattaforma.

| Livello | Contenuto | Portabile? |
|---|---|---|
| **Dato** | frontmatter YAML, campi, relazioni | ✅ **Sì.** Markdown + YAML standard, parsabile in 3 righe da qualunque linguaggio |
| **Presentazione** | blocchi Dataview, wikilink `[[...]]`, callout `> [!note]` | ❌ Obsidian-specifico |

**Il vault non è vincolato a Obsidian: Obsidian è solo uno dei renderer possibili.** Il vault *è già* un grafo — lessons, template, clausole e requisiti sono nodi; `drd`, `ecss`, `review` sono archi — semplicemente oggi quel grafo lo interroga solo Dataview.

### Pattern consigliato: docs-as-code

Il markdown in git resta la **sorgente di verità**; uno step di build lo parsa e produce un artefatto strutturato (JSON/SQLite); la piattaforma target lo consuma. Obsidian rimane un editor comodo, non un requisito.

### La separazione da fare prima di portare

Nel vault oggi convivono due cose di natura diversa, e vanno separate:

- **Conoscenza** (lessons, template, matrice ECSS) — condivisa, cambia raramente, scritta da pochi → resta markdown in git, versionata, con review delle modifiche.
- **Dati di progetto** (decisioni di tailoring, deliverable in lavorazione) — per-tenant, mutabili, scritti da molti in parallelo → **richiedono database, auth, isolamento**. Non possono restare file in un contesto multi-utente.

---

## 7. Limiti noti e debito tecnico

**Da sistemare**
- Il template del **Verification Plan** è ricostruito, non estratto dal DRD reale: va riallineato a ECSS-E-ST-10-02 (i documenti di verifica hanno una tabella propria, Table G-1, non la Table A-1).
- Nel parsing della Table 7-2, la riga **5.2.3.7a** ha celle vuote nel PDF originale: due valori (colonne ground) non sono stati estratti. Impatto nullo in pratica (quelle colonne sono tutte `-`), ma va segnalato per correttezza.
- I suffissi numerici della matrice (`X1`, `//2`) rimandano alla colonna *Comments* dello standard, **non riportata**: per il testo esatto delle condizioni va consultato il PDF.

**Fragilità strutturali**
- Il match per stringa (regola 2 sopra) è una bomba a orologeria in multi-utente → migrare a ID stabili.
- Il grafo di Obsidian **non mostra** le relazioni lesson↔template, perché vivono nel frontmatter e non come wikilink. Non è un bug: è una conseguenza del modello. Le tabelle Dataview sono la fonte di verità, non il grafo.

**Non ancora costruito**
- Validatore/linter dello schema (necessario appena il numero di lessons cresce: i bug diventano invisibili).
- Template ICD (E-ST-10-24 Annex B) — completerebbe l'aggancio di LL-002.
- Libreria lessons: 2 casi su un obiettivo di 15-20.

---

## 8. Roadmap

**Immediato**
- Popolare le lessons (Ariane 5 V88, Schiaparelli, Mars Polar Lander, Challenger, Columbia…). Target 15-20 casi ben mappati: **valgono più di 100 abbozzati**.
- Template ICD, Technical Requirements Specification, Design Definition File.

**A massa critica raggiunta** (≥15 lessons, ≥8 template)
- **Analisi di impatto del tailoring**: "se escludo il requisito 5.3.4a, quali deliverable cadono e quali lessons smetto di intercettare?" È una traversata di grafo, non una query tabellare — e non esiste in nessuno strumento standard.
- **Buchi di copertura**: quali deliverable non hanno nessuna lesson agganciata (= punti ciechi); quali clausole compaiono in più fallimenti (= da non tagliare mai in tailoring).
- Layer RAG per l'interrogazione puntuale delle clausole, con obbligo di citare standard + clausola.

**Prospettiva**
- **Versione formativa.** Il materiale è già a metà strada: le lessons insegnano il *perché* di una clausola, che è ciò che manca a un junior. Direzioni: il caso rovesciato in esercizio ("ecco il contesto, cosa decidi?", con la catena causale rivelata dopo); il deliverable da **rivedere** invece che scrivere, con errori deliberati pescati dalle lessons — imparare a recensire un documento è una competenza SE enorme e mai insegnata esplicitamente.
- Avvertenza: un ambiente di auto-apprendimento **non sostituisce il mentoring**. Va progettato come strumento *attorno a cui* senior e junior lavorano insieme.

---

## 9. Principi di progetto (da non perdere nel porting)

1. **Deliverable-first.** Ogni elemento esiste per supportare la produzione di un output reale. Niente materiale di consultazione fine a sé stesso.
2. **La causa radice è quasi sempre organizzativa.** Hubble non è "errore ottico" ma "verifica critica senza cross-check indipendente". MCO non è "errore di unità" ma "interfaccia non controllata tra due team". Le versioni divulgative sbagliano quasi sempre questo punto — usare solo report d'inchiesta ufficiali.
3. **Il razionale vale più della decisione.** Un tailoring senza il *perché* è indifendibile in review e inutile sul progetto successivo.
4. **Non si scrive due volte.** Una lesson vive in un posto solo e affiora ovunque serva.
5. **Il sistema vale se lo si usa.** Un deliverable prodotto davvero insegna più di dieci template perfetti mai aperti.

---

*Fonte primaria: ECSS-E-ST-10C Rev.1 (15 febbraio 2017). Tutte le strutture vanno riallineate alla revisione applicabile al progetto specifico.*
