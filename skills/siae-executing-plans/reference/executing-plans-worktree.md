# siae-executing-plans — Worktree Setup Dettagliato

> Reference linked da `../SKILL.md`. Setup workspace isolato pre-implementazione.

## Quando usare worktree

- Il progetto richiede un branch dedicato per evitare conflitti con lavoro in corso
- L'implementazione tocca molti file e vuoi isolare l'esperimento
- L'utente sta gia' lavorando su altri branch/feature in parallelo
- Il piano contiene `REQUIRED SUB-SKILL: siae-git-worktrees` esplicito

**NON usare worktree quando:**
- Il piano e' una singola modifica banale (1-2 file)
- Il branch corrente e' gia' dedicato e pulito
- L'utente ha esplicitamente chiesto di lavorare sul branch corrente

---

## Setup Step

### Step 0 — Setup Workspace Isolato (opzionale)

Card rischio: 🟢 SICURO

Se il progetto richiede un branch dedicato o workspace isolato, invoca
`siae-git-worktrees` prima di iniziare l'implementazione. Previene conflitti
con lavoro in corso su altri branch.

```
REQUIRED SUB-SKILL: siae-git-worktrees (opzionale)
```

La sub-skill gestisce:
- creazione worktree con naming convention `wt-<topic>`
- branch dedicato `feat/<topic>` o equivalente
- sync hooks DevForge (symlink `.claude/` da repo root)
- isolamento da branch principale

---

## Sync hooks DevForge

I worktree creati con `git worktree add` non ereditano automaticamente la
configurazione `.claude/` (hooks, settings) dal repo principale. La sub-skill
`siae-git-worktrees` crea un symlink:

```bash
ln -s ../../.claude .claude
```

Senza questo step, hooks DevForge (TDD gate, brainstorming gate, ecc.) non
si attivano nel worktree e l'esecuzione del piano salta i checkpoint
automatici.

---

## Cleanup

Dopo merge della PR:

```bash
git worktree remove <path-worktree>
git branch -d <branch-name>     # solo dopo merge confermato
```

Se il worktree contiene modifiche non committate, `git worktree remove`
richiede `--force` — verifica sempre lo stato prima.

---

## Riferimenti

- `siae-git-worktrees/SKILL.md` — istruzioni operative complete
- `feedback_worktree_hooks.md` — gotcha hooks non sincronizzati
