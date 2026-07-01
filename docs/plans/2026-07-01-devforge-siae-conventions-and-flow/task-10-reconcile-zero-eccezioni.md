# Task 10 — Riconcilia "zero eccezioni" con lo scaling trivial (Lite-present)

**Cluster:** C brainstorm (REQ-DF-04 — brainstorming proporzionato alla complessità)
**Dipendenze:** nessuna — allineamento testuale/memory, indipendente da Task 08/09 (overview: "Task 10 indipendente (allineamento testo/memory)").

## Goal

Tutti i punti che oggi asseriscono "il processo si esegue SEMPRE, zero eccezioni" senza carve-out — `skills/siae-brainstorming/SKILL.md` (Scaling + Legge di Ferro), `lib/skills-core.js:421`, `tests/skill-activation/cases.yml:65-68`, `hooks/ENV_VARS.md`, e la memoria auto-persistita — sono riformulati per riflettere la policy Lite-present approvata: la PROFONDITÀ scala sempre, il gate hook non forza il processo sui cambiamenti trivial, l'enforcement resta assoluto sui complessi.

## File coinvolti

- `skills/siae-brainstorming/SKILL.md` — **modifica**, righe 20-46 (HARD-GATE) e righe 50-63 (Scaling — Adatta la Profondità).
- `lib/skills-core.js` — **modifica**, riga 421 (stringa disambiguation `siae-brainstorming SEMPRE ... zero eccezioni`).
- `tests/skill-activation/cases.yml` — **modifica**, righe 65-68 (caso `feature-config-change`).
- `hooks/ENV_VARS.md` — **modifica**, append a fine file (dopo riga 206, sezione `## Rollout and rollback`), nuova sezione `## Brainstorming complexity scaling (REQ-DF-04)`.
- `tests/test_reconcile_zero_eccezioni.sh` — **nuovo** file di test grep-guard (stile `tests/compression-regression/assert_behavioral_invariants.sh`).
- `/Users/detomasi/.claude/projects/-Users-detomasi-Library-Mobile-Documents-com-apple-CloudDocs-siae-dev-forge/memory/feedback_brainstorming_always.md` — **modifica** (fuori dal repo git, memoria auto-persistita utente).
- `/Users/detomasi/.claude/projects/-Users-detomasi-Library-Mobile-Documents-com-apple-CloudDocs-siae-dev-forge/memory/MEMORY.md` — **modifica**, riga 10 (bullet `feedback_brainstorming_always.md`).

## Step TDD

### Step 1 — Scrivi il test che fallisce (codice completo)

Crea `tests/test_reconcile_zero_eccezioni.sh`:

```bash
#!/usr/bin/env bash
# test_reconcile_zero_eccezioni.sh — guard: "zero eccezioni" riconciliato con
# lo scaling trivial (Lite-present, REQ-DF-04, ADR design 2026-07-01).
# La PROFONDITA' scala sempre; il gate non forza il processo sui trivial;
# l'enforcement resta assoluto sui complessi/IaC/multi-repo.
set -eu
PASS=0; FAIL=0
cd "$(git rev-parse --show-toplevel)"

_assert() {
    local name="$1"; local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then echo "  PASS  $name"; PASS=$((PASS+1))
    else echo "  FAIL  $name (cmd: $cmd)"; FAIL=$((FAIL+1)); fi
}

echo "=== skills/siae-brainstorming/SKILL.md — carve-out trivial presente ==="
_assert "menziona 'gate' + 'trivial' nella sezione Scaling" \
    "grep -qi 'trivial' skills/siae-brainstorming/SKILL.md"
_assert "NON asserisce più 'si eseguono SEMPRE' senza carve-out (stringa esatta rimossa)" \
    "! grep -q 'I 7 step si eseguono SEMPRE' skills/siae-brainstorming/SKILL.md"
_assert "la profondità scala esplicitamente (testo aggiornato)" \
    "grep -qi 'la.*PROFONDIT.*scala' skills/siae-brainstorming/SKILL.md"
_assert "Legge di Ferro/HARD-GATE ancora presenti (invariante non rimossa)" \
    "grep -q '## HARD-GATE' skills/siae-brainstorming/SKILL.md"

echo ""
echo "=== lib/skills-core.js — riga disambiguation qualificata ==="
_assert "NON asserisce più 'zero eccezioni' senza qualifica trivial/complesso" \
    "! grep -q 'zero eccezioni' lib/skills-core.js"
_assert "menziona 'trivial' o soglia nella riga disambiguation siae-brainstorming" \
    "grep -A0 'siae-brainstorming\` SEMPRE' lib/skills-core.js | grep -qi 'trivial\|soglia\|complessi'"

echo ""
echo "=== tests/skill-activation/cases.yml — commento allineato ==="
_assert "commento feature-config-change non cita più 'zero eccezioni' come motivazione assoluta" \
    "! grep -A2 'id: feature-config-change' tests/skill-activation/cases.yml | grep -q 'zero eccezioni'"

echo ""
echo "=== hooks/ENV_VARS.md — sezione brainstorming complexity documentata ==="
_assert "DEVFORGE_BRAINSTORM_COMPLEXITY documentato" \
    "grep -q 'DEVFORGE_BRAINSTORM_COMPLEXITY' hooks/ENV_VARS.md"
_assert "DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES documentato" \
    "grep -q 'DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES' hooks/ENV_VARS.md"

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
```

