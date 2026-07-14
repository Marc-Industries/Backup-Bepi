# ECSS corpus — knowledge layer (docs-as-code)

**Contributo: Jacopo Coccimiglio** — questo materiale nasce dal suo "ECSS second
brain", un sistema di supporto alla **produzione di deliverable** conformi ECSS
(non un archivio di standard). Vedi `BRIEF - Handover.md` e `REPORT - Progettazione.md`.

## Cosa c'è qui

Questa cartella è la **sorgente di verità** (human-readable) del layer di
conoscenza ECSS. È versionata in git, cambia di rado, la scrivono in pochi.

| File | Contenuto | Fonte |
|---|---|---|
| `Indice Lifecycle.md` | Table A-1: deliverable → standard → DRD annex → review | ECSS-E-ST-10C Rev.1, Annex A |
| `Matrice Pre-Tailoring ECSS.md` | Table 7-2: ~100 requisiti × 9 product type, con i punti `//` da decidere | ECSS-E-ST-10C Rev.1, clausola 7 |
| `Lessons/` | Anti-pattern da report d'inchiesta ufficiali (Hubble, MCO) | mishap boards NASA |
| `BRIEF - Handover.md`, `REPORT - Progettazione.md` | disegno del sistema, principi, roadmap | Coccimiglio |

## Come arriva in BEPI (build → app)

Il dato **strutturato** consumato dall'app vive in `src/bepi/ecss/data/` (JSON +
i template DRD in markdown), caricato da `src/bepi/ecss/corpus.py`. I JSON sono
derivati dalle tabelle qui sopra con ID stabili (`DRD-SEP`, `DRD-VP`…) — la
prima cosa che Coccimiglio raccomanda per uscire dall'uso personale (handover §5).

- **Conoscenza** (questa cartella + `data/`) → file in git, versionata.
- **Dati di progetto** (decisioni di tailoring, stato deliverable per missione)
  → Supabase con RLS (tab *Deliverables* / *Tailoring* della pagina ECSS).

## Versioning (ECSS invecchia)

Ogni record porta una `revision` (`ECSS-E-ST-10C Rev.1`). Le missioni "pinnano"
una baseline; aggiornare il corpus non tocca una missione in corso. Si salvano
**mappature e metadati**, non la prosa (copyright + cambia più in fretta): per
il testo esatto delle clausole si rimanda al PDF ufficiale su ecss.nl.

## Aggiornare a una nuova revisione

1. Aggiorna i file sorgente qui (o aggiungine di nuovi con la nuova revisione).
2. Rigenera i JSON in `src/bepi/ecss/data/` (nuove righe con la nuova `revision`,
   **mai** mutare quelle esistenti).
3. Le missioni nuove adottano la baseline nuova; quelle in corso restano sulla
   loro finché non la si aggiorna esplicitamente.
