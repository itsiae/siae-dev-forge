# Design — Arricchimento eventi telemetria per qualità KPI (branch_created + has_tests)

- **Data:** 2026-06-12
- **Autore:** Lorenzo De Tomasi (+ DevForge)
- **Tipo:** Feature (telemetria producer, additivo)
- **Complessità:** Media (1 nuovo hook + estensione 1 hook)
- **Branch:** `feat/telemetry-kpi-enrichment`

## Contesto / Problema

Due KPI di Rosario soffrono di qualità del dato a monte:
- **KPI #3 (lead time):** oggi usa il proxy "primo commit del branch" (lower-bound; un
  branch aperto e lasciato fermo non si vede).
- **KPI #5 (has_tests):** copertura ~42%, e detection con pattern incompleti.

Verifica codice (3 agent + lettura diretta):
- `devforge_log` (`lib/logger.sh:499`) accetta `event_type` libero e inietta già a
  **ogni evento** top-level: `repo_root`, `project_canonical`, `repo_remote`, `branch`,
  `auth_email` (`logger.sh:553-557`).
- `has_tests` calcolato in `hooks/post-commit-review:55`, emesso a `:78` nel payload `commit_created`.
- `git rev-parse --abbrev-ref @{-1}` restituisce il base branch dopo `checkout -b`/`switch -c`
  (verificato empiricamente).

### Fuori scope (verificato, niente da fare lato plugin)
- **#5a "repo nel payload PR":** GIÀ SODDISFATTO — `pr_opened`/`pr_merged` portano già
  `repo_remote` + `project_canonical` + `branch` top-level. Il gap residuo (re-attribuzione
  author=bot dei mirror GitLab→GitHub) è 100% nella pipeline `github_collector.py` (BOT_REGEX),
  downstream. Nessuna modifica plugin necessaria.
- **Copertura 42% has_tests:** deriva da plugin vecchi sui client (emit incondizionato da 1.84.1,
  nessun gating versione). Forzare l'update = config server/S3, fuori scope plugin.

## Vincolo non negoziabile

**Additivo puro.** Nessuna modifica che alteri eventi/campi esistenti consumati dalla pipeline.
Solo: (a) nuovo evento `branch_created`; (b) nuovi campi nel meta di `commit_created`
(`tests_files_changed`) + ampliamento pattern di `has_tests`. Zero-loss telemetria invariato.
Coerente con [[feedback_telemetry_raw_only_additive]] (raw, additivo, no score derivati).

## Design

### Componente A — `#1` evento `branch_created` (nuovo hook `branch-tracker`)
- Nuovo `hooks/branch-tracker` (PostToolUse Bash). Entry in `hooks.json` nel matcher Bash PostToolUse.
- **Detect (compound-safe + flag-tollerante):** due fasi.
  1. `lib/cmd-parser.sh` `devforge_cmd_has_subcommand "$CMD" git checkout` || `git switch`
     (forma 2-token, come `pre-commit:76`): gestisce comandi compound/wrapper (`cd X && git checkout ...`).
     Se nessuna → exit 0.
  2. Estrai il nome target SOLO se c'è un flag di creazione branch (`-b`/`-c`/`--branch`),
     tollerando flag intermedi (es. `git checkout -q -b feature/x`):
     ```
     TARGET=$(printf '%s' "$CMD" | sed -nE 's/.*[[:space:]](-b|-c|--branch)[[:space:]]+([^[:space:]]+).*/\2/p' | head -1)
     [ -z "$TARGET" ] && exit 0    # nessun -b/-c → es. "git checkout main" → no evento
     ```
  NB: NON si usa la forma 3-token rigida `git checkout -b` (matcherebbe solo se `-b` è
  ESATTAMENTE il 3° token → fallirebbe su `git checkout -q -b`, il caso più comune emesso
  da tool/script). La protezione anti-falso-positivo è il guard sotto, non la posizione del flag.
- **Guard "branch effettivamente creato"** (gestisce comando fallito, es. `-b` su branch già
  esistente, dove PostToolUse scatta comunque): confronta `TARGET` con HEAD corrente.
  Emetti SOLO se combaciano:
  ```
  CUR=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
  [ "$CUR" = "$TARGET" ] || exit 0    # comando fallito o HEAD non cambiato → no evento
  ```
  Questo è ciò che esclude i falsi positivi (un `-b` spurio in un comando che non ha creato
  quel branch non avrà HEAD==TARGET).
- **Emissione:**
  - `base_branch=$(git rev-parse --abbrev-ref @{-1} 2>/dev/null || echo "")`
    (detached HEAD / nessun branch precedente → stringa vuota, non errore)
  - `devforge_log "branch_created" "success" "{\"base_branch\":\"<safe>\"}"`
  - `branch`, `repo_root`, `repo_remote` arrivano già top-level da `devforge_log` (NON duplicati nel meta).
