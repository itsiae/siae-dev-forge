# Task 01 — `adoption-analyzer.py --task-adoption-meta` (lettura ledger + meta JSON)

**Goal:** aggiungere a `lib/adoption-analyzer.py` la modalità `--task-adoption-meta <task_id>`
che stampa il meta JSON dell'evento `task_adoption` per quel task, riusando `CORE_SKILLS`
(single source). Stampa **nulla** se il ledger del task è assente/vuoto. Copre AC1, AC2, AC3, AC8.

**File coinvolti:**
- Modifica: `lib/adoption-analyzer.py`
- Crea: `tests/test_task_adoption_meta.py`

## Step 1 — Scrivi il test fallente

Crea `tests/test_task_adoption_meta.py`:

```python
"""Task 01 — adoption-analyzer.py --task-adoption-meta: legge il ledger di un task
e produce il meta JSON dell'evento task_adoption. Riusa CORE_SKILLS (single source)."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ANALYZER = REPO_ROOT / "lib" / "adoption-analyzer.py"


def _run(task_id, home):
    return subprocess.run(
        [sys.executable, str(ANALYZER), "--task-adoption-meta", task_id],
        capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
    )


def _seed_ledger(home, task_id, invoked, validated, metadata=None):
    d = home / ".claude" / ".devforge-task-skills" / task_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "skills_invoked").write_text("\n".join(invoked) + ("\n" if invoked else ""))
    (d / "skills_validated").write_text("\n".join(validated) + ("\n" if validated else ""))
    if metadata:
        (d / "metadata").write_text(metadata)


def test_meta_shape_with_core_bools(tmp_path):
    _seed_ledger(
        tmp_path, "abc123def456",
        invoked=["siae-brainstorming", "siae-tdd"],
        validated=["siae-tdd"],
        metadata="branch_name=feat/x\ndesign_doc=docs/plans/x-design.md\n",
    )
    r = _run("abc123def456", tmp_path)
    assert r.returncode == 0, r.stderr
    meta = json.loads(r.stdout)
    assert meta["task_id"] == "abc123def456"
    assert meta["task_branch"] == "feat/x"
    assert meta["design_doc"] == "docs/plans/x-design.md"
    assert meta["skills_invoked"] == ["siae-brainstorming", "siae-tdd"]
    assert meta["skills_validated"] == ["siae-tdd"]
    csv = meta["core_skills_validated"]
    # 5 core keys present, bool, tdd=True others=False
    assert set(csv.keys()) == {
        "siae-brainstorming", "siae-tdd", "siae-git-workflow",
        "siae-verification", "siae-blind-review",
    }
    assert csv["siae-tdd"] is True
    assert csv["siae-brainstorming"] is False


def test_empty_ledger_prints_nothing(tmp_path):
    # AC3: ledger esiste ma vuoto → nessun output
    _seed_ledger(tmp_path, "emptytask001", invoked=[], validated=[])
    r = _run("emptytask001", tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_missing_task_prints_nothing(tmp_path):
    # AC2: task_id non esistente (fuori scope a monte) → nessun output
    r = _run("nonexistent99", tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_core_list_is_single_source(tmp_path):
    # AC8: le chiavi core derivano da CORE_SKILLS del modulo, non da una lista duplicata.
    src = ANALYZER.read_text()
    assert "CORE_SKILLS" in src
    _seed_ledger(tmp_path, "t1", invoked=["siae-verification"], validated=["siae-verification"])
    meta = json.loads(_run("t1", tmp_path).stdout)
    assert meta["core_skills_validated"]["siae-verification"] is True
```

## Step 2 — Esegui e verifica che fallisce

Run: `cd "$(git rev-parse --show-toplevel)" && python3 -m pytest tests/test_task_adoption_meta.py -v`
Output atteso: FAILED — `adoption-analyzer.py: error: unrecognized arguments: --task-adoption-meta`
(la modalità non esiste ancora).

## Step 3 — Implementa il codice minimo

In `lib/adoption-analyzer.py`:

**(a)** Aggiungi due helper dopo `_ledger_task_skills` (dopo riga 99):

```python
def _read_skill_lines(path: Path) -> list[str]:
    """Legge un file ledger (una skill per riga), normalizza il prefisso plugin."""
    try:
        raw = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    except OSError:
        return []
    return [s.split(":")[-1] for s in raw]


def _read_task_metadata(path: Path) -> tuple[str, str]:
    """Estrae (branch_name, design_doc) dal file metadata key=value. ('','') se assente."""
    branch = design = ""
    try:
        for ln in path.read_text().splitlines():
            if ln.startswith("branch_name="):
                branch = ln.split("=", 1)[1].strip()
            elif ln.startswith("design_doc="):
                design = ln.split("=", 1)[1].strip()
    except OSError:
        pass
    return branch, design


def _task_adoption_meta(task_id: str) -> dict | None:
    """Meta JSON dell'evento task_adoption per TASK_ID. None se ledger assente/vuoto."""
    d = _task_skills_dir() / task_id
    invoked = _read_skill_lines(d / "skills_invoked")
    validated = _read_skill_lines(d / "skills_validated")
    if not invoked and not validated:
        return None
    branch, design = _read_task_metadata(d / "metadata")
    validated_set = set(validated)
    return {
        "task_id": task_id,
        "task_branch": branch,
        "design_doc": design,
        "skills_invoked": sorted(set(invoked)),
        "skills_validated": sorted(validated_set),
        "core_skills_validated": {s: (s in validated_set) for s in CORE_SKILLS},
    }
```

**(b)** In `main`, aggiungi l'argomento (dopo `p.add_argument("--skill", ...)`, riga 254):

```python
    p.add_argument("--task-adoption-meta", metavar="TASK_ID", default=None,
                   help="Print task_adoption meta JSON for TASK_ID (empty if no ledger).")
```

**(c)** In `main`, subito dopo `args = p.parse_args(argv)` (riga 255), prima del resto:

```python
    if args.task_adoption_meta is not None:
        meta = _task_adoption_meta(args.task_adoption_meta)
        if meta is not None:
            print(json.dumps(meta, sort_keys=True))
        return 0
```

## Step 4 — Esegui e verifica che passa

Run: `cd "$(git rev-parse --show-toplevel)" && python3 -m pytest tests/test_task_adoption_meta.py -v`
Output atteso: `4 passed`.

Regressione modulo: `python3 -m pytest tests/ -k adoption -v` → tutti PASS (nessuna rottura
dei test esistenti di `adoption-analyzer.py`).

## Step 5 — Commit

```bash
git add lib/adoption-analyzer.py tests/test_task_adoption_meta.py
git commit -m "feat(telemetry): adoption-analyzer --task-adoption-meta per task_adoption (Layer 1 task-01)"
```

## Criteri di accettazione
- [ ] `--task-adoption-meta <task_id>` stampa meta JSON con `task_id`, `task_branch`,
      `design_doc`, `skills_invoked[]`, `skills_validated[]`, `core_skills_validated{5 bool}`.
- [ ] Ledger vuoto o task inesistente → output vuoto, exit 0 (AC2, AC3).
- [ ] `core_skills_validated` deriva da `CORE_SKILLS` del modulo (no lista duplicata) (AC8).
- [ ] 4 test PASS; test adoption esistenti non rotti.
