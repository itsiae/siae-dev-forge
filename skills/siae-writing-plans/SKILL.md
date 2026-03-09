---
name: siae-writing-plans
description: >
  Use when a design has been approved and needs to become an implementation plan.
  Trigger: design approvato da siae-brainstorming, spec/requisiti esistenti, piano da aggiornare.
---

# SIAE Writing Plans — Da Design a Piano Implementativo

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · WRITING PLANS                         ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 2. Design (output)

---

## HARD-GATE

<HARD-GATE>
NON scrivere il piano senza un design approvato. Se non esiste un design doc
validato dall'utente, torna a `siae-brainstorming` prima.
</HARD-GATE>

Un piano senza design validato = assunzioni non esaminate = lavoro da rifare.

---

## LA LEGGE DI FERRO

```
OGNI STEP DEL PIANO E' UNA SINGOLA AZIONE DA 2-5 MINUTI,
CON PATH ESATTI, CODICE COMPLETO E COMANDO ATTESO
```

"Aggiungi la validazione" non e' uno step. Non e' un piano. E' un'aspirazione.

---

## Quando si Applica

**Invocata da siae-brainstorming** dopo l'approvazione del design (Step 6).

**Invocata direttamente quando:**
- Hai un design doc gia' approvato e devi produrre il piano
- Devi aggiornare/rivedere un piano esistente dopo feedback
- Hai una spec/requisiti e il design e' implicito o semplice

**NON usare quando:**
- Il design non e' ancora stato approvato (prima `siae-brainstorming`)
- Il piano esiste ed e' gia' valido — non riscriverlo senza motivo

---

## Processo

### Step 1 — Leggi il Design Doc

Leggi il design doc approvato in `docs/plans/YYYY-MM-DD-*-design.md`.

Identifica:
- Goal e scope
- Componenti/moduli da creare o modificare
- Stack e framework
- Criteri di accettazione
- Dipendenze tra task

### Step 2 — Decomposizione in Task

Suddividi il lavoro in task indipendenti (o con dipendenze esplicite).

**Ogni task:**
- Copre un componente/modulo/feature atomica
- Segue il ciclo TDD: test fallente → implementazione → refactor → commit
- E' completabile da un subagent con contesto fresco
- Ha un output verificabile

**Regola di dimensione:** se un task richiede piu' di 30 minuti, spezzalo.

### Step 3 — Scrivi il Piano Bite-Sized

**Header obbligatorio** — copia esattamente:

```markdown
# [Nome Feature] — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** [Una frase su cosa costruisce questo piano]
**Architettura:** [2-3 frasi sull'approccio tecnico]
**Stack:** [Tecnologie e framework coinvolti]
**SP:** [Stima story points totale]

---
```

**Template per ogni task:**

````markdown
### Task N: [Nome Componente / Modulo]

**File coinvolti:**
- Crea: `path/esatto/al/file.py`
- Modifica: `path/esatto/al/file.java` (righe 45-67)
- Test: `tests/path/esatto/test_file.py`

**Step 1: Scrivi il test fallente**

```java
@Test
void should_[comportamento]_when_[condizione]() {
    // Arrange
    var input = new MyClass("valore");

    // Act
    var result = myService.process(input);

    // Assert
    assertThat(result.getStatus()).isEqualTo("ATTESO");
}
```

**Step 2: Esegui il test e verifica che fallisce**

```bash
mvn test -pl modulo -Dtest=MyClassTest#should_[comportamento]
```
Output atteso: `FAIL — MyService: method not found`

**Step 3: Implementazione minimale**

```java
public Result process(MyClass input) {
    return Result.of("ATTESO");
}
```

**Step 4: Esegui il test e verifica che passa**

```bash
mvn test -pl modulo -Dtest=MyClassTest#should_[comportamento]
```
Output atteso: `BUILD SUCCESS — Tests run: 1, Failures: 0`

**Step 5: Commit**

```bash
git add path/esatto/al/file.java tests/path/esatto/test_file.java
git commit -m "feat(modulo): aggiungi [comportamento]"
```
````

### Step 4 — Salva il Piano

Salva in `docs/plans/YYYY-MM-DD-<topic>-plan.md` (distinto dal design doc).

Se il design doc gia' include una sezione piano, aggiungila li' come sezione separata.

Committa il file piano:

🟡 MEDIO — Mostra pre-flight card prima del commit

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-writing-plans |
|:---|
| 📋 Piano: `<filename>.md` |
| 🔢 Task: `<N> task definiti` |
| 1. 📌 Azione: Commit piano implementativo |
| 📂 `docs/plans/<filename>.md` |
| 💡 Perche': Piano validato, pronto per commit |
| 🚫 Se NO: Il piano resta non committato |

```bash
git add docs/plans/YYYY-MM-DD-<topic>-plan.md
git commit -m "docs(plans): aggiungi piano implementativo per [feature]"
```

