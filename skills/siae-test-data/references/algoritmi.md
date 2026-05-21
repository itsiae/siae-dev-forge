# Algoritmi — Calcolo CF, P.IVA, validazioni

Questo file e' la **single source of truth** per gli algoritmi della skill.
Tutti i calcoli sono pensati per essere eseguiti **direttamente da Claude** (lettura
file + ragionamento step-by-step), senza richiedere runtime Python locale.
Gli script Python in `scripts/` sono una scorciatoia opzionale per dataset grandi.

---

## 1. Codice Fiscale persona fisica (16 caratteri)

### Struttura
```
[3 cogn][3 nome][2 anno][1 mese][2 giorno][4 belfiore][1 checksum]
```

### Step 1 — Codice cognome (3 char)

```
1. Maiuscolo + rimuovi accenti + tieni solo lettere A-Z
2. Estrai consonanti in ordine, poi vocali in ordine
3. Concatena: prime_3_consonanti + vocali + "XXX"
4. Tronca a 3 caratteri
```

Esempi:
- "Rossi" -> consonanti `RSS`, vocali `OI` -> **RSS**
- "Bo" -> consonanti `B`, vocali `O` -> `BO` + `XXX` -> **BOX**
- "D'Angelo" -> normalizzato `DANGELO` -> cons `DNGL`, voc `AEO` -> **DNG**

### Step 2 — Codice nome (3 char)

```
1. Maiuscolo + rimuovi accenti + tieni solo lettere A-Z
2. Estrai consonanti in ordine
3. SE numero consonanti >= 4: prendi 1a, 3a, 4a
   ALTRIMENTI: prime_3_consonanti + vocali + "XXX", tronca a 3
```

Esempi:
- "Mario" -> cons `MR` (solo 2), voc `AIO` -> `MR` + `AIO` + `XXX` -> **MRA**
- "Francesco" -> cons `FRNCSC` (6, >=4) -> F(1) N(3) C(4) -> **FNC**
- "Giulia" -> cons `GL` (2), voc `IUIA` -> `GL` + `IUIA` -> **GLI**

### Step 3 — Anno (2 cifre)

Ultime 2 cifre dell'anno di nascita.
- 1985 -> **85**
- 2003 -> **03**

### Step 4 — Mese (1 lettera)

Tabella ufficiale:
```
Gen=A  Feb=B  Mar=C  Apr=D  Mag=E  Giu=H
Lug=L  Ago=M  Set=P  Ott=R  Nov=S  Dic=T
```

### Step 5 — Giorno (2 cifre)

```
SE genere = "F": giorno + 40  (zero-padding: 01 -> 41, 15 -> 55)
ALTRIMENTI: giorno (zero-padding: 01 -> 01, 15 -> 15)
```

### Step 6 — Codice catastale Belfiore (4 char)

Lookup in `references/belfiore_comuni.json` per nati in Italia,
oppure in `references/belfiore_esteri.json` per nati all'estero.

Esempi:
- Roma -> **H501**
- Milano -> **F205**
- Germania -> **Z112**
- Francia -> **Z110**

### Step 7 — Checksum (1 lettera)

I primi 15 caratteri vengono numerati partendo da 1. Le **posizioni dispari**
(1, 3, 5, ..., 15) usano la tabella `DISPARI`, le **pari** (2, 4, ..., 14)
usano la tabella `PARI`. Si sommano i valori; il modulo 26 mappa su A-Z.

#### Tabella DISPARI

```
0->1   1->0   2->5   3->7   4->9   5->13  6->15  7->17  8->19  9->21
A->1   B->0   C->5   D->7   E->9   F->13  G->15  H->17  I->19  J->21
K->2   L->4   M->18  N->20  O->11  P->3   Q->6   R->8   S->12  T->14
U->16  V->10  W->22  X->25  Y->24  Z->23
```

#### Tabella PARI

