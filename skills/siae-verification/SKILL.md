---
name: siae-verification
description: >
  Use when about to claim work is complete, fixed, or passing — requires running
  verification commands before any success claims. Trigger: prima di commit, PR,
  task complete, dichiarazioni di successo, "fatto", "fixato", "funziona".
---

# SIAE Verification — Protocollo di Verifica Pre-Completamento

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · VERIFICATION PROTOCOL              ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** Cross-cutting (tutte le fasi)

---

## LA LEGGE DI FERRO

```
NESSUN CLAIM DI COMPLETAMENTO SENZA EVIDENZA FRESCA
```

<EXTREMELY-IMPORTANT>
Affermare che il lavoro e' completo senza verifica e' disonesta', non efficienza.
Questa skill e' NON NEGOZIABILE. Si applica SEMPRE, senza eccezioni.
</EXTREMELY-IMPORTANT>

---

## Quando si Applica

**SEMPRE** prima di:
- Dichiarare un task "completato" o "fatto"
- Creare un commit
- Aprire o aggiornare una PR
- Dire "funziona", "fixato", "passano", "pronto"
- Qualsiasi affermazione di successo

Se stai per dire una di queste cose, **FERMATI** e segui i 5 step.

---

## I 5 Step della Verifica

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

Lancia i comandi di verifica identificati allo step 1. Non saltare nessun comando.

- Esegui nella directory corretta
- Usa i flag corretti per lo stack
- Non interrompere l'esecuzione prima che finisca
- Se un comando fallisce, NON procedere — torna al codice e fixa

### Step 3 — LEGGI

Leggi l'output **completo** di ogni comando eseguito. Non assumere il risultato.

- Leggi OGNI riga dell'output
- Cerca errori, warning, test falliti, deprecation
- Non dire "tutti i test passano" se non hai letto l'output
- Se l'output e' troncato, rieseguilo con flag di verbose

### Step 4 — VERIFICA

L'output conferma il successo? Rispondi a queste domande:

- [ ] Tutti i test passano? (non "la maggior parte" — TUTTI)
- [ ] Zero errori di compilazione/build?
- [ ] Zero errori di lint/format rilevanti?
- [ ] Il `git diff` mostra solo le modifiche intenzionali?
- [ ] Nessun file dimenticato nello staging?
- [ ] Nessun secret o credenziale esposta?

Se anche UNA risposta e' NO, **non puoi procedere**.

### Step 5 — AFFERMA

Solo ora puoi dichiarare il completamento. La tua affermazione DEVE includere:

1. **Cosa e' stato verificato** (quali comandi)
2. **Risultato** (output sintetico: N test passati, 0 errori, coverage X%)
3. **Claim** (la dichiarazione di completamento)

**Formato obbligatorio:**

```
VERIFICA COMPLETATA:
  Comandi:  [lista comandi eseguiti]
  Risultato: [output sintetico]
  Claim:    [la tua dichiarazione]
```

---

## Cosa NON Conta Come Verifica

| NON e' verifica | Perche' |
|-----------------|---------|
| "Ho letto il codice e sembra corretto" | Leggere != eseguire. I bug non si vedono leggendo. |
| "L'ho testato prima e funzionava" | "Prima" non e' "adesso". Riesegui. |
| "E' un cambio piccolo" | I cambi piccoli causano i bug peggiori. |
| "Ho fatto la stessa cosa su un altro progetto" | Ogni contesto e' diverso. |
| "Il compilatore non ha dato errori" | La compilazione non testa il comportamento. |
| "Ho copiato da codice che funziona" | Il contesto e' diverso. Verifica nel nuovo contesto. |

---

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
| "Il reviewer lo trovera'" | Il reviewer non e' la tua rete di sicurezza personale. Verifica prima tu. |
| "Funzionava 5 minuti fa" | Hai modificato qualcosa in quei 5 minuti. Ri-verifica. |
| "E' solo documentazione" | La documentazione sbagliata e' peggio di quella assente. Verifica i link e il rendering. |
| "Il CI/CD lo testa" | Se il CI fallisce, hai sprecato il tempo di tutti. Testa in locale prima. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Identificare comandi di verifica | 🟢 Sicuro | No |
| Eseguire test (`mvn test`, `npm test`, `pytest`, `vitest`) | 🟡 Medio | Si |
| Eseguire build/compilazione | 🟡 Medio | Si |
| Eseguire `terraform validate` / `terraform plan` | 🟡 Medio | Si |
| Eseguire lint/format | 🟡 Medio | Si |
| Leggere output | 🟢 Sicuro | No |
| Generare report verifica | 🟢 Sicuro | No |

---

## Vincoli

1. **NON** dichiarare completamento senza aver eseguito TUTTI e 5 gli step
2. **NON** dire "Perfetto!", "Fatto!", "Completato!" prima dello step 5 — Mai.
3. **NON** saltare lo step 3 (LEGGI) — l'output va letto, non assunto
4. **NON** considerare la compilazione come sostituto dei test
5. **NON** procedere se anche un solo test fallisce
6. Se non puoi verificare automaticamente, spiega esattamente PERCHE' e cosa l'utente deve controllare manualmente
7. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= 🟡 (test run, build, lint)

---

## Risorse Aggiuntive

Per tabelle dettagliate di claim comuni per stack, comandi richiesti, output attesi e errori tipici, vedi [reference/common-failures.md](reference/common-failures.md).
