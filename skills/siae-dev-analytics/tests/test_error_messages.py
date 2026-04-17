"""AST audit: RuntimeError messages actionable (NF4-NF5)."""
from __future__ import annotations

import ast
from pathlib import Path


VERBS = {"run", "verifica", "configura", "controllare", "install", "esegui", "rimuovi", "usa", "apri",
         "failed", "inaccessible", "invalid", "expected", "must", "resolved"}
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


def _extract_raise_msg(node: ast.Raise) -> str | None:
    if not node.exc or not isinstance(node.exc, ast.Call):
        return None
    if not node.exc.args:
        return None
    arg = node.exc.args[0]
    if isinstance(arg, ast.Constant):
        return arg.value if isinstance(arg.value, str) else None
    if isinstance(arg, ast.JoinedStr):
        parts = [v.value for v in arg.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        return " ".join(parts)
    return None


def test_runtime_errors_actionable():
    """Ogni RuntimeError raise ha messaggio >= 20 char + verbo azione."""
    issues = []
    for py in SCRIPTS_DIR.glob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and node.exc and isinstance(node.exc, ast.Call):
                func = node.exc.func
                if isinstance(func, ast.Name) and func.id == "RuntimeError":
                    msg = _extract_raise_msg(node) or ""
                    if len(msg) < 20:
                        issues.append(f"{py.name}:{node.lineno} msg too short: {msg[:30]!r}")
                    if not any(v in msg.lower() for v in VERBS):
                        issues.append(f"{py.name}:{node.lineno} no verb: {msg[:50]!r}")
    assert not issues, f"Non-actionable errors: {issues}"
