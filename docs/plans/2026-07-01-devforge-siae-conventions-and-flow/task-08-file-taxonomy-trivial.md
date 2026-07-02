# Task 08 — `devforge_change_is_trivial()` in file-taxonomy.sh

**Cluster:** REQ-DF-04 (brainstorming proporzionato alla complessità)
**Dipendenze:** nessuna (funzione pura, nuova, side-effect free; `hooks/brainstorming-gate` la consumerà nel Task 09)

## Goal

`lib/file-taxonomy.sh` espone `devforge_change_is_trivial(file_path, lines_changed)` che ritorna 0 (trivial) se e solo se l'estensione non è IaC (`.tf`/`.hcl`), `lines_changed` è ≤ `DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES` (default 15), e il path non è sensibile (`hooks/`, `lib/*gate*`, `lib/review_evidence/`); altrimenti ritorna 1 (non-trivial). L'aggregazione multi-file è fuori scope (gestita dal hook nel Task 09).

## File coinvolti

- `lib/file-taxonomy.sh` — **modifica**, append dopo la funzione `devforge_file_is_config_only` (righe 90-99, fine file a riga 99/100). Nuova funzione `devforge_change_is_trivial()` inserita dopo riga 99.
- `tests/lib/test_file_taxonomy_trivial.sh` — **nuovo** file di test (stile identico a `tests/lib/test_file_taxonomy.sh`, stesso pattern `_expect_*` + contatori PASS/FAIL + `source lib/file-taxonomy.sh`).

## Step TDD

### Step 1 — Scrivi il test che fallisce (codice completo)

Crea `tests/lib/test_file_taxonomy_trivial.sh`:

```bash
#!/usr/bin/env bash
# test_file_taxonomy_trivial.sh — unit tests for devforge_change_is_trivial (ADR-005, REQ-DF-04)
# ─────────────────────────────────────────────────────────────────
# Covers: trivial = estensione non-IaC AND lines_changed <= soglia AND
# path non-sensibile (hooks/, lib/*gate*, lib/review_evidence/).
# Aggregazione multi-file NON è coperta qui (hook-level, Task 09).
# ─────────────────────────────────────────────────────────────────
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB_FILE="${REPO_ROOT}/lib/file-taxonomy.sh"

if [ ! -f "$LIB_FILE" ]; then
    echo "FAIL — $LIB_FILE not found"
    exit 1
fi

# shellcheck disable=SC1090
source "$LIB_FILE"

_expect_trivial() {
    local name="$1" path="$2" lines="$3"
    if devforge_change_is_trivial "$path" "$lines"; then
        echo "  PASS  $name — $path ($lines lines)"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — $path ($lines lines) should be TRIVIAL"; FAIL=$((FAIL+1))
    fi
}

_expect_not_trivial() {
    local name="$1" path="$2" lines="$3"
    if devforge_change_is_trivial "$path" "$lines"; then
        echo "  FAIL  $name — $path ($lines lines) should NOT be trivial"; FAIL=$((FAIL+1))
    else
        echo "  PASS  $name — $path ($lines lines)"; PASS=$((PASS+1))
    fi
}

echo "=== 1. Trivial: small change, non-IaC, non-sensitive path ==="
_expect_trivial "small markdown"  "README.md" 5
_expect_trivial "small python"    "app/handler.py" 5
_expect_trivial "at threshold"    "app/handler.py" 15

echo ""
echo "=== 2. NOT trivial: sensitive path (hooks/) ==="
_expect_not_trivial "hooks pr-gate"  "hooks/pr-gate" 5
_expect_not_trivial "hooks any file" "hooks/session-start" 3

echo ""
echo "=== 3. NOT trivial: sensitive path (lib/*gate*) ==="
_expect_not_trivial "lib gate file"  "lib/tdd-gate-helpers.sh" 5
_expect_not_trivial "lib gate dir"   "lib/gate/foo.sh" 5

echo ""
echo "=== 4. NOT trivial: sensitive path (lib/review_evidence/) ==="
_expect_not_trivial "review_evidence" "lib/review_evidence/_sarif.py" 5

echo ""
echo "=== 5. NOT trivial: IaC extension regardless of size ==="
_expect_not_trivial "tf 1 line"   "terraform/main.tf" 1
_expect_not_trivial "hcl 1 line"  "terragrunt.hcl" 1

echo ""
echo "=== 6. NOT trivial: over the line threshold ==="
_expect_not_trivial "40 lines python" "app/handler.py" 40
_expect_not_trivial "16 lines just over" "app/handler.py" 16

echo ""
echo "=== 7. Configurable threshold via DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES ==="
(
    export DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES=5
    if devforge_change_is_trivial "app/handler.py" 10; then
        echo "  FAIL  10 lines should NOT be trivial with threshold=5"
        exit 1
    else
        echo "  PASS  10 lines correctly NOT trivial with threshold=5"
    fi
) && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
```

