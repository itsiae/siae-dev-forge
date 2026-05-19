---
task: 08
title: Version bump dual-source + CHANGELOG + PR
status: PENDING
estimate_min: 30
type: release
depends_on: [01, 02, 03, 04, 05, 06, 07]
---

# Task 08 — Version bump + CHANGELOG + PR

## Obiettivo

Allineare version bump su DOPPIA sorgente (memory `project_plugin_version_dual_source`),
aggiungere entry CHANGELOG v1.61.0, aprire PR verso main con descrizione completa.

## File da modificare

1. `plugin.json` — bump version `1.60.0` → `1.61.0`
2. `.claude-plugin/marketplace.json` — bump version stesso campo (allineato)
3. `CHANGELOG.md` — entry v1.61.0

## Version bump (dual source)

**plugin.json:**
```json
{
  "name": "siae-devforge",
  "version": "1.61.0",
  ...
}
```

**.claude-plugin/marketplace.json:**
```json
{
  ...
  "plugins": [{
    "name": "siae-devforge",
    "version": "1.61.0",
    ...
  }]
}
```

Verifica entrambi allineati prima di commit:

```bash
PLUGIN_V=$(jq -r .version plugin.json)
MARKET_V=$(jq -r '.plugins[] | select(.name=="siae-devforge").version' .claude-plugin/marketplace.json)
[[ "$PLUGIN_V" == "$MARKET_V" ]] || { echo "MISMATCH: $PLUGIN_V vs $MARKET_V"; exit 1; }
```

## CHANGELOG entry

```markdown
## [1.61.0] — 2026-05-XX

### Added
- **siae-codebase-map-tiered**: nuova sub-skill per generazione gerarchica
  CLAUDE.md (L1 root + L2 package + L3 child on-demand) secondo best practice
  Anthropic ([post 14 mag 2026](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start))
- **hook session-start-tiered-advisor**: rileva CLAUDE.md mancanti o stale
  (>=30 commit OR >14 giorni) all'avvio sessione e suggerisce rigenerazione via
  `additionalContext` non-bloccante
- `emit-claude-md.py`: frammentatore CODEBASE_MAP.md → CLAUDE.md gerarchici
- `anti-bloat-lint.py`: lint advisory per CLAUDE.md (max 200 righe, no overlap parent)

### Changed
- `siae-codebase-map`: aggiunto Step 7a opt-in `--tiered` che invoca sub-skill
  tiered. Comportamento default invariato (backward compatible).

### Notes
- Per attivare: `/forge-map --tiered` su repo Maven multi-module o monorepo TS
- L'hook advisory è async, non blocca boot
- Anti-bloat lint advisory (exit 0 sempre, warning su stdout)
```

## PR

Branch suggested: `feat/tiered-claude-md`

```bash
git checkout -b feat/tiered-claude-md
git push -u origin feat/tiered-claude-md
```

**PR title:** `feat(skills): tiered CLAUDE.md generation + session-start advisory`

**PR body** (via `--body-file` per evitare heredoc issue, memory `feedback_pr_body_via_file`):

Salva contenuto in `/tmp/pr-body-tiered.md`:

```markdown
## Summary

Implementa best practice Anthropic post "How Claude Code works in large codebases"
(14 mag 2026): generazione automatica gerarchia CLAUDE.md L1+L2+L3 con
load-on-demand + import @ chain + anti-bloat.

## Changes

- ✨ Sub-skill `siae-codebase-map-tiered` (opt-in via `/forge-map --tiered`)
- ✨ Hook `session-start-tiered-advisor` non-bloccante (stale detection)
- ✨ Script `emit-claude-md.py` + `anti-bloat-lint.py`
- 🧪 28 nuovi test (6+5+7+10 unit/integration + 1 no-regression count)
- 📚 Design doc: `docs/plans/2026-05-19-tiered-claude-md-design.md`

## Compatibility

- Zero-regression: `/forge-map` senza `--tiered` invariato
- Hook async + exit 0 sempre → boot non bloccato

## Test plan

- [x] 28/28 test PASS
- [x] Coverage >=85% su nuovi script
- [x] `python3 -m json.tool hooks/hooks.json` valido
- [x] plugin.json + marketplace.json version allineati
- [x] CHANGELOG aggiornato
- [x] Manual test su fixture spring-boot-sample (`/forge-map --tiered`)
```

```bash
gh pr create --title "feat(skills): tiered CLAUDE.md generation + session-start advisory" --body-file /tmp/pr-body-tiered.md
```

## Pre-flight 🔴 ALTO

Pre-flight card prima di push + PR (operazione pubblica, irreversibile per remoto):

| 🔴 ALTO — Release v1.61.0 |
|:---|
| Bump version 1.60.0 → 1.61.0 · PR pubblica verso main · 28 test devono PASS |
| **▼ Azione** |
| 1. Verifica plugin.json == marketplace.json |
| 2. Verifica CHANGELOG entry presente |
| 3. Verifica 28/28 test PASS |
| 4. git push + gh pr create |
| 🚫 Se NO: branch rimane locale, no PR |

## Criteri di accettazione

1. ✅ plugin.json version 1.61.0
2. ✅ marketplace.json version 1.61.0 (allineato)
3. ✅ CHANGELOG entry v1.61.0 completa
4. ✅ Branch push e PR aperta
5. ✅ PR body via --body-file (memory `feedback_pr_body_via_file`)
6. ✅ CI/test verde su PR
7. ✅ Reviewer assegnato (via `siae-requesting-review`)

## Definition of Done

- Version bump dual + CHANGELOG committed
- PR aperta e link condiviso con l'utente
- CI green
- Commit: `chore(release): bump v1.61.0 — tiered CLAUDE.md`
