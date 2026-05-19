# Task 02 — Fix green: Criterion 6 + `_count_release_tags`

**Goal:** Implementare il fix che porta a verde i 4 test del task 01 senza rompere i 134 test esistenti.

## File coinvolti

- Modifica: `lib/release_risk/detector.py` (funzione `criterion_6_first_release`)
- Modifica: `lib/release_risk/cli.py` (funzione `_count_release_tags` + costante `RELEASE_TAG_GLOBS_DEFAULT` + chiamata in `assess`)

## Step TDD

### Step 1 — Modifica `lib/release_risk/detector.py` righe 77-84

Sostituisci la funzione `criterion_6_first_release` con:

```python
def criterion_6_first_release(git_tag_count: int, tag_lookup_status: str = "OK") -> CriterionResult:
    """+2 se prima release del servizio (nessun tag release precedente).

    tag_lookup_status="UNAVAILABLE" se subprocess git ha fallito → TOOL_UNAVAILABLE
    (no silent fallback a YES da count=0 indistinguibile).
    """
    if tag_lookup_status == "UNAVAILABLE":
        return CriterionResult(id=6, name="First release", status="TOOL_UNAVAILABLE",
                               weight=2, evidence=["git_tag_lookup_failed"],
                               source="git:tag")
    if git_tag_count == 0:
        return CriterionResult(id=6, name="First release", status="YES", weight=2,
                               evidence=[f"git_tag_count={git_tag_count}"],
                               source="git:tag")
    return CriterionResult(id=6, name="First release", status="NO", weight=2,
                           evidence=[f"git_tag_count={git_tag_count}"], source="git:tag")
```

### Step 2 — Modifica `lib/release_risk/cli.py` righe 171-178

Sostituisci la funzione `_count_release_tags` con:

```python
RELEASE_TAG_GLOBS_DEFAULT = ("release*", "v*", "*RELEASE*", "*-RELEASE", "RELEASE-*")


def _count_release_tags(repo_root: Path) -> tuple[int, str]:
    """Returns (count, status) where status in {"OK", "UNAVAILABLE"}.

    Env override: DEVFORGE_RELEASE_RISK_TAG_GLOBS (csv).
    """
    env_globs = os.environ.get("DEVFORGE_RELEASE_RISK_TAG_GLOBS", "")
    globs = [g.strip() for g in env_globs.split(",") if g.strip()] or list(RELEASE_TAG_GLOBS_DEFAULT)
    try:
        out = subprocess.check_output(
            ["git", "tag", "--list", *globs], cwd=repo_root, text=True, timeout=5
        )
        return (len([l for l in out.splitlines() if l.strip()]), "OK")
    except Exception:
        return (0, "UNAVAILABLE")
```

Posiziona `RELEASE_TAG_GLOBS_DEFAULT` come module-level constant dopo gli import (righe 11-12).

### Step 3 — Aggiorna chiamata `_count_release_tags` in `assess()` riga 72

Sostituisci:
```python
git_tag_count = _count_release_tags(repo_root)
```
con:
```python
git_tag_count, tag_lookup_status = _count_release_tags(repo_root)
```

E sostituisci la chiamata `criterion_6_first_release(git_tag_count)` in `assess()` con:
```python
criterion_6_first_release(git_tag_count, tag_lookup_status),
```

### Step 4 — Verifica RED → GREEN

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
source .venv-analytics/bin/activate && \
pytest tests/test_release_risk_detector_6_10.py tests/test_release_risk_cli.py -v 2>&1 | tail -20
```

Output atteso:
```
test_c6_first_release_yes PASSED
test_c6_first_release_no PASSED
test_c6_tool_unavailable_on_subprocess_fail PASSED
test_c6_no_with_explicit_ok_status PASSED
test_count_release_tags_returns_tuple_with_status_ok PASSED
test_count_release_tags_returns_unavailable_on_subprocess_fail PASSED
====== N passed in X.YZs ======
```

### Step 5 — Full regression `pytest tests/test_release_risk_*`

```bash
pytest tests/test_release_risk_ -v 2>&1 | tail -10
```

Output atteso: tutti i 134+4 = 138 test PASS.

### Step 6 — Commit

```bash
git add lib/release_risk/detector.py lib/release_risk/cli.py && \
git commit -m "fix(release-risk): c6 propagates TOOL_UNAVAILABLE + extended tag globs

- criterion_6_first_release accepts tag_lookup_status param
- _count_release_tags returns (count, status) tuple
- Default globs include *RELEASE*, *-RELEASE, RELEASE-* (SIAE pattern)
- Env override DEVFORGE_RELEASE_RISK_TAG_GLOBS

Closes silent-YES on subprocess fail + false-positive on SIAE tag pattern.
Refs: docs/plans/2026-05-16-release-risk-silent-no-fix-design.md"
```

## Criteri di accettazione

- [ ] I 4 test del task 01 passano (GREEN)
- [ ] Tutti i test pre-esistenti continuano a passare (no regression)
- [ ] `RELEASE_TAG_GLOBS_DEFAULT` esposta come module constant
- [ ] Env `DEVFORGE_RELEASE_RISK_TAG_GLOBS="custom*,prod-*"` override funzionante (verificato in test esistenti via monkeypatch oppure manual check)
- [ ] Commit con messaggio `fix(release-risk):`
