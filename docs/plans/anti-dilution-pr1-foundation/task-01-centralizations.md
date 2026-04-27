# Task 01 — Creare 4 centralizations in lib/*.md

**Stato:** [PENDING]
**Execution:** subagent OR in-session
**Dipendenze:** nessuna
**Durata stimata:** 5-8 min

## Goal

Creare 4 file di centralizzazione in `lib/` che consolidano sezioni ripetute nelle 5 skill backbone. Questi file vengono referenziati (non embedded) dalle skill compressed nei task T03-T08.

## File da creare

### 1. `lib/risk-taxonomy.md` (estrae da 5 skill)

```markdown
# Classificazione Rischio Operazioni — Standard DevForge

| Livello | Definizione | Card richiesta |
|---------|-------------|----------------|
| 🟢 SICURO | Operazione locale, reversibile istantaneamente | No |
| 🟡 MEDIO | Reversibile ma richiede azione (git revert, undo) | Sì |
| 🔴 ALTO | Difficile da annullare (force-push, tag pubblicati) | Sì |
| 🚨 CRITICO | Irreversibile o con impatto esterno (prod deploy, credenziali) | Sì + conferma esplicita |

## Esempi standard

| Operazione | Livello |
|-----------|---------|
| Read, Glob, Grep | 🟢 SICURO |
| Edit file locale, scrittura design doc | 🟢 SICURO |
| git commit, git add | 🟡 MEDIO |
| git push feature branch | 🟡 MEDIO |
| git push --force su main | 🚨 CRITICO |
| git tag push (release) | 🔴 ALTO |
| gh pr create | 🟡 MEDIO |
| AWS deploy (Terraform apply) | 🔴 ALTO |
| DROP TABLE, rm -rf | 🚨 CRITICO |

Le skill individuali referenziano questa tabella invece di duplicarla.
```

### 2. `lib/operational-limits.md`

```markdown
# Limiti Operativi — Standard DevForge

Applicabili a tutte le skill DevForge salvo override esplicito.

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue. |
| Step totali di un task | 30 min | Spezza in sub-task. |
| Comandi bash consecutivi senza output check | 3 | Verifica prima di proseguire. |

Override per skill: vedere sezione "Limiti" nella singola SKILL.md se presente.
```

### 3. `lib/permission-denied-handling.md`

```markdown
# Permission Denied Handling — Standard DevForge

Strategie uniformi quando un tool è negato in skill DevForge.

## Se Write negato
1. Presenta il contenuto come output testuale formattato in chat
2. Indica il path suggerito
3. L'utente copia manualmente
4. Procedi con il step successivo normalmente

## Se Bash negato (generico)
1. Informa cosa serviva eseguire
2. Fornisci il comando esatto
3. Se è un check (git log, ls), degrada a tool alternativi (Read, Glob)
4. Se è un'azione (commit, push), istruisci l'utente

## Se Bash (git commit) negato
1. File già scritto, non committato
2. Istruisci: `git add <file> && git commit -m "<msg>"`
3. Procedi normalmente

## Se Edit negato
1. Mostra la modifica desiderata in chat (before/after)
2. Utente applica manualmente
3. Non re-tentare automaticamente

## Principio
Il valore primario della skill si preserva sempre via degradazione graceful.
Non abbandonare la skill: cambia modalità.
```

### 4. `lib/checkpoint-schema.md`

```markdown
# Checkpoint Schema — Standard DevForge

Formato standard per output strutturato delle skill.

## Regole

- Ogni step significativo emette 1 checkpoint
- Formato: `[SKILL-NAME:STEP-ID] Descrizione`
- Campi key:value, no testo narrativo
- Emesso in chat visibile all'utente (non in log silenzioso)

## Esempi canonici

```
[BRAINSTORM:INTAKE] Analisi completata
  Stack: Java/Spring Boot
  Pattern: REST microservice
  Confidence: HIGH (3/3 fonti concordanti)
  File analizzati: 7
  Lacune: nessuna
```

```
[TDD:RED] Test fallente scritto
  File: tests/test_validator.py
  Test: test_invalid_isrc_format
  Run: pytest -k test_invalid_isrc_format
  Output: FAILED (ValidationException)
```

```
[VERIFICATION:ASSERT] Claim verificato
  Claim: "endpoint /users ritorna 200"
  Comando: curl localhost:8080/users
  Output: HTTP/1.1 200 OK
  Evidenza: salvata in .devforge-verification-log
```

Le skill individuali possono definire step-id specifici ma devono seguire
il formato chiave:valore e la riga di intestazione.
```

## Step

### Step 1: crea la directory lib/ se assente

```bash
test -d lib && echo "lib/ exists" || mkdir -p lib
```
Output atteso: `lib/ exists` (già esistente — contiene logger.sh, ecc)

### Step 2: scrivi i 4 file

Usa Write tool per ciascuno dei 4 file sopra. Usa il contenuto esatto fornito.

### Step 3: verifica

```bash
ls -la lib/*.md && wc -l lib/risk-taxonomy.md lib/operational-limits.md lib/permission-denied-handling.md lib/checkpoint-schema.md
```
Output atteso: 4 file presenti, totale < 200 righe.

### Step 4: commit

```bash
git add lib/risk-taxonomy.md lib/operational-limits.md lib/permission-denied-handling.md lib/checkpoint-schema.md
git commit -m "feat(lib): add centralizations for skill compression

Part of PR #1 anti-dilution.
ADR-003: centralize risk taxonomy, limits, permission handling, checkpoint schema.
Referenced (not embedded) by compressed SKILL.md in T03-T08."
```

## Acceptance

- [ ] 4 file creati in `lib/`
- [ ] Contenuto fedele allo specificato (copia-incolla, no reinterpretazione)
- [ ] `wc -l lib/{risk-taxonomy,operational-limits,permission-denied-handling,checkpoint-schema}.md` < 200 righe totali
- [ ] Commit con conventional message `feat(lib):`
