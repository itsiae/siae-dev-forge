---
title: Tiered CLAUDE.md — generazione automatica gerarchica
date: 2026-05-19
status: DESIGN
goal: Implementare best practice Anthropic post "How Claude Code works in large codebases" (14 mag 2026) generando automaticamente CLAUDE.md gerarchici (L1 root + L2 package + L3 child on-demand) con hook SessionStart advisory non-bloccante
stack: DevForge plugin (bash hooks + Python scripts + markdown skill)
sp_human: 5
sp_augmented: 2
risk: MEDIUM
---

# Tiered CLAUDE.md — Design Doc

## Contesto

**Fonte:** Post Anthropic [How Claude Code works in large codebases](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start) (Applied AI team, 14 maggio 2026) + [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices).

**Modello a 5 livelli ufficiale Anthropic:**

| Livello | Path | Caricamento | Contenuto |
|---|---|---|---|
| L0 globale | `~/.claude/CLAUDE.md` | Sempre | Preferenze utente cross-progetto |
| L1 root | `./CLAUDE.md` | Session start | Big picture, bash commands, repo etiquette |
| L1 personal | `./CLAUDE.local.md` | Session start | Personale (gitignored) |
| L2 parent | `./<package>/CLAUDE.md` | Session start (in monorepo) | Convenzioni del package |
| L3 child | `./<package>/<subdir>/CLAUDE.md` | **On-demand** quando Claude legge file lì dentro | Pattern locali ristretti |

**Citazioni chiave:**
- *"root file describes only the highest-level structure, subdirectory files provide the next level of detail, loading on demand"*
- *"For each line, ask: 'Would removing this cause Claude to make mistakes?' If not, cut it"*
- Anti-pattern: *"Bloated CLAUDE.md files cause Claude to ignore your actual instructions"*

**Gap nel tooling ufficiale:** `/init` Anthropic genera mono-file root. `siae-codebase-map` SIAE produce `docs/CODEBASE_MAP.md` mono-file. Nessuna automazione per gerarchia multi-livello con load-on-demand.

## Decisioni

1. **Soglia L3:** >=10 file source AND pattern locale distintivo (framework diverso / convenzione locale / mock setup non inferibile dal parent). Sotto soglia → no L3, eredita L2.
2. **Stale detection:** `>=30 commit dal last_mapped` OR `>14 giorni` — doppia soglia per adattarsi a cadenze variabili.
3. **Default mode:** opt-in via flag `--tiered` su `/forge-map`. Skill esistente comportamento invariato. Zero regression.

## Approcci valutati

| # | Approccio | Pro | Contro | Verdetto |
|---|---|---|---|---|
| A | Estensione monolitica di `siae-codebase-map` | Riuso totale, 1 skill | Skill bloat (337→500+ righe) | ❌ |
| **B** | **Sub-skill `siae-codebase-map-tiered` + hook separato** | **Separazione concern, pattern validato (siae-git-env), zero-regression** | **+1 file SKILL.md** | ✅ |
| C | Skill standalone `siae-tiered-context` | Scope chiarissimo | Duplica detection logic | ❌ |

## Architettura

```
siae-codebase-map (existing, invariata in 95%)
   │ Step 1-6: scan + CODEBASE_MAP.md
   │ Step 7 (NEW gate): se --tiered → REQUIRED SUB-SKILL
   ▼
siae-codebase-map-tiered (NEW sub-skill, ~150 righe)
   │ Read CODEBASE_MAP.md frontmatter + module list
   │ scripts/emit-claude-md.py
   │   - L1 root: 200 righe max
   │   - L2 per Maven module / TS package: import @../CLAUDE.md
   │   - L3 opzionale (soglia 10 file + pattern locale)
   │ scripts/anti-bloat-lint.py: WARN se file >200 righe o >70% overlap parent
   │ Pre-flight 🟡 MEDIO (preview path target)
   ▼
File system:
   docs/CODEBASE_MAP.md (source-of-truth)
   ./CLAUDE.md (L1)
   ./<module>/CLAUDE.md (L2, import @../CLAUDE.md)
   ./<module>/<subdir>/CLAUDE.md (L3, opzionale)

hooks/session-start-tiered-advisor (NEW bash, ~80 righe)
   matcher: "startup|resume" (NON "clear|compact" — solo apertura sessione)
   NON-BLOCKING (exit 0 sempre):
     1. Glob docs/CODEBASE_MAP.md
     2. Se assente → additionalContext "⚠ Nessuna codebase map"
     3. Se stale (>=30 commit OR >14 giorni) → additionalContext "ℹ CLAUDE.md stale"
     4. timeout 3s, errori silent (pipefail + 2>/dev/null per memory feedback_session_start_hook_invariants)
```

