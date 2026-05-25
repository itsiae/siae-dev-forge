"""Test Task 08 — setter-logic-prescan.

Classifica setter Java come trivial/non_trivial. Phase 5 usa il risultato per
generare assertion ADAPTED (es. lowercase) invece di round-trip naive che
fallirebbe su entity SIAE legacy con normalizer.

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


def _entity_with_setters(setters: list) -> str:
    body = "\n\n    ".join(setters)
    return f"""package it.siae.test;

import org.apache.commons.text.StringEscapeUtils;

public class TestEntity {{
    private String titolo;
    private String classeStampa;
    private String id;

    {body}
}}
"""


def test_trivial_setter_classified(tmp_path):
    """`this.x = x;` body → trivial."""
    from setter_scanner import scan_setters
    java = tmp_path / "TestEntity.java"
    java.write_text(_entity_with_setters([
        "public void setId(String id) { this.id = id; }",
    ]))
    result = scan_setters(java)
    assert "setId" in result
    assert result["setId"]["kind"] == "trivial"
    assert result["setId"]["transforms"] == []


def test_lowercase_setter_classified_nontrivial(tmp_path):
    """`this.x = x.toLowerCase();` → non_trivial + transforms=[lowercase]."""
    from setter_scanner import scan_setters
    java = tmp_path / "TestEntity.java"
    java.write_text(_entity_with_setters([
        "public void setClasseStampa(String classeStampa) { this.classeStampa = classeStampa.toLowerCase(); }",
    ]))
    result = scan_setters(java)
    assert result["setClasseStampa"]["kind"] == "non_trivial"
    assert "lowercase" in result["setClasseStampa"]["transforms"]


def test_unescape_html_classified_nontrivial(tmp_path):
    """`this.x = StringEscapeUtils.unescapeHtml(x.toLowerCase())` → non_trivial."""
    from setter_scanner import scan_setters
    java = tmp_path / "TestEntity.java"
    java.write_text(_entity_with_setters([
        "public void setTitolo(String titolo) { this.titolo = StringEscapeUtils.unescapeHtml(titolo.toLowerCase()); }",
    ]))
    result = scan_setters(java)
    assert result["setTitolo"]["kind"] == "non_trivial"
    assert "lowercase" in result["setTitolo"]["transforms"]
    assert "unescape_html" in result["setTitolo"]["transforms"]


def test_conditional_setter_classified(tmp_path):
    """Setter con `if` → non_trivial + has_conditional=True."""
    from setter_scanner import scan_setters
    java = tmp_path / "TestEntity.java"
    java.write_text(_entity_with_setters([
        "public void setTitolo(String titolo) { if (titolo != null) { this.titolo = titolo.trim(); } }",
    ]))
    result = scan_setters(java)
    assert result["setTitolo"]["kind"] == "non_trivial"
    assert result["setTitolo"]["has_conditional"] is True


def test_apply_transforms_lowercase_trim():
    """apply_transforms('  ABC  ', [trim, lowercase]) → 'abc'."""
    from setter_scanner import apply_transforms
    assert apply_transforms("  ABC  ", ["trim", "lowercase"]) == "abc"


def test_apply_transforms_uppercase():
    from setter_scanner import apply_transforms
    assert apply_transforms("abc", ["uppercase"]) == "ABC"


def test_apply_transforms_unknown_passthrough():
    """Transform sconosciuta è pass-through (no crash)."""
    from setter_scanner import apply_transforms
    assert apply_transforms("hello", ["unescape_html", "lowercase"]) == "hello"


def test_multi_setter_in_one_class(tmp_path):
    """Classe con 3 setter mix trivial + non_trivial → tutti rilevati."""
    from setter_scanner import scan_setters
    java = tmp_path / "TestEntity.java"
    java.write_text(_entity_with_setters([
        "public void setId(String id) { this.id = id; }",
        "public void setClasseStampa(String cs) { this.classeStampa = cs.toLowerCase(); }",
        "public void setTitolo(String t) { this.titolo = t.trim(); }",
    ]))
    result = scan_setters(java)
    assert result["setId"]["kind"] == "trivial"
    assert result["setClasseStampa"]["kind"] == "non_trivial"
    assert result["setTitolo"]["kind"] == "non_trivial"


def test_cli_emits_setter_scan_json(tmp_path):
    """CLI: python3 setter_scanner.py <repo> → setter-scan.json."""
    repo = tmp_path / "repo"
    src = repo / "src" / "main" / "java" / "it" / "siae" / "test"
    src.mkdir(parents=True)
    (src / "TestEntity.java").write_text(_entity_with_setters([
        "public void setId(String id) { this.id = id; }",
        "public void setClasseStampa(String cs) { this.classeStampa = cs.toLowerCase(); }",
    ]))
    (repo / ".code-coverage").mkdir()
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "setter_scanner.py"), str(repo)],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert "TestEntity" in out
    assert out["TestEntity"]["setId"]["kind"] == "trivial"
    assert out["TestEntity"]["setClasseStampa"]["kind"] == "non_trivial"