### Step 2 — Esegui e osserva il FAIL atteso

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/lib/test_file_taxonomy_trivial.sh
```

Output atteso (la funzione non esiste ancora; `command not found` è dentro un `if`, quindi `set -eu` NON termina lo script — ogni chiamata stampa l'errore su stderr e restituisce non-zero, facendo cadere l'helper nel ramo FAIL):

```
=== 1. Trivial: small change, non-IaC, non-sensitive path ===
tests/lib/test_file_taxonomy_trivial.sh: line 23: devforge_change_is_trivial: command not found
  FAIL  small markdown — README.md (5 lines) should be TRIVIAL
tests/lib/test_file_taxonomy_trivial.sh: line 23: devforge_change_is_trivial: command not found
  FAIL  small python — app/handler.py (5 lines) should be TRIVIAL
tests/lib/test_file_taxonomy_trivial.sh: line 23: devforge_change_is_trivial: command not found
  FAIL  at threshold — app/handler.py (15 lines) should be TRIVIAL
...
Total: 13 — PASS: 10 — FAIL: 3
```

Exit code: `3` (i 3 casi `_expect_trivial` fanno FAIL perché la funzione mancante restituisce sempre non-zero; i casi `_expect_not_trivial` invece PASSano per errore, essendo un falso-verde da correggere in Step 3). Questo conferma il RED state sui 3 casi che devono risultare trivial.

### Step 3 — Implementa il codice minimo (codice completo, path reali)

Apri `lib/file-taxonomy.sh` e aggiungi, dopo la fine della funzione `devforge_file_is_config_only` (dopo la riga `}` a riga 99), il seguente blocco:

```bash