### Step 5 — Execution Handoff

Dopo aver salvato e committato il piano, offri la scelta di esecuzione:

```
Piano salvato in docs/plans/<filename>.md. Come vuoi procedere?

1. Subagent (questa sessione) — dispatcho subagent freschi per ogni task,
   review spec + quality tra i task, iterazione rapida

2. Sessione separata — apri una nuova sessione con il file piano,
   esecuzione a batch con checkpoint umani

Quale preferisci?
```

**Se Subagent (opzione 1):**

```
REQUIRED SUB-SKILL: siae-subagent-development
```

Rimani nella sessione corrente. siae-subagent-development gestisce l'orchestrazione.

**Se Sessione separata (opzione 2):**

```
REQUIRED SUB-SKILL: siae-executing-plans
```

1. Guida l'utente ad aprire una nuova sessione Claude Code nella directory del progetto
2. Istruisci: "Carica il piano con: `cat docs/plans/<filename>.md` e inizia l'implementazione seguendo la skill siae-executing-plans"
3. Il piano ha l'header `REQUIRED SUB-SKILL` embedded — il nuovo Claude lo trovera' automaticamente

**NON invocare siae-subagent-development senza la scelta esplicita dell'utente.**

---

## Regole di Qualita' del Piano

### Path esatti — sempre

```
# SBAGLIATO
Modifica il service di autenticazione

# GIUSTO
Modifica: `src/main/java/it/siae/auth/AuthService.java` (righe 112-134)
```

### Codice completo — sempre

```
# SBAGLIATO
Aggiungi la validazione dell'ISRC

# GIUSTO
if (!isrc.matches("^[A-Z]{2}-[A-Z0-9]{3}-[0-9]{2}-[0-9]{5}$")) {
    throw new ValidationException("ISRC non valido: " + isrc);
}
```

### Comandi con output atteso — sempre

```
# SBAGLIATO
Esegui i test

# GIUSTO
Run: `pytest tests/test_isrc_validator.py::test_invalid_format -v`
Output atteso: FAILED — ValidationException: ISRC non valido
```

### Step atomici — un'azione per step

```
# SBAGLIATO (troppo grande)
Implementa il validator ISRC con test e aggiornamento config

# GIUSTO (atomico)
Step 1: Scrivi il test per formato ISRC non valido
Step 2: Esegui e verifica che fallisce
Step 3: Implementa il regex di validazione
Step 4: Esegui e verifica che passa
Step 5: Commit
```

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Il piano e' nella mia testa, basta implementare" | I piani non scritti sono assunzioni. Scrivili. |
| "I task sono ovvi, non serve dettagliare" | Ovvio per te. Opaco per un subagent con contesto fresco. |
| "Il codice nel piano puo' essere uno sketch" | Il codice incompleto nel piano diventa codice incompleto nell'implementazione. |
| "I path li ricorda il subagent" | Il subagent ha contesto fresco. Zero. Dai i path esatti. |
| "Questo task e' troppo grande ma lo scrivo uguale" | Spezzalo. Un task grande e' un task che fallira' a meta'. |
| "Aggiungo i comandi di test dopo" | Senza comandi nel piano, il subagent li inventa. Spesso sbagliati. |
| "E' solo un aggiornamento di config, non serve piano" | Le config rotte vanno in produzione. Testa e pianifica. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura design doc | 🟢 Sicuro | No |
| Scrittura piano su file | 🟢 Sicuro | No |
| Git commit piano | 🟡 Medio | Si |
| Execution handoff → subagent | 🟡 Medio | Si (in siae-subagent-development) |

---

## Permission Denied Handling

**Se Write viene negato (salvataggio piano):**
1. Presenta il piano completo come output testuale formattato in chat
2. Indica il path suggerito: `docs/plans/YYYY-MM-DD-<topic>-plan.md`
3. L'utente puo' copiare il contenuto manualmente
4. Procedi a Step 5 (execution handoff) normalmente

**Se Bash (git commit) viene negato:**
1. Il file e' stato scritto ma non committato
2. Informa: `git add docs/plans/<file> && git commit -m "docs(plans): aggiungi piano per <feature>"`
3. Procedi a Step 5 normalmente

---

## Integrazione SDLC

```
siae-brainstorming (Step 6: design approvato)
    └── REQUIRED SUB-SKILL: siae-writing-plans
        └── piano bite-sized salvato in docs/plans/
            └── execution handoff:
                ├── subagent → REQUIRED SUB-SKILL: siae-subagent-development
                └── sessione separata → REQUIRED SUB-SKILL: siae-executing-plans
```

**Skill correlate:**
- `siae-brainstorming` — produce il design doc che questa skill consuma
- `siae-subagent-development` — esegue il piano nella stessa sessione
- `siae-executing-plans` — esegue il piano in sessione separata
- `siae-tdd` — ogni subagent implementer usa TDD per ogni task del piano
