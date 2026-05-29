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