```
0->0   1->1   2->2   3->3   4->4   5->5   6->6   7->7   8->8   9->9
A->0   B->1   C->2   D->3   E->4   F->5   G->6   H->7   I->8   J->9
K->10  L->11  M->12  N->13  O->14  P->15  Q->16  R->17  S->18  T->19
U->20  V->21  W->22  X->23  Y->24  Z->25
```

#### Mapping modulo -> char

```
0->A 1->B 2->C 3->D 4->E 5->F 6->G 7->H 8->I 9->J 10->K 11->L 12->M
13->N 14->O 15->P 16->Q 17->R 18->S 19->T 20->U 21->V 22->W 23->X 24->Y 25->Z
```

### Esempio completo end-to-end

**Input**: Mario Rossi, 01/01/1985, M, nato a Roma

1. Cognome `Rossi` -> consonanti `RSS` -> **RSS**
2. Nome `Mario` -> consonanti `MR` (<4), voc `AIO` -> `MRAIO` -> **MRA**
3. Anno `1985` -> **85**
4. Mese 01 -> **A**
5. Giorno M 01 -> **01**
6. Roma -> **H501**
7. Parziale: `RSSMRA85A01H501`

   Calcolo checksum:
   | pos | char | tipo | valore |
   |-----|------|------|--------|
   | 1   | R    | disp | 8      |
   | 2   | S    | pari | 18     |
   | 3   | S    | disp | 12     |
   | 4   | M    | pari | 12     |
   | 5   | R    | disp | 8      |
   | 6   | A    | pari | 0      |
   | 7   | 8    | disp | 19     |
   | 8   | 5    | pari | 5      |
   | 9   | A    | disp | 1      |
   | 10  | 0    | pari | 0      |
   | 11  | 1    | disp | 0      |
   | 12  | H    | pari | 7      |
   | 13  | 5    | disp | 13     |
   | 14  | 0    | pari | 0      |
   | 15  | 1    | disp | 0      |

   Somma = 103. 103 % 26 = 25 -> **Z**

**CF finale**: `RSSMRA85A01H501Z`

---

## 2. Partita IVA italiana (11 cifre)

### Struttura
```
[7 progressivo][3 provincia ISTAT][1 checksum]
```

### Step 1 — Progressivo
7 cifre numeriche, scelte casualmente (es. `1234567`).

### Step 2 — Codice provincia ISTAT
3 cifre da `references/forme_giuridiche.json` chiave `_codici_provincia_istat`.
Esempi: RM -> `001`, MI -> `002`, NA -> `003`.

### Step 3 — Checksum (Luhn-AdE)

```
parziale_10 = progressivo + codice_provincia
somma = 0
for i, cifra in enumerate(parziale_10, start=1):
    d = int(cifra)
    if i % 2 == 0:        # posizione pari (la 2a, 4a, ...)
        d *= 2
        if d > 9:
            d -= 9
    somma += d
checksum = (10 - somma % 10) % 10
piva = parziale_10 + str(checksum)
```

### Esempio
- Progressivo `1234567`, provincia RM (`001`) -> parziale `1234567001`
- Posizioni dispari (i=1,3,5,7,9): 1+3+5+7+0 = 16
- Posizioni pari (i=2,4,6,8,10): 2->4, 4->8, 6->3 (12-9), 0->0, 1->2 -> 4+8+3+0+2 = 17
- Somma totale: 33
- Checksum: (10 - 33%10) % 10 = (10-3) % 10 = **7**
- P.IVA: **12345670017**

---

## 3. Data di nascita serial Excel

Excel rappresenta le date come numero di giorni dal `1899-12-30`, ma con un
**bug storico**: considera il 1900 come anno bisestile. Per date >= 1900-03-01
il calcolo combacia con `(data - 1899-12-30).days`.

### Conversione data -> serial
```
delta = (data - date(1899, 12, 30)).days
SE data >= 1900-03-01: serial = delta
ALTRIMENTI:            serial = delta - 1
```

### Conversione serial -> data
```
SE serial < 60: data = date(1899, 12, 30) + (serial + 1) giorni
ALTRIMENTI:     data = date(1899, 12, 30) + serial giorni
```

