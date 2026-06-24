# Task 04 — Gate finale: verifica ADERENZA e ALLINEAMENTO

**Goal:** chiudere il goal utente *"verifica aderenza e allineamento"* con evidenza concreta — l'implementazione aderisce al design e alla fonte, e l'allineamento single-source regge. Stato: `[PENDING]`.
**Dipende da:** Task 01 + 02 + 03 (gate finale, dopo tutto il resto).

## Cosa significano qui (no nuovo sottosistema — solo verifica)
- **Aderenza:** il file regole cattura fedelmente le regole fornite; l'implementazione soddisfa ogni AC del design.
- **Allineamento:** esiste UNA sola fonte (nessun duplicato del contenuto regole altrove) e il link è LIVE (test verde = valutazione continua in CI).

## Step

### Step 1 — Aderenza al design (mapping AC → evidenza)
Verifica i 6 AC del design `docs/plans/2026-06-24-siae-global-rules-injection-design.md §7`:
```bash
# AC1: file + 7 sezioni
test "$(grep -c '^## ' skills/using-devforge/reference/siae-global-rules.md)" = "7" && echo "AC1 OK"
# AC2: iniezione referenziata
grep -E 'session_context=.*global_rules_section' hooks/session-start >/dev/null && echo "AC2 OK"
# AC5: test verde
bash tests/hooks/test_session_start_global_rules.sh >/dev/null && echo "AC5 OK"
```
Output atteso: `AC1 OK`, `AC2 OK`, `AC5 OK`.

### Step 2 — Allineamento single-source (nessuna duplicazione del contenuto regole)
Il contenuto regole deve vivere SOLO nel file fonte. Verifica che NON sia stato copiato dentro la SKILL.md del backbone né in altre skill:
```bash
# Sentinel unici delle regole NON devono comparire fuori dalla fonte
grep -rn 'Do NOT over-scope changes' skills/ hooks/ | grep -v 'skills/using-devforge/reference/siae-global-rules.md'
grep -rn '10.255.1.241' skills/ hooks/ | grep -v 'siae-global-rules.md'
```
Output atteso: **nessuna riga** per il primo grep (regole non duplicate). Il secondo può matchare solo eventuali commenti del hook, MAI un secondo file di regole.

### Step 3 — Allineamento dedup verso skill (rimando, non duplicazione divergente)
```bash
grep -q 'siae-git-workflow' skills/using-devforge/reference/siae-global-rules.md && echo "rimando git OK"
grep -q 'siae-github-env-sync' skills/using-devforge/reference/siae-global-rules.md && echo "rimando github-env OK"
```
Output atteso: entrambi `OK`.

### Step 4 — Aderenza alla fonte (fedeltà delle 7 sezioni fornite)
Verifica manuale (checklist): le 7 sezioni corrispondono alle Global Rules fornite, con SOLO le 3 normalizzazioni del design §4.1 (no account gh personale, workspace OneDrive→OneDrive/iCloud, rimandi a skill). Nessuna regola fornita è stata omessa o alterata nel significato.

### Step 5 — No-regression suite hook + backbone
```bash
for t in tests/hooks/test_session_start_*.sh; do echo "== $t =="; bash "$t" || echo "REGRESSIONE in $t"; done
node tests/using-devforge-backbone.test.js 2>/dev/null && echo "backbone OK" || echo "backbone: verifica manuale"
```
Output atteso: tutti i test session-start `FAIL=0`; nessuna riga `REGRESSIONE`.

### Step 6 — REQUIRED SUB-SKILL
Invoca `siae-verification` per la verifica evidence-based finale prima di dichiarare il branch pronto.

## Criteri di accettazione
- [ ] Tutti gli AC del design verificati con evidenza (Step 1).
- [ ] Zero duplicazione del contenuto regole fuori dalla fonte (Step 2).
- [ ] Rimandi a skill presenti (Step 3).
- [ ] Fedeltà delle 7 sezioni confermata (Step 4).
- [ ] Zero regressioni (Step 5).
- [ ] `siae-verification` eseguita (Step 6).

## Nota di scope (anti-over-scope)
Questo task verifica aderenza/allineamento dell'ARTEFATTO. Il monitoraggio dell'aderenza
*runtime* delle sessioni alle regole (compliance telemetry per-sessione/PR) è una feature
SEPARATA e più grande — fuori da questo piano per rispettare il vincolo "minimale".
Se la vuoi, va aperto un brainstorming dedicato.
