# Task 07 — Riscrivi gli heredoc/prompt iniettati agli agent (base dinamica + troncamento)

**Cluster:** B diff PR (REQ-DF-03)
**Dipendenze:** Task 04 (`lib/pr-base-resolver.sh` → `devforge_resolve_pr_base()`) + Task 05 (`lib/diff-truncate.sh` → `devforge_diff_or_summary()`) DEVONO essere completati prima (questo task chiama entrambe le funzioni).

## Goal

Le istruzioni prosa iniettate come `additional_context` a fresh LLM agent (`hooks/pr-gate`, `hooks/post-commit-review`) e il prompt fresh-eyes (`skills/siae-subagent-development/SKILL.md`) non devono più istruire l'agent a eseguire `git diff origin/main...HEAD` letterale: devono istruire a risolvere la base dinamicamente (via `devforge_resolve_pr_base()`) e a troncare i diff grandi (via `devforge_diff_or_summary()`), verificato da un test grep che asserisce l'assenza della stringa letterale `origin/main...HEAD` (e `origin/main)..HEAD` per il caso two-dot) nei tre file.

## File coinvolti

- Modifica: `hooks/pr-gate` righe 205-266 (heredoc `PR_GATE_INSTRUCTIONS`, hardcode a riga 218) + una riga di setup prima del heredoc per calcolare `PR_GATE_RESOLVED_BASE`.
- Modifica: `hooks/post-commit-review` righe 373-421 (heredoc `REVIEW_INSTRUCTIONS`, hardcode a righe 385 e 407) + righe di setup prima del heredoc (dopo riga 371, prima di riga 373) per calcolare `REVIEW_RESOLVED_BASE`.
- Modifica: `skills/siae-subagent-development/SKILL.md` riga 303 (prompt fresh-eyes, hardcode `git diff $(git merge-base HEAD origin/main)..HEAD`).
- Nuovo test: `tests/test_no_literal_origin_main_in_prompts.py`.

**Nota bene (verificato leggendo il codice reale, NON dal design doc):** in `hooks/post-commit-review` le variabili `default_branch` (riga 132) e `BASE_BRANCH` (riga 181) citate come "già calcolate" NON sono riusabili letteralmente al punto di costruzione del heredoc (riga 373): `default_branch` è `local` dentro la funzione `_devforge_pr_author_emails_json` (righe 131-170, out of scope quando la funzione ritorna) e `BASE_BRANCH` è popolata SOLO dentro il branch `git push` con PR esistente (righe 173-200), mentre il heredoc `REVIEW_INSTRUCTIONS` viene costruito per ENTRAMBI i path `gh pr create` e `git push` (guardia riga 339-340). Questo task quindi introduce una variabile nuova `REVIEW_RESOLVED_BASE` calcolata subito prima del heredoc chiamando `devforge_resolve_pr_base()` (che internamente gestisce sia il caso "PR esiste" sia "nessuna PR ancora" con la stessa precedenza documentata in Task 04), invece di riferirsi a variabili di scope incompatibile.

## Step TDD

### Step 1 — Scrivi il test fallente (COMPLETO)

Crea `tests/test_no_literal_origin_main_in_prompts.py`:

