# Task 04 — Strip Leakage `siae-git-workflow` (PRODUZIONE/CERTIFICAZIONE)

**Goal:** Parametrizzare tag SIAE-specific (`PRODUZIONE`, `CERTIFICAZIONE`, `COLLAUDO`) → placeholder generici con esempio SIAE come fallback documentato.

**File coinvolti:**
- `skills/siae-git-workflow/SKILL.md` (linea ~134 + altre menzioni)

## Step 1 — Identifica tutte occorrenze

```bash
grep -nE 'PRODUZIONE|CERTIFICAZIONE|COLLAUDO' skills/siae-git-workflow/SKILL.md
```

Output atteso: lista linee con tag hardcoded (probabili: trigger description, sezione tag deploy, esempi).

## Step 2 — Strategia edit

**Frontmatter description**: rimuovi tag SIAE-specific dal trigger keyword, sostituisci con language generico:
- Da: `"tag COLLAUDO/CERTIFICAZIONE/PRODUZIONE"`
- A: `"tag deploy ambiente"`

**Body skill**: parametrizza tag con placeholder + nota esempio SIAE:

Pattern:
```markdown
Tag deploy: `<ENV_TAG>` (es. SIAE: `PRODUZIONE`, `CERTIFICAZIONE`, `COLLAUDO`).
```

## Step 3 — Edit puntuali

Per ogni occorrenza:
1. Leggi contesto con `sed -n '<line-5>,<line+5>p' skills/siae-git-workflow/SKILL.md`
2. Edit con tool Edit, preservando exact whitespace
3. Verifica diff con `git diff skills/siae-git-workflow/SKILL.md` dopo ogni edit

## Step 4 — Verifica generalizzazione

```bash
# Frontmatter description NON deve contenere tag SIAE:
sed -n '1,20p' skills/siae-git-workflow/SKILL.md | grep -E 'PRODUZIONE|CERTIFICAZIONE|COLLAUDO' && echo "FAIL frontmatter" || echo "PASS frontmatter"

# Body può menzionare come ESEMPIO (es. "es. SIAE: PRODUZIONE"):
grep -nE 'es\.\s+SIAE.*PRODUZIONE' skills/siae-git-workflow/SKILL.md | head -2
```

Output atteso:
- `PASS frontmatter`
- 1+ match nel body (ENV_TAG con esempio SIAE)

## Step 5 — Commit atomico

```bash
git add skills/siae-git-workflow/SKILL.md
git commit -m "chore(skills): parametrize SIAE deploy tags in siae-git-workflow

Tag PRODUZIONE/CERTIFICAZIONE/COLLAUDO erano hardcoded nel trigger description e
body. Ora <ENV_TAG> placeholder con esempio SIAE come reference. Skill diventa
riusabile su altri progetti con naming tag diverso, mantenendo SIAE come default
documentato."
```

## Criteri accettazione

- 0 match `PRODUZIONE\|CERTIFICAZIONE\|COLLAUDO` nel frontmatter description
- Body ha placeholder `<ENV_TAG>` o `<PROD_TAG>` con esempio SIAE
- Skill ancora invocabile su prompt SIAE ("tag PRODUZIONE", "deploy in CERTIFICAZIONE") via esempio body
- Commit atomico

## NO-REGRESSION

Manualmente verifica: skill deve continuare ad attivarsi su prompt come "creo tag PRODUZIONE per deploy" o "git tag CERTIFICAZIONE". Il match avviene su "git tag" + nome ambiente, non su keyword hardcoded.
