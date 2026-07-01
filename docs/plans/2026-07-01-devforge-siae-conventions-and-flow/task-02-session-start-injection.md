# Task 02 — Injection dei 3 file canonici in session-start (fallback esplicito + byte-budget)

**Cluster:** A contesto (REQ-01/02/06)
**Dipendenze:** Task 01 (crea `skills/using-devforge/reference/siae-environments.md`, `siae-plan-deploy.md`, `siae-multirepo.md`)

## Goal

`hooks/session-start` inietta le 3 sezioni (ambienti, plan/deploy, multirepo) in `additional_context`, con marker esplicito `[FONTE NON DISPONIBILE: ...]` se un file è assente e marker `[troncato]` se il contenuto supera il budget di `head -c 1800` byte.

## File coinvolti

- **MODIFICA:** `hooks/session-start:337-345` (blocco `SIAE Global Rules` esistente + riga `session_context=...`)
- **CREA:** `tests/hooks/session-start-conventions.test.sh`
- **MODIFICA:** `tests/run-all.sh` (registrazione esplicita del nuovo test, accanto alla registrazione di `test_session_start_global_rules.sh` a riga 1213)

## Step TDD

### Step 1 — Scrivi il test fallente (Red)

Crea `tests/hooks/session-start-conventions.test.sh`:

