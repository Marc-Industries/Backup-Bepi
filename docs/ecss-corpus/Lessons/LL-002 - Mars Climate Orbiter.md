---
type: lesson
id: LL-002
caso: Mars Climate Orbiter — mismatch di unità di misura
programma: MCO / NASA, 1999
cosa_successe: Il software di terra produceva impulsi in unità imperiali (libbra-forza·secondo) mentre la navigazione li attendeva in unità metriche (newton·secondo). L'errore di traiettoria portò la sonda troppo in basso nell'atmosfera marziana e ne causò la distruzione.
causa_radice: Disallineamento di unità a un'interfaccia software tra due team (Lockheed Martin e JPL), non intercettato da una verifica end-to-end né da un controllo di interfaccia formale. Radice di INTERFACE MANAGEMENT e verifica integrata.
ecss: [E-ST-10-02, E-ST-10-24]
drd: [Verification Plan, Interface Control Document, System Engineering Plan]
lesson: Le convenzioni condivise a un'interfaccia (unità, formati, riferimenti) vanno dichiarate, verificate end-to-end e non assunte. Un ICD non controllato è un fallimento latente.
fonte: "Mars Climate Orbiter Mishap Investigation Board — Phase I Report (NASA, 1999)"
tags: [lesson, anti-pattern, interface-management, verification]
---

# LL-002 — Mars Climate Orbiter, mismatch di unità

## Sintesi
Sonda persa per un disallineamento di unità a un'interfaccia software tra due team, mai catturato da una verifica integrata.

## Catena causale
1. Due team usavano unità diverse per la stessa grandezza fisica (impulso).
2. L'assunzione non fu mai esplicitata né verificata all'interfaccia.
3. Mancò una verifica end-to-end che avrebbe mostrato l'incoerenza.

## Aggancio al deliverable
Tocca tre documenti: il [[Template - Verification Plan|Verification Plan]] (verifica integrata end-to-end), l'**Interface Control Document** (dichiarazione e controllo delle convenzioni di interfaccia) e il [[Template - System Engineering Plan|System Engineering Plan]], il cui DRD alla clausola 4.1.e prescrive esplicitamente di **definire il sistema di unità del progetto**. Compare quindi in tutti e tre i template.

## Fonte
Phase I Report del Mishap Investigation Board (NASA, 1999).