## Componenti

1. `skills/siae-codebase-map-tiered/SKILL.md` (~150 righe)
2. `skills/siae-codebase-map-tiered/scripts/emit-claude-md.py` (~200 righe)
3. `skills/siae-codebase-map-tiered/scripts/anti-bloat-lint.py` (~80 righe)
4. `hooks/session-start-tiered-advisor` bash (~80 righe)
5. `hooks/hooks.json` — entry SessionStart additionalContext aggiunta
6. `skills/siae-codebase-map/SKILL.md` Step 7 (~15 righe modificate)
7. `.claude-plugin/marketplace.json` + `plugin.json` — version bump (memory `project_plugin_version_dual_source`)
8. `CHANGELOG.md` — entry v1.61.0
9. Test fixtures + test unit/integration

## Flusso dati

```
User: /forge-map --tiered
  → siae-codebase-map Step 1-6 (esistente, no change)
  → Step 7 NEW: pre-flight 🟡 MEDIO preview gerarchia path
  → REQUIRED SUB-SKILL siae-codebase-map-tiered
    → emit-claude-md.py legge CODEBASE_MAP.md
    → genera L1 + L2 + L3 opzionali
    → anti-bloat-lint.py su ogni file (WARN, non blocca)
    → output lista file scritti

Session next start:
  → hooks/session-start-tiered-advisor (matcher startup|resume)
  → timeout 3s, exit 0 sempre
  → if stale/missing → stdout additionalContext (Claude lo vede, non-blocca utente)
```

## Error handling

| Errore | Comportamento |
|---|---|
| emit-claude-md.py fail | Preserva CODEBASE_MAP.md (source-of-truth). CLAUDE.md derivati rigenerabili. Exit 1, messaggio chiaro all'utente. |
| Hook advisor timeout >3s | Silent skip (kill processo). Exit 0. Boot non blocca. |
| Hook git command error | 2>/dev/null. Exit 0. Memory feedback_session_start_hook_invariants. |
| Anti-bloat lint WARN | Mostra warning, scrive comunque file. Utente decide se trim. |
| CODEBASE_MAP.md mancante in tiered mode | Errore esplicito: "Esegui /forge-map prima di --tiered". |

## Testing strategy

**Unit:**
- `emit-claude-md.py` su 3 fixture: single-repo Java Maven, monorepo TS pnpm, single Python
- `anti-bloat-lint.py` su file >200 righe → WARN
- Parse frontmatter `last_mapped` valido + invalido

**Integration:**
- Hook session-start-tiered-advisor: fixture CODEBASE_MAP con `last_mapped` antico → assert additionalContext "stale"
- Hook con repo nuovo no map → assert additionalContext "nessuna codebase map"
- Hook exit code 0 in tutti gli scenari (incluso git fail)

**No-regression:**
- `/forge-map` senza `--tiered` → CODEBASE_MAP.md generato, no CLAUDE.md L2/L3 (backward compatible)
- Aggiungi a `tests/test_hook_no_regression.py` (count 25→26, memory `pr252_test_count_drift`)

**E2E:**
- Branch worktree fresh, `/forge-map --tiered` su fixture spring-boot-sample (multi-module)
- Verify L1 root + 1 L2 per Maven module
- Verify import @ syntax presente in ogni L2
- Verify L3 NON generato su subdir <10 file

## Criteri di accettazione