```bash
#!/usr/bin/env bash
# Test: hooks/session-start inietta le 3 sezioni canoniche SIAE (environments,
# plan-deploy, multirepo) con fallback esplicito su file assente e marker di
# troncamento su file oversize.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/session-start"
REF_DIR="${PLUGIN_ROOT}/skills/using-devforge/reference"
ENV_FILE="${REF_DIR}/siae-environments.md"
PLAN_FILE="${REF_DIR}/siae-plan-deploy.md"
MULTIREPO_FILE="${REF_DIR}/siae-multirepo.md"

PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

for f in "$ENV_FILE" "$PLAN_FILE" "$MULTIREPO_FILE"; do
    if [ ! -f "$f" ]; then
        echo "  SKIP  tutti i check: $(basename "$f") assente (Task 01 non applicato)"
        echo ""; echo "PASS=$PASS FAIL=$FAIL"
        exit 1
    fi
done

# (A) STRUTTURALE — wiring presente nel hook per i 3 file + fallback + budget.
ok "legge siae-environments.md" \
   "grep -q 'siae-environments.md' '$HOOK'"
ok "legge siae-plan-deploy.md" \
   "grep -q 'siae-plan-deploy.md' '$HOOK'"
ok "legge siae-multirepo.md" \
   "grep -q 'siae-multirepo.md' '$HOOK'"
ok "usa head -c 1800 per il budget byte" \
   "grep -q 'head -c 1800' '$HOOK'"
ok "marker fallback esplicito presente nel sorgente" \
   "grep -q 'FONTE NON DISPONIBILE' '$HOOK'"
ok "marker troncamento presente nel sorgente" \
   "grep -q '\\[troncato\\]' '$HOOK'"
ok "sezioni referenziate in session_context" \
   "grep -E 'session_context=.*\\\$\\{?siae_environments_section' '$HOOK' >/dev/null && \
    grep -E 'session_context=.*\\\$\\{?siae_plan_deploy_section' '$HOOK' >/dev/null && \
    grep -E 'session_context=.*\\\$\\{?siae_multirepo_section' '$HOOK' >/dev/null"

# (B) FUNZIONALE (a) — con i 3 file presenti, additional_context contiene le 3 sezioni.
TMPHOME="$(mktemp -d)"; mkdir -p "$TMPHOME/.claude"
STDOUT=$(printf '{}' | HOME="$TMPHOME" bash "$HOOK" 2>/dev/null || true)
if echo "$STDOUT" | grep -q 'additional_context'; then
    ok "func(a): additional_context contiene marcatore ambienti/stage" \
       "echo \"\$STDOUT\" | grep -qi 'ambient'"
    ok "func(a): additional_context contiene marcatore plan/deploy" \
       "echo \"\$STDOUT\" | grep -qi 'plan'"
    ok "func(a): additional_context contiene marcatore multirepo" \
       "echo \"\$STDOUT\" | grep -qi 'multirepo\\|multi-repo'"
    ok "func(a): stdout è JSON valido" \
       "echo \"\$STDOUT\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
else
    echo "  SKIP  func(a): session-start non ha prodotto additional_context in sandbox"
fi

# (B) FUNZIONALE (b) — file assente → marker esplicito, MAI empty-string silenzioso.
BAK_ENV="${ENV_FILE}.bak.$$"
trap '[ -f "$BAK_ENV" ] && mv -f "$BAK_ENV" "$ENV_FILE" 2>/dev/null || true' EXIT
mv "$ENV_FILE" "$BAK_ENV"
TMPHOME2="$(mktemp -d)"; mkdir -p "$TMPHOME2/.claude"
STDOUT2=$(printf '{}' | HOME="$TMPHOME2" bash "$HOOK" 2>/dev/null || true)
mv "$BAK_ENV" "$ENV_FILE"; trap - EXIT
if echo "$STDOUT2" | grep -q 'additional_context'; then
    ok "func(b): file assente -> marker 'FONTE NON DISPONIBILE' iniettato" \
       "echo \"\$STDOUT2\" | grep -q 'FONTE NON DISPONIBILE'"
    ok "func(b): stdout resta JSON valido anche con fallback" \
       "echo \"\$STDOUT2\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
else
    echo "  SKIP  func(b): session-start non ha prodotto additional_context in sandbox"
fi

# (B) FUNZIONALE (c) — file oversize (> 1800 byte) -> marker [troncato].
BAK_PLAN="${PLAN_FILE}.bak.$$"
trap '[ -f "$BAK_PLAN" ] && mv -f "$BAK_PLAN" "$PLAN_FILE" 2>/dev/null || true' EXIT
cp "$PLAN_FILE" "$BAK_PLAN"
python3 -c "print('X' * 2500)" > "$PLAN_FILE"
TMPHOME3="$(mktemp -d)"; mkdir -p "$TMPHOME3/.claude"
STDOUT3=$(printf '{}' | HOME="$TMPHOME3" bash "$HOOK" 2>/dev/null || true)
mv "$BAK_PLAN" "$PLAN_FILE"; trap - EXIT
if echo "$STDOUT3" | grep -q 'additional_context'; then
    ok "func(c): file oversize -> marker '[troncato]' iniettato" \
       "echo \"\$STDOUT3\" | grep -q '\\[troncato\\]'"
    ok "func(c): stdout resta JSON valido con troncamento" \
       "echo \"\$STDOUT3\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
else
    echo "  SKIP  func(c): session-start non ha prodotto additional_context in sandbox"
fi

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

### Step 2 — Esegui e verifica che fallisce (Red)

Comando:
```bash
bash tests/hooks/session-start-conventions.test.sh
```

Output atteso (assumendo Task 01 già applicato, quindi i 3 file esistono ma il wiring in `hooks/session-start` no): i 7 check strutturali (A) fanno `FAIL` perché `siae-environments.md`, `siae-plan-deploy.md`, `siae-multirepo.md`, `head -c 1800`, `FONTE NON DISPONIBILE`, `[troncato]` e le 3 variabili `_section` non compaiono ancora nel hook. I check funzionali (B) possono risultare `SKIP` o `FAIL` a seconda dell'ambiente sandbox. Riga finale:
```
PASS=0 FAIL=7
```
Exit code diverso da 0.

### Step 3 — Implementa il wiring minimo (Green)

Modifica `hooks/session-start`. Individua il blocco esistente (righe 333-343, subito prima di `session_context=...` a riga 345):

```bash
# --- SIAE Global Rules (fonte unica versionata, iniezione team-wide) ---
# Mirror del read di using-devforge/SKILL.md. Fail-safe: file mancante -> sezione vuota
# -> session_context resta JSON valido. 2>/dev/null (NON 2>&1): un errore di lettura su
# file opzionale non deve finire iniettato nel contesto.
global_rules_content=$(cat "${PLUGIN_ROOT}/skills/using-devforge/reference/siae-global-rules.md" 2>/dev/null || echo "")
global_rules_section=""
if [ -n "$global_rules_content" ]; then
    global_rules_escaped=$(escape_for_json "$global_rules_content")
    global_rules_section="\\n\\n**SIAE Global Rules (operational guardrails — sempre attive):**\\n\\n${global_rules_escaped}"
