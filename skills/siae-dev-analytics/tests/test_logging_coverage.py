"""AST audit: ogni except handler ha log.* call (NF21-NF23)."""
import ast
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
MODULES_TO_AUDIT = [
    "autodetect_sources", "collect_github", "collect_s3_telemetry",
    "collect_anthropic_api", "compute_kpis", "compute_ai_impact",
    "compute_branches", "compute_reviews", "export_glossary", "run_analytics",
]


def _has_log_call(node: ast.AST) -> bool:
    """Check if subtree contains a log.* call."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if isinstance(n.func.value, ast.Name) and n.func.value.id in ("log", "logger", "logging"):
                return True
    return False


def test_exception_handlers_have_logging():
    """Ogni except body contiene almeno 1 log.* call (eccetto bare raise)."""
    issues = []
    for mod_name in MODULES_TO_AUDIT:
        path = SCRIPTS_DIR / f"{mod_name}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if not _has_log_call(node):
                    is_bare_raise = any(isinstance(s, ast.Raise) for s in node.body)
                    is_return = any(isinstance(s, ast.Return) for s in node.body)
                    if not is_bare_raise and not is_return:
                        issues.append(f"{mod_name}:{node.lineno} except senza log")
    assert not issues, f"Logging gaps: {issues}"
