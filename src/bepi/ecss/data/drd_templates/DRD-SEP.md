---
type: drd-template
deliverable: System Engineering Plan
titolo: System Engineering Plan (SEP)
ecss_source: ECSS-E-ST-10C Rev.1
drd_ref: Annex D
chiamato_da: "requisiti 5.1a e 5.3.4a di ECSS-E-ST-10"
fase: [0, A, B, C, D, E]
review: [MDR, PRR, SRR, PDR, CDR, QR, AR]
status: template
---

> [!info] Come si usa
> Scaffold del **documento-ombrello del system engineering**. Struttura fedele all'Annex D di ECSS-E-ST-10C Rev.1.
> 1. Duplica e rinomina (`SEP - Progetto XYZ`), cambia `status` in `in-lavorazione` e `type` in `drd-doc`.
> 2. Applica il tailoring: elimina le sezioni non applicabili.
> 3. Compila. Sotto ogni titolo, la guida riporta il contenuto prescritto dal DRD.

> [!abstract] Scopo (dal DRD, D.1.2)
> Definire approccio, metodi, procedure, risorse e organizzazione per coordinare e gestire **tutte le attività tecniche** necessarie a specificare, progettare, verificare, far operare e mantenere il sistema in conformità ai requisiti del cliente.
> Copre l'**intero ciclo di vita** ed è stabilito **per ogni item del product tree**. Evidenzia rischi, elementi critici, tecnologie specificate, e le possibilità di riuso e standardizzazione.
> Il SEP è un elemento del **project management plan** (ECSS-M-ST-10).

> [!tip] Adattare il contenuto alla fase
> Il DRD raccomanda esplicitamente di **modulare il SEP sulla fase**: più analisi dei rischi e nuove tecnologie nelle fasi 0/A/B; più verifica e validazione nelle fasi C/D.

---

## 1. Introduzione
> [!note] DRD <1>
> Scopo, obiettivo, contenuto del documento e ragione che ne ha motivato la stesura (riferimento a programma/progetto e fase).

*(da compilare)*

## 2. Documenti applicabili e di riferimento
> [!note] DRD <2>
> Elencare i documenti applicabili e di riferimento. Il DRD richiede **esplicitamente** i riferimenti a: business agreement; project management plan (ECSS-M-ST-10 Annex A); product assurance plan (ECSS-Q-ST-10 Annex A); configuration management plan (ECSS-M-ST-40 Annex A); production plan; mission operations plan (ECSS-E-ST-70 Annex G); ILS plan.

*(da compilare)*

---

## 3. Project overview

### 3.1 Obiettivi e vincoli di progetto
> [!note] DRD <3.1>
> Nove punti prescritti: obiettivo del progetto e bisogno dell'utente; obiettivo del sistema come stabilito dalla TS (E-ST-10-06 Annex A); elementi principali dell'architettura di sistema e vincoli di riuso; caratteristiche del ciclo di vita e sviluppo incrementale; elementi di supporto (GSE, facility); vincoli organizzativi (contractor, partner, fornitori); lista delle criticità iniziali; regolamenti nazionali e internazionali; capacità di verifica e validazione disponibili (test, analisi, simulazione).

*(da compilare)*

### 3.2 Logica di evoluzione del prodotto
> [!note] DRD <3.2>
> Sviluppo incrementale: implementazione progressiva delle funzionalità, versioni successive, obiettivi e strategia per la loro implementazione.

*(da compilare)*

### 3.3 Fasi, review e pianificazione
> [!note] DRD <3.3>
> Milestone principali che guidano il processo SE; fasi del ciclo di vita e review principali coerenti col project management plan. Date delle milestone o durata delle fasi, e **percorso critico** secondo il master schedule.

*(da compilare — vedi [[Indice Lifecycle]] per i deliverable attesi a ciascuna review)*

### 3.4 Approccio all'approvvigionamento
> [!note] DRD <3.4>
> Strategia di acquisizione degli item del product tree (make or buy, product line, sviluppo incrementale).

*(da compilare)*

### 3.5 Criticità iniziali
> [!note] DRD <3.5>
> Lista delle criticità identificate all'inizio della/e fase/i coperte dal SEP: problemi, soggetti critici che richiedono attenzione, investigazione, azione e pianificazione dedicate.

*(da compilare)*

---

## 4. System design approach

### 4.1 Input del system engineering
> [!note] DRD <4.1>
> Input guida (business agreement; output delle fasi precedenti o esterni al SEP; project management plan, product assurance plan, risk management plan, configuration/documentation management plan).
> Mezzi e facility **esterni** messi a disposizione dal cliente o da terzi, con i relativi requisiti di interfaccia e l'autorità responsabile. Mezzi e facility **interni**.
> Deve contenere il **Coordinate System Document** (E-ST-10-09 Annex A).

> [!warning] 4.1.e — Sistema di unità di misura
> **Il SEP deve definire il sistema di unità da usare nel progetto.** È una clausola breve e facile da liquidare, ed è esattamente quella la cui assenza ha distrutto il Mars Climate Orbiter (vedi tabella in fondo). Non lasciarla implicita, e assicurati che sia propagata a tutti i fornitori.

*(da compilare)*

