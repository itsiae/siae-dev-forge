# Task 12 — PR programmatic-first + linguaggio onesto + no-review advisory su sviluppo

**Cluster:** D (REQ-DF-05) · **Dipendenze:** Task 07 (condivide `hooks/pr-gate:205-266`) + Task 11.

**Goal:** DevForge apre le PR programmaticamente come default (manuale = ultimo ricorso esplicito), il gate `pr-gate` usa linguaggio coerente con la sua reale natura advisory, e i gate di review scalano ad advisory quando la base PR è `sviluppo` (review facoltativa SIAE) — senza toccare branch protection né `gh pr merge --auto`.

## File coinvolti
- `skills/siae-git-env/SKILL.md` (modifica — FALLBACK table `~:105-116`; bias "assume FALLBACK safe default" `~:157-169`)
- `skills/siae-finishing-branch/reference/finishing-branch-checklist.md` (modifica — Step 5 FALLBACK `~:352-383`; permission-denied `~:406-409`)
- `skills/siae-requesting-review/SKILL.md` (modifica — permission-denied `~:221-233`)
- `hooks/pr-gate` (modifica — heredoc `PR_GATE_INSTRUCTIONS` `~:205-266`, SOLO la parte linguaggio; la base-resolution è già gestita da Task 07)
- `hooks/pr-blind-review-gate` (modifica — parse `--base`, advisory su `sviluppo`, `~:28-31` estrazione TOOL_COMMAND, `~:110-125` carve-out `risk=low`)
- `hooks/pr-premortem-gate` (modifica — stesso pattern)
- `tests/hooks/pr-no-review-advisory.test.sh` (nuovo)

## Step TDD

### Step 1 — Test fallente (no-review advisory + manuale last-resort)
Crea `tests/hooks/pr-no-review-advisory.test.sh`:
```bash
#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fail=0
run_gate(){ # $1=hook  $2=command  -> stampa decision (block|advisory|allow)
  printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$2" \
    | DEVFORGE_TEST_RISK=code bash "$ROOT/hooks/$1" 2>/dev/null | grep -oE '"decision":"[a-z]*"' || echo '"decision":"allow"'
}
# base=sviluppo -> NON deve essere un hard block (advisory/allow)
OUT=$(run_gate pr-blind-review-gate 'gh pr create --base sviluppo --fill')
echo "$OUT" | grep -q '"decision":"block"' && { echo "FAIL: block su base=sviluppo"; fail=1; } || echo "PASS: no-block su sviluppo"
# base=main (o --fill senza base) -> strict come oggi
OUT=$(run_gate pr-blind-review-gate 'gh pr create --base main --fill')
echo "$OUT" | grep -q '"decision":"block"' || { echo "NOTE: main non bloccato (ok se blind-review gia' fatto)"; }
# Manuale = ultimo ricorso: la FALLBACK table non deve presentare il manuale come primo path
grep -q 'ULTIMO RICORSO\|ultimo ricorso' skills/siae-git-env/SKILL.md || { echo "FAIL: manuale non marcato last-resort"; fail=1; }
exit $fail
```

### Step 2 — Esegui e verifica FAIL
Run: `bash tests/hooks/pr-no-review-advisory.test.sh`
Output atteso (pre-fix): `FAIL: block su base=sviluppo` e/o `FAIL: manuale non marcato last-resort`, exit 1.

### Step 3 — Implementa
1. **Parse base + advisory** — in `hooks/pr-blind-review-gate` e `hooks/pr-premortem-gate`, dopo l'estrazione di `TOOL_COMMAND` (`~:28-31`), estrai la base:
   ```bash
   PR_BASE=$(printf '%s' "$TOOL_COMMAND" | grep -oE -- '(--base|-B)[ =]+[^ ]+' | grep -oE '[^ =]+$' | head -1)
   # --fill / base omessa -> strict (default repo = main)
   if [ "$PR_BASE" = "sviluppo" ]; then
     # review facoltativa su sviluppo (direttiva DevOps SIAE): scala ad advisory
     # come il carve-out esistente risk=low
     ADVISORY=1
   fi
   ```
   Dove oggi il gate emette `decision:block` per mancanza di `siae-blind-review`/`siae-premortem`, se `ADVISORY=1` emette invece un messaggio advisory (stesso ramo di `risk=low`, `~:110-125`) senza `decision:block`.
2. **Linguaggio onesto pr-gate** — in `hooks/pr-gate` heredoc `PR_GATE_INSTRUCTIONS` (`~:205-266`): sostituisci "Questo NON e' opzionale... E' un gate bloccante" con formulazione advisory onesta (es. "Raccomandato: dispatcha code-reviewer + spec-reviewer prima di aprire la PR. Se il diff è a basso rischio puoi procedere con `gh pr create`."). NON reintrodurre il linguaggio "bloccante" senza `decision:block`. (La base-resolution nello stesso heredoc è già di Task 07 — non duplicare.)
3. **Programmatic-first** — nei siti manual-ask riformula così che `gh pr create` sia il default e il template manuale sia marcato `ULTIMO RICORSO`:
   - `siae-git-env/SKILL.md` FALLBACK table (`~:105-116`): la riga "Apri PR" indica prima il tentativo programmatico (`gh pr create`, o `gh api repos/{o}/{r}/pulls` se il CLI subcommand fallisce ma `gh auth token` è disponibile), poi il template manuale come `ULTIMO RICORSO`.
   - Rimuovi il bias `~:157-169` "Assumi FALLBACK_MODE come default sicuro" → "tenta prima il path programmatico; degrada al manuale solo dopo fallimento verificato".
   - `finishing-branch-checklist.md` `~:352-383` e `~:406-409`, `siae-requesting-review/SKILL.md` `~:221-233`: stessa riformulazione + rimuovi la razionalizzazione "review non necessaria → apri manuale".

### Step 4 — Esegui e verifica PASS
Run: `bash tests/hooks/pr-no-review-advisory.test.sh`
Output atteso: `PASS: no-block su sviluppo`, nessun FAIL, exit 0.
Run: `grep -rn 'ULTIMO RICORSO' skills/siae-git-env/SKILL.md skills/siae-finishing-branch skills/siae-requesting-review` → almeno 3 match.
Run: `! grep -q 'gate bloccante' hooks/pr-gate && echo OK` → atteso `OK`.
Registra il test in `tests/run-all.sh`.

### Step 5 — Commit
`fix(pr-flow): programmatic-first PR + linguaggio pr-gate advisory + no-review su sviluppo (REQ-DF-05)`

## Criteri di accettazione
- [ ] `gh pr create` è il path di default; il template manuale è marcato `ULTIMO RICORSO` (AC1 apertura programmatica, AC3 non chiede ripetutamente manuale).
- [ ] `pr-gate` non usa più "gate bloccante" senza block reale → l'agent procede invece di tentennare (AC1).
- [ ] Base PR `sviluppo` → gate review advisory (no hard block); base omessa/`main` → strict (AC2 no-review path corretto, senza toccare branch protection).
- [ ] Rimossa la razionalizzazione "review non necessaria → apri manuale".
- [ ] Nuovo test registrato; suite esistente verde.