1. ✅ `/forge-map --tiered` su repo Maven multi-module → CLAUDE.md L1 + 1 L2 per modulo
2. ✅ Ogni L2 contiene `@../CLAUDE.md` import (no duplicazione root content)
3. ✅ L3 generato solo se subdir >=10 file AND pattern locale distintivo
4. ✅ Hook session-start con CODEBASE_MAP.md vecchia >14gg O >=30 commit → additionalContext stale (exit 0, non blocca boot)
5. ✅ `/forge-map` senza `--tiered` → comportamento invariato (no CLAUDE.md L2/L3)
6. ✅ Anti-bloat lint: ogni CLAUDE.md <200 righe OR warning esplicito
7. ✅ Test no-regression count +1 (hook list)
8. ✅ Hook errors silent (2>/dev/null, exit 0 sempre — boot mai bloccato)
9. ✅ `plugin.json` + `marketplace.json` allineati su version bump
10. ✅ CHANGELOG.md entry v1.61.0

## Rischi

| Rischio | Mitigazione |
|---|---|
| Bloat CLAUDE.md L2/L3 contraddice anti-bloat Anthropic | anti-bloat-lint.py automatico + soglia L3 alta (10 file) |
| Hook session-start lento | timeout 3s hard cap, async:false ma git rev-list veloce |
| Conflitto con CLAUDE.md root scritto a mano | Pre-flight mostra preview, utente decide overwrite |
| Cache plugin disallineata (memory `reference_plugin_cache_sync`) | Documentare sync manuale post-install in CHANGELOG |
| Repo iCloud (memory `iCloud repo operational tax`) push lento | Test su SSD local prima di push |

## ADR (Architecture Decision Records)

**ADR-1: Sub-skill vs skill standalone vs estensione monolitica.**
Sub-skill `siae-codebase-map-tiered` scelta perché:
- Pattern già validato con `siae-git-env` come sub-skill di `siae-git-workflow`/`siae-finishing-branch`
- Separazione concern: mapping (codebase-map) vs emit CLAUDE.md (tiered)
- Skill esistente quasi invariata (zero-regression)

**ADR-2: Hook non-bloccante via additionalContext.**
Hook SessionStart emette su stdout (additionalContext) e mai output.message bloccante. Exit 0 sempre.
- Memory `feedback_session_start_hook_invariants`: pipefail guard + 2>/dev/null
- L'utente non viene mai bloccato dal boot
- Claude vede il suggerimento e propone azione, non forza

**ADR-3: Opt-in via --tiered.**
Default mode invariato per zero-regression.
- Skill esistente continua a funzionare per chi non vuole gerarchia
- Auto-detect monorepo rifiutato: comportamento meno prevedibile, breaking change implicito

## Stima

- **5 SP Umano** (5 file nuovi + 2 modifiche + test + version bump)
- **2 SP Augmented** (subagent paralleli per implementazione + test in TDD)

## Decomposizione preliminare (handoff a siae-writing-plans)

1. **Task 1**: Scaffold sub-skill `siae-codebase-map-tiered` (SKILL.md + scripts/ dir)
2. **Task 2**: Implementare `emit-claude-md.py` (TDD)
3. **Task 3**: Implementare `anti-bloat-lint.py` (TDD)
4. **Task 4**: Modificare `siae-codebase-map` Step 7 per invocazione sub-skill condizionale
5. **Task 5**: Implementare `hooks/session-start-tiered-advisor` (TDD via fixture)
6. **Task 6**: Aggiornare `hooks/hooks.json` con entry SessionStart additionalContext
7. **Task 7**: Test no-regression hook count (memory pr252)
8. **Task 8**: Version bump dual-source (plugin.json + marketplace.json), CHANGELOG, PR

## Fonti

- [How Claude Code works in large codebases (Anthropic, 14 mag 2026)](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start)
- [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- Memory `feedback_session_start_hook_invariants` — pipefail + stdout redirect
- Memory `project_plugin_version_dual_source` — bump dual source-of-truth
- Memory `pr252_test_count_drift` — aggiungere hook a test count
- Memory `reference_plugin_cache_sync` — sync manuale post-install