Rendi eseguibile e verifica che sia lanciabile con `bash`:

```bash
chmod +x tests/test_reconcile_zero_eccezioni.sh
```

### Step 2 — Esegui e osserva il FAIL atteso

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/test_reconcile_zero_eccezioni.sh
```

Output atteso (stato attuale pre-fix: SKILL.md ha ancora "si eseguono SEMPRE" senza qualifica trivial, `zero eccezioni` è ancora in skills-core.js, il commento cases.yml cita ancora "zero eccezioni", ENV_VARS.md non ha la sezione):

```
=== skills/siae-brainstorming/SKILL.md — carve-out trivial presente ===
  FAIL  menziona 'gate' + 'trivial' nella sezione Scaling (cmd: grep -qi 'trivial' skills/siae-brainstorming/SKILL.md)
  FAIL  NON asserisce più 'si eseguono SEMPRE' senza carve-out (stringa esatta rimossa) (cmd: ! grep -q 'I 7 step si eseguono SEMPRE' skills/siae-brainstorming/SKILL.md)
  FAIL  la profondità scala esplicitamente (testo aggiornato) (cmd: grep -qi 'la.*PROFONDIT.*scala' skills/siae-brainstorming/SKILL.md)
  PASS  Legge di Ferro/HARD-GATE ancora presenti (invariante non rimossa)

=== lib/skills-core.js — riga disambiguation qualificata ===
  FAIL  NON asserisce più 'zero eccezioni' senza qualifica trivial/complesso (cmd: ! grep -q 'zero eccezioni' lib/skills-core.js)
  FAIL  menziona 'trivial' o soglia nella riga disambiguation siae-brainstorming (cmd: grep -A0 'siae-brainstorming` SEMPRE' lib/skills-core.js | grep -qi 'trivial\|soglia\|complessi')

=== tests/skill-activation/cases.yml — commento allineato ===
  FAIL  commento feature-config-change non cita più 'zero eccezioni' come motivazione assoluta (cmd: ! grep -A2 'id: feature-config-change' tests/skill-activation/cases.yml | grep -q 'zero eccezioni')

=== hooks/ENV_VARS.md — sezione brainstorming complexity documentata ===
  FAIL  DEVFORGE_BRAINSTORM_COMPLEXITY documentato (cmd: grep -q 'DEVFORGE_BRAINSTORM_COMPLEXITY' hooks/ENV_VARS.md)
  FAIL  DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES documentato (cmd: grep -q 'DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES' hooks/ENV_VARS.md)

Total: 9 — PASS: 1 — FAIL: 8
```

Exit code: `8`.

### Step 3 — Implementa il codice minimo (codice completo, path reali)

**3a. `skills/siae-brainstorming/SKILL.md` righe 20-46 (HARD-GATE)** — sostituisci il blocco:

```
NON invocare skill di implementazione, scrivere codice, o creare scaffold FINCHE'
non hai presentato il design e l'utente lo ha approvato. Questo si applica a OGNI
progetto, indipendentemente dalla semplicita' percepita.

