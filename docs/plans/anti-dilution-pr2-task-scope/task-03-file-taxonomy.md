---
task: 03
title: lib/file-taxonomy.sh — classificazione estensioni (ADR-005)
size: S
blocks: [05, 06]
---

# Task 3 — `lib/file-taxonomy.sh`

Classificazione centralizzata delle estensioni file. Sostituisce le regex
duplicate in tdd-gate e brainstorming-gate. Risolve ambiguità su `.sh/.bash`
(deny-by-default, opt-in `DEVFORGE_BASH_TDD=1`).

## API

```bash
# devforge_file_requires_tdd FILE_PATH
# Return 0 if file needs TDD gate, 1 otherwise
devforge_file_requires_tdd() {
    local f="$1"
    # exclude paths (test/, tests/, __tests__, *.spec.*, ...)
    _devforge_file_excluded "$f" && return 1
    # check extension class
    case "$f" in
        *.java|*.ts|*.tsx|*.js|*.jsx|*.py|*.vue|*.go|*.kt|*.rb|*.rs|*.swift|*.scala|*.sql) return 0 ;;
        *.sh|*.bash) [ "${DEVFORGE_BASH_TDD:-0}" = "1" ] && return 0 || return 1 ;;
        *) return 1 ;;
    esac
}

# devforge_file_requires_brainstorming FILE_PATH
# Superset di TDD + IaC (.tf, .hcl)
devforge_file_requires_brainstorming() {
    local f="$1"
    _devforge_file_excluded "$f" && return 1
    case "$f" in
        *.tf|*.hcl) return 0 ;;
        *) devforge_file_requires_tdd "$f" ;;
    esac
}

# devforge_file_is_config_only FILE_PATH
# Config file: no gate applicato per default
devforge_file_is_config_only() {
    case "$1" in
        *.yaml|*.yml|*.json|*.toml|*.ini|*.properties) return 0 ;;
        *) return 1 ;;
    esac
}

# _devforge_file_excluded FILE_PATH
# Internal: path exclusion (test files, docs, plans)
_devforge_file_excluded() {
    local f="$1"
    # test paths
    echo "$f" | grep -qE "(^|/)(test|tests|__tests__|spec)/" && return 0
    # test file patterns
    echo "$f" | grep -qE "(Test|IT)\.(java|kt)$" && return 0
    echo "$f" | grep -qE "\.(spec|test)\." && return 0
    echo "$f" | grep -qE "(^|/)test_.*\.py$" && return 0
    echo "$f" | grep -qE "_test\.go$" && return 0
    # docs/plans
    echo "$f" | grep -qE "(^|/)(docs|plans|evals)/" && return 0
    # markdown always excluded
    echo "$f" | grep -qE "\.md$" && return 0
    return 1
}
```

## Tassonomia

| Classe | Estensioni | Trigger gate |
|---|---|---|
| tdd_required | .java .ts .tsx .js .jsx .py .vue .go .kt .rb .rs .swift .scala .sql | tdd-gate + brainstorming-gate |
| brainstorming_only | .tf .hcl | brainstorming-gate (no TDD — valida via plan/lint) |
| config_only | .yaml .yml .json .toml .ini .properties | no gate |
| ambiguous | .sh .bash | opt-in via `DEVFORGE_BASH_TDD=1` |
| excluded (always) | .md, paths con test/tests/__tests__/spec, *.spec.*, docs/, plans/ | no gate |

## Note decisionali

- **Ambiguous deny-by-default**: hook DevForge sono bash → se attivassimo
  il gate su .sh, entreremmo in loop infinito sui nostri stessi hook.
  Opt-in via `DEVFORGE_BASH_TDD=1` per repo SIAE che usano bash come
  codice di produzione.
- **Config files no gate**: yaml/json sono strutturali, validati da schema
  o lint, non da TDD.
- **SQL come tdd_required**: migrazioni hanno test (dry-run / plan /
  CREATE vs DROP symmetry), rientrano nel contratto TDD.

## Acceptance

- [ ] `lib/file-taxonomy.sh` creato con 3 API pubbliche + 1 internal
- [ ] Test `tests/lib/test_file_taxonomy.sh` ≥25 casi
  - [ ] tutte le estensioni classificate correttamente
  - [ ] exclusion patterns (test/, .spec., docs/, ...)
  - [ ] DEVFORGE_BASH_TDD=1 → .sh triggera TDD
  - [ ] DEVFORGE_BASH_TDD=0 → .sh no TDD
  - [ ] unknown extension → no gate
- [ ] Regex equivalenti a quelle attuali in tdd-gate + brainstorming-gate
  (verifica cross-reference pre-migration)

## Out of scope

- Integrazione nei gate → task 5+ (chiamare `devforge_file_requires_tdd` al posto del regex match)
