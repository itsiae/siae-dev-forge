# Task 12 — Renderer integration in code-reviewer + spec-reviewer

**SP:** 1.0 · **AC mappati:** AC #7 · **Dipendenze:** Task 04-11 · **Wave:** 4

## Goal

Aggiungere "Step 0.5 — Load Pre-Computed Evidence" agli agent `code-reviewer.md` e `spec-reviewer.md`. Gli agent leggono `.claude/review-evidence/<sha>.json` e usano i valori numerici come ground truth, citando `source` per ogni claim.

## File coinvolti

**Modificare:**
- `agents/code-reviewer.md` (inserire Step 0.5 tra Step 0 e "PRIMA DELLA REVIEW")
- `agents/spec-reviewer.md` (analoga sezione)

**Creare:**
- `tests/test_review_evidence_renderer_contract.py` (verifica che agent .md contengano Step 0.5 ben formato)

## Step TDD

### Step 1 — Test contract sui file agent

```python
"""Verifica che gli agent contengano la sezione Step 0.5 evidence-loading."""
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CODE_REVIEWER = REPO_ROOT / "agents" / "code-reviewer.md"
SPEC_REVIEWER = REPO_ROOT / "agents" / "spec-reviewer.md"


def test_code_reviewer_has_step_0_5():
    content = CODE_REVIEWER.read_text()
    assert "Step 0.5" in content
    assert ".claude/review-evidence/" in content
    assert "evidence_from_json" in content or "verdict" in content
    assert "NON ricalcolare" in content or "non ricalcolare" in content.lower()


def test_code_reviewer_lists_source_field():
    content = CODE_REVIEWER.read_text()
    assert "source" in content
    assert "local:" in content or "ci:sarif:" in content


def test_code_reviewer_has_fallback_branch():
    content = CODE_REVIEWER.read_text()
    assert "evidence not pre-computed" in content
    assert "NON-DETERMINISTIC" in content


def test_spec_reviewer_has_spec_drift_section():
    content = SPEC_REVIEWER.read_text()
    assert "Step 0.5" in content
    assert "spec_drift" in content
    assert "drift_severity" in content


def test_spec_reviewer_has_fallback_branch():
    content = SPEC_REVIEWER.read_text()
    assert "evidence not pre-computed" in content
```

### Step 2 — Esegui test (fallisce)

```bash
pytest tests/test_review_evidence_renderer_contract.py -v
```

**Output atteso:** 5 FAIL, sezioni non ancora presenti.

### Step 3 — Modifica `agents/code-reviewer.md`

Trova la sezione "Step 0 — Tool Loading" e inserisci dopo di essa, prima di "PRIMA DELLA REVIEW":

```markdown
## Step 0.5 — Load Pre-Computed Evidence (Deterministic Quality Signals)

Prima di iniziare il 6-punti, leggi `.claude/review-evidence/<sha>.json` dove
`<sha>` è l'output di `git rev-parse HEAD`. Il file è prodotto dall'hook
`review-evidence` e contiene coverage, lint, complessità, CI quality reports e
spec-drift NUMERICI per il SHA corrente.

**Se evidence presente:**

1. Carica il JSON via `Read` (formato: schema_version 1.0, vedi `lib/review_evidence/schema.py`)
2. **NON ricalcolare** coverage/lint/complessità — usa i valori dell'evidence
3. Cita il `source` per ogni claim:
   - `local:coverage.py` / `local:lcov` / `local:jacoco-maven` → metrica locale eseguita
   - `local:ruff` / `local:eslint` / `local:checkstyle+pmd` / `local:tflint` → linter locali
   - `local:radon` / `local:complexity-report` → complessità locale
   - `ci:sarif:Qodana` / `ci:sarif:SonarQube` / `ci:sarif:CodeQL` → da artefatto CI
4. Se `verdict.block == true`, parti dal verdetto:
   ```
   Block triggered. Block reasons (deterministic):
   - {reason1}
   - {reason2}
   ```
5. Se `dirty_tree == true`, annota: "Evidence calcolata su working tree dirty — valori non riproducibili al 100%"
6. Se `metrics.ci_quality.available == false` con reason `no completed CI runs`, annota:
   "CI quality reports non ancora disponibili per questo SHA. Il pattern operativo è:
   primo `gh pr create` opera su soli segnali locali; dopo che la CI ha girato,
   `gh pr edit` ri-attiva l'hook che fetcha gli artefatti SARIF."

**Se evidence assente** (file non esiste):

- Annota nel verdetto finale: "**evidence not pre-computed** — falling back to subjective review"
- Procedi con review classica MA marca esplicitamente ogni finding come `NON-DETERMINISTIC`
- Suggerisci all'utente: "Lancia `/forge-evidence` prima di re-runnare la review per evidence riproducibile"

**Comportamento atteso:** la review citerà metriche numeriche (es. "coverage 65%
da `local:coverage.py`, ruff segnala 3 errori da `local:ruff`") invece di
affermazioni soggettive ("la coverage sembra bassa").
```

### Step 4 — Modifica `agents/spec-reviewer.md`

Aggiungi sezione analoga, focalizzata su `spec_drift`:

```markdown
## Step 0.5 — Load Pre-Computed Spec-Drift Evidence

Prima di analizzare il design doc, leggi `.claude/review-evidence/<sha>.json`
per la sezione `spec_drift` calcolata deterministicamente dall'hook.

**Se evidence presente con spec_drift non-null:**

- `design_doc_path` — path del design doc auto-discovered (o env override)
- `files_in_plan` — path estratti dalle sezioni allowlist del doc (code-fence/quote ignorati)
- `files_changed` — output di `git diff --diff-filter=AMR -M <base>...HEAD`
- `unplanned_files` — set difference (files modificati ma non nel piano)
- `drift_severity` — `none | low | medium | high`

**Cita i numeri:** "Drift `medium` rilevato: 4 file modificati non presenti nel
design doc `2026-05-12-foo-design.md`: `src/x.py`, `src/y.py`, ..."

**Se `drift_severity == high`**, parti dal verdetto: il design non copre la
maggior parte delle modifiche; il design doc deve essere aggiornato prima del
merge.

**Se evidence assente:**

- Annota "evidence not pre-computed" e procedi con analisi manuale del design doc
- Esegui `git diff --name-only <base>...HEAD` manualmente e confronta
- Marca findings come `NON-DETERMINISTIC`
```

### Step 5 — Esegui test (passa)

```bash
pytest tests/test_review_evidence_renderer_contract.py -v
# 5 passed
```

### Step 6 — Commit

```bash
git add agents/code-reviewer.md agents/spec-reviewer.md \
        tests/test_review_evidence_renderer_contract.py
git commit -m "feat(review-evidence): wire Step 0.5 evidence-loading in agents (#task-12)"
```

## Criteri di accettazione

- [ ] `agents/code-reviewer.md` contiene "Step 0.5" con istruzioni evidence-loading
- [ ] Sezione cita `.claude/review-evidence/<sha>.json` come source
- [ ] Mappa i `source:` value (local:* e ci:sarif:*) per citation
- [ ] Branch fallback (evidence assente) → mark "NON-DETERMINISTIC"
- [ ] `agents/spec-reviewer.md` ha analoga sezione spec_drift-focused
- [ ] 5 test contract passano
