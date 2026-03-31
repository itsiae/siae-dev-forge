# Task 01 — Skill Skeleton + Frontmatter + Banner

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md`
**Dipende da:** nessuno

---

## Obiettivo

Creare la struttura base della skill con frontmatter corretto, banner DevForge,
legge di ferro, sezione comandi (`/forge-btp-baseline` e `/forge-btp-audit`),
e placeholder per Phase 1 e Phase 2 (da riempire nei task successivi).

---

## Step 1 — Test: verifica che la skill NON esista ancora

```bash
ls /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/ 2>/dev/null \
  && echo "ALREADY EXISTS" || echo "OK — not found, safe to create"
```

Output atteso: `OK — not found, safe to create`

---

## Step 2 — Crea la directory

```bash
mkdir -p /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit
```

---

## Step 3 — Scrivi `SKILL.md` con skeleton completo

Crea il file `skills/siae-btp-upgrade-audit/SKILL.md` con questo contenuto esatto:

```markdown
---
name: siae-btp-upgrade-audit
description: >
  Rileva regressioni di business logic durante upgrade librerie SAP BTP deprecate.
  Fase 1 (BASELINE): estrae fingerprint strutturato da branch vecchio.
  Fase 2 (AUDIT): confronta con branch nuovo e genera gap report per app.
  Trigger: /forge-btp-baseline, /forge-btp-audit, upgrade SAP BTP, librerie deprecate SAP,
  gap analysis SAP BTP, no-regression upgrade UI5, verifica migrazione BTP.
---

# siae-btp-upgrade-audit — SAP BTP Upgrade Audit

[BANNER DEVFORGE]

> **Tipo:** Flexible | **Fase SDLC:** 4. Implementation (tool di supporto upgrade)

---

## LA LEGGE DI FERRO

NESSUNA DICHIARAZIONE DI "MIGRAZIONE OK" SENZA GAP REPORT VERIFICATO.

## Comandi

| Comando | Azione |
|---------|--------|
| `/forge-btp-baseline <branch> [--app=nome]` | Fase 1: genera fingerprint dal branch vecchio |
| `/forge-btp-audit <old-branch> <new-branch> [--app=nome]` | Fase 2: gap analysis completa o per singola app |

**Repo target fisso:** `itsiae/liquidazione`

---

## Prerequisiti

Prima di eseguire qualsiasi fase, verifica:

```bash
gh auth status 2>&1 | grep "Logged in"
```

Output atteso: `✓ Logged in to github.com`

Se fallisce: esegui `gh auth login` prima di procedere.

---

## [PLACEHOLDER: PHASE 1 — BASELINE]
## [PLACEHOLDER: PHASE 2 — AUDIT]
## [PLACEHOLDER: DIFF ENGINE]
## [PLACEHOLDER: GAP REPORT]
```

Il banner DevForge è quello standard del design system (vedi altri SKILL.md per riferimento).

---

## Step 4 — Verifica che il file esista e abbia il frontmatter corretto

```bash
head -10 /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso:
```
---
name: siae-btp-upgrade-audit
description: >
  Rileva regressioni di business logic durante upgrade librerie SAP BTP deprecate.
```

---

## Step 5 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add siae-btp-upgrade-audit skeleton"
```
