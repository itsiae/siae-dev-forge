#!/usr/bin/env bash
# DevForge plugin-cache-resilience — sopravvivenza delle sessioni attive all'auto-update.
# Sourcabile, zero side-effect al source. Design: 2026-06-19-plugin-cache-resilience-design.md
#
# Problema: Claude Code ancora gli hook a ${CLAUDE_PLUGIN_ROOT}=cache/.../<VERSION> (snapshot a boot).
# L'auto-update nativo rimuove la cache versionata vecchia → le sessioni già attive vedono
# "Plugin directory does not exist" e TUTTI gli hook falliscono. Questa funzione, eseguita da
# session-start (sempre dalla versione corrente, esistente), ricrea i path versionati mancanti
# puntandoli alla corrente (symlink; fallback copia atomica su Windows), così le sessioni vecchie
# si auto-riparano al primo session-start successivo.
#
# INVARIANTI DI SICUREZZA (non negoziabili — vedi spec-review):
#   GUARD-1: opera SOLO dentro la cache plugin Claude (mai path utente arbitrari).
#   GUARD-2: deduce `cur` solo da dir REALI (mai da symlink → niente autoreferenza).
#   GUARD-3: non tocca MAI una dir reale (anche incompleta → nessun cp-r sopra, nessun data loss).
#   GUARD-4: rimuove solo symlink che puntano a un semver locale (mai symlink estranei).
#   Copia atomica tmp+mv (concorrenza/Windows). Best-effort: ogni write `|| true`, return 0 sempre.

devforge_ensure_version_compat() {
    local plugin_root="${1:-}" base cur reg v tmp _target
    [ -n "$plugin_root" ] || return 0
    base="$(dirname "$plugin_root")"

    # GUARD-1: solo dentro la cache plugin Claude
    case "$base" in
        */.claude/plugins/cache/siae-devforge/siae-devforge) : ;;
        *) return 0 ;;
    esac
    [ -d "$base" ] || return 0

    # CUR autorevole = basename(plugin_root) se semver puro E dir reale (non symlink)
    cur="$(basename "$plugin_root")"
    if ! { printf '%s' "$cur" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' && [ -d "$base/$cur" ] && [ ! -L "$base/$cur" ]; }; then
        # GUARD-2: fallback = versione più alta tra le dir REALI (non symlink). Nessuna → return 0.
        cur="$(
            for v in "$base"/*/; do
                [ -d "$v" ] || continue
                v="${v%/}"; v="${v##*/}"
                printf '%s' "$v" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || continue
                if [ -L "$base/$v" ]; then continue; fi
                printf '%s\n' "$v"
            done | sort -t. -k1,1n -k2,2n -k3,3n | tail -1
        )"
        [ -n "$cur" ] || return 0
    fi

    reg="${HOME}/.claude/.devforge-known-plugin-versions"
    # Append incondizionato (no grep-guard): evita il TOCTOU tra grep e append in concorrenza.
    # Il dedup è garantito dal sort -u sotto, eseguito ad ogni run nello stesso processo.
    printf '%s\n' "$cur" >> "$reg" 2>/dev/null || true
    # cap ultime 10 versioni (sort numerico per-campo, portabile BSD/GNU — no sort -V) + dedup
    if [ -f "$reg" ]; then
        tmp="$(grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' "$reg" 2>/dev/null | sort -t. -k1,1n -k2,2n -k3,3n -u | tail -10)"
        printf '%s\n' "$tmp" > "$reg" 2>/dev/null || true
    fi
    [ -f "$reg" ] || return 0

    while IFS= read -r v; do
        [ -n "$v" ] || continue
        [ "$v" != "$cur" ] || continue
        # path già risolvibile (dir reale o symlink valido) → MAI toccare
        if [ -e "$base/$v/hooks/run-hook.cmd" ]; then continue; fi
        # GUARD-3: dir REALE (anche incompleta) → skip, mai cp-r sopra, mai data loss.
        # NB: nessuna chiamata a funzioni esterne qui (es. devforge_log): sotto `set -u`
        # un loro unbound-var sarebbe fatale e NON catturabile da `|| true` del chiamante,
        # potendo abortire session-start. La funzione resta auto-contenuta (solo builtin/coreutils).
        if [ -d "$base/$v" ] && [ ! -L "$base/$v" ]; then
            continue
        fi
        # qui: $base/$v assente oppure symlink rotto. GUARD-4: rimuovi solo symlink il cui target
        # è un semver PURO (un nostro link). Regex ancorata ^..$ (il glob di `case` con `.` non
        # ancorato matcherebbe a torto target tipo "1.2.3-beta" o "1.2.3/sub" → rimozione indebita).
        if [ -L "$base/$v" ]; then
            _target="$(readlink "$base/$v" 2>/dev/null)"
            if printf '%s' "$_target" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
                rm -f "$base/$v" 2>/dev/null || true
            else
                continue   # symlink "estraneo" (target non-semver) → non toccare
            fi
        fi
        # ricrea: symlink relativo + verifica; fallback copia ATOMICA (tmp+mv) per Windows/concorrenza
        if ln -s "$cur" "$base/$v" 2>/dev/null && [ -e "$base/$v/hooks/run-hook.cmd" ]; then
            :
        else
            rm -f "$base/$v" 2>/dev/null || true
            tmp="$base/.compat.${v}.$$"
            rm -rf "$tmp" 2>/dev/null || true
            if cp -r "$base/$cur" "$tmp" 2>/dev/null && mv "$tmp" "$base/$v" 2>/dev/null; then
                :
            else
                rm -rf "$tmp" 2>/dev/null || true
            fi
        fi
    done < "$reg"
    return 0
}