### 4.2 Output del system engineering
> [!note] DRD <4.2>
> Elencare gli output SE previsti per le fasi coperte (panoramica in Annex A → [[Indice Lifecycle]]).
> Descrivere: strategia delle attività SE ed eventi tecnici intermedi; attività di progettazione con obiettivi e output per fase; attività ingegneristiche principali e loro relazioni con le milestone; **model philosophy** (E-ST-10-02 §4.2.5); **margin policy** per fase, categoria di prodotto e maturità.
> Inoltre: metodi e processi (concurrent engineering, value analysis, cicli di iterazione); interrelazioni tra discipline; interazione con cliente e fornitori; coerenza delle attività in parallelo; attività di controllo; **valutazione dell'uso di COTS**.
> In caso di evoluzione incrementale: strategia di design per release iniziale, release successive e loro verifica/deployment, introduzione di nuove tecnologie, tool di analisi, controllo delle evoluzioni.

*(da compilare)*

### 4.3 Responsabilità e organizzazione del team SE
> [!note] DRD <4.3>
> Entità partecipanti e loro funzioni secondo il project management plan; ruoli e responsabilità chiave (system engineer, discipline engineer, technical manager); descrizione del lavoro cooperativo tra i team.

*(da compilare)*

### 4.4 Coordinamento del system engineering
> [!note] DRD <4.4>
> Coordinamento esterno e interno, in linea con il project management plan.

*(da compilare)*

---

## 5. Implementazione e piani collegati

### 5.1 Descrizione dei task di system engineering

#### 5.1.1 Descrizione del processo SE
> [!note] DRD <5.1.1>
> Descrivere il processo SE **tailorato sulle specificità del progetto**: tutti i task dalle condizioni iniziali (kick-off) all'evento di chiusura (review), le loro relazioni, le interfacce con gli altri attori, e le iterazioni esistenti.
> Per **ogni task**: informazioni in ingresso e loro origine, documenti prodotti e loro destinazione, funzioni SE svolte e contributo degli altri attori.

*(da compilare)*

#### 5.1.2 Integrazione delle discipline ingegneristiche
> [!note] DRD <5.1.2>
> Definire processo e controllo per ciascuna disciplina, richiamando gli standard applicabili e i piani dedicati che sono parte integrante del SEP:
> - **Meccanica** (termica, strutture, meccanismi, ECLS, propulsione, pirotecnica, parti meccaniche, materiali) → serie ECSS-E-ST-3x
> - **Elettrica/elettronica** (potenza, conversione, distribuzione, ottica, avionica, microonde, EMC, interfacce elettriche) → ECSS-E-ST-20
> - **Software** (volo, terra, checkout, simulazione) → ECSS-E-ST-40
> - **Comunicazioni** (link budget, data management, RF, protocolli) → ECSS-E-ST-50
> - **Controllo** (AOCS, robotica, rendez-vous e docking)
> - **Ambiente spaziale** (detriti, protezione planetaria, ambiente indotto) → ECSS-E-ST-10-04
> - **Interfaccia SE ↔ produzione**
> - **Operazioni** (definizione e preparazione, analisi di missione e traiettoria, operabilità: autonomia, scenari, modi nominali e non, FDIR) → ECSS-E-ST-70
> - **Logistica e manutenzione** a terra e in orbita
> - **Human factors** → ECSS-E-ST-10-11

*(da compilare)*

#### 5.1.3 Work package
> [!note] DRD <5.1.3>
> Definire e descrivere i work package delle attività ingegneristiche, mantenuti nella work breakdown structure.

*(da compilare)*

### 5.2 Piani collegati
> [!note] DRD <5.2>
> I sub-plan che coprono parti delle attività SE vanno **allegati al SEP**. Identificare i piani rilevanti nelle quattro categorie:
> 1. **Programmatici** — SEP dei sotto-prodotti, industrial procurement plan, risk management plan, off-the-shelf plan
> 2. **Verifica** — [[Template - Verification Plan|Verification Plan]], AIT plan, AIV plan, technology plan, system calibration plan
> 3. **Discipline** — fracture control, EMC, RF, alignment, software development, orbital debris mitigation, planetary protection, cleanliness
> 4. **Operazioni** — launch site operations, commissioning e operation support
>
> Descrivere vincoli e interazioni che questi piani impongono alle attività SE.

> [!warning] Attenzione a VP / AIT / AIV
> VP e AIT plan possono essere parte integrante del SEP, emessi separatamente (senza sovrapposizione), oppure combinati nell'**AIV Plan**. Ma l'esistenza dell'AIV Plan **esclude** VP e AIT plan indipendenti. È una scelta architetturale da fare consapevolmente, non per inerzia.

*(da compilare)*

### 5.3 Metodi, tool e modelli
> [!note] DRD <5.3>
> Elencare e descrivere metodi, tool e data model usati dal team SE.
> In particolare per **tracciabilità dei requisiti e dimostrazione della verifica (VCD)**: metodi e tool specifici, incluse le interfacce verso i fornitori di livello inferiore, e il riuso di elementi (COTS).

*(da compilare)*

### 5.4 Criticità
> [!note] DRD <5.4>
> Problemi che richiedono attenzione, investigazione o azione nella fase corrente; rischi identificati e misure di mitigazione.

*(da compilare)*

---

## 6. System engineering per le fasi successive
> [!note] DRD <6>
> Introdurre le attività SE delle fasi successive e, come minimo, elencare le criticità e i rischi da mitigare in quelle fasi.

*(da compilare)*

---

## ⚠ Fallimenti storici che questo documento serve a prevenire

```dataview
TABLE caso AS "Caso", causa_radice AS "Causa radice (reale)", fonte AS "Fonte ufficiale"
WHERE type = "lesson" AND contains(drd, this.deliverable)
SORT id ASC
```
