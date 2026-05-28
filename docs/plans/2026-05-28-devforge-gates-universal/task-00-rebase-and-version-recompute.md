# Task 00 — Pre-task: rebase su main + version recompute + line number re-verify

> **REQUIRED SUB-SKILL:** `siae-verification`
> **PRE-REQUISITO di tutti i task 1-9.** Da eseguire PRIMA del task 01.

**Goal:** Branch `feat/skill-premortem` rebased su main aggiornato (v1.70.0+), version bump del piano riallineato (v1.69.0 obsoleto → v1.71.0), tutti i line number reference nei task verificati post-rebase.

**File coinvolti:**
- Rebase: `git rebase origin/main` su tutto il branch
- Modifica: `docs/plans/2026-05-28-devforge-gates-universal-design.md` (version refs 1.69.0 → 1.71.0)
- Modifica: `docs/plans/2026-05-28-devforge-gates-universal/overview.md` (version refs)
- Modifica: `docs/plans/2026-05-28-devforge-gates-universal/task-08-docs-and-version-bump.md` (1.69.0 → 1.71.0)
- Verifica: tutti i `task-NN` con `L<numero>` reference su `hooks/*` post-rebase

---

## Step 1 — Verifica stato e rebase

```bash
cd "$REPO_ROOT"
git fetch origin main
git log --oneline feat/skill-premortem..origin/main | head -10
# Atteso: lista di commit che main ha avanzato (es. bump 1.69.0, 1.70.0, ecc.)

git checkout feat/skill-premortem
git rebase origin/main
```

**Edge case:** se rebase ha conflitti (probabile su `plugin.json`, `marketplace.json`, `CHANGELOG.md`):

```bash
# Risolvi conflitti tenendo la versione di main (siamo solo aggiunte docs nel branch
# pre-task-00; il bump versione vero del piano sarà in task-08).
git checkout --theirs .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git rebase --continue
```

## Step 2 — Determina nuova target version

```bash
CURRENT_MAIN_VERSION=$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['version'])")
echo "Main attuale: v$CURRENT_MAIN_VERSION"
# Atteso: 1.70.0 o successivo

# Nuova target version = next minor di main
NEW_TARGET="$(python3 -c "
v='$CURRENT_MAIN_VERSION'.split('.')
print(f'{v[0]}.{int(v[1])+1}.0')
")"
echo "Nuova target version per il piano: v$NEW_TARGET"
# Atteso: 1.71.0 se main = 1.70.0
```

## Step 3 — Update version reference nei doc del piano

Sostituisci tutte le occorrenze `1.69.0` con `$NEW_TARGET` (valore calcolato Step 2, presunto `1.71.0`):

```bash
# Verifica prima quante occorrenze
grep -rn "1\.69\.0" docs/plans/2026-05-28-devforge-gates-universal*

# Sostituisci (con sed -i compatibile macOS BSD)
find docs/plans/2026-05-28-devforge-gates-universal* -type f -name '*.md' \
    -exec sed -i.bak "s/1\.69\.0/${NEW_TARGET}/g" {} \;
find docs/plans/2026-05-28-devforge-gates-universal* -name '*.bak' -delete

# Verifica zero residui
grep -c "1\.69\.0" docs/plans/2026-05-28-devforge-gates-universal*/*.md
# Atteso: tutti zero
```

## Step 4 — Re-verify line numbers nei task

I task 02-06 referenziano line number specifici di `hooks/*-gate`. Post-rebase main potrebbe averli shiftati. Verifica con grep e aggiorna manualmente:

```bash
# pr-premortem-gate riferimento (era L61-71 inline + L19-23 source)
grep -n 'grep -qE "\[/:\]itsiae/"' hooks/pr-premortem-gate
grep -n 'PLUGIN_ROOT=' hooks/pr-premortem-gate
grep -n 'source.*lib/' hooks/pr-premortem-gate | head -5

# Ripeti per tdd-gate, pr-blind-review-gate, plan-gate-write, brainstorming-gate
for hook in tdd-gate pr-blind-review-gate plan-gate-write brainstorming-gate; do
    echo "=== hooks/$hook ==="
    grep -n 'grep -qE "\[/:\]itsiae/"' "hooks/$hook"
done
```

Se i line number nei task (es. `task-02-refactor-pr-premortem-gate.md` "Edit 2 — sostituisci L61-71") sono drift, aggiorna i task md prima di iniziare l'implementazione.

## Step 5 — Commit rebase + version update

```bash
git add docs/plans/2026-05-28-devforge-gates-universal*
git commit -m "docs(plans): rebase on main + bump target version to v${NEW_TARGET}

Post-rebase: line numbers re-verified in 5 gate hooks. Target version
for v1.69.0 obsolete (main is now v$CURRENT_MAIN_VERSION) — bumped to
v${NEW_TARGET} across design + plan files.

Co-Authored-By: SIAE DevForge"

git push --force-with-lease origin feat/skill-premortem
```

⚠️ `--force-with-lease`: necessario dopo rebase, ma sicuro (fallisce se altri hanno pushato nel frattempo).

---

## Criteri di accettazione

- [ ] `git log feat/skill-premortem..origin/main` ritorna 0 commit (branch in sync)
- [ ] `plugin.json` versione = quella di main (NON ancora bumpata, sarà task 08)
- [ ] `grep -c "1\.69\.0" docs/plans/2026-05-28-devforge-gates-universal*/*.md` ritorna tutti zero
- [ ] Tutti i line number reference nei task 02-06 verificati e aggiornati se shifted
- [ ] Branch push verde con `--force-with-lease`
