# Task 07 — Breakglass ibrido scoped sui 5 path tool-fail (ADR-1 = Opzione C)

**Goal:** Introdurre in `hooks/review-evidence` un breakglass dedicato (env var `DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS=1` OR state-file `~/.claude/.devforge-evidence-toolfail` con auto-decremento `N=count`) che rilascia il block **solo** sui 5 fallimenti di tooling reali, **mai** sui verdetti di qualità.

> Dipendenza: dopo Task 06 (stesso file).

## I 5 path di tool-fail (righe nel file)
| Riga | Causa | Reason attuale |
|---|---|---|
| 102 | jq assente su trigger bloccante | "jq is required..." |
| 305 | lock contention | "lock contention on..." |
| 351 | collector crash RC≠0 | "${BLOCK_REASON}..." |
| 386 | no evidence file dopo compute | "no evidence file..." |
| 398 | evidence JSON non valido / placeholder iCloud | "evidence file ... not valid JSON..." |

## File coinvolti
- Modifica: `hooks/review-evidence` (helper nuovo + 5 path)
- Nuovo test: `tests/test_review_evidence_breakglass.py` (o caso in `tests/test_review_evidence_hook.py`)

## Step TDD

### Step 1 — Scrivi i test (test-first)
Crea i casi:
1. **jq-missing + breakglass env** → con `DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS=1` e trigger `gh pr create`, simula jq assente → output `{}` (allow). Pattern per simulare jq assente in subprocess Python:
   ```python
   env = {**os.environ, "PATH": "/nonexistent", "DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS": "1"}
   # subprocess.run(["bash", "hooks/review-evidence"], input=envelope_json, env=env, ...)
   ```
   L'helper usa solo builtin (`cat`/`rm`/`mv`/`echo`/`case`), quindi funziona anche con PATH vuoto/senza jq.
2. **jq-missing + breakglass state-file** → senza env, con file `~/.claude/.devforge-evidence-toolfail` contenente `N=2` → output `{}` e file decrementato a `N=1`.
3. **state-file esaurito** → file con `N=1`: dopo un uso, output `{}` e file rimosso.
4. **GUARD CRITICO**: `BLOCK_REGRESSION` (verdetto qualità) con `DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS=1` → output resta `"decision":"block"` (il breakglass NON copre i verdetti di qualità).
5. **nessun breakglass** → jq-missing senza env né file → output `"decision":"block"` (comportamento attuale invariato).

### Step 2 — Esegui e verifica che falliscono
```bash
python3 -m pytest tests/test_review_evidence_breakglass.py -v
```
Output atteso: FALLISCONO (helper non esiste ancora).

### Step 3 — Aggiungi l'helper
Inserisci dopo la definizione di `devforge_log` (vicino all'inizio del file, dopo il sourcing della lib comune) la funzione:
```bash
# ── Tool-fail breakglass (ADR-1 C) ──────────────────────────────
# Rilascia il block SOLO sui fallimenti di tooling ambientali, MAI sui
# verdetti di qualità. Sorgenti: env var OR state-file con auto-decremento.
_devforge_evidence_toolfail_breakglass() {
    if [ "${DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS:-0}" = "1" ]; then
        return 0
    fi
    _bg_file="${HOME}/.claude/.devforge-evidence-toolfail"
    [ -f "$_bg_file" ] || return 1
    _bg_data=$(cat "$_bg_file" 2>/dev/null || echo "")
    case "$_bg_data" in
        N=*) _bg_n="${_bg_data#N=}" ;;
        *)   _bg_n=1 ;;
    esac
    case "$_bg_n" in (*[!0-9]*|"") _bg_n=0 ;; esac
    if [ "$_bg_n" -lt 1 ]; then
        rm -f "$_bg_file" 2>/dev/null || true
        return 1
    fi
    _bg_n=$((_bg_n - 1))
    if [ "$_bg_n" -le 0 ]; then
        rm -f "$_bg_file" 2>/dev/null || true
    else
        echo "N=${_bg_n}" > "${_bg_file}.tmp" && mv "${_bg_file}.tmp" "$_bg_file"
    fi
    return 0
}
```

### Step 4 — Applica il check ai 5 path
In ciascuno dei 5 path tool-fail, PRIMA di emettere `{"decision":"block",...}`, inserisci:
```bash
if _devforge_evidence_toolfail_breakglass; then
    devforge_log "evidence_toolfail_breakglass_used" "warn" \
        "{\"path\":\"<jq_missing|lock|collector_crash|no_evidence|invalid_json>\"}" 2>/dev/null || true
    echo '{}'
    exit 0
fi
```
Sostituendo `<...>` con l'etichetta del path corrispondente. Aggiorna anche i reason di questi 5 path: sostituisci `Override: DEVFORGE_SKIP_EVIDENCE=1 (env var, session-scoped breakglass)` con `Breakglass tool-fail: DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS=1 o file ~/.claude/.devforge-evidence-toolfail (solo fallimenti di tooling)`.

> **GUARD CRITICO — dove NON mettere la chiamata.** Il breakglass non deve mai
> rilasciare un verdetto di qualità. La garanzia è *per costruzione*: la chiamata
> `_devforge_evidence_toolfail_breakglass` va inserita **SOLO** nei 5 path
> tool-fail (102, 305, 351, 386, 398) e **MAI** nei rami `BLOCK_REGRESSION`
> (~459-463), `BLOCK_HARD_FLOOR`, `SEVERELY_DEGRADED`. Non aggiungere check
> "verdetto qualità → non chiamare": semplicemente non chiamare l'helper lì.

> NB path 102 (jq missing): l'helper usa `cat`/`rm`/`mv`/`echo` builtin, NON jq → funziona anche senza jq. Verificalo.

### Step 5 — Esegui, verifica, commit
```bash
bash -n hooks/review-evidence
python3 -m pytest tests/test_review_evidence_breakglass.py tests/test_review_evidence_hook.py -v
grep -n "DEVFORGE_SKIP_EVIDENCE" hooks/review-evidence   # atteso: nessun match
grep -c "_devforge_evidence_toolfail_breakglass" hooks/review-evidence  # atteso: 6 (1 def + 5 call)
```
Output atteso: tutti PASS; nessun residuo `DEVFORGE_SKIP_EVIDENCE`; helper chiamato nei 5 path.
```bash
git add hooks/review-evidence tests/test_review_evidence_breakglass.py
git commit -m "feat(hooks): breakglass ibrido scoped sui 5 path tool-fail di review-evidence"
```

## Criteri di accettazione
- [ ] Helper `_devforge_evidence_toolfail_breakglass` definito e chiamato nei 5 path (102, 305, 351, 386, 398).
- [ ] Breakglass funziona via env var E via state-file con auto-decremento `N=count`.
- [ ] **GUARD**: `BLOCK_REGRESSION`/hard-floor con breakglass attivo → resta block (test 4 PASS).
- [ ] Path jq-missing usa solo builtin (nessuna dipendenza da jq nell'helper).
- [ ] Nessun residuo `DEVFORGE_SKIP_EVIDENCE` in `hooks/review-evidence`.
- [ ] `bash -n` senza errori; suite review-evidence PASS.
