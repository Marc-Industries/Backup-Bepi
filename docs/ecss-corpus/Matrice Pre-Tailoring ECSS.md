---
type: riferimento
titolo: Matrice di pre-tailoring ECSS (Table 7-2)
fonte: "ECSS-E-ST-10C Rev.1 (15 February 2017), clausola 7, Table 7-2"
---

# Matrice di pre-tailoring — ECSS-E-ST-10C Rev.1

> [!info] Cos'è
> ECSS ha **già fatto un primo tailoring** dei requisiti di E-ST-10 per nove tipi di prodotto spaziale. Questa nota riporta la Table 7-2 e, soprattutto, isola i **punti in cui la decisione spetta a te**.

> [!abstract] Legenda (Table 7-1)
> | Simbolo | Significato |
> |---|---|
> | `X` | applicabile |
> | `-` | non applicabile |
> | `//` | **applicabilità non definibile a priori — da decidere in fase di tailoring** |
> | `>>` | applicabile a un tipo di prodotto di livello inferiore; il tailoring è responsabilità del cliente di quel livello |
> | `X#` / `//#` | come sopra, ma con condizioni specifiche nella colonna Comments dello standard |
>
> Un requisito è considerato applicabile a un tipo di prodotto **se è verificato su quel tipo di prodotto**.

> [!warning] Ground segment e Software: colonne vuote
> Nella Table 7-2 le colonne Ground segment e Software sono tutte `-`. Non è una svista: ECSS considera **ECSS-E-ST-70** (ground systems and operations), **ECSS-E-ST-40** (software) e **ECSS-Q-ST-80** (software PA) **pienamente sufficienti** per lo sviluppo di questi item. Se lavori su quei domini, il tuo standard di riferimento è un altro.

---

## Il dato che conta: quanti punti decisionali hai

Il carico di tailoring cambia drasticamente col livello di prodotto:

| Tipo di prodotto | Applicabili `X` | **Da decidere `//`** | Non applicabili `-` |
|---|---|---|---|
| Space system | 99 | **0** | 1 |
| Space segment element/sub-system | 84 | **15** | 1 |
| Space segment equipment | 29 | **66** | 5 |
| Launch segment element/sub-system | 56 | **44** | 0 |
| Launch segment equipment | 8 | **19** | 73 |
| Ground segment element/sub-system | — | — | 100 (coperto da altri standard) |
| Ground segment equipment | — | — | 100 (coperto da altri standard) |
| Ground support equipment | — | — | 99 (coperto da altri standard) |
| Software | — | — | 99 (coperto da altri standard) |

> [!tip] Come leggerla
> A livello **Space system** non c'è nulla da decidere: si applica tutto. Scendendo verso l'**equipment**, la maggior parte dei requisiti diventa `//` — cioè il tailoring è quasi interamente lavoro tuo. È lì che questo layer ti fa risparmiare tempo vero.

---

## Punti di decisione per tipo di prodotto

Sono le celle `//`: i requisiti su cui **lo standard non decide per te**. Per ogni progetto vanno risolti in applicabile / non applicabile / modificato, e la decisione va motivata e tracciata (vedi [[Tailoring - Template Progetto]]).

Il criterio ricorrente suggerito dallo standard nei Comments è: *product heritage, complessità ingegneristica e contesto di industrializzazione*.


### Space segment element/sub-system — 15 decisioni

`5.2.1d` · `5.2.3.7a` · `5.3.1e` · `5.3.1i` · `5.3.4a` · `5.3.4b` · `5.3.4c` · `5.3.4d` · `5.3.4e` · `5.3.4f` · `5.4.1.1d` · `5.4.1.1e` · `5.4.1.3b` · `5.4.1.3c` · `5.4.1.3e`


### Space segment equipment — 66 decisioni

`5.1a` · `5.1d` · `5.2.1d` · `5.2.1e` · `5.2.3.2a` · `5.2.3.2b` · `5.2.3.3b` · `5.2.3.3c` · `5.2.3.4a` · `5.2.3.4b` · `5.2.3.8a` · `5.2.3.9a` · `5.3.1b` · `5.3.1c` · `5.3.1d` · `5.3.1e` · `5.3.1f` · `5.3.1g` · `5.3.1h` · `5.3.2a` · `5.3.2b` · `5.3.2d` · `5.3.2e` · `5.3.3a` · `5.3.3b` · `5.3.4a` · `5.3.4b` · `5.3.4c` · `5.3.4d` · `5.3.4e` · `5.3.4f` · `5.3.4g` · `5.3.4h` · `5.4.1.1a` · `5.4.1.1b` · `5.4.1.1d` · `5.4.1.1e` · `5.4.1.1f` · `5.4.1.3a` · `5.4.1.3b` · `5.4.1.3c` · `5.4.1.3d` · `5.4.1.3e` · `5.4.1.3f` · `5.4.1.4a` · `5.4.1.4b` · `5.4.2.1a` · `5.4.2.1c` · `5.4.2.2a` · `5.4.2.3a` · `5.5.2c` · `5.5.2f` · `5.6.1a` · `5.6.1f` · `5.6.1g` · `5.6.2a` · `5.6.3a` · `5.6.3b` · `5.6.3c` · `5.6.5a` · `5.6.5b` · `5.6.8a` · `5.6.8c` · `5.6.9a` · `5.6.9b` · `5.6.9c`