# devforge_change_is_trivial FILE_PATH LINES_CHANGED
# Return 0 if the single-file change is trivial: non-IaC extension AND
# lines_changed <= DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES (default 15) AND
# path is not sensitive (hooks/, lib/*gate*, lib/review_evidence/).
# A small edit to a gate/enforcement file is high-risk, so it is forced
# non-trivial regardless of size — same carve-out logic as IaC.
# Multi-file aggregation is NOT handled here (caller/hook responsibility).
devforge_change_is_trivial() {
    local f="${1:-}" lines="${2:-0}"
    [ -z "$f" ] && return 1

    # IaC is always non-trivial (design-gated regardless of diff size).
    case "$f" in
        *.tf|*.hcl) return 1 ;;
    esac

    # Sensitive paths force non-trivial: hooks/, lib/*gate*, lib/review_evidence/.
    case "$f" in
        hooks/*|*/hooks/*) return 1 ;;
        lib/review_evidence/*) return 1 ;;
    esac
    case "$f" in
        lib/*gate*|*/lib/*gate*) return 1 ;;
    esac

    local threshold="${DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES:-15}"
    if [ "$lines" -gt "$threshold" ] 2>/dev/null; then
        return 1
    fi

    return 0
}
```

### Step 4 — Esegui e osserva il PASS atteso

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/lib/test_file_taxonomy_trivial.sh
```

Output atteso:

```
=== 1. Trivial: small change, non-IaC, non-sensitive path ===
  PASS  small markdown — README.md (5 lines)
  PASS  small python — app/handler.py (5 lines)
  PASS  at threshold — app/handler.py (15 lines)

=== 2. NOT trivial: sensitive path (hooks/) ===
  PASS  hooks pr-gate — hooks/pr-gate (5 lines)
  PASS  hooks any file — hooks/session-start (3 lines)

=== 3. NOT trivial: sensitive path (lib/*gate*) ===
  PASS  lib gate file — lib/tdd-gate-helpers.sh (5 lines)
  PASS  lib gate dir — lib/gate/foo.sh (5 lines)

=== 4. NOT trivial: sensitive path (lib/review_evidence/) ===
  PASS  review_evidence — lib/review_evidence/_sarif.py (5 lines)

=== 5. NOT trivial: IaC extension regardless of size ===
  PASS  tf 1 line — terraform/main.tf (1 lines)
  PASS  hcl 1 line — terragrunt.hcl (1 lines)

=== 6. NOT trivial: over the line threshold ===
  PASS  40 lines python — app/handler.py (40 lines)
  PASS  16 lines just over — app/handler.py (16 lines)

=== 7. Configurable threshold via DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES ===
  PASS  10 lines correctly NOT trivial with threshold=5

Total: 13 — PASS: 13 — FAIL: 0
```

Exit code: `0`.

Verifica di non-regressione sulla suite esistente della stessa libreria:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/lib/test_file_taxonomy.sh
```

Output atteso (invariato):

```
Total: 48 — PASS: 48 — FAIL: 0
```

### Step 5 — Commit

```bash
git add lib/file-taxonomy.sh tests/lib/test_file_taxonomy_trivial.sh
git commit -m "feat(file-taxonomy): add devforge_change_is_trivial for brainstorm gate scaling

Introduce a pure, unit-testable classifier that flags a single-file
change as trivial when: extension is not IaC (.tf/.hcl), lines_changed
is within DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES (default 15), and the
path is not sensitive (hooks/, lib/*gate*, lib/review_evidence/).
Multi-file aggregation stays a hook-level concern (REQ-DF-04, Task 09)."
```

## Criteri di accettazione

- [ ] `devforge_change_is_trivial()` esiste in `lib/file-taxonomy.sh`, è side-effect free (nessuna scrittura su file/env), e accetta 2 argomenti posizionali (`file_path`, `lines_changed`).
- [ ] Ritorna non-trivial (1) per estensione `.tf`/`.hcl` indipendentemente da `lines_changed` (AC2/AC3 design — IaC sempre complesso).
- [ ] Ritorna non-trivial (1) per path sotto `hooks/` indipendentemente da `lines_changed` (path-sensibile, AC2 design).
- [ ] Ritorna non-trivial (1) per path sotto `lib/` che matcha `*gate*` indipendentemente da `lines_changed` (path-sensibile, AC2 design).
- [ ] Ritorna non-trivial (1) per path sotto `lib/review_evidence/` indipendentemente da `lines_changed` (path-sensibile, AC2 design).
- [ ] Ritorna trivial (0) per un file non-IaC, path non-sensibile, con `lines_changed` ≤ soglia (default 15) — soglia esattamente inclusiva (15 = trivial, 16 = non-trivial) (AC1/AC3 design).
- [ ] Soglia configurabile via `DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES`, default 15 se non settata (AC3 design).
- [ ] `bash tests/lib/test_file_taxonomy_trivial.sh` esce con codice 0, tutti i PASS.
- [ ] `bash tests/lib/test_file_taxonomy.sh` (suite esistente) resta verde, 48/48 PASS — zero regressioni sulla libreria.
- [ ] Nessun placeholder, nessuna logica di aggregazione multi-file in questa funzione (scope riservato al Task 09/hook).
