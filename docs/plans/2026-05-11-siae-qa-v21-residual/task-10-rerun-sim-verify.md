# Task 10 — Re-run simulazione 3 fixture + verifica Criterio #7

**Goal:** Eseguire una nuova simulazione end-to-end della skill `siae-qa v2.1.0` (post-fix Task 1-9) sulle 3 golden fixture e verificare che il diff strutturale rientri nei bound del Criterio #7 rivisto in iter 3 del design.

**SP:** 1 (Umano) / 0.5 (Augmented)

**File coinvolti:**
- Output: `evals/workspace/siae-qa-sim-v21/{enumerative_spec,functional_be,role_based}/` (3 dir con MFINAL.json + TC_DRAFT.json + coverage_certificate.json)
- Report: `audit-reports/siae-qa-v21-simulation-report.md`

## Step 1 — Preparazione workspace nuovo

```bash
mkdir -p evals/workspace/siae-qa-sim-v21/{enumerative_spec,functional_be,role_based}
ls evals/workspace/siae-qa-sim-v21/
```

**Output atteso:** 3 dir create.

## Step 2 — Dispatch 3 simulation agent in parallelo

Per ogni fixture, invocare un subagent che simula il workflow end-to-end della skill v2.1.0. Usare lo stesso prompt pattern della simulazione v2.0.0 (vedi `evals/workspace/siae-qa-sim/`), ma:
- Path output: `evals/workspace/siae-qa-sim-v21/<fixture>/`
- Skill version target: `2.1.0` (le 7 ADR sono attive)
- Verifica criterio: usare il Criterio #7 **rivisto** del design (`docs/plans/2026-05-11-siae-qa-v21-residual-design.md` Criteri di Accettazione)

Prompt template (da personalizzare per ogni fixture):

```
Simula l'esecuzione end-to-end di siae-qa v2.1.0 (post-fix ADR-001..007) sulla fixture <FIXTURE>.

Input: evals/eval-sets/siae-qa/golden/<FIXTURE>/input.md
Skill rules: skills/siae-qa/SKILL.md (v2.1.0, vedi frontmatter)
Output target dir: evals/workspace/siae-qa-sim-v21/<FIXTURE>/

Step:
1. Read input.md
2. Phase 0 → 1 → 1.5 (applica regole esplosione AGGIORNATE incluse ADR-001/002/003/007)
3. Write MFINAL.json (schema reference/schemas/m_final.schema.json)
4. Phase 4b (applica ADR-005 multi-step mutating)
5. Write TC_DRAFT.json (schema reference/schemas/tc_draft.schema.json)
6. Phase 4c/4d
7. Write coverage_certificate.json (schema reference/schemas/coverage_certificate.schema.json)
8. Run validator: python3 skills/siae-qa/reference/scripts/validate_outputs.py --m-final ... --tc-draft ... --certificate ...
9. Confronto strutturale vs expected_*.json:
   - count(SIM.rows) vs count(EXP.rows): delta entro Criterio #7
   - set(SIM.entity) == set(EXP.entity)
   - distribuzione POS/NEG/EDGE/ROLE entro tolleranza
   - matrix_row_id SIM hanno mapping semantico a row EXP (no fantasma)

Output: simulation report markdown nello stesso formato dei 3 simulation report v2.0.0.
```

Lanciare i 3 agent in parallelo (singolo messaggio con 3 Agent tool call).

## Step 3 — Verifica Criterio #7 sui 3 output

Dopo i 3 simulation report disponibili, verificare i bound:

```bash
python3 <<'EOF'
import json

bounds = {
    "enumerative_spec": {"exp": 25, "tolerance": max(int(25*0.15), 4)},  # = 4
    "functional_be": {"exp": 8, "tolerance": 3},  # EXP <= 10
    "role_based": {"exp": 9, "tolerance": 3},  # EXP <= 10
}

results = {}
for fx, cfg in bounds.items():
    with open(f"evals/workspace/siae-qa-sim-v21/{fx}/MFINAL.json") as f:
        sim = json.load(f)
    sim_rows = len(sim["rows"])
    delta = abs(sim_rows - cfg["exp"])
    pass_criterion = delta <= cfg["tolerance"]
    results[fx] = {
        "sim_rows": sim_rows,
        "exp_rows": cfg["exp"],
        "delta": delta,
        "tolerance": cfg["tolerance"],
        "pass": pass_criterion,
    }

print("\nCriterio #7 verification:\n")
print(f"{'Fixture':<25} {'SIM':>5} {'EXP':>5} {'Delta':>7} {'Bound':>7}  Result")
print("-" * 70)
for fx, r in results.items():
    print(f"{fx:<25} {r['sim_rows']:>5} {r['exp_rows']:>5} {r['delta']:>7} {r['tolerance']:>7}  {'PASS' if r['pass'] else 'FAIL'}")

all_pass = all(r["pass"] for r in results.values())
print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
import sys
sys.exit(0 if all_pass else 1)
EOF
```

**Output atteso:**
```
Criterio #7 verification:

Fixture                     SIM   EXP   Delta   Bound  Result
----------------------------------------------------------------------
enumerative_spec             25    25       0       4  PASS
functional_be                10     8       2       3  PASS
role_based                    9     9       0       3  PASS

Overall: PASS
```