fi
# --- End SIAE Global Rules ---
```

Subito dopo la riga `# --- End SIAE Global Rules ---` (e prima di `session_context="<EXTREMELY_IMPORTANT>...`), inserisci il nuovo blocco:

```bash
# --- SIAE Canonical Conventions (environments/plan-deploy/multirepo) ---
# 3 file canonici versionati (REQ-01/02/06). Ogni file è cappato a
# SIAE_CONVENTIONS_MAX_BYTES byte (allineato a GLOBAL_MEMORY_MAX_BYTES riga 296)
# per contenere il bloat (ADR-1). A differenza di siae-global-rules.md sopra,
# qui il fallback NON è silenzioso: un file mancante inietta un marker esplicito
# così l'agente dichiara l'assenza invece di ipotizzare i valori (REQ-01 AC4).
SIAE_CONVENTIONS_MAX_BYTES=1800

devforge_load_siae_convention() {
    # $1 = path assoluto file, $2 = etichetta topic per il marker di fallback
    local file_path="$1"
    local topic_label="$2"
    local raw_content
    local full_size

    if [ ! -f "$file_path" ]; then
        echo "[FONTE NON DISPONIBILE: ${topic_label} SIAE — NON ipotizzare, dichiara l'assenza]"
        return
    fi

    raw_content=$(cat "$file_path" 2>/dev/null || echo "")
    if [ -z "$raw_content" ]; then
        echo "[FONTE NON DISPONIBILE: ${topic_label} SIAE — NON ipotizzare, dichiara l'assenza]"
        return
    fi

    full_size=$(wc -c < "$file_path" 2>/dev/null | tr -d '[:space:]')
    local capped_content
    capped_content=$(head -c "$SIAE_CONVENTIONS_MAX_BYTES" "$file_path" 2>/dev/null || echo "")
    if [ -n "$full_size" ] && [ "$full_size" -gt "$SIAE_CONVENTIONS_MAX_BYTES" ]; then
        printf '%s\n[troncato]' "$capped_content"
    else
        printf '%s' "$capped_content"
    fi
}

siae_environments_raw="$(devforge_load_siae_convention "${PLUGIN_ROOT}/skills/using-devforge/reference/siae-environments.md" "elenco ambienti/stage")"
siae_environments_escaped=$(escape_for_json "$siae_environments_raw")
siae_environments_section="\\n\\n**SIAE Ambienti/Stage (fonte canonica):**\\n\\n${siae_environments_escaped}"

siae_plan_deploy_raw="$(devforge_load_siae_convention "${PLUGIN_ROOT}/skills/using-devforge/reference/siae-plan-deploy.md" "best practice PLAN/PLAN+DEPLOY")"
siae_plan_deploy_escaped=$(escape_for_json "$siae_plan_deploy_raw")
siae_plan_deploy_section="\\n\\n**SIAE PLAN / PLAN+DEPLOY (fonte canonica):**\\n\\n${siae_plan_deploy_escaped}"

siae_multirepo_raw="$(devforge_load_siae_convention "${PLUGIN_ROOT}/skills/using-devforge/reference/siae-multirepo.md" "convenzione multi-repo iac/bff/spa")"
siae_multirepo_escaped=$(escape_for_json "$siae_multirepo_raw")
siae_multirepo_section="\\n\\n**SIAE Multi-repo iac/bff/spa (fonte canonica):**\\n\\n${siae_multirepo_escaped}"
# --- End SIAE Canonical Conventions ---
```

Poi aggiorna la riga `session_context=...` (attuale riga 345) aggiungendo le 3 nuove variabili subito dopo `${global_rules_section}`. Da:

```bash
session_context="<EXTREMELY_IMPORTANT>\nHai siae-devforge.\n\n${python3_banner_section}${version_status_escaped}${branching_section}${global_rules_section}\n\n**Below is the content of your 'siae-devforge:using-devforge' meta-skill - the DevForge backbone for skill activation. For all other skills, use the 'Skill' tool:**\n\n${using_devforge_escaped}${catalog_section}${global_memory_section}\n</EXTREMELY_IMPORTANT>"
```

