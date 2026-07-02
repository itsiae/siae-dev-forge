from lib.retro.writer import Lesson, merge_into_text, write_lessons


def L(section, content):
    return Lesson(section=section, content=content)


def test_append_block_when_absent():
    out = merge_into_text("# Mio CLAUDE\n\nregola umana.\n", [L("Bash", "- usa path assoluti")])
    assert "regola umana." in out                      # sezione umana intatta
    assert "<!-- devforge:retro:start -->" in out
    assert "### Bash" in out and "path assoluti" in out


def test_replace_by_heading_idempotent():
    base = merge_into_text("base\n", [L("Bash", "- v1")])
    once = merge_into_text(base, [L("Bash", "- v2")])
    twice = merge_into_text(once, [L("Bash", "- v2")])
    assert once.count("### Bash") == 1                 # replace, non duplica
    assert "- v2" in once and "- v1" not in once
    assert once == twice                                # idempotente


def test_carry_forward_untouched_section():
    base = merge_into_text("base\n", [L("Bash", "- b"), L("Read", "- r")])
    upd = merge_into_text(base, [L("Bash", "- b2")])   # solo Bash ri-emesso
    assert "### Read" in upd and "- r" in upd           # Read portato avanti
    assert "- b2" in upd


def test_dry_run_no_write(tmp_path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("orig\n", encoding="utf-8")
    res = write_lessons(f, [L("Bash", "- x")], apply=False)
    assert f.read_text(encoding="utf-8") == "orig\n"    # NON scritto
    assert "### Bash" in res                             # ma ritorna il preview


def test_apply_writes(tmp_path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("orig\n", encoding="utf-8")
    write_lessons(f, [L("Bash", "- x")], apply=True)
    assert "### Bash" in f.read_text(encoding="utf-8")   # scritto
