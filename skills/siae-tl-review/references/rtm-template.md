# Template RTM — Requirements Traceability Matrix

> Riferimento operativo per la **FASE 3** della skill `siae-tl-review`. Leggere
> quando: bisogna generare la RTM, definire il livello di copertura, o
> mostrare un esempio "fatto bene" all'utente.

## 1. Cos'e' una RTM (e perche' bidirezionale)

La Requirements Traceability Matrix (RTM) e' lo strumento ISTQB / IEEE 829 per
**dimostrare** che ogni requisito ha almeno un test che lo verifica e
viceversa. La bidirezionalita' e' cruciale:

- **Forward traceability** (Requisito → TC): garantisce che nessun requisito
  sia non testato.
- **Backward traceability** (TC → Requisito): individua TC orfani (test
  obsoleti o requisiti impliciti non documentati).

Una RTM unidirezionale e' un mezzo strumento: nasconde meta' dei rischi.

## 2. Template tabellare obbligatorio

### 2.1 Vista forward (Requisito → TC)

```markdown
| ID Req | Descrizione Requisito | AC | TC Correlati (ID TL) | Tipo Copertura | Gap |
|--------|-----------------------|----|----|----------------|-----|
```

Una **riga per ogni AC** (non per ogni requisito) — un requisito con 3 AC
genera 3 righe.

### 2.2 Vista inversa (TC → Requisito)

```markdown
| TC ID | Mappato a (Req.AC) | Note |
|-------|--------------------|------|
```

Una **riga per ogni TC** della TL. I TC non mappati a nessun requisito sono
flaggati come orfani.

## 3. Legenda `Tipo Copertura`

| Simbolo | Significato | Quando usarlo |
|---------|-------------|---------------|
| `Happy Path ✅` | Flusso principale coperto | Almeno 1 TC eseguibile manualmente copre l'AC nel suo percorso "felice" (input valido, utente autorizzato, sistema in stato nominale). |
| `Edge Case ⚠️`  | Caso limite coperto | Coperto da BVA (Boundary Value Analysis): valori minimi/massimi, lunghezze stringhe, date al confine, etc. |
| `Caso Negativo ❌` | Flusso di errore coperto | Coperto da EP (Equivalence Partitioning) classe invalida: input rifiutato, permesso negato, timeout. |
| `Non Coperto 🔴` | Nessun TC eseguibile per questo AC | Gap critico — emerge in sezione 4 del report finale. |
| `Coperto ma NON ESEGUIBILE 🟠` | Esiste un TC, ma flaggato `NON ESEGUIBILE MANUALMENTE` (G4) | Conta come gap effettivo. |

## 0. Nota normativa — deduzioni e casi inventati

**Gli esempi nelle sezioni seguenti mostrano AC e TC derivati esclusivamente
da requisiti espliciti nel materiale fornito.** Non usare questi esempi come
legittimazione per dedurre TC non ancorati a requisiti reali.

Regola operativa (G2): se un AC non e' nel materiale fornito, il campo AC
nella RTM riporta `"Non verificabile dal materiale"` e il campo Gap riporta
`"AC mancante — richiede conferma con il team"`. NON inventare un AC
"plausibile" per completare la riga.

I valori soglia presenti nell'esempio compilato (sezione 4) — es. "15 minuti
di blocco", "link scade dopo 1h" — sono puramente dimostrativi. Non devono
essere mutuati in RTM reali senza conferma esplicita nei requisiti di progetto.
Ogni AC nella RTM deve citare la fonte (`Jira BTP-NNN`, `Doc §X`, `Chat
R-NN`) che lo rende verificabile.

---

## 4. Esempio completo compilato

### Scenario

- **Requisiti** (estratti da Jira `BTP-101..BTP-103`):
  - `R-01` — Login utente con username + password.
  - `R-02` — Recupero password via email.
  - `R-03` — Logout con invalidazione sessione.
