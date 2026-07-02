# Task 06 — Wire del resolver PR base nei siti bash (no heredoc)

**Cluster:** B diff (REQ-DF-03)
**Dipendenze:** Task 04 (`lib/pr-base-resolver.sh` con `devforge_resolve_pr_base()`); Task 05 (`lib/diff-truncate.sh`) NON è richiesto per questo task — nessun sito qui tocca la size-guard.

## Goal

Sostituire l'hardcode `origin/main` nei 4 siti bash non-heredoc (`lib/diff-risk-classifier.sh:16`, `hooks/pr-blind-review-gate:115`, `hooks/pr-premortem-gate:113`, `hooks/pr-gate:59-61`) e invertire la precedenza in `lib/review_evidence/collector.py:379-382`, così che un branch derivato da un base non-`main` (es. `sviluppo`) venga classificato/diffato contro il proprio base reale invece che sempre contro `origin/main`.

## File coinvolti

- `lib/diff-risk-classifier.sh:16-20` (modifica)
- `hooks/pr-blind-review-gate:110-116` (modifica)
- `hooks/pr-premortem-gate:108-114` (modifica)
- `hooks/pr-gate:59-61` (modifica)
- `lib/review_evidence/collector.py:376-382` (modifica)
- `tests/hooks/pr-base-wiring.test.sh` (nuovo)
- `tests/test_review_evidence_collector_v2.py` (modifica — nuovo test `test_orchestrate_v2_baseline_uses_caller_base_not_origin_main`)

**NON toccare (release-scoped, legittimi):** `skills/siae-release-risk/*`, `lib/release_risk/genesis.py`, `lib/release_risk/regression_delta.py`, `lib/release_risk/cli.py:170,190`, `hooks/pr-release-gate:71-73`.

## Step TDD

### Step 1 — Test fallente (bash): branch da `sviluppo`, non da `main`

Crea `tests/hooks/pr-base-wiring.test.sh`:

```bash
#!/usr/bin/env bash
# pr-base-wiring.test.sh — regressione REQ-DF-03: i siti bash devono classificare/diffare
# contro il base REALE del branch (es. sviluppo), non contro origin/main hardcoded.
# Design: docs/plans/2026-07-01-devforge-siae-conventions-and-flow/design.md (REQ-DF-03 AC1/AC2/AC4)
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"

# $1 = nome repo temp (output). Crea main + sviluppo, branch work da sviluppo con
# un file .py committato SOLO su sviluppo (assente su main) — se il diff scope
# usasse ancora origin/main, lo status includerebbe anche quel file come "nuovo",
# ma il file che ci interessa e' quello aggiunto SOLO su work rispetto a sviluppo.
_mkrepo_sviluppo_base() {
    local td; td=$(mktemp -d)
    ( cd "$td" && git init -q && git config user.email t@t && git config user.name t \
      && echo base > base.py && git add -A && git commit -qm base && git branch -m main \
      && git checkout -qb sviluppo \
      && echo dev-only > dev-only.py && git add -A && git commit -qm sviluppo-work \
      && git remote add origin "$td-bare-placeholder" 2>/dev/null || true
      git update-ref refs/remotes/origin/main "$(git rev-parse main)"
      git update-ref refs/remotes/origin/sviluppo "$(git rev-parse sviluppo)"
      git checkout -qb work
      echo x > a.md && git add -A && git commit -qm doc-on-work ) >/dev/null 2>&1
    echo "$td"
}

echo "=== AC-1/AC-2: diff-risk-classifier con base=sviluppo (via resolver) → low (solo .md aggiunto su work) ==="
TD=$(_mkrepo_sviluppo_base)
RISK=$( cd "$TD" && source "${REPO_ROOT}/lib/pr-base-resolver.sh" && source "${REPO_ROOT}/lib/diff-risk-classifier.sh" \
        && RESOLVED=$(devforge_resolve_pr_base) && devforge_classify_diff_risk "$RESOLVED" )
if [ "$RISK" = "low" ]; then echo "  PASS"; PASS=$((PASS+1)); else echo "  FAIL: RISK=$RISK (atteso low)"; FAIL=$((FAIL+1)); fi
rm -rf "$TD"

echo "=== AC-1/AC-4: diff-risk-classifier con default origin/main (nessun base esplicito) → code (dev-only.py visto come nuovo rispetto a main) ==="
TD=$(_mkrepo_sviluppo_base)
RISK=$( cd "$TD" && source "${REPO_ROOT}/lib/diff-risk-classifier.sh" && devforge_classify_diff_risk )
if [ "$RISK" = "code" ]; then echo "  PASS (conferma bug pre-fix: default origin/main include dev-only.py)"; PASS=$((PASS+1)); else echo "  FAIL: RISK=$RISK (atteso code)"; FAIL=$((FAIL+1)); fi
rm -rf "$TD"

echo "=== AC-1/AC-2: pr-gate MERGE_BASE risolve sviluppo (non main) quando il branch parte da sviluppo ==="
TD=$(_mkrepo_sviluppo_base)
RESOLVED_MB=$( cd "$TD" && source "${REPO_ROOT}/lib/pr-base-resolver.sh" && RESOLVED=$(devforge_resolve_pr_base) && git merge-base HEAD "origin/${RESOLVED}" )
EXPECTED_MB=$( cd "$TD" && git rev-parse sviluppo )
if [ "$RESOLVED_MB" = "$EXPECTED_MB" ]; then echo "  PASS"; PASS=$((PASS+1)); else echo "  FAIL: got=$RESOLVED_MB expected=$EXPECTED_MB"; FAIL=$((FAIL+1)); fi
rm -rf "$TD"

echo "=== AC-1: pr-blind-review-gate/pr-premortem-gate usano il resolver, non literal origin/main ==="
for GATE in pr-blind-review-gate pr-premortem-gate; do
    if grep -qF 'devforge_classify_diff_risk "origin/main"' "${REPO_ROOT}/hooks/${GATE}"; then
        echo "  FAIL: ${GATE} ancora hardcoded a origin/main"; FAIL=$((FAIL+1))
    else
        echo "  PASS: ${GATE} non hardcoda origin/main"; PASS=$((PASS+1))
    fi
done

echo "=== AC-1: pr-gate non hardcoda piu' la catena origin/sviluppo||origin/main letterale senza resolver ==="
if grep -qF 'git merge-base HEAD origin/sviluppo 2>/dev/null' "${REPO_ROOT}/hooks/pr-gate" \
   && ! grep -q 'devforge_resolve_pr_base' "${REPO_ROOT}/hooks/pr-gate"; then
    echo "  FAIL: pr-gate non chiama devforge_resolve_pr_base"; FAIL=$((FAIL+1))
else
    echo "  PASS: pr-gate wired al resolver"; PASS=$((PASS+1))
fi

echo ""; echo "RESULT: PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
```

Rendi eseguibile:

```bash
chmod +x "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/tests/hooks/pr-base-wiring.test.sh"
```

Aggiungi in `tests/test_review_evidence_collector_v2.py` (dopo `test_orchestrate_v2_calls_baseline_cache`, prima di `test_orchestrate_v2_calls_compute_regression_verdict`):

