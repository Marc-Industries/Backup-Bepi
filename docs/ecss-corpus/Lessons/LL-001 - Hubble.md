---
type: lesson
id: LL-001
caso: Hubble — aberrazione sferica dello specchio primario
programma: HST / NASA, 1990
cosa_successe: Lo specchio primario fu lavorato con una curvatura leggermente errata. Il difetto non fu intercettato prima del lancio e degradò le immagini fino alla missione di servizio del 1993.
causa_radice: Il null corrector usato per guidare la lavorazione era mal assemblato (un elemento ottico spaziato in modo errato). Misure indipendenti che segnalavano l'anomalia furono ignorate e non riconciliate. La radice è di PROCESSO — assenza di cross-check indipendente su una verifica critica — non di progetto ottico.
ecss: [E-ST-10-02]
drd: [Verification Plan]
lesson: Una verifica critica affidata a un singolo strumento senza ridondanza indipendente è un single point of failure di processo. I dati discordanti vanno riconciliati, non scartati.
fonte: "The Hubble Space Telescope Optical Systems Failure Report (Allen Board, NASA, 1990)"
tags: [lesson, anti-pattern, verification, review-independence]
---

# LL-001 — Hubble, aberrazione sferica

## Sintesi
Difetto ottico non rilevato a terra a causa di un processo di verifica privo di controlli indipendenti su una misura critica.

## Catena causale
1. Il null corrector di riferimento era assemblato in modo errato.
2. La lavorazione dello specchio seguì fedelmente uno strumento sbagliato.
3. Verifiche indipendenti suggerivano un problema, ma non furono trattate come segnale da approfondire.
4. Nessun cross-check indipendente fu imposto sulla misura più critica del programma.

## Aggancio al deliverable
Tocca direttamente la sezione **8 — Indipendenza delle verifiche critiche** del [[Template - Verification Plan|Verification Plan]]: è esattamente la clausola che, se applicata, avrebbe imposto la ridondanza mancante.

## Fonte
Riferirsi al report d'inchiesta ufficiale (Allen Board, 1990), non a riassunti divulgativi che tendono a descriverlo come errore di lavorazione anziché di processo.