```python
"""Guard: le istruzioni prosa iniettate come additional_context a fresh LLM
agent (o come prompt subagent) NON devono istruire l'agent a eseguire
`git diff origin/main...HEAD` letterale — su un branch derivato da
`sviluppo`/`release/*` quel comando produce un diff sbagliato (README/gotcha
REQ-DF-03). L'istruzione corretta è risolvere la base dinamicamente via
`devforge_resolve_pr_base()` / `$PARENT_BRANCH` e troncare i diff grandi via
`devforge_diff_or_summary()`.

Verificato leggendo hooks/pr-gate, hooks/post-commit-review e
skills/siae-subagent-development/SKILL.md — i tre siti noti che hardcodavano
`origin/main` nella prosa iniettata agli agent (fix REQ-DF-03 / Task 07).
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).parent.parent

FILES = [
    REPO / "hooks" / "pr-gate",
    REPO / "hooks" / "post-commit-review",
    REPO / "skills" / "siae-subagent-development" / "SKILL.md",
]

# Pattern letterali che indicano un hardcode "diffa sempre da origin/main"
# nella prosa rivolta all'agent, a prescindere dal branch di lavoro reale.
FORBIDDEN_SNIPPETS = [
    "git diff origin/main...HEAD",
    "git diff origin/main..HEAD",
    "git merge-base HEAD origin/main)..HEAD",
]


def test_no_hardcoded_origin_main_diff_in_agent_prompts():
    offenders = []
    for f in FILES:
        text = f.read_text(errors="ignore")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                offenders.append(f"{f.relative_to(REPO)}: {snippet!r}")
    assert not offenders, (
        "Prosa rivolta all'agent hardcoda ancora origin/main come base "
        "letterale (rompe su branch derivati da sviluppo/release): "
        + "; ".join(offenders)
    )


def test_pr_gate_instructs_dynamic_base_resolution():
    text = (REPO / "hooks" / "pr-gate").read_text()
    assert "devforge_resolve_pr_base" in text, (
        "pr-gate deve richiamare il resolver condiviso prima di costruire "
        "l'istruzione prosa per l'agent"
    )


def test_post_commit_review_instructs_dynamic_base_resolution():
    text = (REPO / "hooks" / "post-commit-review").read_text()
    assert "devforge_resolve_pr_base" in text, (
        "post-commit-review deve richiamare il resolver condiviso prima di "
        "costruire l'istruzione prosa per l'agent"
    )


def test_fresh_eyes_prompt_uses_resolved_parent_branch():
    text = (
        REPO / "skills" / "siae-subagent-development" / "SKILL.md"
    ).read_text()
    assert "$PARENT_BRANCH" in text, (
        "il prompt fresh-eyes deve usare una base risolta ($PARENT_BRANCH), "
        "non origin/main hardcoded"
    )
```

### Step 2 — Esegui e verifica che fallisce

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && python3 -m pytest tests/test_no_literal_origin_main_in_prompts.py -v
```

Output atteso (FAIL, 4 failed):
```
tests/test_no_literal_origin_main_in_prompts.py::test_no_hardcoded_origin_main_diff_in_agent_prompts FAILED
tests/test_no_literal_origin_main_in_prompts.py::test_pr_gate_instructs_dynamic_base_resolution FAILED
tests/test_no_literal_origin_main_in_prompts.py::test_post_commit_review_instructs_dynamic_base_resolution FAILED
tests/test_no_literal_origin_main_in_prompts.py::test_fresh_eyes_prompt_uses_resolved_parent_branch FAILED
============================== 4 failed in 0.XXs ===============================
```

### Step 3 — Implementa (COMPLETO)

**3a. `hooks/pr-gate`** — inserisci il calcolo della base risolta subito prima del heredoc esistente (dopo la riga `devforge_log "pr_gate" "success" "{\"check\":\"security_scan_clean\"}"` e prima di `read -r -d '' PR_GATE_INSTRUCTIONS << 'INSTRUCTIONS_EOF' || true`), poi riscrivi il blocco "Step 0" del heredoc:

Sostituisci (righe 202-222 circa):
```bash
devforge_log "pr_gate" "success" "{\"check\":\"security_scan_clean\"}"

read -r -d '' PR_GATE_INSTRUCTIONS << 'INSTRUCTIONS_EOF' || true
# DevForge PR Gate — Security scan PASSED

Il security scan automatico e' passato (nessun secret nel diff).

## AZIONE OBBLIGATORIA — Dispatch Agent Review

DEVI dispatchare ENTRAMBI gli agent ADESSO, PRIMA di eseguire gh pr create.
Questo NON e' opzionale. NON e' un suggerimento. E' un gate bloccante.

### Step 0: Ottieni il diff (OBBLIGATORIO)

```bash
git diff origin/main...HEAD
```

Salva l'output. Lo passerai nel prompt di ENTRAMBI gli agent.
NON passare i path dei file — passa il DIFF TESTUALE. Leggere file interi spreca token.
```

con:
```bash
devforge_log "pr_gate" "success" "{\"check\":\"security_scan_clean\"}"

source "${PLUGIN_ROOT}/lib/pr-base-resolver.sh" 2>/dev/null || true
PR_GATE_RESOLVED_BASE=$(devforge_resolve_pr_base 2>/dev/null || echo "main")

read -r -d '' PR_GATE_INSTRUCTIONS_TEMPLATE << 'INSTRUCTIONS_EOF' || true
# DevForge PR Gate — Security scan PASSED

Il security scan automatico e' passato (nessun secret nel diff).

## AZIONE OBBLIGATORIA — Dispatch Agent Review

DEVI dispatchare ENTRAMBI gli agent ADESSO, PRIMA di eseguire gh pr create.
Questo NON e' opzionale. NON e' un suggerimento. E' un gate bloccante.

### Step 0: Ottieni il diff (OBBLIGATORIO)

NON dare per scontato che la base sia `origin/main`: il branch di lavoro puo'
derivare da `sviluppo` o da `release/*`. La base corretta e' gia' stata
risolta per te:

```bash
git diff __PR_GATE_RESOLVED_BASE__...HEAD
```

Se il diff supera ~2000 righe, NON leggerlo tutto: usa prima
`git diff --stat __PR_GATE_RESOLVED_BASE__...HEAD` e poi i singoli file solo
on-demand (vedi lib/diff-truncate.sh — evita loop/hang su diff enormi).

Salva l'output. Lo passerai nel prompt di ENTRAMBI gli agent.
NON passare i path dei file — passa il DIFF TESTUALE. Leggere file interi spreca token.
INSTRUCTIONS_EOF

PR_GATE_INSTRUCTIONS="${PR_GATE_INSTRUCTIONS_TEMPLATE//__PR_GATE_RESOLVED_BASE__/$PR_GATE_RESOLVED_BASE}"
```

**3b. `hooks/post-commit-review`** — inserisci il calcolo della base risolta dopo la riga `escape_for_json() { devforge_sanitize_json_str "$1"; }` (riga 371) e prima di `read -r -d '' REVIEW_INSTRUCTIONS << 'REVIEW_EOF' || true` (riga 373), poi riscrivi i due punti hardcoded (righe 383-386 e 405-407):

Sostituisci (righe 369-421):
```bash
# JSON escaping is centralized in lib/logger.sh :: devforge_sanitize_json_str.
# Local alias for readability in this file.
escape_for_json() { devforge_sanitize_json_str "$1"; }

read -r -d '' REVIEW_INSTRUCTIONS << 'REVIEW_EOF' || true
# DevForge PR Auto-Review

Una PR e' stata creata o il branch e' stato pushato. DEVI lanciare automaticamente questi due agent in parallelo.

## REGOLA CRITICA: Passa il DIFF, non i path dei file

Gli agent di review DEVONO ricevere il diff testuale nel prompt, NON i path dei file.
Passare i path causa la lettura dei file interi — spreco di token enorme.

**Step preliminare obbligatorio:**
```bash
git diff origin/main...HEAD
```

Salva l'output di questo comando. Lo passerai nel prompt di ENTRAMBI gli agent.

## 1. Code Review (siae-devforge:code-reviewer)

Lancia l'agent con subagent_type="siae-devforge:code-reviewer".
Nel prompt INCLUDI il diff testuale completo, NON i path dei file.
L'agent eseguira' la review a 6 punti SOLO sul diff: conformita' al piano, code standards,
security, error handling, test coverage, architettura.

## 2. Security Check (siae-devforge:siae-security)

Invoca la skill siae-devforge:siae-security per verificare SOLO il diff:
- Nessun secret/credenziale nel diff
- IAM least privilege se ci sono policy AWS
- OWASP Top 10 compliance
- PII handling per dati autori/artisti SIAE

## Istruzioni

1. Ottieni il diff completo: `git diff origin/main...HEAD`
2. Lancia ENTRAMBI in parallelo usando il tool Agent:
   - Agent con subagent_type="siae-devforge:code-reviewer" — passa il DIFF nel prompt
   - Invoca Skill("siae-devforge:siae-security") per il security check — passa il DIFF
3. Mostra i risultati quando arrivano
4. Se trovano problemi critici, segnalali PRIMA di qualsiasi altra azione

IMPORTANTE: Analizza SOLO il diff — NON leggere file interi. Gli agent NON devono usare
Read o Glob per leggere file completi. Tutto il contesto necessario e' nel diff.
Se un agent ha bisogno di contesto aggiuntivo (es. design doc),
passa il path nel prompt ma SOLO per i criteri di accettazione, non per rileggere il codice.

NON chiedere all'utente se vuole la review — e' automatica.
NON saltare questo step — ogni PR viene revisionata.
REVIEW_EOF
```

con:
```bash
# JSON escaping is centralized in lib/logger.sh :: devforge_sanitize_json_str.
# Local alias for readability in this file.
escape_for_json() { devforge_sanitize_json_str "$1"; }

source "${PLUGIN_ROOT}/lib/pr-base-resolver.sh" 2>/dev/null || true
REVIEW_RESOLVED_BASE=$(devforge_resolve_pr_base 2>/dev/null || echo "main")

read -r -d '' REVIEW_INSTRUCTIONS_TEMPLATE << 'REVIEW_EOF' || true
# DevForge PR Auto-Review

Una PR e' stata creata o il branch e' stato pushato. DEVI lanciare automaticamente questi due agent in parallelo.

## REGOLA CRITICA: Passa il DIFF, non i path dei file

Gli agent di review DEVONO ricevere il diff testuale nel prompt, NON i path dei file.
Passare i path causa la lettura dei file interi — spreco di token enorme.

**Step preliminare obbligatorio:**

NON dare per scontato che la base sia `origin/main`: il branch puo' derivare
da `sviluppo` o `release/*`. La base corretta e' gia' stata risolta:

```bash
git diff __REVIEW_RESOLVED_BASE__...HEAD
```

Se il diff supera ~2000 righe, usa prima `git diff --stat __REVIEW_RESOLVED_BASE__...HEAD`
e poi i singoli file solo on-demand (vedi lib/diff-truncate.sh — evita loop/hang).

Salva l'output di questo comando. Lo passerai nel prompt di ENTRAMBI gli agent.

## 1. Code Review (siae-devforge:code-reviewer)

Lancia l'agent con subagent_type="siae-devforge:code-reviewer".
Nel prompt INCLUDI il diff testuale completo, NON i path dei file.
L'agent eseguira' la review a 6 punti SOLO sul diff: conformita' al piano, code standards,
security, error handling, test coverage, architettura.

## 2. Security Check (siae-devforge:siae-security)

Invoca la skill siae-devforge:siae-security per verificare SOLO il diff:
- Nessun secret/credenziale nel diff
- IAM least privilege se ci sono policy AWS
- OWASP Top 10 compliance
- PII handling per dati autori/artisti SIAE

## Istruzioni

1. Ottieni il diff completo con la base risolta via `devforge_resolve_pr_base()` (Task 04), troncando con `devforge_diff_or_summary()` (Task 05) se enorme.
2. Lancia ENTRAMBI in parallelo usando il tool Agent:
   - Agent con subagent_type="siae-devforge:code-reviewer" — passa il DIFF nel prompt
   - Invoca Skill("siae-devforge:siae-security") per il security check — passa il DIFF
3. Mostra i risultati quando arrivano
4. Se trovano problemi critici, segnalali PRIMA di qualsiasi altra azione

IMPORTANTE: Analizza SOLO il diff — NON leggere file interi. Gli agent NON devono usare
Read o Glob per leggere file completi. Tutto il contesto necessario e' nel diff.
Se un agent ha bisogno di contesto aggiuntivo (es. design doc),
passa il path nel prompt ma SOLO per i criteri di accettazione, non per rileggere il codice.

NON chiedere all'utente se vuole la review — e' automatica.
NON saltare questo step — ogni PR viene revisionata.
REVIEW_EOF

REVIEW_INSTRUCTIONS="${REVIEW_INSTRUCTIONS_TEMPLATE//__REVIEW_RESOLVED_BASE__/$REVIEW_RESOLVED_BASE}"
```

**3c. `skills/siae-subagent-development/SKILL.md`** — sostituisci la riga 303:

Sostituisci:
```
1. Usa `git diff $(git merge-base HEAD origin/main)..HEAD` per TUTTI i cambiamenti
```

con:
```
1. Risolve la base con `devforge_resolve_pr_base()` (`lib/pr-base-resolver.sh` — non assume `origin/main`: usa la PR aperta se esiste, altrimenti merge-base contro il default branch reale) e usa `git diff $PARENT_BRANCH...HEAD` per TUTTI i cambiamenti. Se il diff e' grande, prima `git diff --stat $PARENT_BRANCH...HEAD`, poi i file uno a uno on-demand.
```

### Step 4 — Esegui e verifica che passa

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && python3 -m pytest tests/test_no_literal_origin_main_in_prompts.py -v && bash -n hooks/pr-gate && bash -n hooks/post-commit-review
```

Output atteso:
```
tests/test_no_literal_origin_main_in_prompts.py::test_no_hardcoded_origin_main_diff_in_agent_prompts PASSED
tests/test_no_literal_origin_main_in_prompts.py::test_pr_gate_instructs_dynamic_base_resolution PASSED
tests/test_no_literal_origin_main_in_prompts.py::test_post_commit_review_instructs_dynamic_base_resolution PASSED
tests/test_no_literal_origin_main_in_prompts.py::test_fresh_eyes_prompt_uses_resolved_parent_branch PASSED
============================== 4 passed in 0.XXs ===============================
```
(`bash -n` non stampa nulla se la sintassi è valida — nessun output = successo.)

### Step 5 — Commit

```bash
git add hooks/pr-gate hooks/post-commit-review skills/siae-subagent-development/SKILL.md tests/test_no_literal_origin_main_in_prompts.py
git commit -m "fix(gates): risolvi la base dinamicamente nei prompt iniettati agli agent, no più origin/main hardcoded"
```

## Criteri di accettazione

- [ ] `hooks/pr-gate` non contiene più `git diff origin/main...HEAD` letterale nel heredoc; usa `devforge_resolve_pr_base()` per calcolare `PR_GATE_RESOLVED_BASE` prima di costruire l'istruzione (AC1 REQ-DF-03: base = merge-base del target, non main).
- [ ] `hooks/post-commit-review` non contiene più `git diff origin/main...HEAD` letterale nel heredoc (righe ex-385/407); usa `devforge_resolve_pr_base()` per calcolare `REVIEW_RESOLVED_BASE` invece di riusare variabili fuori scope (AC1/AC2 REQ-DF-03).
- [ ] `skills/siae-subagent-development/SKILL.md:303` non contiene più `git merge-base HEAD origin/main)..HEAD`; usa `$PARENT_BRANCH` risolto + guida paginazione per diff grandi (AC1/AC3 REQ-DF-03).
- [ ] Entrambi gli heredoc riscritti includono guida esplicita di troncamento (`--stat` prima dei file interi) per diff grandi, mirror dell'intento di `lib/diff-truncate.sh` (AC3 REQ-DF-03: no loop/hang).
- [ ] `python3 -m pytest tests/test_no_literal_origin_main_in_prompts.py -v` PASS (4/4).
- [ ] `bash -n hooks/pr-gate` e `bash -n hooks/post-commit-review` non riportano errori di sintassi.
- [ ] Nessuna modifica al linguaggio "gate bloccante" di `hooks/pr-gate:210-213` in questo task — quella modifica (advisory language) è a carico di Task 12, per non sovrapporre le due edit sullo stesso blocco (nota di coordinamento nel design REQ-DF-05).
