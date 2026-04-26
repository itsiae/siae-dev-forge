---
name: forge-adoption
description: >
  Mostra la tua adoption personale delle 5 skill core DevForge, confrontata
  con la media del team. Legge il ledger task-scoped di PR #2 e aggrega da
  ~/.claude/devforge-activity.jsonl. Utile prima di aprire una PR per
  auto-valutare se stai seguendo il workflow.
---

# /forge-adoption

Stampa una tabella compatta con:

- **User**: la tua adoption per le 5 skill core, **task-scoped** quando il
  ledger `~/.claude/.devforge-task-skills/` è popolato, altrimenti
  session-scope come fallback.
- **Team median**: la mediana dell'adoption session-scope calcolata su
  tutti gli utenti visti in `devforge-activity.jsonl` (finestra configurabile).
- **Delta**: differenza in punti percentuali. Negativo = sotto la media team.

## Come invocare

Esegui lo script Python wrappato dalla skill:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/adoption-analyzer.py --format table --window 7
```

Parametri:

| Flag | Valore default | Descrizione |
|---|---|---|
| `--format` | `table` | `table` / `json` / `recap` / `block` |
| `--window` | `7` | Giorni di storia `activity.jsonl` da aggregare |
| `--skill` | — | Richiesto per `--format block` (una delle 5 core) |

## Core skills

`siae-brainstorming`, `siae-tdd`, `siae-git-workflow`, `siae-verification`, `siae-blind-review`.

## Come leggere il delta

| Delta | Interpretazione |
|---|---:|
| ≥ +5pp | Sopra la media team — stai tenendo il passo. |
| ±5pp | Allineato — nessuna azione immediata. |
| < -5pp | Sotto la media team — invoca la skill più in ritardo prima del prossimo commit. |

## Esempio output

```
| Skill | User | Team median | Delta |
|---|---:|---:|---:|
| `siae-brainstorming` | 62% | 38% | +24pp |
| `siae-tdd` | 48% | 38% | +10pp |
| `siae-git-workflow` | 71% | 62% | +9pp |
| `siae-verification` | 15% | 3% | +12pp |
| `siae-blind-review` | 25% | 0% | +25pp |

_Window: last 7 days. User is task-scope when ledger is populated,
session-scope fallback otherwise. Team median is always session-scope._
```

## Note implementative

- Nessuna chiamata di rete. I dati sono tutti locali (ledger + JSONL).
- Se il ledger è assente (PR #2 non deployato), tutte le righe User
  usano session-scope come User e il confronto col Team median perde
  significato differenziale.
- Il comando è **solo-lettura**: zero side effects, safe da invocare
  più volte.

## Escalation

Se la tabella mostra < -10pp su 3+ skill su 5, chiedi a `siae-dev-analytics`
un report esteso con granularità settimanale.
