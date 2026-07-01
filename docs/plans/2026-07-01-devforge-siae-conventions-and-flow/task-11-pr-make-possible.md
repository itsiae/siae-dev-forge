# Task 11 — Fix "PR quasi impossibile": timeout review-evidence + idempotenza + README

**Cluster:** D (REQ-DF-05) · **Dipendenze:** nessuna (indipendente).

**Goal:** Rimuovere le tre cause-radice che rendono l'apertura PR "quasi impossibile": (1) il timeout dichiarato di `review-evidence` inferiore all'attesa interna del lock → fail-closed spurio; (2) assenza di guard di idempotenza in `siae-finishing-branch` → errore grezzo "PR already exists"; (3) `pr-premortem-gate` non documentato nel README (sotto-rappresenta i gate bloccanti).

## File coinvolti
- `hooks/hooks.json` (modifica — voci `review-evidence` PreToolUse+PostToolUse Bash, campo `timeout`)
- `hooks/review-evidence` (lettura/verifica — attesa lock `~:280-319`)
- `skills/siae-finishing-branch/reference/finishing-branch-checklist.md` (modifica — Step 5 `~:301-383`)
- `skills/siae-release-pr-to-main/SKILL.md` (lettura — pattern idempotenza `:114-117`)
- `README.md` (modifica — tabella "Review & Quality" `~:299-306`)
- `tests/hooks/review-evidence-timeout.test.sh` (nuovo)

## Step TDD

### Step 1 — Test fallente (timeout coerente)
Crea `tests/hooks/review-evidence-timeout.test.sh`:
```bash
#!/usr/bin/env bash
# Verifica: il timeout dichiarato in hooks.json per review-evidence
# >= massima attesa lock interna in hooks/review-evidence.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fail=0

# Attesa lock interna (max iterazioni * sleep). Il loop usa un contatore su 1s.
MAX_WAIT=$(grep -oE 'LOCK_MAX_WAIT=[0-9]+|for +i +in +\$\(seq +1 +([0-9]+)\)' "$ROOT/hooks/review-evidence" \
  | grep -oE '[0-9]+' | sort -rn | head -1)
[ -z "$MAX_WAIT" ] && MAX_WAIT=30

# Timeout dichiarato per review-evidence in hooks.json (minimo tra le occorrenze).
DECLARED=$(python3 - "$ROOT/hooks/hooks.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
mins=[]
def walk(o):
    if isinstance(o,dict):
        cmd=json.dumps(o)
        if 'review-evidence' in cmd and 'timeout' in o:
            mins.append(o['timeout'])
        for v in o.values(): walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(d)
print(min(mins) if mins else 0)
PY
)
if [ "$DECLARED" -lt "$MAX_WAIT" ]; then
  echo "FAIL: review-evidence timeout dichiarato=$DECLARED < attesa lock=$MAX_WAIT"
  fail=1
else
  echo "PASS: timeout=$DECLARED >= attesa=$MAX_WAIT"
fi
exit $fail
```

### Step 2 — Esegui e verifica FAIL
Run: `bash tests/hooks/review-evidence-timeout.test.sh`
Output atteso (pre-fix): `FAIL: review-evidence timeout dichiarato=20 < attesa lock=30`, exit 1.

### Step 3 — Implementa il fix
1. **Timeout** — in `hooks/hooks.json`, per **entrambe** le voci `review-evidence` (PreToolUse:Bash e PostToolUse:Bash) porta `"timeout": 20` → `"timeout": 35` (35 > 30s di attesa lock + margine). Verifica prima il valore reale dell'attesa in `hooks/review-evidence` (`~:287` / loop `:302-318`) e imposta `timeout` = attesa + 5.
2. **Idempotenza** — in `finishing-branch-checklist.md` Step 5, PRIMA del blocco `gh pr create`, inserisci:
   ```markdown
   #### 5.0 Pre-check idempotenza (evita "PR already exists")
   ```bash
   EXISTING=$(gh pr list --head "$(git branch --show-current)" --state open --json number,url -q '.[0].url' 2>/dev/null)
   if [ -n "$EXISTING" ]; then echo "PR gia' aperta: $EXISTING — non ricreo"; exit 0; fi
   ```
   Se una PR aperta esiste, ritorna l'URL e NON esegue `gh pr create` (pattern da `siae-release-pr-to-main/SKILL.md:114-117`).
3. **README** — nella tabella "Review & Quality" (`~:299-306`) aggiungi la riga:
   ```markdown
   | `pr-premortem-gate` | PreToolUse:Bash | Richiede `siae-premortem` prima di `gh pr create/edit` (scala ad advisory su diff low-risk) |
   ```

### Step 4 — Esegui e verifica PASS
Run: `bash tests/hooks/review-evidence-timeout.test.sh`
Output atteso: `PASS: timeout=35 >= attesa=30`, exit 0.
Run: `grep -c 'pr-premortem-gate' README.md` → atteso `>=1`.
Run: `grep -q '5.0 Pre-check idempotenza' skills/siae-finishing-branch/reference/finishing-branch-checklist.md && echo OK` → atteso `OK`.
Registra il nuovo test in `tests/run-all.sh` (blocco di registrazione esplicito, mirror di `test_session_start_global_rules.sh`).

### Step 5 — Commit
`fix(pr-flow): allinea timeout review-evidence, idempotenza finishing-branch, doc pr-premortem-gate (REQ-DF-05)`

## Criteri di accettazione
- [ ] Timeout `review-evidence` in `hooks.json` >= attesa lock interna (test verde) → elimina fail-closed spurio (REQ-05 "apertura programmatica possibile").
- [ ] Step 5 di `finishing-branch` fa pre-check `gh pr list --head` e non ricrea una PR esistente (AC3 "non chiede ripetutamente").
- [ ] README elenca `pr-premortem-gate` (doc hygiene, superficie gate visibile).
- [ ] Nuovo test registrato in `tests/run-all.sh`; suite esistente verde (no regressioni).
