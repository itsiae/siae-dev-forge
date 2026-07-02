# Design — DevForge: convenzioni SIAE + fix di flusso

> **Fonte requisiti:** `requirements-devforge.md` (v0.1, 2026-07-01, Owner Core Platforms).
> **Backbone:** brainstorming → **[questo design]** → writing-plans → tdd → verification.
> **Stato:** in attesa di approvazione utente (Step 6b/gate).

## Contesto e obiettivo

Sei requisiti su DevForge, due cluster coerenti (nota trasversale spec riga 131):

- **CONTESTO** (REQ-01/02/06, P2): caricare convenzioni SIAE come contesto versionato.
- **COMPORTAMENTO** (REQ-03 P1, REQ-04 P2, REQ-05 P1): correggere difetti nel flusso.

Mappa del codice reale eseguita (5 agent Explore + 1 dedicato). Tutte le citazioni `file:riga` sotto derivano da ispezione diretta, non da memoria.

## Decisioni utente (AskUserQuestion, questa sessione)

1. **REQ-04** → *Lite-present + gate silente sui trivial*: il gate hook smette di nudge/block sugli edit trivial; la skill mantiene i 7 step con tier "Bassa" quasi-istantaneo; flag override *scoped+logged* (no bypass discrezionale).
2. **Contesto REQ-01/02/06** → *Bounded*: nuovi file canonici + puntatori dai punti che oggi hardcodano; **non** si riscrive il branch-flow delle 4 skill divergenti.
3. **Meccanismo contesto** → *Session-start hook injection*: i file canonici iniettati da `hooks/session-start` come `siae-global-rules.md`. Scelta consapevole (l'utente ha preferito la disponibilità garantita al costo di bloat; mitigazione: file lean).

---

## REQ-DF-01 — Ambienti/stage pipeline (P2)

**Decisione.** Nuovo file versionato `skills/using-devforge/reference/siae-environments.md` = fonte unica canonica dell'elenco ordinato ambienti/stage. Iniettato da `hooks/session-start` con **fallback esplicito** se assente.

**Valori canonici** (verificati da `siae-global-rules.md:8-48`, già team-reviewed — NON inventati):
- **Cloud/AWS** (datalake/IaC; marker `*.tf`, `terragrunt.hcl`, repo `datalake-*`/`*-iac`): valore tecnico `dev` → `qa` → `prod`; GitHub Environment `collaudo`/`certificazione`/`produzione`; deploy via reusable `terragrunt-*`.
- **SPORT/PAE/POP** (microservizi OpenShift; marker `pom.xml`+`mvnw`, `Dockerfile`, `chart/`): `sviluppo` → `collaudo` → `certificazione` → `produzione`; deploy via **git tag** (`git tag sviluppo|collaudo` + push) → OpenShift.
- **Regola anti-confusione (AC2):** `collaudo` = stage di test; `certificazione` = pre-produzione. Il file esplicita l'ordine e i due significati.

**Change sites.**
- `skills/using-devforge/reference/siae-environments.md` — **nuovo** (contenuto canonico, lean).
- `hooks/session-start:333-345` — aggiungere blocco di lettura mirror di quello `siae-global-rules.md`, MA con fallback esplicito: se `cat` fallisce, iniettare marker `[FONTE NON DISPONIBILE: elenco ambienti/stage SIAE — NON ipotizzare gli stage, dichiara l'assenza]` invece dell'empty-string silenzioso (soddisfa AC4).
- `skills/siae-onboarding/SKILL.md:166-174` (tabella `### 3.2 Ambienti` hardcoded + tag pattern sospetti `v*.*.*-dev.*`/`-rc.*`/`-cert.*`/`v*.*.*`) e `48-55` (blocco `.siae-config.json`, array `environments` a riga 52) → sostituire con puntatore alla fonte canonica; **rimuovere** i tag pattern non verificati (non propagare invenzioni). [citazioni corrette post spec-review]
- `skills/siae-onboarding/reference/factory-configs.md:98-105,178-198,239-245` → puntatore alla fonte canonica.

**AC mapping.** AC1 (ordine corretto da fonte)→file+injection; AC2 (collaudo≠certificazione)→sezione dedicata; AC3 (file versionato, non hardcoded)→nuovo file + rimozione hardcode onboarding; AC4 (dichiara se assente)→fallback esplicito session-start.

---

## REQ-DF-02 — Best practice PLAN e PLAN+DEPLOY (P2)

**Decisione.** Nuovo file `skills/using-devforge/reference/siae-plan-deploy.md`, iniettato a session-start.

**Disambiguazione obbligatoria (gotcha collisione nomi).** Il file apre chiarendo: *"PLAN"* qui = **pipeline infrastrutturale SIAE** (`terragrunt-plan.yaml` — plan; `cd-terragrunt-plan-deploy.yaml` — plan+deploy), **non** il "PLAN" interno DevForge (EnterPlanMode/`siae-writing-plans`).

**Contenuto** (composto da fonti verificate in-repo — `siae-global-rules.md:32-48`, `branching-strategy.md:19-22`):
- **PLAN** (checklist standard, AC1): terragrunt plan su ambiente target → review del plan output → nessun apply senza plan verde.
- **PLAN+DEPLOY** (AC2): progressione ambienti **senza salti** — cloud `dev→qa→prod`, microservizi `sviluppo→collaudo→certificazione→produzione`; nessun deploy verso `certificazione`/`produzione` senza il **gate** previsto (branching: solo `release/**`→`main`; produzione = merge su `main`).
- **Deviazioni** (AC4): il file istruisce a segnalarle esplicitamente, mai applicarle in silenzio.

**Change sites.**
- `skills/using-devforge/reference/siae-plan-deploy.md` — **nuovo**.
- `hooks/session-start` — blocco injection + fallback esplicito (come REQ-01).

**AC mapping.** AC1→sezione PLAN checklist; AC2→sezione progressione+gate; AC3 (documentate in fonte, caricate a inizio workflow)→file + injection (session-start = disponibile all'avvio); AC4→sezione deviazioni.

---

## REQ-DF-06 — Convenzione multi-repo iac/bff/spa (P2)

**Decisione.** Nuovo file `skills/using-devforge/reference/siae-multirepo.md`, iniettato a session-start.

**Contenuto** (ruoli dalla spec righe 19-21 — fonte = requisito stesso):
- `iac` → Infrastructure as Code (modifiche infra).
- `bff` → Backend for Frontend (API/backend).
- `spa` → Single Page Application (frontend).
- Regola di routing (AC1): infra→`iac`, API/backend→`bff`, frontend→`spa`; **mai** applicare modifiche nel repo sbagliato (AC2).
- Cross-cutting (AC4): nuovo endpoint con infra+consumo frontend → ripartire coerentemente sui tre repo.
- Riconoscimento (AC3): **convenzione naming a suffisso verificata sull'org `itsiae`** (`gh repo list itsiae`, 2026-07-01): `*-iac` (50+ repo), `*-bff` (13 repo), `*-spa` (9 repo). Triple complete che esemplificano lo split 3-repo: `jarvis-{iac,bff,spa}`, `rete-eventi-{core-iac,bff,spa}`, `routing-algorithm-{core-iac,bff,spa}`, `dataplatform-datacatalog-{iac,bff,spa}`. Segnale **secondario** via marker di stack/contenuto (iac = `*.tf`/`terragrunt.hcl`; bff = servizio backend API; spa = frontend `package.json`+router/build) così il riconoscimento non dipende solo dal nome. **Fonte grounding, NON invenzione** (fix BLOCK spec-review). Nota: SIAE usa anche `-be`/`-fe`/`-service` per microservizi SPORT/PAE — questo file documenta la convenzione `iac/bff/spa` come da REQ-DF-06, senza sovrascrivere le altre.

**Change sites.** file nuovo + injection session-start (+ fallback esplicito).

**AC mapping.** AC1→sezione routing; AC2→regola esplicita "non toccare il repo sbagliato"; AC3→sezione naming (suffisso org-verified + marker stack); AC4→sezione cross-cutting.

---

## Iniezione IBRIDA: session-start + momenti clou (REQ-01/02/06)

**Decisione utente (2ª AskUserQuestion).** Oltre alla baseline `session-start`, le convenzioni vanno **re-iniettate ai momenti clou**, iniettando **solo la sezione pertinente** (compatta, byte-budget) — non tutti e 3 i file. Riusa il pattern esistente `hooks/sport-task-detect` (UserPromptSubmit, rileva task e inietta) + `hooks/devforge-context` (banner compatto diff-deduped).

**Nuovo hook `hooks/convention-injector`** (UserPromptSubmit + PreToolUse:Bash/Edit/Write), 3 trigger (tutti confermati dall'utente):
1. **Task/PR di deploy** — segnale: keyword nel prompt (`deploy`, `collaudo`, `certificazione`, `terragrunt`, `make dev|qa`, `git tag`, `release`) o comando `gh pr create` → inietta `siae-environments` + `siae-plan-deploy` (ordine stage + gate).
2. **Edit IaC / contesto multi-repo** — segnale: Edit/Write su `*.tf`/`*.hcl`, o cwd/remote match `*-iac`/`*-bff`/`*-spa` → inietta `siae-multirepo` + `siae-environments`.
3. **Promozione ambiente** — segnale: comando `git tag sviluppo|collaudo`, o PR/merge verso `release`/`main` → inietta `siae-plan-deploy` (progressione senza salti + gate cert/prod).

Dedup via state-hash (come `devforge-context:22-43`) per non re-iniettare la stessa sezione ad ogni prompt. Budget: `head -c 1200` per sezione. Se il file canonico manca → marker "FONTE NON DISPONIBILE" (coerente con session-start). Questo copre l'esigenza REQ-02 "caricate come contesto **all'avvio del workflow**" meglio della sola session-start.

---

## REQ-DF-03 — Diff PR sul branch corretto (P1, bloccante)

**Problema.** ~11 siti hardcodano `origin/main`; nessuna troncatura del diff (root del loop/hang). L'algoritmo corretto (merge-base distance voting) esiste solo come prosa in `siae-finishing-branch`.

**Decisione.** Due helper condivisi nuovi + sostituzione mirata degli hardcode buggy (NON quelli release→main legittimi).

**Nuovi componenti.**
- `lib/pr-base-resolver.sh` — funzione `devforge_resolve_pr_base()`: precedenza (1) `gh pr view --json baseRefName` se una PR esiste; (2) merge-base distance voting su `origin/release/*` + `origin/sviluppo` (algoritmo di `siae-finishing-branch` Step 0b, `finishing-branch-checklist.md:79-83`); (3) `git symbolic-ref refs/remotes/origin/HEAD`; (4) `main` solo come ultimo fallback.
- `lib/diff-truncate.sh` — helper `devforge_diff_or_summary()`: se `git diff <base>...HEAD | wc -l` > soglia `DEVFORGE_MAX_DIFF_LINES` (default 2000), emette `--stat` + `--name-only` + primi N file, con nota "diff troncato, richiedi i file mancanti on-demand" → **prosegue** invece di bloccarsi (AC3).

**Change sites (bug — da fixare).**
- `lib/diff-risk-classifier.sh:16-20` — default `origin/main` → richiedere base esplicita o usare il resolver.
- `hooks/pr-blind-review-gate:115` e `hooks/pr-premortem-gate:~113` — usare l'output del resolver, non literal `origin/main`.
- `hooks/pr-gate:59-61` — sostituire catena `origin/sviluppo||origin/main||HEAD~1` con resolver; `:205-266` (heredoc iniettato all'agent) — riscrivere la prosa `git diff origin/main...HEAD` (righe 218/222) → istruzione a risolvere la base dinamicamente + guardia dimensione (usa `diff-truncate`).
- `hooks/post-commit-review:385,407` (heredoc REVIEW_INSTRUCTIONS) — riusare `default_branch`/`BASE_BRANCH` già calcolati nello stesso file (`:131-136`, `:176-181`) + guardia dimensione.
- `lib/review_evidence/collector.py:376-382` — invertire precedenza: `base` fornito prima del `rev-parse origin/main` hardcoded.
- `skills/siae-subagent-development/SKILL.md:303` — prompt fresh-eyes: `$PARENT_BRANCH` risolto + guida paginazione.

**Change sites (NON toccare — legittimi per branching strategy).** `skills/siae-release-risk`, `lib/release_risk/genesis.py` (default param), `regression_delta.py`, `cli.py:170,190` — diffano `release/**` vs `main`, che è corretto (solo release→main). **`hooks/pr-release-gate:71-73`** rientra qui (fix WARN spec-review): è raggiunto solo dopo il branch-gate `^release/` (`:44-48`) e `PR_BASE==main` (`:67`), quindi `origin/main` è corretto in produzione; sostituirlo con `$PR_BASE` cambierebbe solo la modalità test `DEVFORGE_RELEASE_RISK_ANY_PR=1` in modo indesiderato. Documentare tutti come release-scoped per evitare over-fix futuri.

**Config.** `DEVFORGE_MAX_DIFF_LINES` (default 2000) documentato in `hooks/ENV_VARS.md`.

**AC mapping.** AC1 (base = merge-base del target, non main)→resolver; AC2 (diff = solo modifiche del branch)→resolver corretto; AC3 (no loop, troncatura)→diff-truncate; AC4 (regressione branch non-main)→test con branch derivato da `sviluppo`/`release`.

---

## REQ-DF-04 — Brainstorming proporzionato alla complessità (P2)

**Problema.** 3 gate enforcano brainstorming; solo `brainstorming-gate` ha counter progressivo (1/2-3/4+). Segnale complessità = solo estensione file. "Zero eccezioni" asserito in 4 punti + test.

**Decisione (Lite-present).** Il gate smette di nudge/block su **trivial**; la skill mantiene il processo con profondità scalata; flag override *scoped+logged*.

**Definizione trivial (euristica configurabile, AC3):** 1 solo file toccato nel task AND ≤ `DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES` (default 15) righe cambiate AND estensione non-IaC (no `.tf`/`.hcl`) AND **path non-sensibile** — fuori da `hooks/`, `lib/` con `*gate*`, `lib/review_evidence/` (un edit piccolo a un gate/enforcement è alto-rischio → forza 'complesso', carve-out analogo a IaC; fix WARN spec-review). Complesso = multi-file OR IaC OR path-sensibile OR multi-repo → enforcement invariato (AC2).

**Change sites.**
- `lib/file-taxonomy.sh` — nuova `devforge_change_is_trivial(file_path, lines_changed)` (side-effect free, unit-testabile).
- `hooks/brainstorming-gate` — prima del counter (`:110-139`): (a) leggere flag override; (b) se trivial → short-circuit `{}` (no incremento, no nudge). Conteggio multi-file via set per-task `~/.claude/.devforge-task-skills/<task_id>/files_touched` (accumulo cross-invocazione, perché il hook vede 1 file per chiamata — gotcha #6); righe cambiate da `tool_input.old_string/new_string` (Edit) o `content` (Write).
- **Fix collaterale (gotcha #2):** `hooks/post-skill:190-202` resetta solo il counter legacy SID-anchored, non quello task-scoped → correggere reset anche del path task-scoped (bug noto).
- **Riconciliazione "zero eccezioni"** (evitare contraddizione skill↔hook, gotcha #3): `skills/siae-brainstorming/SKILL.md:50-63` (tabella Scaling) + `:20-46` (Legge di Ferro): riformulare da "il processo si esegue SEMPRE, zero eccezioni" → "la **profondità** scala; per i trivial il tier Bassa è quasi-istantaneo e il gate non forza". `lib/skills-core.js:421` e `tests/skill-activation/cases.yml:65-68` (caso config-change) allineati.
- `hooks/plan-gate` + `hooks/plan-gate-write` — **restano assoluti** (decisione): gatano EnterPlanMode / scrittura design-doc, atti che per un trivial l'agent semplicemente non compie. Documentato nel design.

**Flag override (AC4, no bypass — precedente PR #318).** `DEVFORGE_BRAINSTORM_COMPLEXITY` con valori `force-complex` | `force-trivial`, override della **classificazione** (non della Legge di Ferro), **loggato** via `devforge_log` a ogni uso (stile toolfail-breakglass). `force-trivial` NON bypassa l'enforcement per un cambiamento indipendentemente classificato complesso via un secondo segnale forte (IaC/multi-repo restano complessi). Documentato in `hooks/ENV_VARS.md`.

**Guard-test.** Nuovo test in `tests/test_no_discretionary_bypass.py` che asserisce il nuovo flag agisce solo sulla classificazione; nuovi scenari in `tests/hooks/brainstorming-gate.test.sh` (trivial no-nudge; multi-file/IaC nudge; force-complex; force-trivial non bypassa IaC).

**Memory.** Aggiornare `feedback_brainstorming_always.md` per riflettere la riconciliazione (profondità scala; trivial = gate silente) — evita drift nelle sessioni future (gotcha #8).

**AC mapping.** AC1 (trivial no full brainstorm)→short-circuit; AC2 (complesso attiva)→invariato; AC3 (soglia configurabile)→env var + euristica; AC4 (flag override precedenza)→flag scoped+logged.

---

## REQ-DF-05 — Apertura PR programmatica (P1)

**Problema (root cause verificate).**
1. **Bug timeout**: `review-evidence` attende ≤30s lock (`:287`/`:302-318`) ma `hooks.json:56-62` dichiara `timeout:20` → harness uccide il hook → **fail-closed spurio** su `gh pr create`.
2. `hooks/pr-gate:205-266` — linguaggio "gate bloccante" senza `decision:block` reale → l'agent tentenna/chiede.
3. Nessun guard di idempotenza in `siae-finishing-branch` (a differenza di `siae-release-pr-to-main:114-117`) → errore "PR already exists" grezzo → workaround manuale.
4. Manual-ask condizionati SOLO su disponibilità `gh` (FALLBACK_MODE) o Bash-denied, mai su "review non necessaria"; il "no review needed" è **razionalizzazione dell'agent** da `siae-git-workflow:124` ("su sviluppo review facoltativa").
5. Nessun path no-review/auto-merge: `siae-git-workflow:124` è inerte (non wired ai gate).

**Decisione (bounded, KISS — no GitHub native auto-merge).**
- **Fix bug timeout** [alto ROI]: allineare `hooks.json` timeout `review-evidence` a > attesa lock interna (o ridurre l'attesa < timeout dichiarato). Elimina i block spuri.
- **pr-gate linguaggio onesto**: la sezione dispatch review (`:205-266`) → prosa genuinamente *advisory* (non "gate bloccante" senza block), così l'agent procede con `gh pr create` invece di fermarsi.
- **Idempotenza**: `siae-finishing-branch` Step 5 (`finishing-branch-checklist.md:301-383`) → pre-check `gh pr list --head <branch> --state open --json number,url`; se esiste, ritorna URL, non ri-crea (AC + evita errori grezzi).
- **Programmatic-first**: `siae-git-env:105-116`, `finishing-branch-checklist.md:352-383,406-409`, `siae-requesting-review:221-233` → il default è `gh pr create` programmatico; il template manuale diventa **ultimo ricorso esplicito**; rimuovere il bias "assume FALLBACK safe default" (`siae-git-env:157-169`) e la razionalizzazione "review non necessaria → apri manuale".
- **No-review path (AC2)**: `pr-blind-review-gate` + `pr-premortem-gate` scalano ad **advisory** quando la base PR è `sviluppo` (review facoltativa SIAE), come il carve-out esistente `risk=low` (`pr-blind-review-gate:110-125`). **Meccanismo rilevamento base** (fix WARN spec-review): i gate sono PreToolUse su `gh pr create|edit` — la PR non esiste ancora, quindi NON si usa `gh pr view`; si fa il **parse di `--base`/`-B` dal `TOOL_COMMAND`** (riuso del parser cmd esistente se presente). Se `--base` è omesso (es. `--fill`) → default **strict** (non-advisory), perché il default repo è `main`. **Non** si tocca branch protection né si usa `gh pr merge --auto` (troppo rischioso/YAGNI). "No-review" = PR aperta programmaticamente senza prerequisito di review bloccante su `sviluppo`. `pr-gate` secret-scan e `review-evidence` quality restano attivi (secrets/regressioni contano sempre).
- **Doc**: `README.md:299-306` → aggiungere riga `pr-premortem-gate` mancante.

**Coordinamento con REQ-03.** `hooks/pr-gate:205-266` e `hooks/post-commit-review:373-419` sono toccati da REQ-03 (base dinamica) E REQ-05 (linguaggio) → un'unica edit coordinata per file.

**AC mapping.** AC1 (apre programmaticamente)→programmatic-first + fix timeout/linguaggio; AC2 (no-review → path corretto)→scaling advisory su base=sviluppo; AC3 (non chiede ripetutamente)→rimozione bias manual + idempotenza; AC4 (E2E su repo target)→test E2E su fixture.

---

## Approcci valutati (Step 4)

| Requisito | Alternative | Scelto | Motivo |
|---|---|---|---|
| Contesto | (a) skill-owned on-demand; (b) session-start injection; (c) ibrido indice | **(b)** | Decisione utente (disponibilità garantita) |
| REQ-03 | (a) fix inline per-sito; (b) helper condiviso `resolver`+`truncate` | **(b)** | Logica già triplicata; evita re-drift |
| REQ-04 | (a) full-skip; (b) lite-present | **(b)** | Decisione utente; onora memory + non reintroduce bypass |
| REQ-05 | (a) native auto-merge; (b) programmatic-first + advisory-on-sviluppo | **(b)** | KISS/YAGNI; native auto-merge = rischio branch-protection |

## Testing strategy

- **REQ-03**: unit su `pr-base-resolver.sh` (branch da main/sviluppo/release; PR esistente vs no) + `diff-truncate.sh` (sopra/sotto soglia); regressione hook con branch derivato da non-main.
- **REQ-04**: `tests/hooks/brainstorming-gate.test.sh` nuovi scenari; guard in `tests/test_no_discretionary_bypass.py`; `tests/skill-activation/cases.yml` allineato.
- **REQ-05**: unit idempotenza; test timeout coerente hooks.json↔review-evidence; E2E `gh pr create` su fixture (repo git locale con base non-main) verificando apertura programmatica senza ask manuale.
- **REQ-01/02/06**: test di guardia section-count sui nuovi file (stile `docs/plans/2026-06-24-siae-global-rules-injection/task-01`) + anti-leak grep (no email/IP/path personali) + test injection session-start (contenuto presente / fallback esplicito se file assente).

## Criteri di accettazione globali

- Tutti gli AC dei 6 REQ soddisfatti (mapping sopra).
- Zero regressioni: suite esistente verde + delta vs baseline citato.
- Nessun dato personale/segreto nei nuovi file versionati (grep anti-leak).
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` version bump allineati; CHANGELOG aggiornato.

## Stima SP (doppia scala)

| Cluster | Umano | AI-augmented |
|---|---|---|
| Contesto (REQ-01/02/06) | 3 | 1 |
| REQ-03 (diff/resolver/truncate) | 5 | 2 |
| REQ-04 (brainstorming complexity) | 5 | 2 |
| REQ-05 (PR flow) | 5 | 2 |
| **Totale** | **18** | **7** |

## Rischi / ADR

- **ADR-1**: session-start injection scelto nonostante bloat → mitigazione con **budget byte esplicito** per file (default `head -c 1800` cadauno, allineato a `GLOBAL_MEMORY_MAX_BYTES=2000` in `hooks/session-start:296`) + cap totale; se troncato, il marker lo dichiara. I 3 file sono lean per costruzione. Rivalutare se il context budget diventa critico (fix WARN spec-review).
- **ADR-2**: no-review path limitato a base=`sviluppo` advisory, niente native auto-merge → conservativo per branch protection.
- **ADR-3**: plan-gate/plan-gate-write restano assoluti (non complexity-aware) → coerente con "atti di planning esplicito".
- **Rischio**: 4 modelli branch/ambiente restano divergenti (scope bounded) → documentato, non risolto qui; follow-up separato.
