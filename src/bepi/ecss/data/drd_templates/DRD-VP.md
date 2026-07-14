---
type: drd-template
deliverable: Verification Plan
titolo: Verification Plan (VP)
ecss_source: ECSS-E-ST-10-02C
drd_ref: Annex A
fase: [B, C, D]
review: [PRR, SRR, PDR, CDR, QR, AR]
status: template
---

> [!info] Come si usa questo template
> Questo è uno **scaffold**, non un documento da consegnare così com'è.
> Quando devi produrre un Verification Plan per un progetto:
> 1. Duplica questa nota e rinominala (es. `VP - Progetto XYZ`).
> 2. Cambia `status: template` in `status: in-lavorazione` nel frontmatter.
> 3. Applica il tailoring del progetto: cancella le sezioni non applicabili, segna quelle modificate.
> 4. Compila sezione per sezione. Sotto ogni titolo trovi una nota-guida e il riferimento alla clausola ECSS che la governa.
>
> Le tre righe tra i `---` in cima (il *frontmatter*) sono le etichette che permettono a Dataview di ritrovare e collegare questo documento. Non cancellarle.

---

## 1. Scopo e applicabilità
> [!note] Guida — *ECSS-E-ST-10-02C, scopo del DRD*
> Indica a quale prodotto/progetto si applica il piano, il livello (sistema, sottosistema, equipaggiamento) e i confini. Una frase su cosa il documento copre e cosa esplicitamente non copre.

*(da compilare)*

## 2. Documenti applicabili e di riferimento
> [!note] Guida
> Elenca gli standard applicabili (la serie ECSS-E-ST-10), le specifiche di requisiti da cui derivano le verifiche, e i documenti di interfaccia rilevanti.

*(da compilare)*

## 3. Strategia di verifica
> [!note] Guida — *governata da ECSS-E-ST-10-02C §5 (verification process)*
> Descrivi l'approccio complessivo: cosa si verifica, contro cosa (i requisiti), e con quale logica di copertura. È la sezione che spiega il *perché* delle scelte fatte nelle sezioni successive.

*(da compilare)*

## 4. Metodi di verifica
> [!note] Guida
> Per ogni requisito o gruppo di requisiti, indica il metodo: **test**, **analisi**, **review of design**, **inspection**. Motiva la scelta del metodo dove non è ovvia.

*(da compilare)*

## 5. Livelli e stadi di verifica
> [!note] Guida
> Definisci i livelli (sistema / sottosistema / unità) e gli stadi (qualifica, accettazione, pre-lancio…). Mostra come la verifica si distribuisce lungo il ciclo di vita.

*(da compilare)*

## 6. Model philosophy
> [!note] Guida
> Specifica i modelli usati (EM, EQM, FM, PFM…) e quali verifiche sono assegnate a ciascuno.

*(da compilare)*

## 7. Verification matrix (tracciabilità)
> [!note] Guida — *il cuore del documento*
> Matrice requisito → metodo → livello → stadio → stato. È il punto in cui si dimostra che **ogni** requisito ha una verifica assegnata. La copertura incompleta qui è il difetto più frequente.

*(da compilare — tipicamente una tabella o un riferimento al tool di requirements)*

## 8. Indipendenza delle verifiche critiche
> [!warning] Guida — *clausola che le lessons learned qui sotto rendono non-negoziabile*
> Per le verifiche critiche, definisci la **ridondanza/indipendenza** della misura: chi verifica la verifica. Una misura critica affidata a un singolo strumento o team senza cross-check indipendente è un single point of failure di processo.

*(da compilare)*

## 9. Organizzazione e responsabilità
> [!note] Guida
> Chi è responsabile di quali attività di verifica, e come si gestiscono le interfacce tra team (incluse le convenzioni condivise: unità, formati, baseline).

*(da compilare)*

---

## ⚠ Fallimenti storici che questo documento serve a prevenire
> [!tip] Questo elenco si popola da solo
> Il blocco qui sotto è una query Dataview. Pesca automaticamente tutte le note di tipo `lesson` il cui campo `drd` contiene il deliverable di questa nota (`Verification Plan`). Aggiungi una nuova lesson con l'etichetta giusta e comparirà qui senza toccare questo file.

```dataview
TABLE caso AS "Caso", causa_radice AS "Causa radice (reale)", fonte AS "Fonte ufficiale"
WHERE type = "lesson" AND contains(drd, this.deliverable)
SORT id ASC
```