Stai per scrivere codice, creare file, o invocare siae-tdd/siae-code-standards?
Hai completato TUTTI e 7 i punti della checklist brainstorming?
- NO → FERMATI. Torna al punto mancante. Nessun codice senza design approvato.
- SI → Procedi con siae-writing-plans.
```

con:

```
NON invocare skill di implementazione, scrivere codice, o creare scaffold FINCHE'
non hai presentato il design e l'utente lo ha approvato. Questo si applica a OGNI
progetto, indipendentemente dalla semplicita' percepita — per i task complessi
questo vincolo e' assoluto.

Per i cambiamenti trivial (1 file, poche righe, path non-sensibile, non-IaC — vedi
tabella Scaling sotto) il gate hook non forza nudge/block: la profondita' del
design collassa a un tier "Bassa" quasi-istantaneo, MA il ragionamento sui 7 punti
resta implicito nel flusso, non eliminato.

Stai per scrivere codice, creare file, o invocare siae-tdd/siae-code-standards su
un task complesso?
Hai completato TUTTI e 7 i punti della checklist brainstorming?
- NO → FERMATI. Torna al punto mancante. Nessun codice senza design approvato.
- SI → Procedi con siae-writing-plans.
```

**3b. `skills/siae-brainstorming/SKILL.md` righe 50-63 (Scaling)** — sostituisci il blocco:

```
## Scaling — Adatta la Profondita', MAI il Processo

ZERO ECCEZIONI. I 7 step si eseguono SEMPRE. La complessita' determina la PROFONDITA', non se lo step si esegue. Ogni task produce SEMPRE un piano con subtask via siae-writing-plans.

| Complessita' | Segnali | Profondita' |
|-------------|---------|-------------|
| **Bassa** | Config change, typo, rename, fix isolato (<3 file) | Step brevi (poche frasi). Design doc 10-15 righe. Tutti i 7 step eseguiti. |
| **Media** | CRUD, refactoring, ottimizzazione, bug fix multi-file | Dettaglio moderato. Design doc 30-60 righe. |
| **Alta** | Feature nuova, cross-module, integrazione, migrazione | Checklist completa con massimo dettaglio. |
| **Anti-pattern** | "E' troppo semplice per un design" | I task semplici nascondono assunzioni non esaminate. Il design puo' essere breve, ma DEVI presentarlo e ottenere approvazione. |

<EXTREMELY-IMPORTANT>
NON saltare step. NON abbreviare. NON decidere autonomamente che un task e' "troppo semplice".
</EXTREMELY-IMPORTANT>
```

con:

```
## Scaling — La PROFONDITA' Scala Sempre, il Gate Scala sui Trivial

La complessita' determina SEMPRE la PROFONDITA' del ragionamento. Per i task
complessi il processo e' obbligatorio end-to-end (nessuna eccezione). Per i
task **trivial** (1 file, righe cambiate sotto soglia configurabile, path
non-sensibile, non-IaC — `DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES`, default 15,
vedi `hooks/ENV_VARS.md`) il tier "Bassa" e' quasi-istantaneo e
`hooks/brainstorming-gate` non emette nudge/block: il gate non forza il
processo, ma la profondita' minima (poche frasi di intento) resta la pratica
raccomandata. Ogni task non-trivial produce SEMPRE un piano con subtask via
siae-writing-plans.

| Complessita' | Segnali | Profondita' | Gate hook |
|-------------|---------|-------------|-----------|
| **Trivial** | 1 file, ≤soglia righe, path non-sensibile, non-IaC | Quasi-istantanea (poche frasi di intento, no design doc formale richiesto) | Silente — nessun nudge/block |
| **Bassa** | Config change, typo, rename, fix isolato (<3 file) | Step brevi (poche frasi). Design doc 10-15 righe. Tutti i 7 step eseguiti. | Nudge progressivo (invariato) |
| **Media** | CRUD, refactoring, ottimizzazione, bug fix multi-file | Dettaglio moderato. Design doc 30-60 righe. | Nudge progressivo (invariato) |
| **Alta** | Feature nuova, cross-module, integrazione, migrazione | Checklist completa con massimo dettaglio. | Enforcement pieno (invariato) |
| **Anti-pattern** | "E' troppo semplice per un design" | Se il task NON e' trivial per la definizione sopra, il design puo' essere breve ma DEVI presentarlo e ottenere approvazione — non decidere autonomamente il bypass. | Enforcement pieno |