- Best-effort non bloccante: ogni `git`/`devforge_log` con `2>/dev/null || true`.
- Consumo pipeline (downstream, non in questo design): join `branch` ↔ `PR.headRefName`
  già esistente → `lead_time = merged_at − branch_created.ts`.

### Componente B — `#3` has_tests robusto + tests_files_changed
- In `hooks/post-commit-review` (blocco `commit_created`, righe 53-78):
  - Pattern test ampliato: aggiungere `/__tests__/` e `conftest` all'alternation esistente
    `(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/|^test_|^tests/)`.
  - Nuovo `TESTS_FILES_COUNT=$(echo "$CHANGED_FILES" | grep -cE '<pattern>')` (gestione `|| true` + `${:-0}`).
  - Aggiungere `"tests_files_changed":<int>` nel payload `commit_created` (`:78`), accanto a `has_tests`.
- `has_tests` resta boolean (retrocompat); `tests_files_changed` è nuovo campo additivo.

### Flusso dati / errori
- `branch-tracker`: best-effort, ogni `git`/`devforge_log` con `2>/dev/null || true`; mai bloccante (PostToolUse).
- `post-commit-review`: invariata la struttura; solo 2 nuovi token nel regex + 1 campo JSON.
- Nessun nuovo path di rete; nessun impatto su zero-loss/outbox.

## Testing (TDD)

| # | Test | Atteso |
|---|------|--------|
| T1 | `branch-tracker` su `git checkout -b feature/x` da `main` | emette `branch_created`, meta `base_branch=main` |
| T2 | `branch-tracker` su `git switch -c feature/y` | emette `branch_created`, `base_branch` = branch precedente |
| T3 | `branch-tracker` su comando non-branch (`git status`, `git checkout main` su branch ESISTENTE) | nessun evento, exit 0 |
| T3b | `branch-tracker` su `git checkout -b X` FALLITO (X già esiste, HEAD non cambia) | nessun evento (guard HEAD≠target) |
| T3c | `branch-tracker` da detached HEAD: `git checkout -b feature` | evento emesso, `base_branch=""` (no errore) |
| T4 | `branch-tracker`: evento ha `branch`/`repo_remote` top-level (da devforge_log) | presenti, non duplicati nel meta |
| T5 | has_tests pattern: file `__tests__/a.test.ts` | `has_tests=true` |
| T6 | has_tests pattern: file `conftest.py` | `has_tests=true` |
| T7 | has_tests: commit senza test | `has_tests=false`, `tests_files_changed=0` |
| T8 | `tests_files_changed`: commit con 3 file test su 5 | `tests_files_changed=3`, `has_tests=true` |
| T9 | no-regression: payload `commit_created` esistente invariato salvo campo nuovo | campi pre-esistenti identici |

## Criteri di accettazione

1. `branch_created` emesso solo su creazione branch (`-b`/`-c`), con `base_branch` corretto; mai su altri comandi git.
2. Evento `branch_created` valido JSON, con `branch`/`repo_remote` top-level (no duplicazione nel meta).
3. `has_tests` copre anche `__tests__/` e `conftest`; nessun falso negativo sui pattern pre-esistenti.
4. `tests_files_changed` int coerente con il numero di file test nel diff del commit.
5. Eventi/campi esistenti invariati (additivo): la pipeline non si rompe (T9).
6. Nuovo hook portabile bash 3.2/macOS, best-effort non bloccante.

## Stima SP
- Umano: 5 SP · Augmented: 2 SP

## ADR
- **ADR-1:** `base_branch` via `@{-1}` (PostToolUse-only) vs pre-capture PreToolUse → `@{-1}` (no stato cross-hook, verificato). Detection flag-tollerante (`-b`/`-c`/`--branch` ovunque) + guard HEAD==TARGET: cattura anche `git checkout -q -b` (caso comune) senza falsi positivi. **Limite noto:** `git worktree add <path> -b <branch>` crea un branch ma è un'operazione git diretta non sempre mediata da Claude/PostToolUse → quel branch_created può non essere catturato. Accettato (caso raro nel flusso dev SIAE; il join PR resta valido perché la PR porta comunque headRefName).
- **ADR-2:** nuovo hook `branch-tracker` vs estendere `post-commit-review` → nuovo hook (checkout non cambia HEAD-commit → logica commit non scatta; separazione concern).
- **ADR-3:** #5a escluso dal bundle (già soddisfatto top-level); gap reale è pipeline BOT_REGEX (downstream).
