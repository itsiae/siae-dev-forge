# Task 05 — `count_branch_operators.py`

**Goal:** Nuovo script che conta gli operatori di cortocircuito (`??`, `||`, `&&`, `?:`) per file TS/JS via regex AST-lite (NO ts-morph, zero nuove dipendenze), escludendo commenti e import. Output `.code-coverage/branch-count/<file>.json`. È il segnale "branch-heavy" che oggi manca (gap 6.7/R6).

**WS:** WS-2 · **Dipendenze:** nessuna (Task 06/07/08 lo consumano).

## File coinvolti
- Crea: `skills/code-coverage/scripts/count_branch_operators.py`
- Crea: `skills/code-coverage/scripts/tests/test_count_branch_operators.py`

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_count_branch_operators.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "count_branch_operators.py"


def _run(src: Path) -> dict:
    out = subprocess.run([sys.executable, str(SCRIPT), str(src)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_counts_operators(tmp_path):
    f = tmp_path / "LocaleDao.ts"
    f.write_text(
        "const a = x ?? '';\n"
        "const b = y || z;\n"
        "const c = p && q;\n"
        "const d = cond ? 1 : 2;\n",
        encoding="utf-8",
    )
    out = _run(f)
    assert out["count"] == 4
    assert out["by_operator"]["??"] == 1
    assert out["by_operator"]["||"] == 1
    assert out["by_operator"]["&&"] == 1
    assert out["by_operator"]["?:"] == 1
    assert out["branch_heavy"] is False  # soglia 20


def test_excludes_comments_and_imports(tmp_path):
    f = tmp_path / "x.ts"
    f.write_text(
        "import { A } from './a';   // a || b should not count\n"
        "/* c ?? d also ignored */\n"
        "const real = e ?? f;\n",
        encoding="utf-8",
    )
    out = _run(f)
    assert out["count"] == 1


def test_branch_heavy_flag(tmp_path):
    f = tmp_path / "heavy.ts"
    f.write_text("\n".join(f"const v{i} = a{i} ?? '';" for i in range(25)), encoding="utf-8")
    out = _run(f)
    assert out["count"] == 25
    assert out["branch_heavy"] is True
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_count_branch_operators.py -v`
Output atteso: "No such file" → 3 FAILED.

### Step 3 — Implementa `scripts/count_branch_operators.py`

```python
#!/usr/bin/env python3
"""count_branch_operators.py — conta ??/||/&&/?: in un file TS/JS (regex AST-lite).

Esclude righe di commento singola (//), import/export e blocchi /* */.
NON gestisce annidamenti profondi: accettabile per DAO/mapper (post-mortem R6).
Soglia branch_heavy: count > 20.

Usage: count_branch_operators.py <source_file>
Output JSON: {"file": path, "count": N, "by_operator": {...}, "branch_heavy": bool}
"""
import json
import re
import sys
from pathlib import Path

BRANCH_HEAVY_THRESHOLD = 20

# ternario: ? ... : (escludendo ?. optional chaining e ?? )
_RE = {
    "??": re.compile(r"\?\?"),
    "||": re.compile(r"\|\|"),
    "&&": re.compile(r"&&"),
    "?:": re.compile(r"(?<![?.])\?(?!\.)[^?]"),  # ? non seguito/preceduto da ? o .
}


def _strip_block_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def count_operators(text: str) -> dict:
    text = _strip_block_comments(text)
    by_op = {"??": 0, "||": 0, "&&": 0, "?:": 0}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("import ") or stripped.startswith("export "):
            continue
        # rimuovi commento inline
        code = line.split("//", 1)[0]
        by_op["??"] += len(_RE["??"].findall(code))
        # || conteggia escludendo le occorrenze dentro ?? già contate non serve: operatori distinti
        by_op["||"] += len(_RE["||"].findall(code))
        by_op["&&"] += len(_RE["&&"].findall(code))
        # ternario: conta i "?" che non sono ?? né ?. — approssimazione
        q = code.replace("??", "").replace("?.", "")
        by_op["?:"] += q.count("?")
    count = sum(by_op.values())
    return {"count": count, "by_operator": by_op,
            "branch_heavy": count > BRANCH_HEAVY_THRESHOLD}


def main() -> None:
    src = Path(sys.argv[1])
    text = src.read_text(encoding="utf-8", errors="ignore")
    result = count_operators(text)
    result["file"] = str(src)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_count_branch_operators.py -v`
Output atteso: `3 passed`.

### Step 5 — Commit
```
git add skills/code-coverage/scripts/count_branch_operators.py skills/code-coverage/scripts/tests/test_count_branch_operators.py
git commit -m "feat(code-coverage): add branch-operator counter (regex AST-lite, no ts-morph)"
```

## Criteri di accettazione
- [ ] Conta correttamente 1 per ciascun operatore nel sorgente di esempio (count=4).
- [ ] Esclude commenti `//`, `/* */` e righe `import`/`export`.
- [ ] `count > 20` → `branch_heavy=true`.
- [ ] Output JSON valido con `file`, `count`, `by_operator`, `branch_heavy`.