### Esempi
- `1985-01-01` -> serial `31048`
- `1990-06-15` -> serial `33039`
- `2003-02-01` -> serial `37653`

---

## 4. Vincoli CF / P.IVA per forma giuridica

| Codice | CF | P.IVA | Vincolo (sede ITA) | Sede estera |
|--------|----|----|--------------------|-------------|
| DI     | 16 char personali titolare | 11 cifre | CF ≠ P.IVA | VAT, no P.IVA |
| ENTEP  | 11 cifre numerico         | 11 cifre obb. | indipendenti | VAT |
| ENTE   | 10 cifre numerico         | opzionale | indipendenti | VAT |
| IST    | 10 cifre numerico         | opzionale | indipendenti | VAT |
| ONP    | 10 cifre numerico         | opzionale | indipendenti | VAT |
| COOP   | 11 cifre                  | 11 cifre obb. | **CF = P.IVA** | VAT |
| SDC    | 11 cifre                  | 11 cifre obb. | **CF = P.IVA** | VAT |
| SDP    | 11 cifre                  | 11 cifre obb. | **CF = P.IVA** | VAT |

Per **sede estera**: la P.IVA italiana non si applica; sostituita da `vat_number`
formato `<2 lettere stato><cifre>` (es. `DE123456789`, `FR12345678901`).

---

## 5. Coerenza CAP <-> Citta <-> Provincia

Per ogni indirizzo italiano DEVE valere:
- `cap` ∈ `cap_citta.json["Italia"][citta]["cap_pool"]`
- `provincia` == `cap_citta.json["Italia"][citta]["provincia"]`
- `stato` == "Italia"

Per indirizzi esteri:
- `citta` ∈ `cap_citta.json["Estero"][stato]["citta_pool"]`
- `cap` accoppiato all'indice della citta (idx parallelo nei due array)
- `provincia` = "—"

---

## 6. Formato telefono E.164

```
+<prefisso_internazionale> <cifre_locali>
```

- Italia (`+39`): 10 cifre, formato cellulare `3XX YYYYYYY` (es. `+39 3331112233`)
- Estero: prefisso paese da `belfiore_esteri.json["<stato>"]["prefisso_telefonico"]`

---

## 7. Edge case indirizzo italiano

Pattern supportati (campo `civico` o `via` formattato):

| Pattern | Esempio |
|---------|---------|
| `SNC` | `VIA degli Orti SNC` |
| `ALFANUM_SLASH` | `VIA della Vigna Nuova 10/A` |
| `BIS` | `CORSO Francia 22bis` |
| `TER` | `VIA Appia Nuova 15ter` |
| `KM_PROGRESSIVO_PLUS` | `STRADA STATALE 18 Tirrena Inferiore km 12+500` |
| `KM_VIRGOLA` | `STRADA PROVINCIALE 231 km 3,200` |
| `RANGE_DOPPIO` | `VIALE della Repubblica 110-112` |
| `BILINGUE_DE` | `VIA / STRASSE dei Vigneti / Weinbergweg 8/B` (Bolzano, CAP 39100) |
| `INTERNO` | `TRAVERSA San Giovanni 3 int. 5` |
| `SCALA_PIANO` | `VIA XX Settembre 100 scala B piano 3` |
| `ZONA_INDUSTRIALE` | `ZONA INDUSTRIALE ASI Marcianise lotto 14` (Marcianise CE 81025) |
| `FRAZIONE` | `FRAZIONE Rometta SNC` |
| `AUTOSTRADA_KM` | `AUTOSTRADA A3 km 42` |
| `CONTRADA_SNC` | `CONTRADA Muoio Piccolo SNC` (tipico Sud Italia) |

---

## 8. Pool nomi e cognomi

- `nomi_italiani.json`: pool ISTAT (30 maschili, 30 femminili, 50+ cognomi)
- `nomi_esteri.json`: 9 nazionalita coperte (DE, FR, ES, UK, JP, RO, PL, US, CH)

Scegliere il pool in base a `cittadinanza` / `stato_nascita`.