- **TC** (dalla TL `SIAE_BTP_TestList_ClusterArancione.csv`):
  - `TC-001` — Login OK (happy path).
  - `TC-002` — Login KO password errata.
  - `TC-003` — Login KO username non esistente.
  - `TC-004` — Logout standard.
  - `TC-005` — "Verifica scadenza sessione via query DB `SELECT * FROM
    sessions WHERE ...`" → **NON ESEGUIBILE MANUALMENTE**.

### 4.1 Vista forward

```markdown
| ID Req | Descrizione | AC | TC Correlati | Tipo Copertura | Gap |
|--------|-------------|----|----|----------------|-----|
| R-01   | Login con username+password | AC-1: credenziali valide → dashboard | TC-001 | Happy Path ✅ | Nessuno |
| R-01   | Login con username+password | AC-2: password errata → messaggio errore | TC-002 | Caso Negativo ❌ | Nessuno |
| R-01   | Login con username+password | AC-3: username inesistente → messaggio errore | TC-003 | Caso Negativo ❌ | Nessuno |
| R-01   | Login con username+password | AC-4: 5 tentativi falliti → account bloccato 15min | (nessuno) | Non Coperto 🔴 | Manca TC per rate limiting |
| R-02   | Recupero password via email | AC-1: invio link reset | (nessuno) | Non Coperto 🔴 | TC mancante completamente |
| R-02   | Recupero password via email | AC-2: link scade dopo 1h | (nessuno) | Non Coperto 🔴 | TC mancante completamente |
| R-03   | Logout invalida sessione | AC-1: click "Logout" → torna a login | TC-004 | Happy Path ✅ | Nessuno |
| R-03   | Logout invalida sessione | AC-2: cookie sessione invalidato server-side | TC-005 | Coperto ma NON ESEGUIBILE 🟠 | TC-005 richiede query DB. Riformulazione UI proposta: dopo logout, copia URL dashboard in nuova tab → deve redirigere a login |
```

### 4.2 Vista inversa

La colonna Note aggrega tutti i flag emersi dalla Fase 4 (aggiornata a fine F4,
non alla produzione iniziale della RTM). Regola: cella vuota = nessuna evidenza;
piu' evidenze separate da ` | `.

```markdown
| TC ID | Mappato a | Note |
|-------|-----------|------|
| TC-001 | R-01.AC-1 | |
| TC-002 | R-01.AC-2 | |
| TC-003 | R-01.AC-3 | |
| TC-004 | R-03.AC-1 | |
| TC-005 | R-03.AC-2 | ❌ NON ESEGUIBILE — query DB diretta | ⚠️ Step incompleti — step 2 |
| TC-099 | (nessuno)  | ⚠️ TC orfano — verificare se R-04 mancante o test obsoleto |
```

## 5. Calcolo della copertura

Nel report finale (Fase 5, sezione 3) usa queste metriche:

```
Coverage Happy Path = (# AC con almeno 1 TC Happy Path eseguibile) / (# AC totali) * 100
Coverage Edge Case  = (# AC con almeno 1 TC Edge Case eseguibile) / (# AC con edge case identificati) * 100
Coverage Negativi   = (# AC con almeno 1 TC Negativo eseguibile)  / (# AC con scenari negativi identificati) * 100
```

**Importante:** i TC `🟠` (non eseguibili) NON contano nel numeratore.
Mostrarli separatamente nella sezione gap.

Per l'esempio precedente:
- Happy Path: 2/8 AC = **25%** (R-01.AC-1, R-03.AC-1).
- Casi Negativi: 2/4 AC negativi = **50%** (R-01.AC-2, R-01.AC-3 coperti;
  R-01.AC-4, R-03.AC-2 no).
- Gap critici: 4 AC `Non Coperto 🔴`, 1 AC `🟠`.

## 6. Convenzioni di naming

- **Requisiti**: `R-NN` (2 cifre con padding zero), oppure usa l'ID Jira nativo
  (`BTP-123`) se piu' tracciabile per l'utente.
- **AC**: `AC-N` come suffisso del requisito → riferimento composito
  `R-01.AC-2`.
- **TC**: usa l'ID nativo della TL (`TC-001`, `TC-A045`, etc.) — non
  rinominare.

## 7. Salvataggio della RTM

Quando l'utente conferma la RTM in Fase 3, **salvala** in:

```
./QA-REVIEW/<nome-file-TL>/rtm-<YYYY-MM-DD>.md
```

dove `<nome-file-TL>` e' il nome del file TL senza estensione (es.
`SIAE_BTP_TestList_ClusterArancione`). Se e' stato applicato un filtro di
scope (G9), aggiungere il suffisso: `<nome-file-TL>__<filtro>/`.

Path relativo al **current working directory**. La skill crea la directory
on-demand con `mkdir -p`.

**Anchor header obbligatorio:** ogni requisito nella RTM deve avere un header
Markdown di livello 3 che lo precede, in modo da essere linkabile dal report:

```markdown
### R-01
| R-01 | Login con username+password | AC-1 | ... |
```

Questo consente al report finale di usare `[R-01](rtm-<data>.md#r-01)` per
cross-link diretto.

Se esiste gia' un file con la stessa data, chiedere se sovrascrivere o usare
suffisso orario `-<HHmm>`.

**G8:** nessuna credenziale, PAT o secret in chiaro in questo file.
