"""Verifica presenza moduli v2 + import senza errori."""
import importlib

V2_MODULES = [
    "collect_anthropic_api",
    "compute_ai_impact",
    "compute_branches",
    "compute_reviews",
    "seasonality",
    "export_charts",
    "export_glossary",
    "validators",
]


def test_all_v2_modules_importable():
    """Ogni modulo v2 si importa senza errori."""
    for mod_name in V2_MODULES:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"Import fallito per {mod_name}"


def test_requirements_includes_v2_deps():
    """requirements.txt contiene le 5 dipendenze v2."""
    from pathlib import Path
    req_path = Path(__file__).parent.parent / "scripts" / "requirements.txt"
    content = req_path.read_text()
    for dep in ["hypothesis", "mutmut", "typeguard", "anthropic", "pytz"]:
        assert dep in content, f"Missing dep: {dep}"
