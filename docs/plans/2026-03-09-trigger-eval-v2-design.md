# Trigger Eval v2 — Allineamento ad Anthropic run_eval.py

**Data:** 2026-03-09
**SP:** 3
**Approccio:** A — Riscrittura completa in Python

## Contesto

Il nostro `run-trigger-regression.sh` testa il triggering delle skill con 1 run/query
in modo sequenziale e detection via grep. L'approccio di Anthropic (`run_eval.py`) usa
3 run/query, threshold probabilistico (>=0.5), parallelismo (ProcessPoolExecutor),
e stream-json parsing. Dobbiamo allinearci.

## Decisioni

- **Python puro**: `tests/run-trigger-eval.py` come core, bash wrapper sottile
- **3 run per query** (default, configurabile con `--runs-per-query`)
- **trigger_threshold = 0.5**: 2/3 trigger = pass (non binario)
- **8 worker paralleli** (default, configurabile)
- **Rimozione CLAUDECODE env** per permettere nesting claude-in-claude
- **Stream-json parsing** con `--include-partial-messages` (early detection)
- **Command file temporaneo** in `.claude/commands/` (come Anthropic)
- **Eliminazione `bedrock-trigger-test.py`** e mode `--use-bedrock`

## Architettura

```
tests/
├── run-trigger-eval.py        # Core Python (NUOVO)
├── run-trigger-regression.sh  # Thin wrapper bash (RISCRITTO)
├── run-all.sh                 # Invariato (flag --with-trigger-regression)
└── bedrock-trigger-test.py    # ELIMINATO
```

## run-trigger-eval.py — API

```
python3 tests/run-trigger-eval.py \
  --eval-file evals/trigger-evals/siae-brainstorming.json \
  --skill siae-brainstorming \
  --skill-description "description dal SKILL.md" \
  --runs-per-query 3 \
  --trigger-threshold 0.5 \
  --num-workers 8 \
  --timeout 30 \
  [--model <model-id>] \
  [--verbose]
```

### Output JSON (stdout)

```json
{
  "skill_name": "siae-brainstorming",
  "description": "...",
  "results": [
    {
      "query": "...",
      "should_trigger": true,
      "trigger_rate": 0.67,
      "triggers": 2,
      "runs": 3,
      "pass": true
    }
  ],
  "summary": {
    "total": 20,
    "passed": 18,
    "failed": 2,
    "precision": 0.90,
    "recall": 0.85,
    "accuracy": 0.90
  }
}
```

### Verbose output (stderr)

```
Evaluating: siae-brainstorming (20 queries, 3 runs each, 8 workers)
  [PASS] rate=3/3 expected=true: Devo implementare una nuova feature per il ser...
  [FAIL] rate=0/3 expected=true: Ho un'idea per migliorare il sistema di notifi...
  [PASS] rate=0/3 expected=false: Il test TestRipartizioneService::testCalcoloQ...
Results: 18/20 passed (P:0.90 R:0.85 A:0.90)
```

## Detection flow (per singola query)

1. Crea `.claude/commands/<skill>-skill-<uuid>.md` con description YAML
2. Lancia `claude -p <query> --output-format stream-json --verbose --include-partial-messages`
   - Env: rimuove `CLAUDECODE` per permettere nesting
3. Parsa stream: `content_block_start` (type=tool_use, name=Skill/Read) →
   `content_block_delta` (partial_json contiene skill name) → early return True
4. Se `message_stop` senza tool_use → return False
5. Cleanup: elimina command file temporaneo
6. Timeout: kill processo dopo 30s → return False

## run-trigger-regression.sh — Wrapper

```bash
# Per ogni evals/trigger-evals/*.json:
#   1. Legge description dal SKILL.md corrispondente
#   2. Chiama python3 run-trigger-eval.py con parametri
#   3. Parsa exit code (0=PASS, 1=WARN)
#   4. Aggrega PASS/WARN/SKIP
# Accetta: --skill, --runs-per-query, --num-workers, --timeout
```

## Criteri di accettazione

- [ ] `run-trigger-eval.py` esegue 3 run/query in parallelo
- [ ] trigger_threshold 0.5 (2/3 = pass)
- [ ] Stream-json parsing con early detection
- [ ] CLAUDECODE rimosso dall'env per nesting
- [ ] Command file temporaneo creato/eliminato per ogni query
- [ ] `bedrock-trigger-test.py` eliminato
- [ ] `run-trigger-regression.sh` riscritto come thin wrapper
- [ ] `run-all.sh` funziona con `--with-trigger-regression`
- [ ] Output JSON compatibile con skill-creator di Anthropic
- [ ] Test strutturali passano (75 PASS, 0 FAIL)
