# Design — functional-bug-hunter v1.2.0 improvements

**Data**: 2026-05-21
**Branch**: `feat/siae-functional-bug-hunter`
**Skill target**: `skills/siae-functional-bug-hunter/`
**Audit source**: `audit-reports/functional-bug-hunter-audit-2026-05-21.md`

## Contesto

L'audit ha identificato 10 gap su 4 assi (scope coherence 7.5/10, Anthropic
best practice 7.0, token efficiency 6.0, bug-finding effectiveness 6.5;
media 6.75/10). Il piano di intervento è stato vagliato attraverso un
consensus a 3 lenti (pragmatic / architectural / token-efficiency) con
2 round di cross-pollination e 1 fact-check empirico sul codice.

L'approccio è REFACTOR — non DEPRECATE: la skill ha foundation valida, ma
ha tre cluster di debito:

- 3 capability dichiarate ma non codificate (path feasibility filter,
  runtime modes dispatcher, slash command registrato);
- SKILL.md eager 4059 tokens, 2.7× peer rigid (`siae-debugging` 1664);
- recall bug-finding 65% su 5 archetipi, asimmetrico su FE/DE.

## Decisioni e approcci valutati

| Lens | Effort | Filosofia | Esito |
|------|-------:|-----------|-------|
| 1 — Pragmatic shipper | 3.5h | Reframe > implement; skip recall backlog | Rejected (troppo aggressivo su capability — fact-check ha mostrato che modes NON sono già implementate) |
| 2 — Architect | 28h | Capability declared = capability executable; 5 ADR + 3 PR | Rejected (over-engineering: drop bug_patterns.md split deciso da Lens 2 stesso in Round 2) |
| 3 — Token efficiency | 16h | Eager footprint KPI #1 | Rejected (dogma su Gap 4 reframe; Lens 3 stesso ha cambiato idea in Round 2) |
| **Consenso (selected)** | **~12h** | Middle ground evidence-based: implement le 3 capability, compress eager, additive recall improvements | Selected |

## Architettura post-intervento

Skill structure preservata. Modifiche:

- **SKILL.md** compresso da 422 LOC (4059 tok) a ~200 LOC (~1650 tok)
  via estrazione Phase narrative + dedup hallucination guard.
- **Nuovi reference** (load-on-demand): `pipeline_internals.md`,
  `hallucination_guard.md`, `README.md` (load-matrix), `runtime_modes.md`.
- **Nuovo script**: `scripts/path_feasibility.py` (glob+keyword filter,
  no AST, no formal JSON schema).
- **Refactor**: `scripts/run_lock.py` — aggiunta sub-command `dispatch`
  con Mode enum (interactive/strict/report-only) e 3 branch
  (pause / continue / degrade).
- **Nuovo command file**: `commands/siae-functional-bug-hunter.md` (pattern
  forge-\*.md).
- **Pattern matrix extension**: BP-024..027 additive in
  `references/stacks/typescript-javascript.md` e
  `references/stacks/data-platform.md` (no split bug_patterns.md).

## ADR adottati (3, ridotti da 5 in Round 1 architect lens)

- **ADR-01 — Capability declared = capability executable**: ogni claim
  runtime in SKILL.md DEVE avere artefatto eseguibile testato. Reframe è
  legittimo solo per capability epistemiche (verbi tipo "recommends").
- **ADR-02 — Progressive disclosure via references/README.md load-matrix**:
  ogni reference ha riga unica nella matrix, no `@file:` imports formali
  (peer skill DevForge non li usano).
- **ADR-03 — Mode = behavioural contract**: STRICT mai pausa, INTERACTIVE
  può pausare, REPORT_ONLY accetta partial; dispatcher in `run_lock.py`
  testato con 3 smoke test.

Droppati: ADR matrix/catalog split (Lens 3 ha ragione — additive in
`stacks/*.md` è progressive disclosure naturale), ADR slash command ≠
skill name (semantica equivalente, basta il file).

## Criteri di accettazione

1. `wc -c < SKILL.md` description block ≤1024 char (gate Anthropic).
2. SKILL.md eager tokens ≤2000 (target 1650, peer-aligned).
3. `scripts/path_feasibility.py --help` esce 0, smoke test su 2 fixture
   (positive + negative) passa.
4. `scripts/run_lock.py dispatch strict STOP_AMBIGUOUS_SCOPE` ritorna
   `CONTINUE`; idem `interactive STOP_AMBIGUOUS_SCOPE` ritorna `PAUSE`;
   `report-only STOP_DEPENDENCY_CLOSURE` ritorna `DEGRADE`. Matrix completa
   in `references/runtime_modes.md` — single source of truth allineata con
   `_DISPATCH_TABLE` in `run_lock.py`.
5. `commands/siae-functional-bug-hunter.md` esiste e segue pattern
   `forge-*.md` (frontmatter `description:` + body con invocation example).
6. `references/typescript-javascript.md` contiene 2 nuovi BP esplicitamente
   etichettati BP-024 e BP-025 con trigger + actor primitive.
7. `references/data-platform.md` contiene BP-026 e BP-027.
8. `references/README.md` esiste con load-matrix di tutti i reference.
9. CHANGELOG.md entry v1.2.0 con riferimento all'audit report.
10. `git diff --stat` mostra ~10 file changed + 3 file new.

## Story points

| Componente | SP umano | SP augmented |
|-----------|---------:|-------------:|
| T1-T5 quick wins eager (description + When-to-use + extract Phase + dedup HG + README) | 4 SP | 1 SP |
| T6 path_feasibility.py | 3 SP | 1 SP |
| T7 run_lock.py mode dispatcher | 3 SP | 1 SP |
| T8 command file | 1 SP | 0.5 SP |
| T9-T10 pattern recall BP-024..027 | 4 SP | 1 SP |
| T11 validation + CHANGELOG | 2 SP | 0.5 SP |
| **Totale** | **17 SP** | **5 SP** |

## Out of scope (v1.2.0)

- Split `bug_patterns.md` (5290 tok, viola soft cap ≤2500 ma è on-demand,
  drop deciso in consenso).
- `@file:` imports frontmatter (peer skill DevForge non li usano, drop).
- BP-028 / BP-029 (recall improvement marginale, drop per scope creep).
- Test pytest dedicati per ogni script (smoke test sufficiente per v1.2.0;
  test suite formale → v1.3.0).
- Recall improvements Riverpod-specific (gap A4 #3 in audit, drop per
  scope creep mobile).

## Stato

- Audit completato: 2026-05-21 (4-agent parallel)
- Consensus implementation plan: 2026-05-21 (3-agent + 2 round + fact-check)
- User approval: 2026-05-21 (AskUserQuestion: "Sì, esegui tutto")
- Implementation: in corso (T1-T5 completati al momento della creazione di
  questo design doc, T6-T11 pending)