### Launch segment element/sub-system — 44 decisioni

`5.1a` · `5.1c` · `5.1d` · `5.2.1d` · `5.2.3.1b` · `5.2.3.5a` · `5.2.3.7a` · `5.3.1a` · `5.3.1e` · `5.3.1i` · `5.3.2b` · `5.3.2c` · `5.3.2d` · `5.3.3c` · `5.3.4a` · `5.3.4b` · `5.3.4c` · `5.3.4d` · `5.3.4e` · `5.3.4f` · `5.4.1.1d` · `5.4.1.1e` · `5.4.1.2b` · `5.4.1.3a` · `5.4.1.3b` · `5.4.1.3c` · `5.4.1.3d` · `5.4.1.3e` · `5.4.1.3f` · `5.4.1.4a` · `5.4.1.4b` · `5.4.1.4c` · `5.5.1a` · `5.5.2b` · `5.5.2c` · `5.5.2f` · `5.6.1a` · `5.6.2a` · `5.6.3a` · `5.6.3b` · `5.6.3c` · `5.6.5a` · `5.6.5b` · `5.6.8c`


### Launch segment equipment — 19 decisioni

`5.2.1e` · `5.2.3.2a` · `5.2.3.2b` · `5.2.3.3b` · `5.2.3.3c` · `5.2.3.4a` · `5.2.3.4b` · `5.2.3.5a` · `5.2.3.8a` · `5.2.3.9a` · `5.3.1b` · `5.3.1c` · `5.3.1d` · `5.3.1e` · `5.3.1f` · `5.3.1g` · `5.3.1h` · `5.3.3b` · `5.4.1.1b`


---

## Matrice completa (Table 7-2)

Legenda colonne: **Sys** = Space system · **SS-el** = Space segment element/sub-system · **SS-eq** = Space segment equipment · **LS-el** = Launch segment element/sub-system · **LS-eq** = Launch segment equipment · **GS-el/GS-eq/GSE/SW** = Ground segment, ground support equipment, software

