# Task 02: Test Ermetici con Flag (D2)

**Deliverable:** D2
**Dipendenze:** Task 01 (DEVFORGE_STATE_DIR)
**File coinvolti:** `tests/run-all.sh`

---

## Step 1 — Test: verifica che --fast non esiste ancora

```bash
bash tests/run-all.sh --help 2>&1 || true
```
Output atteso: errore o nessun aiuto (flag non supportato).

## Step 2 — Aggiungi tmpdir automatico e flag parsing

In `tests/run-all.sh`, subito dopo le variabili iniziali, aggiungere:

```bash
# ─── Flag parsing ───
TEST_MODE="integration"  # default
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fast) TEST_MODE="fast"; shift ;;
    --integration) TEST_MODE="integration"; shift ;;
    *) echo "Usage: $0 [--fast|--integration]"; exit 1 ;;
  esac
done

# ─── State dir isolation ───
if [ -z "${DEVFORGE_STATE_DIR:-}" ]; then
    export DEVFORGE_STATE_DIR=$(mktemp -d)
    CLEANUP_STATE_DIR=1
fi
# Ensure state dir exists
mkdir -p "$DEVFORGE_STATE_DIR"
```

## Step 3 — Wrappa i test ambientali in guard

Trova le sezioni di test che invocano hook o scrivono stato. Wrappale con:

```bash
if [ "$TEST_MODE" = "integration" ]; then
    # ... test che invocano hook, scrivono state ...
fi
```

Sezioni da wrappare:
- Test hook pre-commit (invoca `bash hooks/pre-commit`)
- Test hook post-skill (invoca `bash hooks/post-skill`)
- Test capture-test-result
- Qualsiasi test che scrive in `$DEVFORGE_STATE_DIR`

I test statici (validazione skill, frontmatter, naming) restano fuori dal guard.

## Step 4 — Aggiungi cleanup

A fine script, prima del summary:

```bash
# ─── Cleanup ───
if [ "${CLEANUP_STATE_DIR:-}" = "1" ] && [ -d "$DEVFORGE_STATE_DIR" ]; then
    rm -rf "$DEVFORGE_STATE_DIR"
fi
```

## Step 5 — Run e verifica

```bash
# Fast mode: solo test statici, target <5s
time tests/run-all.sh --fast
```
Output atteso: tutti i test statici passano, tempo <5s.

```bash
# Integration mode (default): tutto
tests/run-all.sh
```
Output atteso: tutti i test passano, nessun accesso a `~/.claude/`.

## Step 6 — Commit

```bash
git add tests/run-all.sh
git commit -m "test(suite): add --fast/--integration flags + hermetic state dir

- --fast runs only static tests (validation, frontmatter, naming) in <5s
- --integration (default) runs all tests including hook invocations
- Auto-creates tmpdir for DEVFORGE_STATE_DIR if not set
- Cleanup tmpdir on exit

Co-Authored-By: SIAE DevForge"
```
