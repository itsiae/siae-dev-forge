---
task: 07
title: Aggiornare test no-regression hook count
status: PENDING
estimate_min: 15
type: test
depends_on: [06]
---

# Task 07 — Aggiornare test no-regression hook count

## Obiettivo

Aggiornare il test che verifica il count dei hook registrati (memory
`pr252_test_count_drift`: aggiungere nuovo hook al count atteso).

## File da modificare

1. `tests/test_hooks_no_regression.py` (o equivalente — verifica path esatto)

## Modifica

Localizza l'assertion che conta gli hook attivi:

```python
def test_hook_count():
    hooks = load_hooks_json()
    session_start_hooks = hooks["hooks"]["SessionStart"]
    assert len(session_start_hooks) == 2  # era 1, ora 2
```

E lista degli hook attesi:

```python
EXPECTED_HOOKS = {
    "session-start",
    "session-start-tiered-advisor",  # NEW
    "post-commit-review",
    # ... resto invariato
}
```

## Step prerequisito

Prima di modificare il test, esegui:

```bash
cd "<repo>"
find tests/ -name "*test*hook*count*" -o -name "*test*regression*" | head -5
grep -rn "len.*SessionStart\|SessionStart.*length" tests/
```

Identifica il file esatto. Se non esiste, crea `tests/test_hooks_no_regression.py`.

## Criteri di accettazione

1. ✅ Test aggiornato a count atteso +1
2. ✅ Lista EXPECTED_HOOKS aggiornata con `session-start-tiered-advisor`
3. ✅ `pytest tests/test_hooks_no_regression.py` PASS
4. ✅ Pre-modifica documentata in commit message (count prima → dopo)

## Definition of Done

- Test PASS post-modifica
- Commit: `test(hooks): aggiorna count atteso per session-start-tiered-advisor`
