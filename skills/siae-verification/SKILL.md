---
name: siae-verification
description: >
  Use when verifying that a fix or change is complete BEFORE declaring it done.
  Forces evidence-based verification (run tests, check output, confirm behaviour)
  prima di commit, PR, task complete declarations. **Best after**: siae-debugging
  completed (Phase 4 fix applied) OR siae-tdd cycle done (Red-Green-Refactor).
  Trigger: "il fix funziona", "test passano", "ho finito", "tutto ok",
  "completato", "implementato", "fatto", "fixato", "pronto", "risolto",
  "build verde", "funziona", "finito".
validates_via:
  predicate: verification_run_passed
  evidence_type: log_event
  evidence_check: "DEVFORGE_LOG_FILE contains verification_run event with exit=0 for current sid"
---

# SIAE Verification — Protocollo di Verifica Pre-Completamento

> **Tipo:** Rigid | **Fase SDLC:** Cross-cutting (tutte le fasi)

## LA LEGGE DI FERRO

```
NESSUN CLAIM DI COMPLETAMENTO SENZA EVIDENZA FRESCA
```

<EXTREMELY-IMPORTANT>
Affermare che il lavoro e' completo senza verifica e' disonesta', non efficienza.
Questa skill si applica nei contesti rilevanti — vedi sezione **Eccezioni & proporzionalita'**
per la matrice scaled (typo/comment/doc → check minimi; feature nuova → full battery).
</EXTREMELY-IMPORTANT>

## Context-First Rule (canonical)

