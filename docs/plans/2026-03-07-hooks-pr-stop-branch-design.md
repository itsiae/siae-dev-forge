# Hooks Estesi: pr-gate, stop-gate, branch-check — Design

> **Data:** 2026-03-07
> **Autore:** SIAE AI Competence Center
> **Versione:** 1.0
> **SP stimati:** 3

---

## Contesto

Il sistema hook attuale di siae-devforge ha 3 hook:
- `SessionStart` → inietta `using-devforge`
- `PreToolUse:Bash` → quality gate su `git commit` (5 check)
- `PostToolUse:Skill` → activity log

**Problema identificato:** due comportamenti critici non vengono mai enforced automaticamente:
1. Security review prima di aprire una PR — `siae-finishing-branch` viene quasi mai invocata
2. Verifica prima di dichiarare "fatto" — Claude può fare completion claim senza evidenza
3. Brainstorming prima di creare un branch feature — nessun gate attuale

---

## Goal

Aggiungere 3 hook automatici che non dipendono dalla disciplina del developer:
1. **`pr-gate`** — security scan prima di `gh pr create`
2. **`stop-gate`** — verification reminder prima di ogni stop di Claude
3. **branch-check in `pre-commit`** — warning se branch feature senza design doc

---

## Decisioni Architetturali

**Approccio scelto: B — Script separati**

Motivazione: le 3 responsabilità sono semanticamente distinte. Separare i file
preserva il `pre-commit` esistente (funzionante, testato) e rende ogni hook
autonomo e testabile. L'approccio A (monolitico) avrebbe mescolato logiche diverse
in un unico script difficile da mantenere.

**Meccanismo comune:** tutti gli hook lavorano via `additionalContext` injection.
Il hook bash inietta istruzioni che Claude legge ed esegue. Nessun agente shell
reale, tutto context-driven — stesso pattern del `pre-commit` esistente.

---

## Design Dettagliato

### Hook 1: `pr-gate` (PreToolUse:Bash)

**Trigger:** comando contiene `gh pr create` o `gh pr edit`

**Flusso:**
1. Legge TOOL_COMMAND da stdin JSON
2. Se non match → exit 0 silenzioso
3. Se match → inietta istruzioni di security scan:
   - `git diff $(git merge-base HEAD origin/sviluppo 2>/dev/null || git merge-base HEAD origin/main)...HEAD --name-only`
   - Check su file modificati: secrets, IAM `*`, PII hardcoded, S3 pubblici
   - Pre-flight card: CRITICO blocca, ALTO warn+conferma, nessun issue → procedi

**File:** `hooks/pr-gate`

### Hook 2: `stop-gate` (Stop)

**Trigger:** ogni fine turno di Claude (Stop event)

**Flusso:**
- Inietta sempre un context minimale (3 righe):
  "Se il tuo ultimo output contiene claim di completamento (fatto, fixato,
   completato, funziona, done, fixed, pass, PASS), DEVI eseguire
   siae-verification prima di fermarti."
- Claude valuta se si applica: sì → esegue protocollo, no → ignora silenziosamente

**File:** `hooks/stop-gate`

### Hook 3: branch-check (estensione `pre-commit`)

**Trigger:** comando contiene `git checkout -b` o `git switch -c`

**Flusso:**
1. Estrai JIRA ID con regex `[A-Z]+-[0-9]+` dal nome branch
2. Se NO match → skip silenzioso (exit 0)
3. Se match → cerca `docs/plans/*{JIRA-ID}*design.md`
   - Trovato → procedi silenziosamente
   - Non trovato → inietta warning (non blocca mai):
     "Branch feature/{JIRA-ID}-* senza design doc in docs/plans/.
      Hai eseguito siae-brainstorming? Procedo comunque."

**Modifica:** `hooks/pre-commit` (+~25 righe)

---

## Gestione Errori

Principio comune: **mai bloccare per errore tecnico dell'hook**.

| Scenario | Comportamento |
|----------|--------------|
| Script crasha / exit non-zero | Claude Code ignora, procede normalmente |
| `git diff` fallisce (non in repo) | skip silenzioso, exit 0 |
| `docs/plans/` non esiste | skip check design doc, exit 0 |
| stdin JSON malformato | exit 0 senza output |
| Stop senza contesto rilevante | injection minimale, Claude ignora |
| `gh pr create` su repo senza `sviluppo` | fallback: `git merge-base HEAD origin/main` |
| Branch senza JIRA ID | skip silenzioso, nessun avviso |

---

## Modifiche a `hooks.json`

```json
{
  "hooks": {
    "SessionStart": [ ... esistente ... ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' pre-commit",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' pr-gate",
            "timeout": 15
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' stop-gate",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [ ... esistente ... ]
  }
}
```

---

## Testing

Nuova sezione "Hook Validation" in `tests/run-all.sh`:

1. `pr-gate` esiste ed è eseguibile
2. `stop-gate` esiste ed è eseguibile
3. `hooks.json` contiene entry per `pr-gate` e `stop-gate`
4. `pre-commit` gestisce `git checkout -b` senza crash:
   - Input: `{"command":"git checkout -b feature/SPORT-456-test"}` → output JSON valido
   - Input: `{"command":"git checkout -b fix/no-jira-id"}` → exit 0 silenzioso

---

## Criteri di Accettazione

- [ ] `hooks/pr-gate` intercetta `gh pr create` e inietta security scan instructions
- [ ] `hooks/stop-gate` inietta verification reminder su ogni Stop
- [ ] `hooks/pre-commit` gestisce `git checkout -b` con JIRA ID check
- [ ] Branch senza JIRA ID → nessun output, exit 0
- [ ] `hooks.json` aggiornato con 2 nuove entry (pr-gate, Stop)
- [ ] `tests/run-all.sh` ha sezione Hook Validation con 4 test
- [ ] Test suite: tutti i test passano (attuale 65 + nuovi hook tests)
- [ ] Nessun hook blocca per errore tecnico (graceful degradation)

---

## File Modificati

| File | Tipo | Descrizione |
|------|------|-------------|
| `hooks/pr-gate` | NUOVO | Security scan pre-PR |
| `hooks/stop-gate` | NUOVO | Verification reminder pre-stop |
| `hooks/pre-commit` | MODIFICA | +branch-check per git checkout -b |
| `hooks/hooks.json` | MODIFICA | +pr-gate entry, +Stop entry |
| `tests/run-all.sh` | MODIFICA | +Hook Validation section |
