# Task 03 — effective_target nel sentinel handshake

**Goal:** `sentinel-handshake.sh` calcola `effective_target = max(user_target, ci_threshold)` leggendo `ci-thresholds.json`, scrive i nuovi campi in `user-choice.json` (`user_requested_line/branch`, `ci_threshold_override`, `ci_thresholds_source`, `high_branch_gap`) e logga WARN in `decisions.log`. Risolve gap 6.5 (PASS Phase 6 ma CI rosso) e surfaccia upfront il branch gap (gap 6.6).

**WS:** WS-1 · **Dipendenze:** Task 02 (ci-thresholds.json), Task 01 (line_branch_delta).

## File coinvolti
- Modifica: `skills/code-coverage/lib/sentinel-handshake.sh` (cmd_write: derivazione target; cmd_read: emissione campi)
- Modifica: `skills/code-coverage/scripts/tests/test_sentinel_handshake.sh` (nuovo caso)

## Prerequisito di lettura
Leggi `skills/code-coverage/lib/sentinel-handshake.sh` per identificare la funzione `cmd_write` (dove deriva `target_branch` dal preset) e `cmd_read` (dove emette key=value). Le modifiche vanno innestate nei blocchi Python heredoc esistenti.

> **ATTENZIONE (anti falso-positivo):** la firma reale di `cmd_write` è `write <repo> <target_line>` (NON accetta un terzo argomento branch — viene derivato internamente). Il file `test_sentinel_handshake.sh` usa gli helper `assert_exit` e `assert_json` (NON `assert_equals`/`fail`). Il test deve quindi: (1) invocare `write` con la firma reale; (2) verificare l'override con `assert_json` sul campo robusto `ci_threshold_override == true` E su `target_branch == 70`, non solo sul numero (che potrebbe coincidere col preset per caso). Leggi gli helper esistenti prima di scrivere il caso.

## Step TDD

### Step 1 — Test fallente
In `skills/code-coverage/scripts/tests/test_sentinel_handshake.sh`, aggiungi un caso di test (segui lo stile dei test esistenti nel file — funzioni che invocano lo script e asseriscono su output/file). Caso:

```bash
test_effective_target_overrides_preset() {
  local tmp; tmp=$(mktemp -d)
  mkdir -p "$tmp/.code-coverage"
  # CI impone branch 70, preset utente 60
  echo '{"COVERAGE_BRANCHES": 70, "source": "CI.yaml", "working_directory_issues": []}' \
    > "$tmp/.code-coverage/ci-thresholds.json"
  echo '{"line_branch_delta": 16.77}' > "$tmp/.code-coverage/stack.json"

  bash "$SENTINEL" write "$tmp" 70 60   # adatta la firma reale di cmd_write

  local tb; tb=$(python3 -c "import json;print(json.load(open('$tmp/.code-coverage/user-choice.json'))['target_branch'])")
  assert_equals "70" "$tb" "effective target_branch deve essere 70 (CI override)"

  local ovr; ovr=$(python3 -c "import json;print(json.load(open('$tmp/.code-coverage/user-choice.json'))['ci_threshold_override'])")
  assert_equals "True" "$ovr" "ci_threshold_override deve essere true"

  grep -q "CI enforces higher thresholds" "$tmp/.code-coverage/decisions.log" \
    || fail "manca WARN in decisions.log"
  rm -rf "$tmp"
}
```
(Adatta `$SENTINEL`, `assert_equals`, `fail`, e la firma `write` agli helper realmente presenti nel file di test.)

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && bash scripts/tests/test_sentinel_handshake.sh`
Output atteso: il nuovo caso FALLISce (`ci_threshold_override` assente / `target_branch=60`).

### Step 3 — Implementa
Nel blocco Python di `cmd_write` di `lib/sentinel-handshake.sh`, **dopo** la derivazione del `target_branch` dal preset e **prima** della scrittura di `user-choice.json`, inserisci:

```python
import json as _json, time as _time, os as _os

_user_line = target          # preset scelto dall'utente
_user_branch = target_branch

# CI threshold override
_eff_line, _eff_branch = _user_line, _user_branch
_ci_src = "none"
_ci_path = _os.path.join(repo, ".code-coverage", "ci-thresholds.json")
try:
    _ci = _json.load(open(_ci_path))
    _ci_branch = _ci.get("COVERAGE_BRANCHES") or _ci.get("COVERAGE_THRESHOLD")
    _ci_line = _ci.get("COVERAGE_LINES") or _ci.get("COVERAGE_THRESHOLD")
    if _ci_branch and float(_ci_branch) > _eff_branch:
        _eff_branch = min(95, float(_ci_branch))
    if _ci_line and float(_ci_line) > _eff_line:
        _eff_line = min(95, float(_ci_line))
    _ci_src = _ci.get("source", "none")
except Exception:
    pass

# branch gap upfront
_high_branch_gap = False
try:
    _stack = _json.load(open(_os.path.join(repo, ".code-coverage", "stack.json")))
    _delta = _stack.get("line_branch_delta")
    _high_branch_gap = (_delta is not None and _delta > 15)
except Exception:
    pass

_override = (_eff_branch > _user_branch) or (_eff_line > _user_line)
if _override:
    _msg = (f"[sentinel] WARN: CI enforces higher thresholds than user preset. "
            f"Effective line={int(_eff_line)} branch={int(_eff_branch)} "
            f"(user line={int(_user_line)} branch={int(_user_branch)}). source={_ci_src}")
    _log = _os.path.join(repo, ".code-coverage", "decisions.log")
    with open(_log, "a") as _lf:
        _lf.write(f"[{_time.strftime('%Y-%m-%dT%H:%M:%SZ', _time.gmtime())}] {_msg}\n")

# usa i valori effettivi nel payload
target = int(_eff_line)
target_branch = int(_eff_branch)
```

E nel dizionario payload di `user-choice.json` aggiungi:
```python
    "user_requested_line": int(_user_line),
    "user_requested_branch": int(_user_branch),
    "ci_threshold_override": _override,
    "ci_thresholds_source": _ci_src,
    "high_branch_gap": _high_branch_gap,
```

Nel blocco Python di `cmd_read`, aggiungi le emissioni key=value (usa l'helper `emit` già presente):
```python
emit("ci_threshold_override", ctx.get("ci_threshold_override"))
emit("ci_thresholds_source", ctx.get("ci_thresholds_source"))
emit("high_branch_gap", ctx.get("high_branch_gap"))
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && bash scripts/tests/test_sentinel_handshake.sh`
Output atteso: tutti i casi PASS, incluso `test_effective_target_overrides_preset`.

### Step 5 — Commit
```
git add skills/code-coverage/lib/sentinel-handshake.sh skills/code-coverage/scripts/tests/test_sentinel_handshake.sh
git commit -m "feat(code-coverage): effective_target = max(user, CI threshold) + high_branch_gap surfacing"
```

## Criteri di accettazione
- [ ] CI branch=70 + preset 60 → `user-choice.json.target_branch=70`, `ci_threshold_override=true`, `ci_thresholds_source=CI.yaml`.
- [ ] `decisions.log` contiene `CI enforces higher thresholds`.
- [ ] `line_branch_delta>15` → `high_branch_gap=true`.
- [ ] Nessun `ci-thresholds.json` → comportamento identico a oggi (no override, no crash).
- [ ] `effective_target` mai > 95.
