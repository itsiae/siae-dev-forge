# Phase 2 — Strategy

## Purpose
Selezionare in modo deterministico il framework di test target per ciascuno
stack rilevato in Phase 1 e loggare la rationale in `.code-coverage/decisions.log`.

Single source of truth: `assets/stack-matrix.json`. NESSUNA scelta di framework
è euristica: ogni lookup deve risolversi via la matrice.

---

## Input

- `<repo>/.code-coverage/stack.json` prodotto da `scripts/detect_stack.py`
- `assets/stack-matrix.json`
- `assets/priority-rules.json` (per skip patterns e ordering constants)

## Output

Una entry per ciascun workspace/modulo in `decisions.log`:

```
[phase2] workspace=<path> stack=<lang> framework=<fw> reason=<vitest-first|jest-pinned|matrix-lookup>
```

E un dizionario in-memory `framework_by_workspace` consumato da Phase 5.

---

## Decision tree — Vitest-first (Principio 4)

Per ogni workspace JS/TS:

```mermaid
graph TD
    Start[Workspace JS/TS] --> A{jest.config.{ts,js,mjs,cjs} esiste?}
    A -->|Yes| UseJest[framework = jest<br/>reason = jest-config-present]
    A -->|No| B{package.json scripts.test contiene 'jest'<br/>AND vitest NOT in devDeps?}
    B -->|Yes| UseJest2[framework = jest<br/>reason = jest-script-no-vitest]
    B -->|No| C{constraints.json elenca<br/>CJS incompatibility?}
    C -->|Yes| UseJest3[framework = jest<br/>reason = cjs-constraint]
    C -->|No| D{constraints.json elenca<br/>legacy-jest?}
    D -->|Yes| UseJest4[framework = jest<br/>reason = legacy-constraint]
    D -->|No| UseVitest[framework = vitest<br/>reason = vitest-first-default]
```

Tutte le altre stack (Python, Java, Kotlin, Go, Rust, C#, Flutter) → lookup
diretto in `assets/stack-matrix.json` per `framework`, `coverage_command`,
`report_format`. NON applicare logica oltre la matrice.

---

## Lambda extension (JS/TS)

Se `stack.json.is_lambda == true` per il workspace:
- Template variant = `vitest-lambda-handler` per file matching pattern in
  `priority-rules.json.lambda_handler_globs` (default: `*handler.ts`, `*lambda.ts`).
- Tutti gli altri file del workspace usano il template `vitest` standard.

---

## Monorepo handling

Se `stack.json.monorepo == true`:
- Itera su `stack.json.workspaces[]` (path relativi al repo root).
- Applica il decision tree per OGNI workspace indipendentemente.
- Aggrega `framework_by_workspace` per le Phase successive.

Workspace con `framework == "unknown"` → loggato in `decisions.log` come
`[phase2] workspace=<path> skipped reason=unsupported-language` e omesso
da Phase 5. Block 4 in OUTPUT elencherà tutti i workspace skippati.

---

## Validazione

Al termine della Phase 2, prima di entrare in Phase 3:

```python
import json
stack = json.loads(open(f"{REPO}/.code-coverage/stack.json").read())
selected = framework_by_workspace  # built sopra

# Gate: se TUTTI i workspace sono unsupported → Block 4 + END
if all(v == "unknown" for v in selected.values()):
    emit_block_4_and_end("All workspaces use unsupported languages")
```

Persisti `framework_by_workspace` in `.code-coverage/strategy.json` per
traceability cross-session.
