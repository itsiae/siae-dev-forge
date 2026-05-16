# Task 01 — Test red: Criterion 6 tag pattern + status propagation

**Goal:** Aggiungere 4 test fallenti che asseriscono il nuovo comportamento di `criterion_6_first_release` (parametro `tag_lookup_status`) e di `_count_release_tags` (signature `tuple[int, str]`).

## File coinvolti

- Modifica: `tests/test_release_risk_detector_6_10.py` (aggiungi 2 test)
- Modifica: `tests/test_release_risk_cli.py` (aggiungi 2 test, fixture repo)

## Step TDD

### Step 1 — Aggiungi test in `tests/test_release_risk_detector_6_10.py`

Append a fondo file:

```python
def test_c6_tool_unavailable_on_subprocess_fail():
    """Quando _count_release_tags fallisce, criterion 6 propaga TOOL_UNAVAILABLE invece di YES."""
    r = criterion_6_first_release(0, tag_lookup_status="UNAVAILABLE")
    assert r.status == "TOOL_UNAVAILABLE"
    assert r.weight == 2
    assert "git_tag_lookup_failed" in r.evidence


def test_c6_no_with_explicit_ok_status():
    """Tag count positivo + status OK → NO esplicito."""
    r = criterion_6_first_release(5, tag_lookup_status="OK")
    assert r.status == "NO"
    assert "git_tag_count=5" in r.evidence
```

### Step 2 — Aggiungi test in `tests/test_release_risk_cli.py`

Append a fondo file (importa `_count_release_tags` da `lib.release_risk.cli`):

```python
def test_count_release_tags_returns_tuple_with_status_ok(tmp_path, monkeypatch):
    """_count_release_tags ritorna (count, status='OK') in repo valido con tag."""
    import subprocess
    subprocess.check_call(["git", "init", "-q"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.email", "t@t"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=tmp_path)
    (tmp_path / "f").write_text("x")
    subprocess.check_call(["git", "add", "."], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-q", "-m", "init"], cwd=tmp_path)
    subprocess.check_call(["git", "tag", "2.3.5-RELEASE"], cwd=tmp_path)
    from lib.release_risk.cli import _count_release_tags
    count, status = _count_release_tags(tmp_path)
    assert status == "OK"
    assert count >= 1, f"Expected tag '2.3.5-RELEASE' matched by *-RELEASE glob, got count={count}"


def test_count_release_tags_returns_unavailable_on_subprocess_fail(tmp_path):
    """_count_release_tags ritorna (0, 'UNAVAILABLE') in directory non-git."""
    from lib.release_risk.cli import _count_release_tags
    count, status = _count_release_tags(tmp_path)
    assert status == "UNAVAILABLE"
    assert count == 0
```

### Step 3 — Verifica che i 4 test FALLISCANO

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
source .venv-analytics/bin/activate && \
pytest tests/test_release_risk_detector_6_10.py::test_c6_tool_unavailable_on_subprocess_fail \
       tests/test_release_risk_detector_6_10.py::test_c6_no_with_explicit_ok_status \
       tests/test_release_risk_cli.py::test_count_release_tags_returns_tuple_with_status_ok \
       tests/test_release_risk_cli.py::test_count_release_tags_returns_unavailable_on_subprocess_fail \
       -v
```

Output atteso (RED):
```
FAILED ... test_c6_tool_unavailable_on_subprocess_fail - TypeError: criterion_6_first_release() got an unexpected keyword argument 'tag_lookup_status'
FAILED ... test_count_release_tags_returns_tuple_with_status_ok - ValueError: too many values to unpack (expected 2) — current returns int
```

### Step 4 — Commit (NO implementazione ancora)

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
git add tests/test_release_risk_detector_6_10.py tests/test_release_risk_cli.py && \
git commit -m "test(release-risk): red tests for c6 tag-pattern status propagation

- c6 must accept tag_lookup_status param → TOOL_UNAVAILABLE
- _count_release_tags must return (count, status) tuple
- Asserts 2.3.5-RELEASE tag pattern recognized

Refs: docs/plans/2026-05-16-release-risk-silent-no-fix-design.md"
```

## Criteri di accettazione

- [ ] 4 nuovi test definiti
- [ ] Comando pytest mostra 4 FAILED (red)
- [ ] Commit creato con messaggio convenzionale `test(release-risk):`
- [ ] Nessun fix applicato a `detector.py` o `cli.py`
