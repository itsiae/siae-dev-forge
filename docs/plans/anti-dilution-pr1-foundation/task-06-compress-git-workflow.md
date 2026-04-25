# Task 06 — Comprimere skills/siae-git-workflow/SKILL.md (744→220 righe)

**Stato:** [PENDING]
**Execution:** subagent (parallel-safe)
**Dipendenze:** T01
**Durata stimata:** 12-15 min

## Classificazione K/M/D

| Sezione | Riga | Classe | Azione |
|---|---|---|---|
| `## LA LEGGE DI FERRO` | 28 | K | Verbatim |
| `## PRE-FLIGHT CARD` | 41 | K | Verbatim (regola non negoziabile) |
| `## SCOPE GUARD` | 66 | K | Verbatim |
| `## 0. Environment Check` | 86 | K | Compatto ma verbatim |
| `## 1. Branch Strategy SIAE` | 99 | K | Verbatim |
| `## 2. Branch Naming` | 117 | K | Verbatim |
| `## 3. Conventional Commits` | 133 | K | Verbatim |
| `## 4. Tag-Based Deployment` | 151 | K | Verbatim |
| `## 5. Merge Strategy` | 170 | K | Verbatim |
| `## 6. HARD-GATE Rules` | 181 | K | Verbatim |
| `## Permission Denied Handling` | 194 | M | Ref a `lib/permission-denied-handling.md` |
| `## 7. Vincoli Operativi` | 235 | M | Ref a `lib/operational-limits.md` + override specifici |
| `## 8. Flusso Operativo` | 257 | D | Elimina (duplica Branch Strategy) |
| `## 9. Hotfix e Rollback` | 348 | K | Compatto: mantieni procedura, elimina esempi multipli |
| `## Tabella Anti-Razionalizzazione` | 480 | D | Elimina |
| `## 10. Esempi Pratici — Pre-flight Card` | 496-732 | **D massiccia** | **Sostituisci 9 casi (230 righe) con tabella decisionale 12 righe + 1 esempio template** |
| `## Classificazione Rischio` | 733 | M | Ref a `lib/risk-taxonomy.md` + override git-specifici |

## La grande riduzione: Casi Pratici

Le 230 righe di "Caso 1-9 Pre-flight Card" vengono sostituite da una tabella decisionale:

```markdown
## Pre-flight Card — Decisione rapida

| Comando | Livello | Card richiesta |
|---|---|---|
| `git push` feature branch | 🟡 MEDIO | Sì (standard) |
| `git tag` + push | 🔴 ALTO | Sì + conferma esplicita |
| `git merge` promozione ambiente | 🟡 MEDIO | Sì |
| `git push --force` branch personale | 🔴 ALTO | Sì + conferma |
| `git push --force` branch condiviso | 🚨 CRITICO | **BLOCCO ASSOLUTO** — refuse |
| `git rebase` branch condiviso | 🚨 CRITICO | **BLOCCO ASSOLUTO** — refuse |
| `git branch -D` | 🔴 ALTO | Sì + verify merge-base |
| `git add` + `git commit` | 🟡 MEDIO | Sì (quality gate auto) |
| `git checkout -b` new branch | 🟢 SICURO | No |
| Scope creep: tag non richiesto | - | **STOP** — chiedi prima |

Formato standard della Pre-flight Card: vedi `lib/checkpoint-schema.md` sezione "Pre-flight Card".

Esempio template:
| 🟡 MEDIO — 🔨 DevForge · siae-git-workflow |
|:---|
| Operazione: `git push origin feature/xyz` |
| Branch: `feature/xyz` · Remote: `origin` |
| 1. Azione: push feature branch |
| Perché: sync con remote per review |
| Se NO: i commit locali non sono visibili agli altri |
```

Questo pattern (1 tabella + 1 esempio template) sostituisce 230 righe con ~25.

## Step

Stesso pattern T04/T05. Check specifici:
```bash
grep -q "## PRE-FLIGHT CARD" skills/siae-git-workflow/SKILL.md && echo "PASS preflight"
grep -q "## SCOPE GUARD" skills/siae-git-workflow/SKILL.md && echo "PASS scope_guard"
grep -q "## 6. HARD-GATE Rules" skills/siae-git-workflow/SKILL.md && echo "PASS hardgate"
grep -qE "git push --force" skills/siae-git-workflow/SKILL.md && echo "PASS force_push_doc"
```

## Acceptance

- [ ] `wc -l` ≤ 220
- [ ] Tutte le sezioni K preservate (verificato grep)
- [ ] Tabella decisionale pre-flight presente
- [ ] Conventional Commits regex documentata
- [ ] Branch Strategy (feature/bugfix/hotfix/release) documentata
- [ ] Commit conventional `refactor(skills):`

## Safeguard

**Regola inviolabile**: "BLOCCO ASSOLUTO" per `git push --force` e `git rebase` su branch condiviso DEVE restare. Se la tabella decisionale rischia di sminuirlo, aggiungi un paragrafo di 3 righe sotto la tabella con il blocco esplicito.
