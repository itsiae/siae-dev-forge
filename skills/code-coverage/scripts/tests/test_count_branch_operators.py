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


# ---------------------------------------------------------------------------
# MAJOR fix: export const/function/class con operatori inline NON devono
# essere escluse come se fossero re-export puri o import.
# ---------------------------------------------------------------------------

def test_export_const_with_operator_is_counted(tmp_path):
    """'export const x = a ?? b' deve contribuire al count (era 0 per bug)."""
    f = tmp_path / "dao.ts"
    f.write_text("export const x = a ?? b;\n", encoding="utf-8")
    out = _run(f)
    assert out["count"] >= 1, (
        f"export const con ?? deve dare count>=1, got {out['count']}"
    )


def test_pure_reexport_gives_zero(tmp_path):
    """'export { A, B }' è un re-export puro: count deve essere 0."""
    f = tmp_path / "reexport.ts"
    f.write_text("export { A, B };\n", encoding="utf-8")
    out = _run(f)
    assert out["count"] == 0, (
        f"re-export puro deve dare 0, got {out['count']}"
    )


def test_import_statement_gives_zero(tmp_path):
    """'import {X} from 'y'' non deve contribuire al count."""
    f = tmp_path / "imports.ts"
    f.write_text("import { X } from 'y';\n", encoding="utf-8")
    out = _run(f)
    assert out["count"] == 0, (
        f"import statement deve dare 0, got {out['count']}"
    )
