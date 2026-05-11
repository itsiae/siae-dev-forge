---
title: Skill Alignment & Anti-Dilution Reinforcement
date: 2026-05-03
author: Lorenzo De Tomasi
status: draft
related_prs: [#215, #216, #217]
follow_up_prs: [PR-anti-dilution-4, PR-anti-dilution-5, PR-anti-dilution-6]
sp_human: 30
sp_augmented: 13
---

# Skill Alignment & Anti-Dilution Reinforcement

## 1. Contesto & problema

Il marketplace DevForge contiene 37 skill + 5 agent. Una review di questa sessione (audit interno + ricerca Anthropic best practice) ha rilevato:

**Findings (severity)**:
- 3 CRITICAL: backbone leakage (`sport-*`, `PRODUZIONE` hardcoded in `service-logic-map`, `microservices-map`, `git-workflow`); instruction bloat (`debugging` 420 righe, `brainstorming` 215); trigger overlap senza sequenza esplicita (brainstorm vs architecture, debugging vs verification, finishing vs git-workflow).
- 7 MAJOR: tdd trigger keyword overload (>20), verification overprescriptive tone (7+ "ALWAYS/NEVER" in 60 righe), git-workflow tag SIAE-specific, service-logic-map accorpa 2 modalità, cross-ref non validati, agent senza tool whitelist.
- 3 MINOR: AWS-bias in debugging examples, description oversize in service-logic-map, JIRA inline in brainstorming.

**Problema gemello — under-triggering**: feedback utente diretto "molte skill non vengono chiamate". Cause probabili:
1. Description frontmatter non in pattern Anthropic raccomandato `Use when X. Trigger: ...`
2. Trigger keyword troppo SIAE-specifici → non matchano language naturale utente
3. Description verbose → coda ignorata dal modello
4. Verbi in seconda persona ("guida lo sviluppo") invece terza ("use when developing")
5. Scope ambiguo → modello sceglie "non chiamare"

**Best practice Anthropic rilevanti** (fonti: code.claude.com, anthropic.com/engineering, anthropics/skills):
- SKILL.md <500 righe (target: <200 per skill backbone)
- Description ≤1024 char, terza persona, "un po' pushy"
- Progressive disclosure: metadata sempre in memory, body on-demand, reference solo durante esecuzione
- Single responsibility per skill
- Hook PreToolUse/PostToolUse per enforcement deterministico (NO campo `requires:` ufficiale nel frontmatter)
- Subagent tool whitelisting via `tools: [...]` array
- Plugin namespace prefisso obbligatorio per evitare collision con built-in skill ([issue #33080](https://github.com/anthropics/claude-code/issues/33080))

**Vincolo utente**: zero blocco produttività. Niente hook che bloccano con exit 2.

## 2. Decomposizione in 3 PR

| PR | Sub-problemi | Tipo cambio | Risk | SP-Augmented |
|---|---|---|---|---|
| **PR-4** Backbone hardening | A leakage strip + B progressive disclosure (5 skill bloat) + I-1 description rewrite backbone (8 skill core) | edit testuale + extract `reference/` | basso | 8 |
| **PR-5** Discovery & advisory | I-2 description audit 37 skill + G hook PostToolUse advisory + E verification tone-down + suite test attivazione Bedrock | hook nuovo + 37 frontmatter | medio | 3 |
| **PR-6** Polish | D tdd trigger reduction + F service-logic-map disambiguazione + H subagent tool whitelist + C sequenza in description | breaking minore | medio | 2 |

**Stime totali rivise**: 30 SP-Umano / 13 SP-Augmented (era 18/7; aumento dovuto al bloat scoperto in 3 skill aggiuntive: writing-plans 422, executing-plans 344, finishing-branch 520).

**Ragione split**: A+B sono editing verificabile via diff. G+I-2 cambia behaviour del modello su trigger ambigui (test suite necessaria per evitare regressioni). F è breaking change consumer skill.

## 3. PR-4 — Backbone hardening

### 3.1 A — Strip backbone leakage (3 file)

| File | Cambio |
|---|---|
| `skills/siae-service-logic-map/SKILL.md:10` | rimuovi `"modifica su sport-*/pop-*/pae-*"` → `"modifica su servizio business-critical"` |
| `skills/siae-microservices-map/SKILL.md:6` | rimuovi `"mappa SPORT"` → `"mappa sistema a microservizi"` |
| `skills/siae-git-workflow/SKILL.md:134` | parametrizza `PRODUZIONE`/`CERTIFICAZIONE` → placeholder `<PROD_TAG>`/`<CERT_TAG>` con esempio SIAE come fallback |

Validazione: `grep -rE "sport-\*|pop-\*|pae-\*|PRODUZIONE|CERTIFICAZIONE" skills/siae-{brainstorming,debugging,verification,tdd,using-devforge,writing-plans,executing-plans,finishing-branch,service-logic-map,microservices-map,git-workflow}/` → 0 match.

### 3.2 B — Progressive disclosure (5 skill bloat)

**Baseline backbone (8 skill) misurata 2026-05-03**:

| Skill | Righe attuali | Status | Target |
|---|---|---|---|
| using-devforge | 90 | ✓ ok | mantiene |
| siae-tdd | 179 | ✓ ok | mantiene |
| siae-verification | 179 | ✓ ok | mantiene |
| siae-brainstorming | 214 | ✗ bloat lieve | <180 |
| siae-executing-plans | 344 | ✗ bloat | <200 |
| siae-writing-plans | 422 | ✗ bloat | <200 |
| siae-debugging | 428 | ✗ bloat critico | <200 |
| siae-finishing-branch | 520 | ✗ bloat critico | <200 |

**Score baseline**: 3/8 sotto 200 righe. Target post-PR-4: 8/8.

**`skills/siae-debugging/SKILL.md`** (428 → <200):
- Estrai 4 fasi dettagliate in `reference/debugging-phases.md`
- Estrai tabella anti-rationalization in `reference/debugging-anti-rationalization.md`
- Estrai CloudWatch integration in `reference/debugging-cloudwatch.md`
- SKILL.md mantiene: gate, 4 fasi summary (1 riga ciascuna con link a reference), legge di ferro, output checkpoint format

**`skills/siae-finishing-branch/SKILL.md`** (520 → <200):
- Estrai pre-flight checklist in `reference/finishing-branch-checklist.md`
- Estrai casi specifici (revert, hotfix, squash) in `reference/finishing-branch-scenarios.md`
- SKILL.md mantiene: HARD-GATE, sequenza step principali, REQUIRED SUB-SKILL list

**`skills/siae-writing-plans/SKILL.md`** (422 → <200):
- Estrai template task bite-sized in `reference/writing-plans-task-template.md`
- Estrai pattern subagent-development integration in `reference/writing-plans-execution-handoff.md`
- SKILL.md mantiene: HARD-GATE, processo decomposizione, gate transizione

**`skills/siae-executing-plans/SKILL.md`** (344 → <200):
- Estrai dettaglio worktree setup in `reference/executing-plans-worktree.md`
- Estrai checkpoint sync con writing-plans in `reference/executing-plans-sync.md`
- SKILL.md mantiene: HARD-GATE, esecuzione step-by-step, batch logic

**`skills/siae-brainstorming/SKILL.md`** (214 → <180):
- Estrai checklist 7 punti dettagliata in `reference/brainstorming-checklist.md`
- Estrai JIRA integration in `reference/brainstorming-jira.md`
- SKILL.md mantiene: HARD-GATE, scaling table, 7 punti summary, checkpoint format

**Stima SP rivista PR-4**: 5 → **8 SP-Augmented** (era 2; aumenta per +3 skill bloat extract).

### 3.3 I-1 — Description rewrite backbone (8 skill)

Pattern target: `<Cosa fa>. Use when <trigger>. Examples: <2-3 esempi>.`

Skill backbone (8): brainstorming, tdd, debugging, verification, writing-plans, executing-plans, finishing-branch, using-devforge.

Esempio prima/dopo `siae-debugging`:
- **Prima**: "Esegue root cause investigation prima di proporre qualsiasi fix. Trigger: bug, errore, incident, test che fallisce, comportamento inatteso, eccezione, stacktrace, crash, errore di compilazione, build failure, 500, timeout, NullPointerException, TypeError, non funziona, rotto, fallisce, non va."
- **Dopo**: "Use when investigating a bug, error, or unexpected behaviour before proposing a fix. Forces 4-phase root cause analysis (reproduce → hypothesize → verify → fix). Examples: 'NPE su /endpoint', 'test fallisce in CI', 'comportamento non atteso in produzione'."

Trigger keyword count target: 5-8 per skill (vs 20+ attuali).

### 3.4 Criteri accettazione PR-4

- `find skills/siae-{8-backbone} -name 'SKILL.md' -exec wc -l {} \;` → tutte <200 righe
- 0 match grep leakage SIAE-specific in backbone
- 8/8 description backbone in pattern "Use when X"
- Tutti reference file linkati esistono e sono raggiungibili
- 0 cross-reference rotte: `grep -rE 'REQUIRED SUB-SKILL: siae-[a-z-]+' skills/` → tutti file referenziati esistono

## 4. PR-5 — Discovery & advisory

### 4.1 I-2 — Description audit 37 skill

Per ogni skill in `skills/`:
1. Leggi frontmatter `description`
2. Verifica: pattern "Use when X" presente, length ≤1024 char, trigger keyword 5-12, terza persona, no SIAE-specifics non necessari
3. Se non conforme: riscrivi seguendo template

Output dell'audit: `docs/measurements/skill-description-audit-2026-05-03.md` con tabella before/after per ogni skill.

### 4.2 G — Hook PostToolUse advisory (no-block)

Nuovo file `hooks/skill-advisory.sh`:
- Trigger: `PostToolUse` event con matcher `Skill`
- Logica: legge `.claude/projects/<project>/.skill-state` (JSON con `last_brainstorm_completed`, `last_debug_phase`, `last_tdd_cycle`); se utente sta per chiamare skill X senza prerequisito Y, emette `additionalContext` con suggerimento (max 2KB)
- ESEMPIO: chiama `siae-verification` ma `.skill-state` non ha `last_brainstorm_completed` → output `"Suggerimento: la verifica si applica DOPO un fix completato. Se stai aprendo nuova feature, valuta siae-brainstorming."`
- NON blocca (exit 0 sempre), solo nudge

State file scrittura: hook `PostToolUse` di brainstorming/debugging/tdd updata `.skill-state` quando completano fasi.

Location decisione: **`.claude/projects/<project>/.skill-state`** (per-project, non cross-progetto). Motivazione: workflow gate è project-scoped (un brainstorm in repo A non rilascia gate in repo B).

### 4.3 E — Verification tone-down

`skills/siae-verification/SKILL.md`:
- Riduci 7+ "ALWAYS/NEVER/MANDATORY" → max 3 (uno nella legge di ferro, uno nel HARD-GATE, uno nel summary)
- Aggiungi sezione "Eccezioni & proporzionalità": typo fix, comment-only change, doc update non richiedono full verification battery
- Tono: da "Stop, never, mandatory" a "Verifica adeguata al rischio del cambio"

### 4.4 Suite test attivazione (Bedrock)

**Struttura**:
```
tests/skill-activation/
  cases.yml              # 30 prompt rappresentativi
  run.sh                 # runner Bedrock Haiku 4.5
  evaluator.py           # parser output Claude → match expected
  baseline-2026-05-03.md # snapshot pre-PR
  README.md              # come eseguire, cost cap
```

**Format `cases.yml`**:
```yaml
- id: bug-fix-NPE
  prompt: "ho un NPE su /detailLocale, fixiamo"
  expected_primary: siae-debugging
  expected_chain: [siae-debugging, siae-tdd, siae-verification]
  forbidden: []

- id: new-feature-design
  prompt: "voglio aggiungere un campo a DichiarazioneEventoDTO"
  expected_primary: siae-brainstorming
  expected_chain: [siae-brainstorming, siae-service-logic-map, siae-writing-plans]
  forbidden: [siae-tdd]  # non saltare a TDD senza design

- id: pr-ready
  prompt: "il fix funziona, sono pronto per PR"
  expected_primary: siae-verification
  expected_chain: [siae-verification, siae-finishing-branch, siae-requesting-review]
  forbidden: []
```

30 prompt totali distribuiti: 8 bug/debug, 8 feature/design, 6 verification/PR, 4 architecture/microservices, 4 misc (frontend, IaC, security).

**Runner `run.sh`** (Bedrock Sonnet 4.6 di default, Haiku 4.5 fallback per cost-tight runs):
```bash
#!/usr/bin/env bash
set -euo pipefail
export AWS_REGION=eu-west-1
export CLAUDE_CODE_USE_BEDROCK=1
# Default: Sonnet 4.6 (skill routing realistico = stesso modello Claude Code default)
# Override: TEST_MODEL=haiku per cost-tight runs (esplorazione, iterazioni rapide)
case "${TEST_MODEL:-sonnet}" in
  sonnet) export ANTHROPIC_MODEL="eu.anthropic.claude-sonnet-4-6-20250929-v1:0" ;;
  haiku)  export ANTHROPIC_MODEL="eu.anthropic.claude-haiku-4-5-20251001-v1:0" ;;
  *) echo "TEST_MODEL must be sonnet|haiku"; exit 2 ;;
esac
: "${AWS_BEARER_TOKEN_BEDROCK:?missing}"

REPORT="tests/skill-activation/report-$(date +%F).md"
echo "# Skill Activation Report $(date +%F)" > "$REPORT"

while IFS= read -r case_yaml; do
  prompt=$(yq '.prompt' <<< "$case_yaml")
  id=$(yq '.id' <<< "$case_yaml")
  # invoca Claude Code in --print mode, capture skill invocata
  output=$(echo "$prompt" | claude --print --max-turns 1 2>&1 | head -50)
  python3 evaluator.py "$id" "$output" >> "$REPORT"
done < <(yq -o=json '.[]' tests/skill-activation/cases.yml | jq -c '.')
```

**Cost cap & stima**:
- Sonnet 4.6 (default): ~$0.04 per run (30 prompt × 250 token); 50 run iterativi ≈ $2.00
- Haiku 4.5 (fallback): ~$0.014 per run; 50 run iterativi ≈ $0.70
- Budget hard-stop a $5 via CloudWatch alarm su account Bedrock
- Runner exit early se rate limit / 4xx
- Run manuale, NON in CI automatico (controllo costi esplicito utente)

**KPI**:
- `activation_accuracy` = (% case con `expected_primary` matched correttamente)
- `chain_completeness` = (% case con tutti `expected_chain` evocati)
- `forbidden_rate` = (% case che evocano skill in `forbidden`, deve essere 0)

Baseline pre-PR misurata su `main`, target post-PR-5: accuracy ≥75%, completeness ≥60%, forbidden ≤5%.

### 4.5 Criteri accettazione PR-5

- 37/37 description in pattern "Use when X" (verificabile via grep)
- Hook `skill-advisory.sh` registrato in `.claude/settings.json` PostToolUse
- State file `.skill-state` scritto da brainstorming/debugging/tdd hook PostToolUse
- Report baseline + report post-PR pubblicati in `tests/skill-activation/`
- accuracy post ≥ baseline +15pp

## 5. PR-6 — Polish

### 5.1 D — tdd trigger reduction

`skills/siae-tdd/SKILL.md` frontmatter line 6-8:
- Da: 20+ keyword ("implementa", "codifica", "sviluppa", "scrivi funzione", ...)
- A: 5-8 mirate ("test-driven development", "TDD per feature nuova", "scrittura test prima del codice", "Red-Green-Refactor")

### 5.2 F — service-logic-map disambiguazione (NO split)

Decisione: NON splittare. Mantieni unica skill ma:
- Frontmatter `description`: distingui esplicitamente le due modalità ("Modalità A: build catalog L1+L2+L3 multi-cluster. Modalità B: pre-flight MCP single-task per impact analysis. Use when: ..." con trigger separati)
- Body: aggiungi sezione "Quale modalità scegliere" con flowchart 3 domande

Motivazione no-split: split rompe consumer skill (writing-plans, executing-plans referenziano `siae-service-logic-map`); cost > beneficio.

### 5.3 H — Subagent tool whitelist (5 agent)

Aggiungi `tools:` array a ognuno:

| Agent | Tools whitelist | Rationale |
|---|---|---|
| `code-reviewer` | `[Read, Bash, Grep, Glob]` | review = read-only, no Write/Edit |
| `spec-reviewer` | `[Read, Bash, Grep]` | confronta spec vs code, read-only |
| `mcp-impact-analyst` | `[Read, Bash, mcp__sport-kg__*, ToolSearch]` | KG queries + grep, no Write |
| `qa-investigator` | `[Read, Bash, Grep, mcp__sport-kg__*, mcp__elasticsearch__*, ToolSearch]` | 3-stage investigation, no Write |
| `doc-generator` | `[Read, Bash, Write, Edit, Grep, Glob, mcp__atlassian__*]` | scrive doc + pubblica Confluence |

### 5.4 C — Sequenza in description (advisory)

Aggiungi nel description di skill che hanno prerequisito comune:
- `siae-verification`: "Use when verifying a fix or change is complete. Best after: siae-debugging completed or siae-tdd cycle done."
- `siae-architecture`: "Use when evaluating architectural pattern choice. Best after: siae-brainstorming Step 4 (options proposed)."
- `siae-finishing-branch`: "Use when preparing branch for PR. Best after: siae-verification passed."

NB: non blocca (advisory). L'enforcement reale è via hook G.

### 5.5 Criteri accettazione PR-6

- tdd trigger keyword ≤8
- service-logic-map description distingue 2 modalità
- 5/5 agent con `tools:` array popolato
- 3+ skill con sequence hint in description

## 6. Test, rollback, KPI globali

### 6.1 Strategia test

| Tipo | Cosa | Quando |
|---|---|---|
| Unit | Hook bash con shellcheck + test funzioni isolate | PR-5 |
| Integration | Plugin install in worktree pulito + invoca 5 skill core, verifica reference link risolti | PR-4, PR-5, PR-6 |
| Activation | Suite Bedrock 30 prompt | baseline pre-PR + post ogni PR |
| Manual smoke | Apri Claude Code session, esegui 3 task tipici (bug, feature, PR), osserva skill invocate | post ogni PR |

### 6.2 Rischi & Mitigazioni

| # | Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|---|
| R1 | Hook PostToolUse advisory genera rumore (false positive nudge che spammano context) | media | medio | KPI `nudge_signal_to_noise` su sample manuale 50 prompt post-PR-5; threshold 0.7+; se <0.7, alza soglia matcher |
| R2 | Description rewrite (PR-4 + PR-5) causa regressione skill già funzionanti | media | alto | Baseline Bedrock pre-PR-5 + diff accuracy per skill; rollback granulare per skill se accuracy cala >10pp |
| R3 | State file `.skill-state` corrotto/disallineato | bassa | medio | Hook robusto a parse error con fallback a stato vuoto; reset automatico se JSON invalido; no blocco user su corruzione |
| R4 | Cost cap Bedrock superato durante iterazioni test | bassa | medio | CloudWatch alarm hard-stop $5; runner exit early su 4xx/rate limit; preferenza Haiku per esplorazioni |
| R5 | tdd trigger keyword reduction (PR-6 D) → utenti che usavano keyword rimosse non triggerano più | media | basso | Lista keyword removed in CHANGELOG plugin; smoke test pre-merge con 10 prompt che usano vecchie keyword; documentare migration path |
| R6 | Hook `PostToolUse` matcher su skill name non supportato (gap docs vs runtime) | media | alto | Verifica empirica in PR-5 via prototipo bash isolato prima di scrivere test suite; fallback su `UserPromptSubmit` matcher se PostToolUse non matcha skill events |
| R7 | Progressive disclosure rompe UX skill (utenti devono navigare reference file durante uso) | bassa | medio | SKILL.md mantiene tutto il "decisional content" inline; reference contiene solo deep dive opzionali; link relativi che IDE risolve |
| R8 | Test suite attivazione produce risultati instabili (Sonnet/Haiku scelgono skill diverse run-to-run) | media | medio | Run ogni caso 3 volte, media majority vote; flag come "instabile" caso con varianza alta; usare temperature 0 in chiamate Bedrock |

### 6.3 Rollback

Ogni PR isolata, file-level reversibile:
- PR-4: `git revert` ripristina backbone originale (no migrazione dati)
- PR-5: rimuovi hook in settings.json + revert frontmatter (state file persiste ma ignorato)
- PR-6: revert frontmatter + tools array

### 6.4 KPI globali (post tutte le 3 PR)

| KPI | Baseline | Target |
|---|---|---|
| `activation_accuracy` (suite Bedrock) | da misurare PR-5 step 1 | +15pp |
| `chain_completeness` | da misurare PR-5 step 1 | +10pp |
| `backbone_skills_under_200_lines` | 3/8 | 8/8 |
| `description_pattern_compliance` ("Use when X") | da misurare PR-5 audit | ≥33/37 |
| `agent_tool_whitelist_coverage` | 0/5 | 5/5 |
| `backbone_leakage_grep_match` | 3 file | 0 file |
| `backbone_dogmatic_keyword_count` (verification) | 7+ | ≤3 |
| `nudge_signal_to_noise` (PR-5 hook advisory) | n/a | ≥0.7 |

## 7. JIRA ticket output

```
Tipo: Story
Sommario: DevForge — Skill alignment & anti-dilution reinforcement (PR-4, PR-5, PR-6)
Story Points: 18 SP-Umano / 7 SP-Augmented
Labels: anti-dilution, skill-alignment, devforge, backbone

Descrizione:
Reinforcement del backbone DevForge per ridurre dilution e migliorare auto-invocazione delle skill (problema riportato: "molte skill non vengono chiamate"). 3 PR sequenziali. Vincolo: zero blocco produttività utente, hook solo advisory.

Acceptance Criteria:
- [ ] PR-4: backbone <200 righe, leakage SIAE-specific eliminato, description backbone in pattern Anthropic "Use when X"
- [ ] PR-5: 37/37 description audit completato, hook PostToolUse advisory attivo, suite test attivazione Bedrock con report baseline e post
- [ ] PR-6: agent tool whitelist 5/5, service-logic-map disambiguato, sequence hint advisory in 3+ skill
- [ ] Suite test attivazione: accuracy +15pp vs baseline
- [ ] Cost test Bedrock <$5 totale (Haiku 4.5)
- [ ] Zero regressione: skill backbone restano invocabili sui prompt esistenti
```

## 8. Decisioni architetturali (ADR)

| # | Decisione | Alternativa scartata | Motivazione |
|---|---|---|---|
| 1 | Hook PostToolUse advisory (no-block) | Hook PreToolUse con exit 2 | Vincolo utente "zero blocco produttività" |
| 2 | State file per-project `.claude/projects/<project>/.skill-state` | File globale `~/.claude/devforge-skill-state.jsonl` | Workflow gate è project-scoped |
| 3 | Test runner Bedrock Sonnet 4.6 default (Haiku 4.5 fallback) | Bedrock Opus 4.5 | Sonnet = stesso modello Claude Code default, test realistici; Opus 5x più costoso senza beneficio per skill routing |
| 4 | NO split service-logic-map | Split in 2 skill | Cost > beneficio (rompe consumer skill) |
| 5 | Description pattern "Use when X" terza persona | Mantieni stile italiano "Guida lo sviluppo" | Anthropic best practice esplicita per discovery |
| 6 | Progressive disclosure via `reference/` files | Mantieni inline + comprimi | Pattern ufficiale Anthropic (engineering blog) |
| 7 | 3 PR sequenziali | 1 PR consolidata | Risk isolation: PR-5 cambia behaviour modello, va isolata per A/B test |
| 8 | **No-regression principle** — ottimizzazione preserva comportamento esistente | Refactoring aggressivo che ridefinisce trigger | Vincolo utente esplicito: "ottimizzare skill, non rompere comportamenti". Test attivazione baseline pre-PR DEVE passare anche post-PR. Skill che oggi si attivano correttamente devono continuare a farlo |

### 8.1 Principio operativo no-regression (ADR-8)

**Regola**: ogni cambiamento (description rewrite, progressive disclosure, trigger reduction) DEVE preservare i comportamenti di attivazione esistenti. Solo aggiunte di copertura sono accettabili (skill che oggi NON si attivano e dovrebbero, devono iniziare ad attivarsi). Mai sottrazione di copertura.

**Implementazione**:
1. Baseline activation accuracy misurata PRIMA di ogni PR via suite Bedrock
2. Per ogni skill, accuracy post-PR ≥ accuracy pre-PR (zero degradazione per-skill)
3. Se diff accuracy per qualsiasi skill cala, **revert granulare** della modifica su quella skill, indagine, fix mirato
4. CHANGELOG plugin documenta esplicitamente keyword/trigger removed (PR-6 D in particolare) con migration path
5. Skill che oggi sono "core" e si attivano (anche se sub-ottimalmente) restano attive — l'ottimizzazione è additiva, non sottrattiva

## 9. Riferimenti

- [Claude Code Plugins](https://code.claude.com/docs/en/plugins)
- [Claude Code Hooks Reference (32 events)](https://code.claude.com/docs/en/hooks)
- [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)
- [Anthropic Engineering: Equipping Agents with Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [GitHub Issue #33080 — Skill Collision](https://github.com/anthropics/claude-code/issues/33080)
- [anthropics/skills repo](https://github.com/anthropics/skills)
- Memory: `feedback_subagent_mcp_tool_loading.md`, `feedback_core_skills_project_agnostic.md`, `feedback_env_var_not_propagated_to_hooks.md`
