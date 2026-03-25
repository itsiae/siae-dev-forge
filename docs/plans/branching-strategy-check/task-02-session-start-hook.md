# Task 02 — Modifica session-start: branching summary

**Stato:** [PENDING]
**File coinvolti:**
- `hooks/session-start` (MODIFY)

---

## Contesto

Aggiungere al termine dell'hook `session-start` un blocco che:
1. Legge da cache `~/.claude/.devforge-branching-compliance` (TTL 4h)
2. Se cache fresca → inietta summary compact nel `session_context` JSON
3. Se cache assente o stale → lancia refresh in background (non blocca startup)

---

## Step 1 — Leggi il file corrente

Leggi `hooks/session-start` per trovare il punto di iniezione corretto.
Identifica la riga dove viene costruito l'oggetto JSON di output (di solito
una `printf` o `echo` con `additional_context` o `session_context`).

---

## Step 2 — Aggiungi il blocco branching compliance

Prima della riga di output JSON finale, aggiungi:

```bash
# --- Branching compliance summary (async, non-blocking) ---
BRANCHING_CACHE="${HOME}/.claude/.devforge-branching-compliance"
BRANCHING_SUMMARY=""
NOW_TS=$(date +%s)
CACHE_TTL=14400  # 4 ore

if command -v gh >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    if [ -f "$BRANCHING_CACHE" ]; then
        CACHE_TS=$(jq -r '.ts // 0' "$BRANCHING_CACHE" 2>/dev/null || echo "0")
        CACHE_AGE=$((NOW_TS - CACHE_TS))
        if [ "$CACHE_AGE" -lt "$CACHE_TTL" ]; then
            VIOLATIONS=$(jq -r '.violations // empty' "$BRANCHING_CACHE" 2>/dev/null || echo "")
            REPOS=$(jq -r '.repos_checked // empty' "$BRANCHING_CACHE" 2>/dev/null || echo "")
            if [ -n "$VIOLATIONS" ] && [ "$VIOLATIONS" -gt 0 ]; then
                BRANCHING_SUMMARY="⚠️ Branching compliance: ${VIOLATIONS} violazioni su ${REPOS} repo itsiae — invoca /branching-strategy-check per i dettagli."
            elif [ -n "$VIOLATIONS" ]; then
                BRANCHING_SUMMARY="✅ Branching compliance: tutti i ${REPOS} repo itsiae sono compliant."
            fi
            CACHE_AGE_STALE=0
        else
            CACHE_AGE_STALE=1
        fi
    else
        CACHE_AGE_STALE=1
    fi

    # Refresh in background se cache assente o stale
    if [ "${CACHE_AGE_STALE:-1}" -eq 1 ]; then
        (
            REPOS_JSON=$(gh search repos --owner=itsiae --limit 100 --json fullName -q '[.[].fullName]' 2>/dev/null || echo "[]")
            TOTAL=$(echo "$REPOS_JSON" | jq 'length' 2>/dev/null || echo "0")
            VIOLS=0
            while IFS= read -r repo; do
                [ -z "$repo" ] && continue
                DEFAULT=$(gh repo view "$repo" --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null || echo "main")
                if [ "$DEFAULT" != "main" ]; then
                    VIOLS=$((VIOLS + 1))
                    continue
                fi
                BAD=$(gh pr list --repo "$repo" --base main --state open \
                    --json headRefName -q '[.[] | select(.headRefName | test("^release/") | not)] | length' 2>/dev/null || echo "0")
                VIOLS=$((VIOLS + BAD))
            done < <(echo "$REPOS_JSON" | jq -r '.[]' 2>/dev/null)
            echo "{\"ts\":${NOW_TS},\"violations\":${VIOLS},\"repos_checked\":${TOTAL},\"compliant\":$((TOTAL - VIOLS))}" > "$BRANCHING_CACHE"
        ) &
        disown 2>/dev/null || true
    fi
fi
# --- End branching compliance ---
```

---

## Step 3 — Inietta BRANCHING_SUMMARY nel contesto

Trova la sezione dove viene costruito il contesto da iniettare (es. la variabile
`CONTEXT_PARTS` o la `printf` finale). Aggiungi `BRANCHING_SUMMARY` in quel punto.

Se il contesto viene costruito con newline separate, aggiungi:

```bash
if [ -n "$BRANCHING_SUMMARY" ]; then
    CONTEXT_PARTS="${CONTEXT_PARTS}\\n${BRANCHING_SUMMARY}"
fi
```

Se il contesto è una stringa singola con separatori, adatta al pattern esistente.

---

## Step 4 — Verifica manuale

```bash
# Simula un avvio sessione forzando cache vuota
rm -f "${HOME}/.claude/.devforge-branching-compliance"
bash hooks/session-start <<< '{}'
```

Output atteso: nessun BRANCHING_SUMMARY nel JSON (cache assente → background refresh avviato).

Dopo ~30 secondi (tempo per il background job):
```bash
cat "${HOME}/.claude/.devforge-branching-compliance"
```

Output atteso (esempio):
```json
{"ts":1234567890,"violations":3,"repos_checked":47,"compliant":44}
```

Seconda esecuzione (cache fresca):
```bash
bash hooks/session-start <<< '{}'
```

Output atteso: il JSON di output contiene `⚠️ Branching compliance: 3 violazioni su 47 repo itsiae`.

---

## Step 5 — Commit

```bash
git add hooks/session-start
git commit -m "feat(hooks): add branching compliance summary to session-start"
```
