# Task 08 — Patch lib/phase1-discover.sh + lib/state-schema.json

**Status:** `[PENDING]`
**Depends on:** task-03
**Estimate:** 10 min
**Files:**
- `skills/code-coverage/lib/phase1-discover.sh` (PATCH: aggiungi parallel detect_jest_incompat)
- `skills/code-coverage/lib/state-schema.json` (PATCH: schema additions)

## Goal

Phase 1 discovery deve lanciare `detect_jest_incompat.py` in parallelo con altri detector quando `package.json` presente. Cache gating via `is_cache_valid` vs `STACK_PINNACLE`.

State schema aggiornato per documentare nuovi artifact: `jest-compat.json`, `migration-report.json`, `migration-snapshot/`, `overrides.json`, e nuovo campo `migrate` in `strategy.json.framework_by_workspace[].migrate`.

## Steps

### A. Patch phase1-discover.sh

Leggere `skills/code-coverage/lib/phase1-discover.sh`. Trovare il blocco con il wait loop dei PIDS (cerca `for pid in "${PIDS[@]}"`) e il successivo `echo "[phase1] discovery complete"`.

Inserire IMMEDIATAMENTE PRIMA del wait loop:

```bash
# Phase 2 pre-compute: detect_jest_incompat runs in parallel with other
# detectors so Phase 2 can read jest-compat.json without an extra wait.
# Bug-fix 2026-05-28: Vitest-first decision lives here.
if [ -f "$REPO/package.json" ] || find "$REPO" -maxdepth 4 -name package.json -not -path '*/node_modules/*' -print -quit 2>/dev/null | grep -q .; then
  if is_cache_valid "$REPO/.code-coverage/jest-compat.json" "$STACK_PINNACLE"; then
    echo "[cache] jest-compat.json hit"
  else
    python3 "$SKILL_DIR/scripts/detect_jest_incompat.py" "$REPO" \
      > "$REPO/.code-coverage/jest-compat.json" 2>&1 &
    PIDS+=($!)
  fi
fi
```

Verifica:
- `$REPO`, `$SKILL_DIR`, `$STACK_PINNACLE`, `$PIDS`, `is_cache_valid` devono essere già in scope (sono nelle linee precedenti del file).
- Se nomi variabili differenti, allineare a quelli usati nel file.

### B. Patch lib/state-schema.json

Leggere `skills/code-coverage/lib/state-schema.json`. Aggiungere (additive, no breaking change):

```json
{
  "strategy.json": {
    "framework_by_workspace": {
      "<workspace_rel_path>": {
        "framework": "vitest | jest | <other>",
        "reason": "<decision_reason>",
        "migrate": "boolean (NEW: triggers Phase 4b when true)"
      }
    }
  },
  "jest-compat.json": {
    "doc": "Output of detect_jest_incompat.py. Per-workspace Vitest/Jest compatibility verdict.",
    "version": "string",
    "workspaces": {
      "<rel>": {
        "has_jest_artifacts": "bool",
        "jest_artifacts": ["string"],
        "incompatibility_signals": ["I1..I10"],
        "force_jest": "bool",
        "force_jest_reason": "string|null",
        "decision": "vitest-default | vitest-migrate | jest-incompat | jest-forced",
        "decision_reason": "string"
      }
    },
    "error": "string|null"
  },
  "migration-report.json": {
    "doc": "Output of migrate_jest_to_vitest.py. Per-workspace migration outcome.",
    "started_at": "epoch seconds",
    "workspaces": [{
      "workspace": "string",
      "status": "ok | refused | install-failed | install-timeout | verification-failed | internal-error",
      "pm": "npm | pnpm | yarn | yarn-berry | bun",
      "files": {
        "transformed": ["string"],
        "renamed": ["string"],
        "manual_review": ["string"]
      },
      "unmapped_keys": ["string"],
      "verified": "bool"
    }],
    "elapsed_sec": "float"
  },
  "migration-snapshot/": {
    "doc": "Rollback bundle. Snapshot of touched files before Phase 4b migration. Mirror of repo tree relative paths."
  },
  "overrides.json": {
    "doc": "User overrides (optional). Located in .code-coverage/overrides.json.",
    "force_jest": "bool (default false)",
    "force_jest_reason": "string (required if force_jest=true)"
  }
}
```

Se il file `state-schema.json` esiste già con altre chiavi top-level, aggiungere queste come additional properties, NON sovrascrivere quelle esistenti.

### C. Verifiche

```bash
# Bash syntax check
bash -n skills/code-coverage/lib/phase1-discover.sh
# JSON parse check
python3 -c "import json; json.load(open('skills/code-coverage/lib/state-schema.json'))"
```

## Acceptance

- [ ] `bash -n` succede senza errori
- [ ] `state-schema.json` parse senza errori
- [ ] Phase 1 lancia detect_jest_incompat in parallel
- [ ] Cache gate funziona (no doppio run se file fresco)
- [ ] Schema additions non rompono parser esistenti
