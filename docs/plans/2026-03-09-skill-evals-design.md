# Skill Evals & Description Optimization — Design Doc

**Data:** 2026-03-09
**Autore:** DevForge AI + Lorenzo
**SP:** 3
**Stato:** Approvato

---

## Contesto

Le 26 skill DevForge hanno description scritte a mano senza validazione empirica.
Il blog post Anthropic "[Improving skill-creator](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)" introduce evals, benchmark, A/B testing e description optimization per le skill Claude Code.

### Problemi attuali

1. **Zero evals funzionali** — testiamo struttura (frontmatter, VDS) ma non "la skill produce output corretto"
2. **Nessun tracking regressioni** — cambiamenti a modello o skill non vengono rilevati
3. **Description non ottimizzate** — trigger description keyword-based, non validate empiricamente
4. **Nessun A/B testing** — modifiche skill senza confronto strutturato

### Decisione

**Approccio C — Ibrido:**
- Installare `skill-creator` (Anthropic) come plugin di authoring esterno
- Integrare i risultati (trigger eval queries) nel test runner DevForge per CI/regression

---

## Sezione 1: Installazione e Setup

### skill-creator plugin

Installazione come plugin aggiuntivo (NON dentro siae-dev-forge/):

```bash
claude plugins install skill-creator --from anthropics/skills
```

Dipendenze: `claude` CLI, Python 3, `jq`.

### Struttura directory

```
siae-dev-forge/
├── evals/                          ← NUOVO
│   ├── trigger-evals/              ← output del description optimizer
│   │   ├── siae-brainstorming.json
│   │   ├── siae-tdd.json
│   │   └── ...
│   └── workspace/                  ← risultati benchmark (gitignored)
│       └── iteration-N/
```

`evals/workspace/` in `.gitignore`. I file `trigger-evals/*.json` committati (dataset regressione).

---

## Sezione 2: Description Optimization

### Workflow per skill

Per ogni skill (partendo dalle più critiche):

1. Genera 20 eval queries — 10 should-trigger + 10 should-not-trigger
2. Review con utente via viewer HTML
3. Run optimization loop: `python -m scripts.run_loop --eval-set <json> --skill-path <skill> --max-iterations 5`
4. Applica `best_description` al frontmatter YAML

### Priorità ottimizzazione

| Priorità | Skill | Motivo |
|----------|-------|--------|
| 1 | `siae-brainstorming` | Gate per tutto il design |
| 2 | `siae-verification` | Cross-cutting, deve attivarsi prima di claim completamento |
| 3 | `siae-debugging` | Deve vincere su risposte dirette per bug |
| 4 | `siae-git-workflow` | Triggerare su operazioni git, non menzioni casuali |
| 5 | `siae-tdd` | Attivarsi su qualsiasi scrittura di codice |
| 6-26 | Resto | Batch successivi |

### Formato trigger eval (compatibile skill-creator)

```json
[
  {"query": "Ho un bug nel servizio di autenticazione...", "should_trigger": true},
  {"query": "Fammi un riassunto di questo documento", "should_trigger": false}
]
```

---

## Sezione 3: Integrazione Test Runner (CI/Regression)

### Nuova suite: Trigger Regression Tests

Aggiunta a `tests/run-all.sh` con flag `--with-trigger-regression`.

Per ogni file `evals/trigger-evals/<skill>.json`:
1. Query `should_trigger: true` → verifica invocazione skill
2. Query `should_trigger: false` → verifica NON invocazione
3. Calcolo precision e recall

### Output

```
=== Trigger Regression Tests ===
  PASS  siae-brainstorming: 9/10 should-trigger, 10/10 should-not-trigger (P:1.00 R:0.90)
  WARN  siae-tdd: 7/10 should-trigger — recall sotto soglia (0.70 < 0.80)
```

### Soglie

- **Recall >= 0.80** — skill triggera almeno 80% dei casi dovuti
- **Precision >= 0.80** — skill non triggera più del 20% dei casi non dovuti
- Sotto soglia = WARN (non FAIL) — le description sono probabilistiche

### Modalità esecuzione

```bash
# Veloce (strutturale, gratis)
bash tests/run-all.sh

# Completo (include trigger regression, consuma token)
bash tests/run-all.sh --with-trigger-regression
```

Script dedicato: `tests/run-trigger-regression.sh`

---

## Sezione 4: Scope Futuro (non in questo sprint)

### Evals funzionali

Verifica qualità output (es. "brainstorming produce 2-3 approcci con trade-off?").
Richiede Executor + Grader subagent, tempo e token significativi.
Tenuto come fase 2.

### Workflow operativo

```
AUTHORING (occasionale)           CI/REGRESSION (ad ogni PR)
─────────────────────             ─────────────────────────
1. Scrivi/modifica skill          tests/run-all.sh --with-trigger-regression
2. skill-creator → Eval mode      → Legge trigger-evals/*.json
3. Description optimizer           → Verifica precision/recall
4. Salva trigger-evals/*.json     → WARN se sotto 0.80
5. Committa tutto
```

---

## Deliverable

| # | Deliverable | Tipo |
|---|------------|------|
| 1 | Installazione skill-creator plugin | Setup |
| 2 | Directory `evals/` + `.gitignore` workspace | Scaffold |
| 3 | Description optimization top 5 skill | Authoring |
| 4 | File `trigger-evals/*.json` per top 5 | Test data |
| 5 | Nuovo blocco in `tests/run-all.sh` con flag `--with-trigger-regression` | Code |
| 6 | Script `tests/run-trigger-regression.sh` | Code |

---

## Criteri di accettazione

- [ ] skill-creator installato e funzionante
- [ ] Top 5 skill hanno description ottimizzate con `best_description`
- [ ] 5 file `trigger-evals/*.json` committati con 20 query ciascuno
- [ ] `tests/run-all.sh --with-trigger-regression` esegue la suite
- [ ] Precision e recall >= 0.80 per le top 5 skill
- [ ] `tests/run-all.sh` (senza flag) continua a funzionare come prima

---

## Fonti

- [Improving skill-creator: Test, measure, and refine Agent Skills](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)
- [skill-creator SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
- [schemas.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/references/schemas.md)