| Req. | Sys | SS-el | SS-eq | LS-el | LS-eq | GS-el | GS-eq | GSE | SW |
|---|---|---|---|---|---|---|---|---|---|
| **5.1a** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.1c** | X | X1 | - | //2 | - | - | - | - | - |
| **5.1d** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.2.1a** | X | X | X | X | - | - | - | - | - |
| **5.2.1b** | X | X | X1 | X | - | - | - | - | - |
| **5.2.1c** | X | X | X1 | X | - | - | - | - | - |
| **5.2.1d** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.2.1e** | X | X | //1 | X | //1 | - | - | - | - |
| **5.2.2a** | X | X | X1 | X | - | - | - | - | - |
| **5.2.2b** | X | X | X1 | X | - | - | - | - | - |
| **5.2.2c** | X | X | X | X | - | - | - | - | - |
| **5.2.3.1a** | X | X | X1 | X | - | - | - | - | - |
| **5.2.3.1b** | X | X | X1 | // | - | - | - | - | - |
| **5.2.3.1c** | X | X | X1 | X | X1 | - | - | - | - |
| **5.2.3.2a** | X | X | //1 | X | //1 | - | - | - | - |
| **5.2.3.2b** | X | X | //1 | X | //1 | - | - | - | - |
| **5.2.3.3b** | X | X | //1 | X | //1 | - | - | - | - |
| **5.2.3.3c** | X | X | //1 | X | //1 | - | - | - | - |
| **5.2.3.4a** | X | X | //1 | X | //1 | - | - | - | - |
| **5.2.3.4b** | X | X | //1 | X | //1 | - | - | - | - |
| **5.2.3.5a** | X | X | X1 | // | //2 | - | - | - | - |
| **5.2.3.7a** | X | // | - | // | - | - | - | ? | ? |
| **5.2.3.8a** | X | X | //1 | X | //1 | - | - | - | - |
| **5.2.3.9a** | X | X | //1 | X | //1 | - | - | - | - |
| **5.3.1a** | X | - | - | //1 | - | - | - | - | - |
| **5.3.1b** | X | X1 | //2 | X1 | //2 | - | - | - | - |
| **5.3.1c** | X | X | //2 | X1 | //2 | - | - | - | - |
| **5.3.1d** | X | X | //2 | X1 | //2 | - | - | - | - |
| **5.3.1e** | X | //1 | //1 | //1 | //1 | - | - | - | - |
| **5.3.1f** | X | X | //2 | X1 | //2 | - | - | - | - |
| **5.3.1g** | X | X | //2 | X1 | //2 | - | - | - | - |
| **5.3.1h** | X | X | //2 | X1 | //2 | - | - | - | - |
| **5.3.1i** | X | //1 | - | //1 | - | - | - | - | - |
| **5.3.1j** | X1 | X1 | X1 | X | - | - | - | - | - |
| **5.3.2a** | X | X | //2 | X1 | - | - | - | - | - |
| **5.3.2b** | X | X | //1 | // | - | - | - | - | - |
| **5.3.2c** | X1 | X1 | X1 | // | - | - | - | - | - |
| **5.3.2d** | X | X | //1 | // | - | - | - | - | - |
| **5.3.2e** | X | X | //2 | X1 | - | - | - | - | - |
| **5.3.3a** | X | X | //2 | X1 | - | - | - | - | - |
| **5.3.3b** | X | X | //2 | X1 | //2 | - | - | - | - |
| **5.3.3c** | X | X | - | //1 | - | - | - | - | - |
| **5.3.4a** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.3.4b** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.3.4c** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.3.4d** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.3.4e** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.3.4f** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.3.4g** | X | X | //2 | X1 | - | - | - | - | - |
| **5.3.4h** | X | X | //2 | X1 | - | - | - | - | - |
| **5.4.1.1a** | X | X | //2 | X1 | - | - | - | - | - |
| **5.4.1.1b** | X | X | //2 | X1 | //2 | - | - | - | - |
| **5.4.1.1c** | X | X | X1 | X | - | - | - | - | - |
| **5.4.1.1d** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.4.1.1e** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.4.1.1f** | X | X | //2 | X1 | - | - | - | - | - |
| **5.4.1.2a** | X | X | X | X | - | - | - | - | - |
| **5.4.1.2b** | X | X | X1 | // | - | - | - | - | - |
| **5.4.1.2c** | X | X | X | X | - | - | - | - | - |
| **5.4.1.3a** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.4.1.3b** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.4.1.3c** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.4.1.3d** | X | X1 | //2 | // | - | - | - | - | - |
| **5.4.1.3e** | X | //1 | //1 | //1 | - | - | - | - | - |
| **5.4.1.3f** | X | X1 | //2 | // | - | - | - | - | - |
| **5.4.1.4a** | X | X | //1 | // | - | - | - | - | - |
| **5.4.1.4b** | X | X | //1 | // | - | - | - | - | - |
| **5.4.1.4c** | - | X | X1 | // | - | - | - | - | - |
| **5.4.2.1a** | X | X | //1 | X | - | - | - | - | - |
| **5.4.2.1b** | X | X | X1 | X | - | - | - | - | - |
| **5.4.2.1c** | X | X | //1 | X | - | - | - | - | - |
| **5.4.2.2a** | X | X | //1 | X | - | - | - | - | - |
| **5.4.2.3a** | X | X | //1 | X | - | - | - | - | - |
| **5.5.1a** | X | X | X | // | - | - | - | - | - |
| **5.5.2b** | X | X | X | // | - | - | - | - | - |
| **5.5.2c** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.5.2d** | X | X | X | X | - | - | - | - | - |
| **5.5.2f** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.1a** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.1f** | X | X | //2 | X1 | - | - | - | - | - |
| **5.6.1g** | X | X | //2 | X1 | - | - | - | - | - |
| **5.6.2a** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.3a** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.3b** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.3c** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.4a** | X | X | X1 | X | - | - | - | - | - |
| **5.6.5a** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.5b** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.7a** | X | X | X | X | X | - | - | - | - |
| **5.6.7b** | X | X | X | X | X | - | - | - | - |
| **5.6.7c** | X | X | X | X | X | - | - | - | - |
| **5.6.7d** | X | X | X | X | X | - | - | - | - |
| **5.6.7e** | X | X | X | X | X | - | - | - | - |
| **5.6.7f** | X | X | X | X | X | - | - | - | - |
| **5.6.7g** | X | X | X | X | X | - | - | - | - |
| **5.6.8a** | X | X | //1 | X | - | - | - | - | - |
| **5.6.8c** | X | X1 | //2 | //2 | - | - | - | - | - |
| **5.6.9a** | X | X | //1 | X | - | - | - | - | - |
| **5.6.9b** | X | X | //1 | X | - | - | - | - | - |
| **5.6.9c** | X | X | //1 | X | - | - | - | - | - |

---

*Fonte: ECSS-E-ST-10C Rev.1, clausola 7, Table 7-2. I suffissi numerici (`X1`, `//2`) rimandano alla colonna Comments dello standard: consultare il PDF originale per il testo esatto della condizione.*
