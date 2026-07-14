---
type: indice
titolo: Indice Lifecycle — deliverable per review
fonte: "ECSS-E-ST-10C Rev.1 (15 February 2017), Annex A, Table A-1"
---

# Indice Lifecycle
### Quale deliverable produrre, a quale review

> [!info] Come si usa
> È il **punto d'ingresso del vault**. Parti dalla review che hai davanti, trovi i documenti attesi, lo standard e il DRD di riferimento.
>
> - La **Tabella A-1** (sotto) è statica e autorevole: viene dall'annesso A di ECSS-E-ST-10C Rev.1.
> - Le **viste per review** sono Dataview: mostrano da sole quali template esistono già nel tuo vault.
> - La **copertura** ti dice cosa hai e cosa ti manca ancora.

> [!warning] Come leggere le crocette
> Le crocette su una riga indicano i livelli **progressivi di maturità** attesi review dopo review. L'**ultima** crocetta è la review a cui il documento è atteso **completo e finalizzato**.
> Nota: i documenti di verifica hanno una tabella propria (Table G-1 di ECSS-E-ST-10-02).

---

## Tabella A-1 — System engineering deliverable documents

Legenda review: MDR · PRR · SRR · PDR · CDR · QR · AR · ORR · FRR · LRR · CRR · ELR · MCR

### Requisiti e specifiche

| Documento | Standard | DRD | Review |
|---|---|---|---|
| Mission description document | ECSS-E-ST-10 | Annex B | MDR, PRR |
| System concept report | ECSS-E-ST-10 | Annex C | MDR, PRR |
| Preliminary technical requirements specification | ECSS-E-ST-10-06 | Annex A | MDR, PRR |
| Technical requirements specification | ECSS-E-ST-10-06 | Annex A | SRR |
| Interface requirements document | ECSS-E-ST-10-24 | Annex A | PRR, SRR, PDR |
| Prelim. tech. req. spec. — next lower level | ECSS-E-ST-10-06 | Annex A | PRR, SRR |
| Tech. req. spec. — next lower level | ECSS-E-ST-10-06 | Annex A | SRR, PDR |
| Requirement justification file | ECSS-E-ST-10 | Annex O | MDR, PRR, SRR, PDR |
| Requirements traceability matrix (next lower level) | ECSS-E-ST-10 | Annex N | PRR, SRR, PDR |

### Piani

| Documento | Standard | DRD | Review |
|---|---|---|---|
| **System engineering plan** | ECSS-E-ST-10 | Annex D | MDR → AR |
| Technology plan | ECSS-E-ST-10 | Annex E | PRR, SRR, PDR |
| Technology Readiness Status List | ECSS-E-ST-10 | Annex E | MDR, PRR, SRR, PDR |
| Technology matrix | ECSS-E-ST-10 | Annex F | PRR, SRR, PDR |
| **Verification plan** | ECSS-E-ST-10-02 | Annex A | PRR → AR |
| AIT QM/FM plan | ECSS-E-ST-10-03 | Annex A | PDR, CDR, QR, AR |
| Space debris mitigation plan | ECSS-U-AS-10 | — | MDR → MCR |
| Coordinate system document | ECSS-E-ST-10-09 | Annex A | PRR → CDR |

### Design e giustificazione

| Documento | Standard | DRD | Review |
|---|---|---|---|
| Design definition file (DDF) | ECSS-E-ST-10 | Annex G | PRR → QR |
| DDF — next lower level | ECSS-E-ST-10 | Annex G | PDR, CDR, QR, AR |
| Design justification file (DJF) | ECSS-E-ST-10 | Annex K | PRR → QR |
| DJF — next lower level | ECSS-E-ST-10 | Annex K | PDR, CDR, QR |
| Function tree | ECSS-E-ST-10 | Annex H | PRR, SRR, PDR |
| Product tree | ECSS-M-ST-10 | Annex B | PRR, SRR, PDR |
| Specification tree | ECSS-E-ST-10 | Annex J | SRR, PDR |
| Technical budget | ECSS-E-ST-10 | Annex I | PRR → QR |
| Trade off reports | ECSS-E-ST-10 | Annex L | MDR → CDR |
| **Interface control document (ICD)** | ECSS-E-ST-10-24 | Annex B | SRR → FRR |
| Product User Manual | ECSS-E-ST-10 | Annex P | CDR → MCR |
| Mathematical model description | ECSS-E-ST-32 | Annex I | SRR → QR |