<EXTREMELY-IMPORTANT>
Multi-file, IaC (.tf/.hcl), path-sensibile (hooks/, lib/*gate*,
lib/review_evidence/) o multi-repo sono SEMPRE complessi, mai trivial,
indipendentemente dalle dimensioni del diff. NON decidere autonomamente che un
task complesso e' "troppo semplice" per saltare il processo.
</EXTREMELY-IMPORTANT>
```

**3c. `lib/skills-core.js` riga 421** — sostituisci:

```js
    '- `siae-brainstorming` SEMPRE per QUALSIASI task implementativo (feature, bug fix, refactoring, config, ottimizzazione — zero eccezioni). Produce SEMPRE un piano con subtask via siae-writing-plans.',
```

con:

```js
    '- `siae-brainstorming` per QUALSIASI task implementativo (feature, bug fix, refactoring, config, ottimizzazione): la profondita\' scala sempre; per i cambiamenti trivial (1 file, poche righe, path non-sensibile, non-IaC) il gate e\' silente, per i complessi resta obbligatorio. Produce SEMPRE un piano con subtask via siae-writing-plans.',
```

**3d. `tests/skill-activation/cases.yml` righe 65-68** — sostituisci:

```yaml
- id: feature-config-change
  prompt: "modifico il timeout del client HTTP da 5s a 30s"
  expected_primary: siae-brainstorming
  # anche cambio config richiede brainstorm (memory: zero eccezioni)
```

con:

```yaml
- id: feature-config-change
  prompt: "modifico il timeout del client HTTP da 5s a 30s"
  expected_primary: siae-brainstorming
  # config change resta expected_primary siae-brainstorming: il segnale testuale
  # ("modifico... client HTTP") non permette di inferire se e' 1 file/poche righe
  # (trivial, gate silente) o multi-file (complesso, gate attivo) — la skill si
  # aggancia comunque; il gate hook scala l'enforcement in base al diff reale.
```

**3e. `hooks/ENV_VARS.md`** — append in fondo al file (dopo la riga `- Hard revert: \`git revert <PR #2 merge commit>\`.` a riga 205, fine file riga 206), nuova sezione:

```markdown

## Brainstorming complexity scaling (REQ-DF-04)

| Env var | Default | Gate | Description |
|---|---|---|---|
| `DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES` | `15` | `hooks/brainstorming-gate` (via `lib/file-taxonomy.sh::devforge_change_is_trivial`) | Soglia righe cambiate sotto la quale un edit a singolo file, non-IaC, path non-sensibile e' classificato trivial. Il gate non emette nudge/block sui trivial (Lite-present, design `2026-07-01-devforge-siae-conventions-and-flow`). |
| `DEVFORGE_BRAINSTORM_COMPLEXITY` | (unset) | `hooks/brainstorming-gate` | Override *scoped+logged* della classificazione trivial/complesso: `force-complex` forza sempre l'enforcement pieno; `force-trivial` forza il gate silente MA **non** bypassa un secondo segnale forte indipendente (IaC, path-sensibile, multi-repo restano sempre complessi). Ogni uso e' loggato via `devforge_log` (stile toolfail-breakglass, no bypass discrezionale silenzioso). |

Path sensibili sempre complessi indipendentemente dalle dimensioni del diff:
estensione `.tf`/`.hcl`, `hooks/*`, `lib/*gate*`, `lib/review_evidence/*`.
`hooks/plan-gate` e `hooks/plan-gate-write` restano assoluti (non
complexity-aware): gatano atti di planning esplicito (EnterPlanMode,
scrittura design-doc) che per un trivial l'agente semplicemente non compie.
```

### Step 4 — Esegui e osserva il PASS atteso

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/test_reconcile_zero_eccezioni.sh
```

Output atteso:

```
=== skills/siae-brainstorming/SKILL.md — carve-out trivial presente ===
  PASS  menziona 'gate' + 'trivial' nella sezione Scaling
  PASS  NON asserisce più 'si eseguono SEMPRE' senza carve-out (stringa esatta rimossa)
  PASS  la profondità scala esplicitamente (testo aggiornato)
  PASS  Legge di Ferro/HARD-GATE ancora presenti (invariante non rimossa)

=== lib/skills-core.js — riga disambiguation qualificata ===
  PASS  NON asserisce più 'zero eccezioni' senza qualifica trivial/complesso
  PASS  menziona 'trivial' o soglia nella riga disambiguation siae-brainstorming

=== tests/skill-activation/cases.yml — commento allineato ===
  PASS  commento feature-config-change non cita più 'zero eccezioni' come motivazione assoluta

=== hooks/ENV_VARS.md — sezione brainstorming complexity documentata ===
  PASS  DEVFORGE_BRAINSTORM_COMPLEXITY documentato
  PASS  DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES documentato

Total: 9 — PASS: 9 — FAIL: 0
```

Exit code: `0`.

Verifica di non-regressione sulla suite che copre gli invarianti K (Legge di Ferro/HARD-GATE non rimossi da altre skill):

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/compression-regression/assert_behavioral_invariants.sh
```

Output atteso (invariato, nessuna riga in FAIL):

```
Total: 0 — PASS: 0 — FAIL: 0
```

(il conteggio esatto dipende dal numero di assert nel file al momento dell'esecuzione; il criterio di non-regressione è `FAIL: 0`, non un totale fisso).

Verifica anche `node lib/skills-core.js` non genera errori di sintassi dopo l'edit:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && node -e "require('./lib/skills-core.js')" && echo "OK sintassi valida"
```

Output atteso:

```
OK sintassi valida
```

**3f/3g. Memory (fuori dal repo git).** Sovrascrivi `/Users/detomasi/.claude/projects/-Users-detomasi-Library-Mobile-Documents-com-apple-CloudDocs-siae-dev-forge/memory/feedback_brainstorming_always.md` con:

```markdown
---
name: brainstorming-always-mandatory
description: L'utente vuole la PROFONDITA' del brainstorming sempre scalata alla complessita'; sui trivial il gate e' silente, sui complessi il processo resta obbligatorio
type: feedback
---

Il brainstorming parte sempre per ogni task implementativo (feature, bug fix, refactoring, config change, ottimizzazione) NON-trivial. La complessita' determina la PROFONDITA' di ogni step (poche frasi vs paragrafi), non se lo step si esegue — per i task complessi questo resta senza eccezioni.

Per i task **trivial** (1 file, poche righe sotto `DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES`, path non-sensibile, non-IaC — vedi `hooks/ENV_VARS.md`) il gate hook `hooks/brainstorming-gate` non emette piu' nudge/block: il tier "Bassa" collassa a quasi-istantaneo. Multi-file, IaC, path-sensibile (hooks/, lib/*gate*, lib/review_evidence/) o multi-repo restano SEMPRE complessi — mai trivial, indipendentemente dalle dimensioni del diff (design `2026-07-01-devforge-siae-conventions-and-flow`, REQ-DF-04, decisione Lite-present).

**Why:** L'utente aveva osservato che Claude razionalizza per saltare il brainstorming su task "semplici". La riconciliazione 2026-07-01 mantiene questo intento sui task realmente complessi, evitando pero' che il gate rallenti/nudgi su edit banali gia' classificati oggettivamente trivial da un'euristica esplicita (non da giudizio discrezionale dell'agente).

**How to apply:** Non razionalizzare mai autonomamente che un task complesso e' "troppo semplice" per il brainstorming. Se il task e' oggettivamente trivial per la definizione sopra, procedi pure senza design doc formale; altrimenti, anche se sembra banale, il brainstorming va fatto (sara' comunque breve). Sempre produrre un piano con subtask via siae-writing-plans per i task non-trivial.
```

Poi in `MEMORY.md`, riga 10, sostituisci:

```
- [Brainstorming always mandatory](feedback_brainstorming_always.md) — brainstorming per ogni task, zero eccezioni
```

con:

```
- [Brainstorming always mandatory](feedback_brainstorming_always.md) — profondità scala sempre; trivial=gate silente, complessi=processo obbligatorio
```

### Step 5 — Commit

```bash
git add skills/siae-brainstorming/SKILL.md lib/skills-core.js tests/skill-activation/cases.yml hooks/ENV_VARS.md tests/test_reconcile_zero_eccezioni.sh
git commit -m "docs(brainstorming): riconcilia 'zero eccezioni' con lo scaling trivial

Riformula HARD-GATE e tabella Scaling in siae-brainstorming/SKILL.md,
la riga disambiguation in lib/skills-core.js e il commento del caso
feature-config-change in cases.yml: la PROFONDITA' del brainstorming
scala sempre; sui trivial (1 file, poche righe, path non-sensibile,
non-IaC) il gate hook e' silente; sui complessi/IaC/multi-repo il
processo resta obbligatorio senza eccezioni. Documenta
DEVFORGE_BRAINSTORM_COMPLEXITY e DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES
in hooks/ENV_VARS.md. Guard test grep-based previene il ritorno del
testo assoluto senza carve-out (REQ-DF-04)."
```

Nota: il commit non include i file di memoria (`~/.claude/projects/.../memory/`), che sono fuori dal repo git e vanno aggiornati separatamente (Step 3f/3g sopra), non tramite `git commit`.

## Criteri di accettazione

- [ ] `skills/siae-brainstorming/SKILL.md` righe 20-46 (HARD-GATE) non contengono più l'assolutismo senza carve-out; menzionano esplicitamente che sui trivial il gate non forza nudge/block, mentre sui complessi il vincolo resta assoluto.
- [ ] `skills/siae-brainstorming/SKILL.md` righe 50-63 (Scaling) hanno una riga/tier "Trivial" nella tabella con colonna "Gate hook" = "Silente", e la frase "ZERO ECCEZIONI. I 7 step si eseguono SEMPRE" non è più presente testualmente.
- [ ] Il blocco `<EXTREMELY-IMPORTANT>` di chiusura della sezione Scaling resta presente (invariante K non rimossa) ma aggiornato per riferirsi ai task "complessi" invece che a "ogni task".
- [ ] `lib/skills-core.js:421` (o riga vicina dopo l'edit) non contiene più la stringa `zero eccezioni`; la riga disambiguation menziona esplicitamente lo scaling trivial/complesso.
- [ ] `node -e "require('./lib/skills-core.js')"` non solleva errori di sintassi dopo l'edit.
- [ ] `tests/skill-activation/cases.yml` caso `feature-config-change` (righe ~65-68) ha un commento coerente con la nuova policy, non cita più "zero eccezioni" come motivazione assoluta.
- [ ] `hooks/ENV_VARS.md` documenta `DEVFORGE_BRAINSTORM_COMPLEXITY` (valori `force-complex`/`force-trivial`, scoped+logged, non bypassa IaC/path-sensibile) e `DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES` (default 15) in una sezione dedicata.
- [ ] `tests/test_reconcile_zero_eccezioni.sh` esiste, è eseguibile (`chmod +x`), e va da FAIL (Step 2, 8/9 FAIL) a PASS (Step 4, 0/9 FAIL).
- [ ] `bash tests/compression-regression/assert_behavioral_invariants.sh` resta a `FAIL: 0` — zero regressioni sugli invarianti K esistenti (Legge di Ferro, HARD-GATE, checkpoint schema di `siae-brainstorming` e altre skill non toccate da questo task).
- [ ] `/Users/detomasi/.claude/projects/-Users-detomasi-Library-Mobile-Documents-com-apple-CloudDocs-siae-dev-forge/memory/feedback_brainstorming_always.md` riflette la riconciliazione (profondità scala sempre; trivial = gate silente; complessi = processo obbligatorio).
- [ ] `MEMORY.md` riga 10 (bullet `feedback_brainstorming_always.md`) aggiornata con la sintesi riconciliata.
- [ ] Nessun placeholder (`TBD`/`TODO`/`...`/"come sopra"/"simile a") in nessuno dei file toccati.
