#!/usr/bin/env bash
# adoption-emit.sh — emit dell'evento telemetria task_adoption (Layer 1).
# Design: docs/plans/2026-06-14-devforge-adoption-telemetry-design.md §5.1
# Source-only library: nessun side effect al load. Dipendenze (best-effort):
#   - devforge_log         (lib/logger.sh)
#   - devforge_compute_task_id (lib/task-id.sh)
#   - python3 + lib/adoption-analyzer.py --task-adoption-meta (Task 01)
# Tutte le emissioni sono non-bloccanti: qualunque fallimento => return 0.

devforge_emit_task_adoption() {
    command -v devforge_log >/dev/null 2>&1 || return 0
    command -v devforge_compute_task_id >/dev/null 2>&1 || return 0

    local task_id
    task_id=$(devforge_compute_task_id 2>/dev/null || echo "")
    [ -n "$task_id" ] || return 0          # fuori scope (repo non-itsiae / no git)

    local plugin_root="${PLUGIN_ROOT:-}"
    [ -n "$plugin_root" ] || return 0
    local analyzer="${plugin_root}/lib/adoption-analyzer.py"
    [ -f "$analyzer" ] || return 0

    local meta
    meta=$(python3 "$analyzer" --task-adoption-meta "$task_id" 2>/dev/null || true)
    [ -n "$meta" ] || return 0             # ledger assente/vuoto => niente evento

    devforge_log "task_adoption" "success" "$meta" 2>/dev/null || true
    return 0
}