```python
def test_orchestrate_v2_baseline_uses_caller_base_not_origin_main(
    tmp_path: Path, monkeypatch
) -> None:
    """REQ-DF-03: se esiste un ref origin/main DIVERSO dal base del branch
    (es. base=sviluppo), il main_sha usato per la baseline cache deve
    risolvere al base fornito dal chiamante, non a origin/main hardcoded.

    Prima del fix, `main_sha` tentava sempre `rev-parse origin/main` per
    primo: su un branch aperto verso `sviluppo` la baseline veniva letta
    dalla SHA sbagliata (drift silenzioso della cache).
    """
    _init_git(tmp_path)
    sp = subprocess.run
    # main avanza con un secondo commit SOLO su main (diverso da sviluppo).
    (tmp_path / "main-only.py").write_text("# main only\n")
    sp(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    sp(
        ["git", "commit", "-m", "main-only"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    main_sha = _head_sha(tmp_path)
    # origin/main ref punta alla SHA di main (diversa dal base "sviluppo").
    sp(
        ["git", "update-ref", "refs/remotes/origin/main", main_sha],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    # sviluppo diverge da main con un commit indipendente.
    sp(["git", "checkout", "-b", "sviluppo"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "sviluppo-only.py").write_text("# sviluppo only\n")
    sp(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    sp(
        ["git", "commit", "-m", "sviluppo-only"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    sviluppo_sha = _head_sha(tmp_path)
    assert sviluppo_sha != main_sha

    monkeypatch.setenv("DEVFORGE_BASELINE_LOCAL_DIR", str(tmp_path / "fallback"))
    calls: list[tuple[str, str]] = []

    def _spy(repo_full_name: str, main_sha_arg: str):
        calls.append((repo_full_name, main_sha_arg))
        return None

    out = tmp_path / "ev.json"
    with patch(
        "lib.review_evidence.baseline_cache.fetch_baseline", side_effect=_spy
    ):
        code = orchestrate_v2(
            sha=sviluppo_sha,
            base="sviluppo",
            dirty=False,
            out_path=out,
            repo_root=tmp_path,
        )
    assert code == 0
    assert calls, "orchestrate_v2 deve chiamare fetch_baseline almeno una volta"
    resolved_sha = calls[0][1]
    assert resolved_sha == sviluppo_sha, (
        f"main_sha deve risolvere al base fornito (sviluppo={sviluppo_sha}), "
        f"non a origin/main hardcoded (main={main_sha}); got {resolved_sha}"
    )
```

### Step 2 — Esegui e verifica FAIL

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/hooks/pr-base-wiring.test.sh
```

Output atteso (FAIL — `lib/pr-base-resolver.sh` non esiste ancora nel path atteso da questo task in isolamento, oppure `devforge_resolve_pr_base` non è wired):

```
=== AC-1/AC-2: diff-risk-classifier con base=sviluppo (via resolver) → low (solo .md aggiunto su work) ===
  FAIL: RISK=code (atteso low)
=== AC-1/AC-4: diff-risk-classifier con default origin/main (nessun base esplicito) → code (dev-only.py visto come nuovo rispetto a main) ===
  PASS (conferma bug pre-fix: default origin/main include dev-only.py)
=== AC-1/AC-2: pr-gate MERGE_BASE risolve sviluppo (non main) quando il branch parte da sviluppo ===
  FAIL: got= expected=<sha-sviluppo>
=== AC-1: pr-blind-review-gate/pr-premortem-gate usano il resolver, non literal origin/main ===
  FAIL: pr-blind-review-gate ancora hardcoded a origin/main
  FAIL: pr-premortem-gate ancora hardcoded a origin/main
=== AC-1: pr-gate non hardcoda piu' la catena origin/sviluppo||origin/main letterale senza resolver ===
  FAIL: pr-gate non chiama devforge_resolve_pr_base

RESULT: PASS=2 FAIL=4
```

(Nota: la prima riga fallisce con `RISK=code` non per assenza del file lib — se Task 04 è già mergiato nel branch, il fallimento è invece "source: no such file" per `lib/pr-base-resolver.sh` finché questo task non lo integra nella catena; in entrambi i casi il risultato è FAIL con `RESULT: ... FAIL>0`.)

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && python3 -m pytest tests/test_review_evidence_collector_v2.py::test_orchestrate_v2_baseline_uses_caller_base_not_origin_main -q
```

Output atteso (FAIL):

```
FAILED tests/test_review_evidence_collector_v2.py::test_orchestrate_v2_baseline_uses_caller_base_not_origin_main - AssertionError: main_sha deve risolvere al base fornito (sviluppo=...), non a origin/main hardcoded (main=...); got ...
1 failed in 0.XXs
```

### Step 3 — Implementazione minima

