# Task 09 — Pulisci `ENV_VARS.md` + nuovo test doc↔code

**Goal:** Allineare `hooks/ENV_VARS.md` alle rimozioni (9 var + 2 state-file), documentare il nuovo breakglass tool-fail, e aggiungere un test doc↔code che verifica l'assenza delle 9 var rimosse (gap non coperto da `test_env_vars_doc_sync.py`, che copre solo `DEVFORGE_EVIDENCE_*`).

> Dipendenza: dopo Task 1-8 (il test grep-a il codice già ripulito).

## File coinvolti
- Modifica: `hooks/ENV_VARS.md`
- Nuovo test: `tests/test_no_discretionary_bypass.py` (o `.sh`)
- Registrazione: `tests/run-all.sh` (se i test bash vanno elencati lì)

## Step TDD

### Step 1 — Scrivi il nuovo test (test-first)
Crea `tests/test_no_discretionary_bypass.py` che:
1. Definisce la lista delle 9 var rimosse:
   `DEVFORGE_SKIP_BRAINSTORMING, DEVFORGE_SKIP_BLIND_REVIEW, DEVFORGE_SKIP_EVIDENCE, DEVFORGE_SKIP_RETRO_GATE, DEVFORGE_SKIP_GIT_GATE, DEVFORGE_FORCE_STOP, DEVFORGE_SKIP_PREMORTEM, DEVFORGE_SKIP_UPDATE, DEVFORGE_SKIP_TRAILER_HOOK`.
2. Per ogni var: grep ricorsivo nei file funzionali (`hooks/` extensionless, `lib/*.sh`) e asserisce **0 match** (nessun branch attivo).
3. Asserisce che `hooks/ENV_VARS.md` non contiene più nessuna delle 9 var.
4. Asserisce che `hooks/ENV_VARS.md` documenta il nuovo `DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS`.
5. Asserisce che i kill-switch OUT-of-scope sono ANCORA presenti nel codice: `DEVFORGE_ENFORCEMENT_OFF`, `DEVFORGE_USE_SESSION_SCOPE`, `DEVFORGE_RELEASE_RISK_DISABLED`, `DEVFORGE_BREAK_GLASS_REGEX` (regression guard: non li abbiamo rimossi per sbaglio).

### Step 2 — Esegui e verifica che fallisce
```bash
python3 -m pytest tests/test_no_discretionary_bypass.py -v
```
Output atteso: FALLISCE finché `ENV_VARS.md` non è ripulito (asserzioni 3-4).

### Step 3 — Pulisci ENV_VARS.md
In `hooks/ENV_VARS.md`:
- Rimuovi `DEVFORGE_SKIP_TRAILER_HOOK` dalla tabella "Attribuzione" (riga 32).
- Rimuovi dalla tabella "Per-gate bypass (tracked)" (righe 36-42): `DEVFORGE_SKIP_BRAINSTORMING`, `DEVFORGE_SKIP_GIT_GATE`, `DEVFORGE_SKIP_RETRO_GATE`, `DEVFORGE_SKIP_BLIND_REVIEW`, `DEVFORGE_FORCE_STOP`. Aggiungi nota: i gate brainstorming/git/retro/blind-review/premortem/verification non hanno più bypass discrezionale.
- Cerca e rimuovi la voce `DEVFORGE_SKIP_PREMORTEM` se documentata.
- Sostituisci la riga `DEVFORGE_SKIP_EVIDENCE` (riga 55) e la sezione "State file bypass primario" (righe 60-64) con la doc del nuovo breakglass tool-fail: `DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS=1` OR file `~/.claude/.devforge-evidence-toolfail` (`N=count`), **attivo solo sui 5 fallimenti di tooling**, mai sui verdetti di qualità.
- Aggiorna "Bypass behaviour" (righe 100-103): `BLOCK_REGRESSION` non più overridable da env (solo fix / `/forge-fix-evidence`).
- Rimuovi `DEVFORGE_SKIP_UPDATE` ovunque citato.
- Sezione "Abuse-tracking data files" (righe 203-208): rimuovi i 5 counter ora dead (`.devforge-bypass-count`, `.devforge-git-gate-bypass-count`, `.devforge-blind-review-bypass-count`, `.devforge-force-stop-count`, `.devforge-premortem-bypass-count`).

### Step 4 — Esegui e verifica che passa
```bash
python3 -m pytest tests/test_no_discretionary_bypass.py -v
python3 -m pytest tests/test_env_vars_doc_sync.py -v   # non deve regredire
```
Output atteso: entrambi PASS.

### Step 5 — Commit
```bash
git add hooks/ENV_VARS.md tests/test_no_discretionary_bypass.py tests/run-all.sh
git commit -m "docs(hooks): allinea ENV_VARS.md + test doc-code per bypass rimossi"
```

## Criteri di accettazione
- [ ] `ENV_VARS.md` non contiene nessuna delle 9 var rimosse.
- [ ] `ENV_VARS.md` documenta `DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS`.
- [ ] `test_no_discretionary_bypass.py` PASS (codice + doc puliti, kill-switch preservati).
- [ ] `test_env_vars_doc_sync.py` non regredisce.
