from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_notice_attributes_headroom_apache2():
    notice = (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "headroom" in notice.lower()
    assert "Apache" in notice and "2.0" in notice
    assert "chopratejas/headroom" in notice


def test_retro_is_python_package():
    assert (REPO_ROOT / "lib" / "retro" / "__init__.py").exists()
