# Design — Recezione cambi semantici sport-kg v2 nei 4 agent DevForge

**Data**: 2026-05-03
**Autore**: Lorenzo De Tomasi + Claude (siae-brainstorming)
**Stato**: Draft → in review (iterazione 2 dopo spec-review)
**Branch**: `feat/agents-sport-kg-v2-recezione`
**Rischio**: 🟡 MEDIO — modifica testuale a 4 agent prompt; impatto observable su qualità output downstream skill chiamanti

---

## 1. Contesto

Tra **2026-04-28 e 2026-04-30** sport-kg ha mergeato 13 PR (Onde 1-10 + KG v2 D1-D5 logical soundness, PR #23 mergiata in `main` 2026-04-30). I cambi rilevanti per gli agent DevForge:

### 1.1 Tool MCP nuovi (totale 9 nuovi + 1 promosso)

| Origine | Tool | Note |
|---------|------|------|
| **D3** | `graph_consistency_check` | Drift KG↔ES (auth/DTO/schedule) |
| **D3** | `alternate_hypotheses` | Ipotesi ranked per evidence ambigua |
| **D3** | `expand_transitive` | Multi-hop relation-specific (out-of-scope agent — vedi § 13) |
| **D3** | `graph_staleness_report` | Nodi oltre TTL bucket |
| **Onda 6** | `list_rules` | Enumera Drools BusinessRule (22.257 rules) |
| **Onda 6** | `describe_rule` | Dettaglio rule (package, salience, conditions, actions) |
| **Onda 6** | `impact_of_rule_change` | Blast-radius modifica rule |
| **Onda 9** | `who_authenticates` | IdP primary + additional + M2M registrati |
| **Onda 10** | `find_batch_for_keyword` | Discovery BatchJob (@Scheduled) per keyword |
| **Onda 7** | `answer_impact_question` | Orchestrator rule-based (già nel frontmatter mcp-impact-analyst, da promuovere a fallback documentato) |

### 1.2 Cambi semantici cross-tool

- **Envelope D1 additivo** su tutti i 30 tool: campi `inference_type`, `observed_at`, `ttl_hint_seconds`, `falsifiable_by`, `meta`
- **Enum status v2 (D2)**: `CONFIRMED` / `PARTIAL` / `NOT_FOUND_IN_INDEX` / `PROVEN_ABSENT_UNDER_SCOPE` / `REFUTED` (vs binario v1) + `scope_completeness`
- **Mapping v1→v2 (D2 § 2.3)**: `"NOT_EXISTS"` → `NOT_FOUND_IN_INDEX`; `"REFUTED"` legacy → `NOT_FOUND_IN_INDEX` + log warn
- **Split `*_prove_absent`** per disambiguare "non trovato" vs "dimostrato assente"
- **Nuovi nodi nel grafo**: `BusinessRule`, `BatchJob` (@Scheduled), `ExternalSystem` con principals M2M (es. `CONCERTINI_M2M_CONC`)

**Backward compatibility**: dual-format envelope D1 per 60 giorni (deprecation finestra 28-apr → 27-giu).

### 1.3 Onde non rilevanti per gli agent (rationale esplicito)

| Onda | Cambio | Perché non rilevante |
|------|--------|----------------------|
| Onda 1 | `describe_table` + `who_calls` dormancy fix | `who_calls` già usato dagli agent, dormancy fix è internal — output stesso shape |
| Onda 2 | Evidence layer + ExternalSystem | ExternalSystem coperto in § 1.2 sopra |
| Onda 3 | Quality actions | Lato ingestion, no impact su tool MCP |
| Onda 4 | AUTHENTICATES_VIA chain | Esposto via Onda 9 `who_authenticates` (incluso) |
| Onda 5 | Oracle schema columns in `describe_table` | **Possibile impatto su doc-generator** se documenta DB schema — vedi § 6.3 |
| Onda 8 | Mule schema adapter | Lato ingestion |

### 1.4 Stato attuale agent

I 4 agent DevForge che usano sport-kg (`agents/{mcp-impact-analyst,qa-investigator,doc-generator,code-reviewer}.md`) hanno **tutti** un Step 0 — Tool Loading con `ToolSearch query="select:..."` bulk pre-caricamento. Nessuno ha `tools:` esplicito nel frontmatter (pattern dynamic loading, non lista statica).

I bulk loading attuali NON includono i tool elencati in § 1.1. Questo è il gap principale.

## 2. Obiettivi

- Estendere il **bulk loading Step 0 esistente** dei 4 agent con i tool sport-kg v2 rilevanti per il loro ruolo (no nuove sezioni Step 0, no modifica frontmatter)
- Aggiornare le pipeline degli agent per leggere i campi D1 envelope quando presenti (additivi, no version detection)
- Adottare l'enum status v2 nei report degli agent (mappatura diretta su `qa-investigator` CONFIRMED/PARTIAL/REFUTED → 5 valori v2)
- Far emergere `BatchJob` e `BusinessRule` negli output di `mcp-impact-analyst` e nei diagrammi C4 di `doc-generator`
- Aggiungere `who_authenticates` chain nella security section di HLD (`doc-generator`)
- Importare mapping v1→v2 di D2 § 2.3 per gestire dual-format 60gg
- Non introdurre regressioni sui comportamenti già validati (memory `feedback_no_regression_skill_optimization`)

## 3. Non-obiettivi

- ❌ Non riprogettiamo le pipeline degli agent (5-stage / 3-stage / 6-point restano invariate)
- ❌ Non scriviamo codice (sono prompt markdown)
- ❌ Non aggiungiamo `tools:` nel frontmatter (pattern adottato è dynamic ToolSearch)
- ❌ Non promuoviamo Onda 7 `answer_impact_question` come gateway: resta come fallback opzionale (vedi ADR-2)
- ❌ Non aggiungiamo `expand_transitive` agli agent (relation-specific, deferred a fase 2 con trigger esplicito — vedi ADR-6)
- ❌ Non implementiamo logica di version detection KG v1/v2: gli agent leggono i campi se presenti, omettono sezioni se assenti. Il mapping v1→v2 dell'enum status è importato da D2.

## 4. Decisioni architetturali (ADR)

### ADR-1 — 2 PR separate per priorità

- **PR-A (alta)**: `mcp-impact-analyst` + `qa-investigator` — match diretto D1+D2 sui loro output strutturati
- **PR-B (media/bassa)**: `doc-generator` (BatchJob/auth/rules in HLD) + `code-reviewer` (consistency_check Point 4)

**Rationale**: review più gestibile, valore alto a terra subito, rollback granulare.

### ADR-2 — Onda 7 come fallback opzionale, NON gateway

`answer_impact_question` è un orchestrator end-to-end MCP-side (esegue una pipeline completa, ritorna ranking + risposta). Promuoverlo a Stage 0.5 di `mcp-impact-analyst` significa delegare la **scelta dei passi intermedi** al MCP, perdendo trasparenza.

**Distinzione vs `alternate_hypotheses`**: questo è un **primitivo strutturato** che ritorna 2-3 ipotesi ranked che l'agent compone esplicitamente nel proprio reasoning step-by-step. La pipeline esplicita rimane sotto controllo dell'agent. Diverso da delegare l'intera orchestrazione.

Onda 7 lasciato come tool disponibile + citato nei "fallback noti" se la pipeline esplicita 5-stage non si applica.

### ADR-3 — Estensione bulk loading Step 0 esistente, no nuovi `tools:` frontmatter

Tutti e 4 gli agent hanno già Step 0 — Tool Loading con `ToolSearch query="select:..."` bulk loading dinamico. Pattern adottato dal repo, no `tools:` frontmatter.

**Decisione operativa**:
- `mcp-impact-analyst` (oggi 15 tool nel select) → +9 nuovi (D3+Onda 6+Onda 9+Onda 10) — vedi § 6 tabella
- `qa-investigator` (oggi 13 tool) → +9 nuovi (incluso `who_authenticates` mancante dal select pur presente in tools frontmatter)
- `doc-generator` (oggi 7 tool) → +3 nuovi (`who_authenticates`, `list_rules`, `find_batch_for_keyword`) — scope minimal HLD
- `code-reviewer` (oggi 5 tool) → +1 nuovo (`graph_consistency_check`) — singolo tool optional Point 4

Non estendiamo a "suite completa" perché ogni agent serve uno scope specifico e tool aggiuntivi creano rumore senza valore.

### ADR-4 — Enum status v2 mappa esattamente sul vocabolario qa-investigator

Il vocabolario attuale di `qa-investigator` (`CONFIRMED`/`PARTIAL`/`REFUTED`) è un sottoinsieme dell'enum v2. La transizione semantica:
- `CONFIRMED` → `CONFIRMED` (nessun cambio)
- `PARTIAL` → `PARTIAL` (nessun cambio) o `NOT_FOUND_IN_INDEX` (se sample-based + cap raggiunto, "fuori dal nostro scope di ricerca")
- `REFUTED` → `REFUTED` o `PROVEN_ABSENT_UNDER_SCOPE` (se evidence assenza dimostrata, non solo sample mancante)

**Mapping legacy** (importato da D2 § 2.3 per dual-format 60gg):
- MCP ritorna `"NOT_EXISTS"` → agent scrive `NOT_FOUND_IN_INDEX`
- MCP ritorna `"REFUTED"` legacy con scope incompleto → agent scrive `NOT_FOUND_IN_INDEX` + nota "legacy v1 mapped"
- MCP ritorna valore sconosciuto → agent scrive `PARTIAL` + nota "unknown enum value"

Questa è la disambiguazione critica del Q&A oggi.

### ADR-5 — Branch nuovo separato da `feat/devforge-agents-mcp-toolloading`

Quel branch ospita PR-5 test scaffold (skill activation eval, scope diverso). Branch dedicato `feat/agents-sport-kg-v2-recezione` evita mixing scope.

### ADR-6 — `expand_transitive` deferred con trigger esplicito

Il design **non** include `expand_transitive` negli agent. Trigger per re-aprire la decisione in fase 2:
- 2+ task in cui `mcp-impact-analyst` ha mancato blast-radius "library-induced" (es. modifica a `siae-sport-common` non rilevata)
- Evidence misurabile in retrospective o in commenti review

Senza trigger esplicito, "deferred" rischia di essere "deferred forever".

## 5. Architettura — cosa cambia, cosa NO

**Cambia**:
- `ToolSearch query="select:..."` (lista bulk loading) in 4 agent
- Sezioni testuali pipeline degli agent (Stage / Point) per usare i nuovi tool
- Output format markdown degli agent (campi D1 envelope, enum status v2)

**Non cambia**:
- Pipeline degli agent (5-stage / 3-stage / 6-point)
- Frontmatter `tools:` (non esiste, pattern dynamic loading)
- Modello di invocazione dalle skill (Agent tool con `subagent_type`)
- Memory `feedback_subagent_mcp_tool_loading` (ToolSearch select bulk PRIMA di chiamare mcp__*) → resta valido, anzi rafforzato

## 6. Tabella delta unificata per agent

| Tool | Origine | mcp-impact-analyst | qa-investigator | doc-generator | code-reviewer |
|------|---------|--------------------|-----------------|---------------|---------------|
| `graph_consistency_check` | D3 | **ADD** (Stage 3 5° check parallelo) | **ADD** (Stage 1 priors) | SKIP (out-of-scope HLD) | **ADD** (Point 4 optional) |
| `alternate_hypotheses` | D3 | **ADD** (Stage 4 ambiguity drill-down) | **ADD** (Stage 2 PARTIAL enrichment) | SKIP | SKIP |
| `expand_transitive` | D3 | SKIP (relation-specific, ADR-6) | SKIP | SKIP | SKIP |
| `graph_staleness_report` | D3 | **ADD** (output card freshness) | **ADD** (Stage 1 priors check >30gg) | **ADD** (footer cover doc) | SKIP |
| `find_batch_for_keyword` | Onda 10 | **ADD** (Stage 1 disambiguation) | **ADD** (Stage 1 batch keyword) | **ADD** (HLD batch swim lane) | SKIP |
| `who_authenticates` | Onda 9 | **ADD** (Stage 3 wide scan auth) | **ADD** (Stage 1 — già in frontmatter, manca dal select bulk) | **ADD** (HLD security section) | SKIP |
| `list_rules` | Onda 6 | **ADD** (Stage 3 BusinessRule emergence) | **ADD** (Stage 1 rule discovery) | **ADD** (HLD domain rules section) | SKIP |
| `describe_rule` | Onda 6 | **ADD** (Stage 4 rule drill-down condizionale) | **ADD** (Stage 3 deep rule) | SKIP (riassuntivo, non drill-down) | SKIP |
| `impact_of_rule_change` | Onda 6 | **ADD** (Stage 4 rule blast-radius) | SKIP (Q&A non implementativo) | SKIP | SKIP |
| `answer_impact_question` | Onda 7 | **KEEP** (già in frontmatter, promuovere a fallback documentato) | **ADD** (fallback per Q&A complesse) | SKIP | SKIP |

**Totale**:
- mcp-impact-analyst: 8 ADD + 1 promotion (`answer_impact_question`, già in `tools:` frontmatter ma non nel select bulk Step 0) → bulk loading da 15 → 24 tool
- qa-investigator: 9 ADD → bulk loading da 13 → 22 tool
- doc-generator: 4 ADD → bulk loading da 7 → 11 tool
- code-reviewer: 1 ADD → bulk loading da 5 → 6 tool

## 6.1 Dettaglio modifiche `agents/mcp-impact-analyst.md`

**Step 0 — Bulk loading (linea ~110)**: estendere il `select:` esistente con 9 nuovi tool (vedi tabella § 6).

**Stage 1 — Disambiguazione**: aggiungere riga "Se la modifica menziona keyword batch (`@Scheduled`, cron, scheduler), chiamare `find_batch_for_keyword` PRIMA della disambiguazione servizio".

**Stage 3 — Wide scan parallelo**: aggiungere come 5° check parallelo:
- `graph_consistency_check(target_service)` — drift KG↔ES
- (condizionalmente) `who_authenticates(target_service)` per task auth-touching
- `list_rules(target_service)` per task che modificano logica business

**Stage 4 — Drill-down (condizionale rischio MEDIO/ALTO)**: aggiungere:
- `alternate_hypotheses(claim)` se Stage 3 ritorna evidence ambigua
- `describe_rule(rule_id)` + `impact_of_rule_change(rule_id, change_type)` se task tocca BusinessRule

**Output card finale**: estendere blocco markdown con 3 nuovi campi:
- `**Confidence:** <HIGH|MEDIUM|LOW>` (esistente) → arricchire con `(inference_type=<value from envelope>)`
- `**Freshness:** observed_at=<ts>, ttl_hint=<seconds>` (NEW da envelope D1)
- `**Falsifiable_by:** <list>` (NEW da envelope D1, se presente)

**Output card — sezione "Top vincoli"**: status enum v2:
```
1. <vincolo> — Status: PARTIAL (NOT_FOUND_IN_INDEX, ES sample cap)
```

**Stage 3 — output supplementare** (additivo se nodi presenti):
- `**Batch jobs:** <list di BatchJob>`
- `**Business rules:** <list di BusinessRule>`
- `**External callers M2M:** <list ExternalSystem userId+sourceSystem>`

**Sezione "Workaround tool MCP noti"**: aggiungere riga su `*_prove_absent` variants quando blast-radius richiede prova di assenza.

**Sezione "Integrazione con altri agent / skill"**: menzionare `answer_impact_question` come fallback per Q&A pre-design quando la pipeline esplicita non si applica.

## 6.2 Dettaglio modifiche `agents/qa-investigator.md`

**Step 0 — Bulk loading (linea ~118)**: estendere il `select:` esistente con 9 nuovi tool. Critico: `who_authenticates` è in `tools:` frontmatter ma manca dal bulk select Step 0 — questo è un fix di consistenza.

**Stage 1 — KG topology — tabella domanda-tipo**: aggiungere righe:
- "Esiste un batch per <keyword>?" → `find_batch_for_keyword(keyword)` primario
- "Quale regola Drools governa Y?" → `list_rules(filter)` + `describe_rule(rule_id)`
- "Chi è l'IdP di X?" → `who_authenticates(X)` primario (oggi usa `describe_service` + `refresh_external_systems`)

**Stage 1 — opzionale**: chiamata `graph_staleness_report()` come priors check se domanda riguarda dati >30gg.

**Stage 2 — ES runtime**: quando evidence ambigua (sample-based o cap raggiunto), chiamare `alternate_hypotheses(claim)` → arricchire status `PARTIAL` con ipotesi ranked nel report.

**Output structure — sezione "Confidence + Stato hint utente"**: estendere enum a 5 valori:
- `CONFIRMED` (evidenze allineate, 2+ fonti concordi)
- `PARTIAL` (alcune sotto-affermazioni vere, altre n/d)
- `NOT_FOUND_IN_INDEX` (NEW — KG/ES non hanno la entity, ma scope ricerca limitato; ≠ assenza)
- `PROVEN_ABSENT_UNDER_SCOPE` (NEW — `*_prove_absent` ha confermato assenza nel scope)
- `REFUTED` (evidenze contrarie all'hint utente)

**Mapping legacy v1→v2** (in nuova sotto-sezione di "Output structure"):
```
| MCP ritorna v1 | Agent scrive v2 | Nota |
|---|---|---|
| "NOT_EXISTS" | NOT_FOUND_IN_INDEX | Mapping D2 § 2.3 |
| "REFUTED" + scope_completeness=incomplete | NOT_FOUND_IN_INDEX | "legacy v1 mapped" |
| "REFUTED" + scope_completeness=full | REFUTED | Match diretto |
| <unknown> | PARTIAL | "unknown enum value" |
```

**Sezione "Vincoli operativi"**: aggiungere "Hint user 'non esiste' → preferire `*_prove_absent` variants per disambiguare assenza vs ricerca incompleta".

**Sezione "Anti-razionalizzazione"**: aggiungere "PARTIAL e NOT_FOUND_IN_INDEX non sono sinonimi — il primo è 'parzialmente verificato', il secondo è 'fuori dal nostro scope di ricerca'".

## 6.3 Dettaglio modifiche `agents/doc-generator.md`

**Step 0 — Bulk loading (linea ~120)**: estendere il `select:` esistente con 4 nuovi tool: `who_authenticates`, `list_rules`, `find_batch_for_keyword`, `graph_staleness_report`.

**Sezione HLD "C4 Container diagram"**: nuova swim lane "Batch Schedulers" popolata da `BatchJob[]` di `describe_service` o discovery via `find_batch_for_keyword(<service-domain>)`. Se assente → omettere swim lane.

**Sezione HLD "Security"**: nuovo blocco "Authentication chain" da `who_authenticates(service)`:
- IdP primary
- Additional IdP
- Registered M2M callers
- Confidence + observed_at

**Sezione HLD "Domain rules" (NEW)**: se `list_rules(service_filter=<service>)` ritorna rules, embed elenco regole con package + activation pattern (top 10).

**Footer cover doc**: linea "Topologia osservata a `<observed_at>`, TTL stimato `<ttl_hint_seconds>`s" da envelope D1 (es. `describe_service` response).

**Sezione "DB schema" (se applicabile)**: nota interna "Onda 5 ha esteso `describe_table` con columns — già coperto da pattern esistente, no nuovi tool".

## 6.4 Dettaglio modifiche `agents/code-reviewer.md`

**Step 0 — Bulk loading (linea ~95)**: estendere il `select:` esistente con 1 nuovo tool: `graph_consistency_check`.

**Point 4 (Architettura)**: nuova sotto-checklist:
- "Drift KG↔codice": chiamare `graph_consistency_check(service)` se la review tocca un servizio mappato
- Se status `INCONSISTENT`, listare i mismatch nella review come BLOCK
- Se MCP non disponibile o servizio non mappato, skip silenzioso (continua review tradizionale)

## 7. Flusso dati

```
Skill SIAE invocante (siae-brainstorming, siae-debugging, siae-microservices-map, ...)
    ↓ Agent tool, subagent_type=mcp-impact-analyst|qa-investigator|...
Agent system prompt (file in agents/)
    ↓ Step 0: ToolSearch select bulk (lista estesa)
    ↓ Stage N: chiamate mcp__sport-kg__*
sport-kg MCP v2 (envelope D1 dual-format 60gg)
    ↓ envelope additive + status enum v2 + nuovi nodi (BatchJob/BusinessRule/ExternalSystem)
Output strutturato agent → ritorno alla skill chiamante
```

Le skill chiamanti restano invariate. Continuano a ricevere lo stesso "blocco markdown compatto" promesso.

## 8. Gestione errori / edge case

| Caso | Comportamento |
|------|---------------|
| Envelope D1 mancante (KG v1) | Agent legge i campi se presenti, omette sezioni `freshness`/`falsifiable_by`. NO version detection. |
| Tool nuovo non disponibile | ToolSearch select fallisce silenzioso → agent skippa lo stage opzionale. Mai bloccante. |
| MCP ritorna `"NOT_EXISTS"` v1 | Agent scrive `NOT_FOUND_IN_INDEX` (mapping D2 § 2.3) |
| MCP ritorna `"REFUTED"` v1 + `scope_completeness=incomplete` | Agent scrive `NOT_FOUND_IN_INDEX` + nota "legacy v1 mapped" |
| MCP ritorna valore enum sconosciuto | Agent scrive `PARTIAL` + nota "unknown enum value <X>" |
| Onda 7 `answer_impact_question` | NON usato per default. Citato in "fallback opzionale". |
| BatchJob/BusinessRule assenti per il service | Sezione output omessa (non scrivere "n/d"). |
| ExternalSystem M2M caller con userId duplicato | Dedup per max(confidence_score), pattern già esistente per `who_calls`. |
| `graph_consistency_check` ritorna `INCONSISTENT` ma agent non sa interpretare | Includi raw response come "Drift signals" + nota "interpretation deferred to human reviewer" |

## 9. Testing / validation

Niente test automatici (sono prompt markdown). Validazione manuale via smoke test con check binari testabili.

### 9.1 Baseline pre-modifica (no-regression)

**Prima del PR-A**: salvare snapshot output corrente di `mcp-impact-analyst` e `qa-investigator` su 2 dispatch noti:

- Snapshot 1: `mcp-impact-analyst` su `sport-gestione-licenze-service` per task "modifica conferma pagamento PagamentoServiceImpl"
- Snapshot 2: `qa-investigator` su domanda "Chi chiama apigateway-service-ext e quale auth usa"

Salvare in `docs/measurements/2026-05-03-pre-modifica-baseline/` (o equivalente).

**Prima del PR-B**: snapshot di `doc-generator` (HLD `sport-gestione-licenze-service`) e `code-reviewer` (review su PR esempio).

### 9.2 Smoke test PR-A — check binari

#### Test 1: mcp-impact-analyst su `sport-gestione-licenze-service`

Servizio target: `sport-gestione-licenze-service` (ha @Scheduled e Drools rules note).

Assertion (tutti devono passare):
- [ ] Output card include riga `Freshness:` con `observed_at=` e `ttl_hint=`
- [ ] Output card include riga `Falsifiable_by:` (può essere vuoto, ma il campo c'è)
- [ ] Output card include sezione `Batch jobs:` con almeno 1 elemento
- [ ] Output card include sezione `Business rules:` con almeno 1 elemento
- [ ] Status nei vincoli usa enum v2 (almeno 1 occorrenza di `CONFIRMED|PARTIAL|NOT_FOUND_IN_INDEX|PROVEN_ABSENT_UNDER_SCOPE|REFUTED`)
- [ ] Diff vs Snapshot 1 mostra solo righe aggiunte, nessuna riga rimossa o modificata in formattazione legacy

#### Test 2: qa-investigator su domanda auth

Domanda: "Chi chiama apigateway-service-ext e quale auth usa?"

Assertion:
- [ ] Output report include "Confidence" con valore enum v2
- [ ] Output report include "Stato hint utente" con enum v2 (se hint presente)
- [ ] Bulk loading Step 0 contiene `who_authenticates` (verifica pre-dispatch via grep sul file agent)
- [ ] Diff vs Snapshot 2 mostra solo righe aggiunte

### 9.3 Smoke test PR-B — check binari

#### Test 3: doc-generator HLD per `sport-gestione-licenze-service`

Assertion:
- [ ] HLD contiene swim lane "Batch Schedulers" se il servizio ha @Scheduled
- [ ] HLD contiene blocco "Authentication chain" in security section
- [ ] HLD contiene sezione "Domain rules" se `list_rules` ritorna rules
- [ ] Footer cover doc contiene "Topologia osservata a ..."

#### Test 4: code-reviewer su PR esempio

Assertion:
- [ ] Point 4 (Architettura) cita risultato `graph_consistency_check` o "MCP non disponibile"
- [ ] Review continua a funzionare se MCP down (assertion: review completa anche con `mcp-blocked`)

## 10. Criteri di accettazione

- [ ] **AC-1** PR-A merged: 2 agent aggiornati (`mcp-impact-analyst.md`, `qa-investigator.md`) + bulk loading select esteso + sezioni testuali aggiornate
- [ ] **AC-2** PR-A smoke test verde: Test 1 e Test 2 di § 9.2 passano (tutti i check binari)
- [ ] **AC-3** PR-A no-regression: diff output vs Snapshot 1 e 2 mostra **solo** aggiunte, zero righe legacy rimosse o modificate in formattazione
- [ ] **AC-4** PR-B merged: 2 agent aggiornati (`doc-generator.md`, `code-reviewer.md`)
- [ ] **AC-5** PR-B smoke test verde: Test 3 e Test 4 di § 9.3 passano
- [ ] **AC-6** PR-B no-regression: diff vs snapshot pre-modifica = solo aggiunte
- [ ] **AC-7** Sport-kg PR di riferimento citati esplicitamente nei commit message (PR #23 + Onde 6/9/10)

## 11. Stima Story Points (doppia scala)

- **PR-A**: 3 SP-Umano / 2 SP-Augmented (edit testuale guidato + smoke test live MCP — buffer per envelope mismatch)
- **PR-B**: 2 SP-Umano / 1 SP-Augmented
- **Totale iniziativa**: 5 SP-Umano / 3 SP-Augmented

Aumento PR-A da 1 → 2 SP-Augmented per assorbire eventuali mismatch envelope D1 in produzione MCP (memory `Docker VPN networking` documenta overhead setup live).

## 12. Dipendenze e prerequisiti

- ✅ sport-kg PR #23 (D1+D2+D3+D4+D5) merged in main 2026-04-30
- ✅ Onde 1-10 merged (PR #10-#21)
- ✅ Branch dedicato creato: `feat/agents-sport-kg-v2-recezione`
- ⏳ Spec review gate (subagent spec-reviewer, gate utente — iterazione 2 in corso)
- ⏳ Snapshot pre-modifica salvati per AC-3 e AC-6 (eseguire prima del PR-A)
- ⏳ Piano implementativo decomposto via `siae-writing-plans`

## 13. Out of scope (deferred)

- **Promozione `answer_impact_question` come gateway** → riconsiderare in v2 dopo evidenze qualità (memory feedback se la pipeline esplicita produce risultati equivalenti o peggiori)
- **`expand_transitive` adoption** → trigger esplicito ADR-6: 2+ task in cui blast-radius library era utile e l'agent non l'ha trovato. Senza trigger, deferred forever.
- **`*_prove_absent` variants come default** → richiede review semantica caso per caso (oggi solo citate nei vincoli operativi)
- **Aggiungere suite completa MCP a `doc-generator`/`code-reviewer`** → solo i 4+1 tool indispensabili (ADR-3)

## 14. Sezione tracking commit

Questo design doc verrà committato con card 🟡 MEDIO. Trail:

- Design doc: questo file
- Plan: `docs/plans/agents-sport-kg-v2-recezione/overview.md` (via `siae-writing-plans`)
- Task atomici: `docs/plans/agents-sport-kg-v2-recezione/task-NN-*.md`
- Snapshot baseline: `docs/measurements/2026-05-03-pre-modifica-baseline/`
- PR-A: `feat/agents-sport-kg-v2-recezione-pr-a-mcp-qa`
- PR-B: `feat/agents-sport-kg-v2-recezione-pr-b-doc-review`