Prima di leggere file, eseguire comandi, o fare domande all'utente,
verifica se l'informazione e' gia' presente nella conversazione corrente
(messaggi precedenti, output di tool, skill gia' invocate).
Non chiedere cio' che e' gia' stato detto. Non rileggere cio' che e' gia' stato letto.
Questa regola e' riferita da tutte le altre skill DevForge — qui e' la versione autoritativa.

## Quando si Applica

**SEMPRE** prima di: dichiarare un task "completato"/"fatto", creare un commit, aprire/aggiornare una PR,
dire "funziona"/"fixato"/"passano"/"pronto", qualsiasi affermazione di successo.
Se stai per dire una di queste cose, **considera di fermarti** e segui i 5 step
(o la versione scaled in **Eccezioni & proporzionalita'** per cambi triviali).

## Eccezioni & proporzionalita'

La verifica deve essere **proporzionata al rischio del cambio**. Non tutti i cambi richiedono full battery di test.

| Tipo cambio | Verifica richiesta |
|---|---|
| Typo fix in commento o doc | Sintassi check (no test funzionali) |
| Comment-only change | Diff review, no test |
| Doc update (README, CHANGELOG) | Lint markdown, no test |
| Config rename (no semantic change) | Smoke test feature interessata |
| Bug fix isolato | Test unit + smoke test feature |
| Feature nuova / cross-module | Full battery (unit + integration + smoke) |

**Default**: piuttosto verificare in eccesso che in difetto. Ma in ottica DX, evita cerimoniale per cambi triviali.

## Scaling — Verifica Proporzionata al Task

GATE: La verifica e' SEMPRE obbligatoria, ma la profondita' scala con il rischio.

| Complessita' task | Verifica richiesta |
|------------------|--------------------|
| **Banale** (config, typo, docs) | Step 1 + Step 2 (`git diff` + test esistenti) + Step 5 breve |
| **Basso** (fix isolato, <3 file) | Step 1-2-3-5. Step 4 inline. |
| **Medio-Alto** (feature, cross-module) | Tutti e 5 gli step completi. Nessuno shortcut. |

**Regola:** la verifica non si salta MAI. Si scala la profondita', non l'esistenza.
Formato banale una riga: `VERIFICA: git diff OK, test suite passed (N test, 0 fail). Fatto.`

## I 5 Step della Verifica

### Step 0 — PLAN CHECK (se applicabile)

Se il lavoro e' associato a un piano in `docs/plans/`:

```bash
grep -c "\[DONE\]" docs/plans/<file>.md
grep -c "\[PENDING\]" docs/plans/<file>.md
grep -c "\[BLOCKED\]" docs/plans/<file>.md
```

Se PENDING > 0 o BLOCKED > 0: **STOP** — piano non completo, torna ai task mancanti.
Se tutti [DONE] (o lavoro ad-hoc senza piano): procedi a Step 1.

### Step 1 — IDENTIFICA

Determina il modo corretto per verificare il lavoro svolto.

| Tipo di lavoro | Verifica richiesta |
|----------------|-------------------|
| Codice Java | `mvn test -pl {module}` o `mvn verify` |
| Codice TypeScript backend | `yarn test` o `npm test` |
| Codice TypeScript frontend | `npx vitest run` |
| Codice Python | `pytest tests/ -v` |
| Infrastructure (HCL) | `terraform validate` + `terraform plan` |
| Lint/Format | `eslint`, `checkstyle`, `flake8`, `tflint` |
| Build | Compilazione completa senza errori |
| Git | `git status` + `git diff` — verifica cosa stai committando |
| Documentazione | Rendering corretto, link funzionanti, nessun placeholder |

Se il lavoro copre piu' categorie, identifica TUTTE le verifiche necessarie.

### Step 2 — ESEGUI

Lancia i comandi di verifica identificati. Non saltare nessun comando.
- Esegui nella directory corretta, con i flag corretti per lo stack
- Non interrompere prima che finisca
- Se un comando fallisce, NON procedere — torna al codice e fixa

### Step 3 — LEGGI

Leggi l'output **completo** di ogni comando eseguito. Non assumere il risultato.
- OGNI riga: cerca errori, warning, test falliti, deprecation
- Non dire "tutti i test passano" se non hai letto l'output
- Se l'output e' troncato, rieseguilo con flag di verbose

### Step 4 — VERIFICA

L'output conferma il successo? Rispondi:
- [ ] Tutti i test passano? (non "la maggior parte" — TUTTI)
- [ ] Zero errori di compilazione/build?
- [ ] Zero errori di lint/format rilevanti?
- [ ] `git diff` mostra solo le modifiche intenzionali?
- [ ] Nessun file dimenticato nello staging?
- [ ] Nessun secret o credenziale esposta?

Se anche UNA risposta e' NO, **non puoi procedere**.

### Step 5 — AFFERMA

Solo ora puoi dichiarare il completamento. Formato obbligatorio:

```
VERIFICA COMPLETATA:
  Comandi:   [lista comandi eseguiti]
  Risultato: [output sintetico]
  Evidenza:
    - path/to/file.java:45 — metodo process() implementato
    - tests/test_file.py:12 — test should_validate_isrc passa
  Claim:     [la tua dichiarazione]
```

**Regola citazione:** minimo 1 citazione `file:riga` per ogni requisito verificato.
Se non puoi citare `file:riga`, non puoi dichiarare quel requisito completato.

## Cosa NON Conta Come Verifica

| NON e' verifica | Perche' |
|-----------------|---------|
| "Ho letto il codice e sembra corretto" | Leggere != eseguire. I bug non si vedono leggendo. |
| "L'ho testato prima e funzionava" | "Prima" non e' "adesso". Riesegui. |
| "E' un cambio piccolo" | I cambi piccoli causano i bug peggiori. |
| "Ho fatto la stessa cosa su un altro progetto" | Ogni contesto e' diverso. |
| "Il compilatore non ha dato errori" | La compilazione non testa il comportamento. |
| "Ho copiato da codice che funziona" | Il contesto e' diverso. Verifica nel nuovo contesto. |
| "Ho verificato che funziona" (senza citare file:riga) | Prose senza citazione non e' evidenza. |

## Red Flags — Stai Razionalizzando

Questi pensieri significano che NON hai verificato. Fermati.

| Pensiero | Realta' |
|----------|---------|
| "Dovrebbe funzionare" | "Dovrebbe" != "funziona". Verifica. |
| "Probabilmente e' ok" | "Probabilmente" != "certamente". Verifica. |
| "Sembra a posto" | "Sembra" != "e' verificato". Esegui i test. |
| "Ho gia' fatto questo prima" | Ogni contesto e' diverso. Verifica questo specifico caso. |
| "E' un cambio piccolo" | I cambi piccoli causano i bug peggiori. Verifica. |
| "Lo so perche' ho scritto io il codice" | Bias di conferma. Il tuo codice ha bug come tutti gli altri. |
| "I test sono lenti, salto questa volta" | I bug in produzione sono piu' lenti. Esegui i test. |
| "Non ho tempo" | Fixare un bug in produzione costa 10x. Hai tempo per verificare. |
| "Il reviewer lo trovera'" | Il reviewer non e' la tua rete di sicurezza personale. |
| "Funzionava 5 minuti fa" | Hai modificato qualcosa in quei 5 minuti. Ri-verifica. |
| "E' solo documentazione" | La doc sbagliata e' peggio di quella assente. Verifica link e rendering. |
| "Il CI/CD lo testa" | Se il CI fallisce, hai sprecato tempo di tutti. Testa in locale prima. |

## Vincoli

1. **NON** dichiarare completamento senza aver eseguito TUTTI e 5 gli step
2. **NON** dire "Perfetto!", "Fatto!", "Completato!" prima dello step 5
3. **NON** saltare lo step 3 (LEGGI) — l'output va letto, non assunto
4. **NON** considerare la compilazione come sostituto dei test
5. **NON** procedere se anche un solo test fallisce
6. Se non puoi verificare automaticamente, spiega esattamente PERCHE' e cosa l'utente deve controllare
7. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= MEDIO (test run, build, lint)

## Riferimenti

- **Classificazione rischio operazioni:** vedi `lib/risk-taxonomy.md`. Estratto: esecuzione test/build/lint/terraform = MEDIO (card richiesta); identificare comandi, leggere output, generare report = SICURO.
- **Limiti operativi:** vedi `lib/operational-limits.md`. Override: tentativi max per step = 2; step totali protocollo = 5; output max per analisi = 300 righe.
- **Permission denied handling:** vedi `lib/permission-denied-handling.md`. Extra: Step 1/3/4/5 completabili senza permessi; Step 2 (ESEGUI) richiede Bash — se negato, fornisci lista comandi e chiedi all'utente di eseguirli, poi riprendi dallo Step 3 con l'output incollato.
- **Tabelle dettagliate claim/comandi/output per stack:** vedi `reference/common-failures.md`.
