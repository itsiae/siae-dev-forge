# Superpowers Quick Wins — Design Doc

**Data:** 2026-03-29
**Autore:** DevForge brainstorming
**SP:** 2 SP-Umano / 1 SP-Augmented
**Ispirazione:** obra/superpowers v5.0.6 + PR #965

---

## Goal

Portare in DevForge due miglioramenti ispirati da Superpowers:
1. Hook sharing nei worktree (symlink `.claude/`)
2. No Placeholders gate in writing-plans

## Contesto

- **Problema 1:** `siae-git-worktrees` crea worktree senza propagare `.claude/` — l'agent nel worktree non ha hook DevForge (SessionStart, pre-commit, UserPromptSubmit), ne' settings, ne' CLAUDE.md. Parte "nudo".
- **Problema 2:** `siae-writing-plans` non ha un gate esplicito anti-placeholder. Piani con "TBD", "simile al Task N", descrizioni vaghe causano blocchi o allucinazioni nei subagent implementer.

## Approccio scelto

### Modifica 1: Step 3b in siae-git-worktrees — Sync DevForge Config

Aggiungere un nuovo step dopo "Auto-detect Setup" (Step 3) e prima di "Baseline Test Check" (Step 4).

Il nuovo step:
- Rileva `MAIN_REPO` tramite `git worktree list | head -1`
- Crea symlink `.claude/` dal repo principale al worktree
- Crea symlink `CLAUDE.md` root se esiste
- Skip silenzioso se `.claude/` non esiste (repo senza DevForge)

Alternativa scartata: copia fisica — disallineamento immediato se gli hook cambiano durante la sessione.

### Modifica 2: Step 3b in siae-writing-plans — Placeholder Scan Gate

Aggiungere un gate obbligatorio tra Step 3 (Scrivi il Piano) e Step 4 (Salva il Piano).

Pattern vietati:
- `TBD`, `TODO`, `da definire`, `da decidere`
- `similar to` / `simile a` / `come sopra` / `vedi sopra`
- `da completare`
- `[...]` / `...` in blocchi codice
- Riferimenti circolari ("Vedi Task N" senza contenuto inline)

Procedura: scan → lista match → risolvi → ri-scan → zero match → procedi.

Alternativa scartata: integrare nella sezione "Regole di Qualita'" esistente — non e' un gate, e' un suggerimento. L'agent puo' ignorarlo.

## Criteri di accettazione

- [ ] `siae-git-worktrees/SKILL.md` contiene Step 3b con comandi symlink
- [ ] Step 3b fa skip silenzioso se `.claude/` non esiste
- [ ] `siae-writing-plans/SKILL.md` contiene Step 3b Placeholder Scan
- [ ] La tabella pattern vietati e' completa (9 pattern)
- [ ] La procedura di scan e' sequenziale: scan → fix → re-scan → zero match

## Rischi

Nessun rischio significativo. Modifiche additive a file Markdown, nessuna logica eseguibile, nessun breaking change.
