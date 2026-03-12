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

**Perche' questa legge esiste — da 24 failure memories documentate:**
- "Ho verificato" senza evidenza → bug in produzione scoperti dal cliente
- "I test passavano" senza run fresca → ambiente locale diverso da CI
- "L'agent ha detto successo" → 40% dei casi l'agent aveva hallucinated il risultato
- Tempo perso in false completion → redirect → rework: mediamente 3-4 ore per incident

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

### Step 0 — PLAN CHECK (se applicabile)

Se il lavoro corrente è associato a un piano in `docs/plans/`:

1. Identifica il piano associato (il più recente `*-plan.md` nella directory)
2. Conta i task per stato:

```bash
grep -c "\[DONE\]" docs/plans/<file>.md
grep -c "\[PENDING\]" docs/plans/<file>.md
grep -c "\[BLOCKED\]" docs/plans/<file>.md
```

3. **Se PENDING > 0 o BLOCKED > 0:**

```
🔴 STOP — Il piano non è completo.

Piano: docs/plans/<file>.md
Stato: X [DONE] / Y [PENDING] / Z [BLOCKED]

Non puoi procedere con la verifica finale.
Torna a eseguire i task mancanti prima.
```

4. **Se tutti [DONE]:** procedi con Step 1 (IDENTIFICA)

Se non c'è un piano associato (lavoro ad-hoc), salta questo step e procedi direttamente a Step 1.

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

🟡 MEDIO — Mostra pre-flight card prima di eseguire la suite di verifica

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-verification |
|:---|
| 🔧 Comandi: `<lista comandi identificati in Step 1>` |
| 📁 Working dir: `<directory>` |
| 1. 🧪 Azione: Esecuzione suite di verifica |
| 📂 `<comandi>` |
| 💡 Perche': Verifica necessaria prima di qualsiasi claim di completamento |
| 🚫 Se NO: Nessuna verifica eseguita — non puoi dichiarare completamento |

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
  Comandi:   [lista comandi eseguiti]
  Risultato: [output sintetico]
  Evidenza:
    - path/to/file.java:45 — metodo process() implementato
    - tests/test_file.py:12 — test should_validate_isrc passa
  Claim:     [la tua dichiarazione]
```

**Regola citazione:** minimo 1 citazione `file:riga` per ogni requisito verificato.
Se non puoi citare `file:riga`, non puoi dichiarare quel requisito completato.
Formato standard: `path/to/file.ext:NN — descrizione breve`

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
| "Ho verificato che funziona" (senza citare file:riga) | Prose senza citazione non sono evidenza. Cita file:riga o non e' verifica. |

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

## Perche' Importa

Da sessioni reali SIAE dove la verifica e' stata saltata:

- **L'utente ha detto "Non ci credo"** — la fiducia si rompe in un secondo e ci vogliono settimane per ricostruirla
- **Funzioni undefined shippe in produzione** — crash su path critici (diritti d'autore, pagamenti SIAE)
- **Requisiti mancanti scoperti post-release** — feature incomplete che hanno richiesto hotfix urgenti
- **Tempo sprecato in false completion** → re-apertura ticket → rework del developer
- **CI fallito dopo push** — tempo di tutti sprecato, pipeline bloccata, deploy saltato

Questo non e' teorico. Ogni volta che salti la verifica, stai scommettendo la reputazione del team su "probabilmente va bene".

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Ho gia' eseguito i test prima, sicuramente passano ancora" | L'ultima run non e' questa run. Qualsiasi modifica successiva puo' aver rotto qualcosa. Riesegui ora. |
| "L'agent ha confermato che tutto funziona" | Gli agent allucinano successi nel 40% dei casi documentati. L'unica evidenza valida e' l'output reale del comando. |
| "I test ci mettono troppo, li salto questa volta" | Il tempo per fixare un bug in produzione e' 10x il tempo per eseguire i test. Non hai alternative. |
| "Ho letto il codice e non vedo errori" | Leggere il codice non e' eseguire il codice. I bug si nascondono nei path che non stai guardando. |
| "E' un fix di una riga sola, non puo' rompere nulla" | I bug piu' costosi nella storia SIAE sono stati introdotti da modifiche di una riga. Zero eccezioni. |
| "Il CI fara' i test, non devo farli in locale" | Se il CI fallisce, hai sprecato il tempo dell'intero team e bloccato la pipeline. Testa prima in locale. |
| "Ho visto l'output scorrere e sembrava ok" | 'Sembrava ok' non e' evidenza. Devi leggere ogni riga, cercare FAILED, ERROR, WARN. |
| "L'utente aspetta, devo dichiarare done il prima possibile" | Un false completion genera rework immediato. Tre minuti di test ora evitano ore di debug dopo. |
| "I task BLOCKED non sono colpa mia" | Un piano con BLOCKED è un piano incompleto. Risolvi o rimuovi con l'utente. |
| "Mancano solo 1-2 task, posso chiudere" | Parziale = incompleto. Zero eccezioni. |

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

## Permission Denied Handling

**Se Bash viene negato (Step 2 — ESEGUI):**
1. Completa Step 1 (IDENTIFICA) normalmente — e' read-only
2. Presenta la lista esatta dei comandi da eseguire, con directory e flag corretti
3. Chiedi all'utente di eseguirli nel suo terminale e incollare l'output
4. Quando l'utente incolla l'output, procedi con Step 3 (LEGGI) normalmente
5. Completa Step 4 (VERIFICA) e Step 5 (AFFERMA) sui risultati forniti

**Se l'utente non esegue i comandi:**
- NON dichiarare completamento
- Segnala: "Verifica non completabile senza output dei test. Esegui [comandi] e condividi il risultato."

**Formato Step 5 in modalita' degradata:**
```
VERIFICA COMPLETATA (manuale):
  Comandi:   [lista — eseguiti dall'utente]
  Risultato: [basato su output fornito dall'utente]
  Claim:     [dichiarazione]
```

**Fasi completabili senza permessi:** Step 1 (IDENTIFICA), Step 3 (LEGGI), Step 4 (VERIFICA), Step 5 (AFFERMA)
**Fasi che richiedono permessi:** Step 2 (ESEGUI) — Bash per test/build/lint

Se i permessi sono negati:
1. Completa tutte le fasi read-only
2. Presenta riepilogo di cosa e' stato fatto
3. Lista comandi/operazioni per esecuzione manuale
4. NON entrare in loop di retry su tool negato
5. NON dichiarare completamento per fasi non eseguite

---

## Risorse Aggiuntive

Per tabelle dettagliate di claim comuni per stack, comandi richiesti, output attesi e errori tipici, vedi [reference/common-failures.md](reference/common-failures.md).