**`lib/diff-risk-classifier.sh:16-20`** — rendi la base esplicita (nessun default silenzioso a `origin/main`; il chiamante deve passare l'output del resolver):

```bash
# Stampa 'low' | 'code'. $1 = base branch (nessun default: il chiamante DEVE
# risolvere il base reale via lib/pr-base-resolver.sh — REQ-DF-03).
devforge_classify_diff_risk() {
    local base="${1:?devforge_classify_diff_risk richiede un base esplicito (usa devforge_resolve_pr_base)}"
    local status
    status=$(git diff --name-status "${base}...HEAD" 2>/dev/null) || { printf 'code'; return 0; }
    [ -z "$status" ] && { printf 'code'; return 0; }
```

(le righe successive restano invariate).

**`hooks/pr-blind-review-gate:110-116`** — sostituisci il blocco:

```bash
# Proportional scaling: su diff risk=low (doc/manifest) il gate è advisory, non block.
# Floor security/secret invariato (pre-commit non toccato). Design ADR-3.
RISK=code
PR_BASE=""
if source "${PLUGIN_ROOT}/lib/pr-base-resolver.sh" 2>/dev/null \
   && command -v devforge_resolve_pr_base >/dev/null 2>&1; then
    PR_BASE=$(devforge_resolve_pr_base 2>/dev/null || echo main)
fi
if source "${PLUGIN_ROOT}/lib/diff-risk-classifier.sh" 2>/dev/null \
   && command -v devforge_classify_diff_risk >/dev/null 2>&1; then
    RISK=$(devforge_classify_diff_risk "origin/${PR_BASE:-main}" 2>/dev/null || echo code)
fi
```

**`hooks/pr-premortem-gate:108-114`** — stesso identico blocco (sostituisce le righe 108-114 attuali):

```bash
# Proportional scaling: su diff risk=low (doc/manifest) il gate è advisory, non block.
# Floor security/secret invariato (pre-commit non toccato). Design ADR-3.
RISK=code
PR_BASE=""
if source "${PLUGIN_ROOT}/lib/pr-base-resolver.sh" 2>/dev/null \
   && command -v devforge_resolve_pr_base >/dev/null 2>&1; then
    PR_BASE=$(devforge_resolve_pr_base 2>/dev/null || echo main)
fi
if source "${PLUGIN_ROOT}/lib/diff-risk-classifier.sh" 2>/dev/null \
   && command -v devforge_classify_diff_risk >/dev/null 2>&1; then
    RISK=$(devforge_classify_diff_risk "origin/${PR_BASE:-main}" 2>/dev/null || echo code)
fi
```

**`hooks/pr-gate:59-61`** — sostituisci la catena hardcoded con il resolver (aggiungi anche il source, dato che `pr-gate` non carica ancora `diff-risk-classifier.sh` né `pr-base-resolver.sh`):

```bash
source "${PLUGIN_ROOT}/lib/pr-base-resolver.sh" 2>/dev/null || true
PR_BASE="main"
if command -v devforge_resolve_pr_base >/dev/null 2>&1; then
    PR_BASE=$(devforge_resolve_pr_base 2>/dev/null || echo main)
fi
MERGE_BASE=$(git merge-base HEAD "origin/${PR_BASE}" 2>/dev/null \
          || git merge-base HEAD origin/main 2>/dev/null \
          || echo "HEAD~1")
```

**`lib/review_evidence/collector.py:376-382`** — inverti la precedenza (base fornito dal chiamante prima del fallback a `origin/main`):

```python
    # ---- Baseline cache lookup (PR-B Task 09 wired) ----
    # REQ-DF-03: il base fornito dal chiamante ha PRECEDENZA su origin/main.
    # `origin/main` resta solo come ultimo fallback quando `base` non risolve
    # (es. repo locale senza quel ref) — evita drift di cache su branch aperti
    # verso un target diverso da main (es. sviluppo, release/*).
    main_sha = (
        _git(["rev-parse", base], repo_root)
        or _git(["rev-parse", "origin/main"], repo_root)
    )
```

### Step 4 — Esegui e verifica PASS

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/hooks/pr-base-wiring.test.sh
```

Output atteso:

```
=== AC-1/AC-2: diff-risk-classifier con base=sviluppo (via resolver) → low (solo .md aggiunto su work) ===
  PASS
=== AC-1/AC-4: diff-risk-classifier con default origin/main (nessun base esplicito) → code (dev-only.py visto come nuovo rispetto a main) ===
  PASS (conferma bug pre-fix: default origin/main include dev-only.py)
=== AC-1/AC-2: pr-gate MERGE_BASE risolve sviluppo (non main) quando il branch parte da sviluppo ===
  PASS
=== AC-1: pr-blind-review-gate/pr-premortem-gate usano il resolver, non literal origin/main ===
  PASS: pr-blind-review-gate non hardcoda origin/main
  PASS: pr-premortem-gate non hardcoda origin/main
=== AC-1: pr-gate non hardcoda piu' la catena origin/sviluppo||origin/main letterale senza resolver ===
  PASS: pr-gate wired al resolver

RESULT: PASS=6 FAIL=0
```

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && python3 -m pytest tests/test_review_evidence_collector_v2.py -q
```

Output atteso:

```
........                                                                [100%]
8 passed in 0.XXs
```

(8 = 7 test preesistenti + 1 nuovo; il numero esatto preesistente va confermato dal run, ma tutti devono risultare `passed`, zero `failed`.)

Esegui anche la suite classificatore esistente per confermare zero regressioni sul caso `origin/main` esplicito (AC-13 passa ancora `main`/`alt` espliciti, non il default):

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/hooks/test_diff_risk_classifier.sh
```

Output atteso:

```
RESULT: PASS=11 FAIL=0
```

### Step 5 — Commit

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && git add lib/diff-risk-classifier.sh hooks/pr-blind-review-gate hooks/pr-premortem-gate hooks/pr-gate lib/review_evidence/collector.py tests/hooks/pr-base-wiring.test.sh tests/test_review_evidence_collector_v2.py && git commit -m "fix(gates): risolvi il base PR reale nei siti bash invece di origin/main hardcoded

lib/diff-risk-classifier.sh, pr-blind-review-gate, pr-premortem-gate e
pr-gate classificavano/diffavano sempre contro origin/main, anche per
branch aperti verso sviluppo o release/*. Wired al resolver condiviso
(devforge_resolve_pr_base) + invertita la precedenza in
review_evidence/collector.py (base chiamante prima del rev-parse
origin/main hardcoded). REQ-DF-03 AC1/AC2/AC4."
```

## Criteri di accettazione

- [ ] AC1 (base = merge-base del target reale, non sempre `main`): `pr-gate` MERGE_BASE risolve `sviluppo` quando il branch è aperto da `sviluppo` — verificato da `tests/hooks/pr-base-wiring.test.sh` scenario 3.
- [ ] AC1: `hooks/pr-blind-review-gate` e `hooks/pr-premortem-gate` non contengono più la stringa letterale `devforge_classify_diff_risk "origin/main"` — verificato da `tests/hooks/pr-base-wiring.test.sh` scenario 4.
- [ ] AC2 (diff = solo modifiche del branch, non "tutto ciò che manca su main"): `devforge_classify_diff_risk` con base risolto a `sviluppo` classifica `low` un diff solo-`.md` — verificato da scenario 1; lo stesso repo con default `origin/main` implicito classifica `code` (dimostra il bug pre-fix) — verificato da scenario 2.
- [ ] AC4 (regressione branch non-main): tutti gli scenari di `pr-base-wiring.test.sh` usano un branch `work` derivato da `sviluppo` (non da `main`), non solo main→main.
- [ ] `lib/review_evidence/collector.py`: `main_sha` risolve al `base` fornito dal chiamante prima di tentare `origin/main` — verificato da `test_orchestrate_v2_baseline_uses_caller_base_not_origin_main`.
- [ ] Zero regressioni: `tests/hooks/test_diff_risk_classifier.sh` (11/11 PASS, base esplicito invariato) e `tests/test_review_evidence_collector_v2.py` (tutti i test preesistenti ancora PASS) restano verdi.
- [ ] Siti release-scoped (`skills/siae-release-risk/*`, `lib/release_risk/*`, `hooks/pr-release-gate:71-73`) NON modificati — `git diff --name-only` non li include.
- [ ] `lib/diff-risk-classifier.sh` non ha più un default silenzioso `${1:-origin/main}`: chiamata senza argomento fallisce esplicitamente (evita drift futuro da nuovi call-site non wired al resolver).
