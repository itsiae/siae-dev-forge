# Design: branching-strategy-check

**Data:** 2026-03-25
**Autore:** siae-devforge
**Status:** Approvato

---

## Contesto

Portare la skill `branching-strategy-check` dal repo `siae-claude-skills` nel plugin `siae-devforge`.

La skill originale (PR #3) verifica solo le PR in cui l'utente è reviewer.
Requisito ampliato: scan org-wide su **tutti i repo `itsiae`**, non solo quelli con PR in review.

---

## Obiettivo

- Skill invocabile on-demand come `/branching-strategy-check`
- Hook automatico a `SessionStart`: inietta un summary compact di compliance all'avvio sessione
- Il developer vede subito se ci sono violazioni senza dover chiedere

---

## Architettura

### Componenti

| File | Tipo | Responsabilità |
|------|------|----------------|
| `skills/branching-strategy-check/SKILL.md` | Skill | Scan completo org-wide, report dettagliato |
| `hooks/session-start` (modifica) | Hook | Summary compact asincrono, inject in additional_context |

### Flusso

```
SessionStart
    └── session-start hook (già esistente)
            └── branching compliance scan [async background]
                    ├── gh search repos --owner=itsiae
                    ├── check default branch == main
                    ├── check open PRs verso main da non-release/**
                    └── inject summary: "N violazioni in M repo" → additional_context

On demand: /branching-strategy-check
    └── Skill SKILL.md
            └── scan completo + report tabellare dettagliato
```

---

## Decisioni Architetturali

### ADR-1: Scope repo corrente di default, org-wide opzionale

**Decisione rivista (approvata durante implementazione):** la skill controlla il **repo corrente** come Fase 1 (default). L'espansione org-wide è disponibile come Fase 2 su richiesta esplicita.

**Motivo:** il check si applica naturalmente quando si clona o si apre un nuovo repo. Lo scan org-wide resta disponibile on-demand ma non è il comportamento di default — troppo invasivo e lento per l'avvio sessione.

**Comportamento precedente scartato:** `gh search repos --owner=itsiae` come Fase 1 — sostituito da `gh repo view` sul repo corrente.

### ADR-2: Check sincrono sul repo corrente (no cache)

**Decisione rivista (approvata durante implementazione):** l'hook session-start esegue un check **sincrono** sul repo corrente. Nessun file cache, nessun background job.

**Motivo:** controllare un singolo repo è abbastanza veloce da non richiedere cache. La complessità della cache (TTL, background job, file `~/.claude/.devforge-branching-compliance`) è giustificata solo per scan org-wide, che non è più il comportamento di default.

### ADR-3: Separazione skill / hook

- **Hook** → headline solo se ci sono violazioni: `⚠️ Branching compliance [{repo}]: {dettaglio}`
- **Skill** → report completo tabellare con violazioni e repo compliant

Questo mantiene l'avvio di sessione leggero e il report dettagliato disponibile on-demand.

### ADR-4: Limite repo per scan org-wide (Fase 2)

`gh search repos --owner=itsiae --limit 100` — cap a 100 repo per evitare timeout.

---

## Skill SKILL.md — Spec

### Frontmatter
```yaml
name: branching-strategy-check
description: >
  Verifica compliance alla branching strategy SIAE sul repo corrente (o nuovo/clonato).
  Default branch deve essere main. Solo release/** puo' aprire PR verso main.
sdlc_phase: "6. QA Gate"
skill_type: "Flexible"
```

### Comportamento

1. **Fase 1 (default):** check sul repo corrente
   - Controlla default branch (deve essere `main`)
   - Lista PR aperte verso `main` e verifica che vengano da `release/**`
2. **Fase 2 (opzionale):** espansione org-wide su tutti i repo itsiae su richiesta esplicita
3. Genera report markdown con violazioni in evidenza

### Trigger
`"branching check"`, `"compliance org"`, `"/branching-strategy-check"`, `"PR verso main"`, `"verifica branching strategy"`, `"violazioni branching"`, `"default branch"`, `"release branch"`

---

## Hook session-start — Spec modifica

Aggiungere al fondo del blocco di context injection (dopo il check PR merges, prima del lock):

```bash
# Branching compliance summary (async, non-blocking)
BRANCHING_CACHE="${HOME}/.claude/.devforge-branching-compliance"
BRANCHING_SUMMARY=""
NOW_TS=$(date +%s)
CACHE_TTL=14400  # 4 ore

if command -v gh >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    # Leggi cache se fresca
    if [ -f "$BRANCHING_CACHE" ]; then
        CACHE_TS=$(jq -r '.ts' "$BRANCHING_CACHE" 2>/dev/null || echo "0")
        CACHE_AGE=$((NOW_TS - CACHE_TS))
        if [ "$CACHE_AGE" -lt "$CACHE_TTL" ]; then
            VIOLATIONS=$(jq -r '.violations' "$BRANCHING_CACHE" 2>/dev/null || echo "")
            REPOS=$(jq -r '.repos_checked' "$BRANCHING_CACHE" 2>/dev/null || echo "")
            if [ -n "$VIOLATIONS" ] && [ "$VIOLATIONS" -gt 0 ]; then
                BRANCHING_SUMMARY="⚠️ Branching compliance: ${VIOLATIONS} violazioni su ${REPOS} repo itsiae — invoca /branching-strategy-check per i dettagli."
            elif [ -n "$VIOLATIONS" ]; then
                BRANCHING_SUMMARY="✅ Branching compliance: tutti i ${REPOS} repo itsiae sono compliant."
            fi
        fi
    fi

    # Refresh in background se cache assente o stale
    if [ -z "$BRANCHING_SUMMARY" ] || [ "${CACHE_AGE:-99999}" -ge "$CACHE_TTL" ]; then
        (
            REPOS_JSON=$(gh search repos --owner=itsiae --limit 100 --json fullName -q '[.[].fullName]' 2>/dev/null || echo "[]")
            TOTAL=$(echo "$REPOS_JSON" | jq 'length' 2>/dev/null || echo "0")
            VIOLS=0
            for repo in $(echo "$REPOS_JSON" | jq -r '.[]' 2>/dev/null); do
                DEFAULT=$(gh repo view "$repo" --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null || echo "main")
                [ "$DEFAULT" != "main" ] && VIOLS=$((VIOLS + 1)) && continue
                BAD_PRS=$(gh pr list --repo "$repo" --base main --state open \
                    --json headRefName -q '[.[] | select(.headRefName | test("^release/") | not)] | length' 2>/dev/null || echo "0")
                VIOLS=$((VIOLS + BAD_PRS))
            done
            echo "{\"ts\":${NOW_TS},\"violations\":${VIOLS},\"repos_checked\":${TOTAL},\"compliant\":$((TOTAL - VIOLS))}" > "$BRANCHING_CACHE"
        ) &
    fi
fi
```

Il `BRANCHING_SUMMARY` viene poi incluso nel `session_context` JSON già costruito.

---

## Criteri di Accettazione

- [ ] Skill invocabile via Skill tool come `branching-strategy-check`
- [ ] Slash command `/branching-strategy-check` funzionante
- [ ] Skill scannerizza tutti i repo `itsiae` (non solo PR in review)
- [ ] Report mostra violazioni (default branch ≠ main, PR da non-release verso main) e repo compliant
- [ ] session-start inietta summary se ci sono violazioni nel repo corrente
- [ ] Check sincrono sul repo corrente (no cache — un repo è abbastanza veloce)
- [ ] Skill aggiunta al Dynamic Skill Catalog in `using-devforge`
- [ ] Skill aggiunta al catalogo `skills-core.js`

---

## Story Points

**2 SP-Umano / 1 SP-Augmented**

Task prevalente: boilerplate skill + modifica hook bash. Logica `gh` è già testata nella PR originale.

---

## File Modificati / Creati

| File | Operazione |
|------|-----------|
| `skills/branching-strategy-check/SKILL.md` | CREATE |
| `hooks/session-start` | MODIFY (aggiunta branching summary block) |
