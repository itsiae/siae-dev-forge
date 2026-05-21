---
name: siae-functional-bug-hunter
description: Invoca la skill `siae-functional-bug-hunter` per un audit funzionale statico, multi-repo, cross-stack. Ingerisce uno o più repository root, genera bug hypothesis dalla pattern matrix stack-aware, filtra per path feasibility, emette `qa_report.md` deterministico raggruppato per user-journey. Invocazione manuale only — niente hook, niente auto-trigger. Modes: interactive (TTY pausa), strict (CI no-pausa), report-only (partial low-confidence). Vedi `skills/siae-functional-bug-hunter/SKILL.md` per il contratto completo.
argument-hint: '{"roots":["/abs/path/repoA"],"mode":"interactive|strict|report-only","lang":"en|it"}'
---

# /siae-functional-bug-hunter

Static, multi-repo, cross-stack functional bug hunter. Lancia la skill
`siae-functional-bug-hunter` con un argomento JSON conforme al contratto
Inputs documentato in `skills/siae-functional-bug-hunter/SKILL.md`.

## Esempi

```
/siae-functional-bug-hunter {"roots":["/Users/me/repos/sport-gestione-licenze-service"],"mode":"interactive","lang":"it"}
```

```
/siae-functional-bug-hunter {"roots":["/abs/path/repoA","/abs/path/repoB"],"mode":"strict","max_wallclock_minutes":30,"lang":"en"}
```

## Modes

| mode | quando | comportamento STOP |
|---|---|---|
| `interactive` | sessione TTY (workstation dev) | PAUSE su STOP event |
| `strict` | CI / batch / non-TTY | CONTINUE con `low_confidence` flag |
| `report-only` | primo scan codebase sconosciuta | DEGRADE su dependency closure, CONTINUE altrove |

Dispatch matrix completa: `skills/siae-functional-bug-hunter/references/runtime_modes.md`.

## Quando NON usarlo

- Generazione di test automatici (Playwright, JUnit, pytest, ecc.) — out of scope.
- Audit SAST/CVE-only senza manifestazione funzionale — la skill filtra esplicitamente questi findings.
- Performance / load / a11y / UX — usa skill dedicate.
- Refactoring o scrittura sul target repo — la skill è read-only.

## Output

Tutti i file sotto `output_dir` (default `.fbh/runs/<ISO8601>-<scope_hash>/`):
`qa_report.md` (primary), `qa_report.json` (canonical), `hypotheses.json`,
`inventory.json`, `entry_points.json`, `coverage.md`, `open_questions.md`,
`run_manifest.json`, `audit_log.jsonl`.

## Prerequisiti

- Python 3.9+, `jq` ≥1.6 (o fallback Python helper bundled), `git`.
- `tree-sitter` grammar opzionale (fallback regex se assente — segnalato in
  `coverage.md`).
- Bash 4+ o POSIX fallback.

Probe automatico in Phase 0 via `scripts/preflight.sh`.