### Verifica e test

| Documento | Standard | DRD | Review |
|---|---|---|---|
| Verification control document | ECSS-E-ST-10-02 | Annex B | PRR → MCR *(fino a PDR: limitato alla verification matrix)* |
| Test specification | ECSS-E-ST-10-03 | Annex B | CDR → MCR |
| Test procedure | ECSS-E-ST-10-03 | Annex C | CDR → FRR |
| Test report | ECSS-E-ST-10-02 | Annex C | CDR → MCR |
| Verification report | ECSS-E-ST-10-02 | Annex F | CDR → MCR |
| Review of design report | ECSS-E-ST-10-02 | Annex D | CDR, QR |
| Inspection report | ECSS-E-ST-10-02 | Annex E | CDR, QR, AR |
| Correlation report | ECSS-E-ST-31 | Annex C | CDR, QR |

---

## Viste per review — template pronti nel vault

> [!tip] Si popolano da sole
> Ogni template DRD dichiara nel frontmatter a quali review appartiene (`review: [...]`). Questi blocchi li pescano automaticamente. Man mano che aggiungi template, le liste si riempiono senza toccare questa nota.

### SRR — System Requirements Review
```dataview
TABLE titolo AS "Documento", ecss_source AS "Standard", drd_ref AS "DRD"
WHERE type = "drd-template" AND contains(review, "SRR")
SORT titolo ASC
```

### PDR — Preliminary Design Review
```dataview
TABLE titolo AS "Documento", ecss_source AS "Standard", drd_ref AS "DRD"
WHERE type = "drd-template" AND contains(review, "PDR")
SORT titolo ASC
```

### CDR — Critical Design Review
```dataview
TABLE titolo AS "Documento", ecss_source AS "Standard", drd_ref AS "DRD"
WHERE type = "drd-template" AND contains(review, "CDR")
SORT titolo ASC
```

### QR — Qualification Review
```dataview
TABLE titolo AS "Documento", ecss_source AS "Standard", drd_ref AS "DRD"
WHERE type = "drd-template" AND contains(review, "QR")
SORT titolo ASC
```

---

## Copertura — cosa esiste già

Tutti i template presenti nel vault, con le review coperte:

```dataview
TABLE titolo AS "Documento", ecss_source AS "Standard", review AS "Review", status AS "Stato"
WHERE type = "drd-template"
SORT ecss_source ASC
```

## Deliverable in lavorazione

I documenti di progetto attualmente aperti.

> [!warning] Perché un documento potrebbe non comparire qui
> Quando duplichi un template per un progetto vero, servono **tre** campi nel frontmatter: `type: drd-doc`, `status: in-lavorazione` e `progetto: "<nome>"`. Quest'ultimo è quello che si dimentica più spesso — senza, il documento resta orfano in questa vista.

```dataview
TABLE titolo AS "Documento", progetto AS "Progetto", status AS "Stato", review AS "Review"
WHERE type = "drd-doc"
SORT progetto ASC
```

---

## Prossimi template da costruire

Ordine consigliato, per copertura del ciclo:

1. **System engineering plan** (E-ST-10, Annex D) — è il documento-ombrello, richiesto da MDR fino ad AR.
2. **Technical requirements specification** (E-ST-10-06, Annex A) — la base di tutto il resto.
3. **Interface control document** (E-ST-10-24, Annex B) — aggancia già la lesson LL-002 (Mars Climate Orbiter).
4. **Design definition file** (E-ST-10, Annex G).

---

*Fonte: ECSS-E-ST-10C Rev.1, Annex A, Table A-1. Da riallineare se cambia la revisione applicabile al progetto.*