Tolleranze accettabili (range delta atteso dal design iter 4):
- enumerative_spec: 24-26 (delta 0..+1)
- functional_be: 9-10 (delta +1..+2)
- role_based: 9 (delta 0)

## Step 4 — Verifica distribuzione test_type per categoria

```bash
python3 <<'EOF'
import json
from collections import Counter

fixtures = ["enumerative_spec", "functional_be", "role_based"]
for fx in fixtures:
    with open(f"evals/workspace/siae-qa-sim-v21/{fx}/MFINAL.json") as f:
        sim = json.load(f)
    with open(f"evals/eval-sets/siae-qa/golden/{fx}/expected_mfinal.json") as f:
        exp = json.load(f)
    sim_dist = Counter(r["test_type"] for r in sim["rows"])
    exp_dist = Counter(r["test_type"] for r in exp["rows"])
    print(f"\n{fx}:")
    print(f"  SIM: {dict(sim_dist)}")
    print(f"  EXP: {dict(exp_dist)}")
    cats = ["POS", "NEG", "EDGE", "ROLE"]
    max_delta = max(abs(sim_dist[c] - exp_dist[c]) for c in cats)
    tol = 2 if exp_dist.total() > 10 else 1
    print(f"  Max delta per category: {max_delta} (tolerance: {tol}) → {'PASS' if max_delta <= tol else 'FAIL'}")
EOF
```

**Output atteso:** ogni fixture con max_delta <= tolerance (PASS).

## Step 5 — Validator finale su sim outputs

```bash
for fx in enumerative_spec functional_be role_based; do
  echo "=== $fx ==="
  python3 skills/siae-qa/reference/scripts/validate_outputs.py \
    --m-final evals/workspace/siae-qa-sim-v21/$fx/MFINAL.json \
    --tc-draft evals/workspace/siae-qa-sim-v21/$fx/TC_DRAFT.json \
    --certificate evals/workspace/siae-qa-sim-v21/$fx/coverage_certificate.json
  echo "Exit code: $?"
done
```

**Output atteso:** 5/5 PASS per ogni fixture, exit code 0 (o solo `[WARN]` se ADR-006 emette warning su NEG numeric senza EDGE — ma exit code resta 0).

## Step 6 — Genera simulation report consolidato

Creare `audit-reports/siae-qa-v21-simulation-report.md` con la stessa struttura del consolidated report v2.0.0 (vedi conversation history precedente):

```markdown
# siae-qa v2.1.0 — Simulation Report Consolidated

## Aggregate Score Matrix
| Fixture | M_FINAL rows | TC generati | Validator | Criterio #7 | Verdict |
|---|---|---|---|---|---|
| enumerative_spec | <N> | <N> | 5/5 PASS | delta=<X> ≤ 4 PASS | PASS |
| functional_be | <N> | <N> | 5/5 PASS | delta=<X> ≤ 3 PASS | PASS |
| role_based | <N> | <N> | 5/5 PASS | delta=<X> ≤ 3 PASS | PASS |

## Comparison v2.0.0 vs v2.1.0
| Fixture | v2.0.0 SIM rows | v2.1.0 SIM rows | EXP | Δ v2.0 | Δ v2.1 |
|---|---:|---:|---:|---:|---:|
| enumerative_spec | 39 | <N21> | 25 | +14 | +<X> |
| functional_be | 15 | <N21> | 8 | +7 | +<X> |
| role_based | 9 | <N21> | 9 | 0 | 0 |

## Scorecard delta
- Determinism: 4/5 → 5/5 (ADR-001/002/003 chiudono ambiguità)
- Reproducibility: 4/5 → 5/5 (ADR-004/007 chiudono naming + esplosione)
- Test determinism: 5/5 → 5/5 (invariato, già massimo)
- Total: 43/50 → 48/50 (Gold tier consolidato)
```

## Step 7 — Commit

```bash
git add evals/workspace/siae-qa-sim-v21/ audit-reports/siae-qa-v21-simulation-report.md
git commit -m "test(siae-qa-v21): simulation end-to-end + verifica Criterio #7

Re-run simulazione siae-qa v2.1.0 sulle 3 golden fixture post-ADR-001..007.

Risultati attesi (dal design):
- enumerative_spec: SIM 24-26 vs EXP 25 (delta 0..+1, bound ≤4) → PASS
- functional_be: SIM 9-10 vs EXP 8 (delta +1..+2, bound ≤3) → PASS
- role_based: SIM 9 vs EXP 9 (delta 0, bound ≤3) → PASS

Validator: 5/5 PASS per ogni fixture (exit code 0).
Scorecard skill: 43/50 → 48/50 (Gold tier consolidato).

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] 3 simulation report generati in `evals/workspace/siae-qa-sim-v21/`
- [ ] Validator Step 5: 5/5 PASS per ogni fixture (exit 0)
- [ ] Criterio #7 Step 3: tutti i 3 delta entro bound (script Python exit 0)
- [ ] Distribuzione per categoria Step 4: max_delta ≤ tolerance per ogni fixture
- [ ] `audit-reports/siae-qa-v21-simulation-report.md` creato con sezioni: Aggregate Score Matrix, Comparison v2.0.0 vs v2.1.0, Scorecard delta
- [ ] Commit conventional commits
- [ ] **Gate di chiusura piano:** se questo task PASS, il piano v2.1.0 è completo e si può procedere con `siae-finishing-branch` per aprire PR.