a:

```bash
session_context="<EXTREMELY_IMPORTANT>\nHai siae-devforge.\n\n${python3_banner_section}${version_status_escaped}${branching_section}${global_rules_section}${siae_environments_section}${siae_plan_deploy_section}${siae_multirepo_section}\n\n**Below is the content of your 'siae-devforge:using-devforge' meta-skill - the DevForge backbone for skill activation. For all other skills, use the 'Skill' tool:**\n\n${using_devforge_escaped}${catalog_section}${global_memory_section}\n</EXTREMELY_IMPORTANT>"
```

Nota implementativa: a differenza di `global_rules_section` (che sparisce con empty-string se il file manca), le 3 nuove sezioni sono **sempre non-vuote** — contengono o il contenuto capped o il marker `FONTE NON DISPONIBILE` — per soddisfare esplicitamente REQ-01 AC4 (dichiarare l'assenza, non tacere).

### Step 4 — Esegui e verifica che passa (Green)

Comando:
```bash
bash tests/hooks/session-start-conventions.test.sh
```

Output atteso:
```
PASS=13 FAIL=0
```
(oppure un sottoinsieme dei check funzionali in `SKIP` se la sandbox non produce `additional_context` — accettabile, i 7 check strutturali (A) devono essere sempre `PASS`). Exit code 0.

Registra il test in `tests/run-all.sh`. Trova il blocco gemello:
```bash
grep -n 'test_session_start_global_rules.sh' tests/run-all.sh
```
Subito dopo quel blocco (circa riga 1213-1220), aggiungi un blocco analogo:
```bash
if bash "${PLUGIN_ROOT}/tests/hooks/session-start-conventions.test.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/session-start-conventions.test.sh"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "  FAIL  tests/hooks/session-start-conventions.test.sh"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
```
(Usa gli stessi nomi di variabile contatore già in uso nel blocco gemello circostante — verificali con `sed -n '1205,1220p' tests/run-all.sh` prima di incollare, per matchare esattamente lo stile locale.)

Esegui la regressione mirata sugli altri test session-start:
```bash
for t in tests/hooks/test_session_start_*.sh tests/hooks/session-start-*.test.sh; do echo "== $t =="; bash "$t"; done
```
Output atteso: tutti i file terminano con `FAIL=0` e exit 0 — nessuna regressione sui test session-start preesistenti (incluso `test_session_start_global_rules.sh`, che deve restare verde perché il blocco `global_rules_section` non viene toccato, solo esteso).

### Step 5 — Commit

```bash
git add hooks/session-start tests/hooks/session-start-conventions.test.sh tests/run-all.sh
git commit -m "feat(session-start): inietta ambienti/plan-deploy/multirepo con fallback esplicito"
```

## Criteri di accettazione

- [ ] `hooks/session-start` legge i 3 file (`siae-environments.md`, `siae-plan-deploy.md`, `siae-multirepo.md`) via `devforge_load_siae_convention()`.
- [ ] Ogni file è cappato a 1800 byte (`SIAE_CONVENTIONS_MAX_BYTES`, allineato a `GLOBAL_MEMORY_MAX_BYTES=2000` di riga 296).
- [ ] File assente → marker `[FONTE NON DISPONIBILE: <topic> SIAE — NON ipotizzare, dichiara l'assenza]` iniettato al posto di stringa vuota (REQ-01 AC4).
- [ ] Contenuto troncato → marker `[troncato]` appeso.
- [ ] Le 3 sezioni sono referenziate in `session_context` subito dopo `${global_rules_section}`.
- [ ] `tests/hooks/session-start-conventions.test.sh` esiste e termina con `FAIL=0`.
- [ ] Test registrato esplicitamente in `tests/run-all.sh` (no glob discovery).
- [ ] Nessuna regressione sui test `test_session_start_*.sh` / `session-start-*.test.sh` preesistenti.
- [ ] `additional_context` resta JSON valido in tutti e 3 gli scenari (presente / assente / oversize).
