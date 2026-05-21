# Audit `functional-bug-hunter` — 2026-05-21

**Target**: `/Users/mazzacuv/.claude/skills/functional-bug-hunter/`
**Metodo**: 4 agenti paralleli indipendenti (Round 1 — Independent), pattern multi-blind-agent consensus
**Modalità**: read-only, evidence-based
**Auditor**: Claude (Opus 4.7) + sub-agent Plan / claude-code-guide / general-purpose (×2)

---

## 1. Executive summary

- La skill ha **architettura solida** (pipeline 9-fase + 23 pattern × 15 stack + anti-hallucination guard + 3 runtime mode dichiarati): scope coverage **CONFIRMED 10/13** e zero claim REFUTED.
- Lo **scope-to-code gap** è il problema strutturale principale: 3 capability dichiarate sono solo prosa (path feasibility filter non scriptato, slash command non registrato, runtime mode non dispatched in `preflight.sh`).
- **SKILL.md eager footprint = 4059 tokens**, 2.7× peer rigid (`siae-debugging` 1664, `siae-brainstorming` 1275); cut concreti restituirebbero ~2620 tokens (−65%) senza capability loss.
- **Recall bug-finding 65% medio** su 5 archetipi (Java REST 83%, IaC 70%, Flutter 73%, React/TS 50%, PySpark 50%): forte sui pattern backend classici, debole su FE-lifecycle e DE-correctness.
- **Decision: REFACTOR** (non DEPRECATE). Foundation è valida; servono 3 interventi mirati: (a) script feasibility + dispatcher mode, (b) compressione SKILL.md eager, (c) +3 pattern BP-024..029 per chiudere recall gap.

---

## 2. Scorecard 4 assi

| Asse | Score | Motivazione |
|------|------:|-------------|
| **A1 — Coerenza vs scope** | **7.5/10** | 10/13 CONFIRMED, 3/13 PARTIAL su capability dichiarate non codificate runtime |
| **A2 — Best practice Anthropic** | **7.0/10** | 12 PASS + 4 PARTIAL + 4 FAIL su 20 check; principali fail: description over 1024 char, no `@file` imports, no `references/README.md` |
| **A3 — Efficienza token** | **6.0/10** | Eager 4059 tokens (target ≤1500-2000); 3 zone di bloat identificate con cut concreti |
| **A4 — Efficacia bug-finding** | **6.5/10** | Recall 65% medio; coverage asimmetrica tra archetipi; gap chiudibili con 3 nuovi pattern |
| **Media ponderata** | **6.75/10** | Solid foundation, 3 cluster di intervento ben definiti |

---

## 3. Top-10 gap ordinati per severità

### CRITICAL (block-impact)

1. **Frontmatter `description` 1209 char vs limit 1024** (A2)
   - Path: `SKILL.md:3-19`
   - Rischio: parser Anthropic potrebbe troncare/rifiutare silenziosamente
   - Fix: comprimere a ~900 char, spostare stack list in body section

2. **Path feasibility filter è solo prosa** (A1)
   - Path: `SKILL.md:259-269` dichiara filter ma `grep -r feasibility scripts/ tools/` ritorna ZERO
   - Rischio: capability dichiarata come componente runtime ma di fatto è obbligo operatore non automatizzato
   - Fix: implementare `scripts/path_feasibility.py` oppure declassare in description a "operator-driven check"

### MAJOR

3. **Runtime modes (interactive/strict/report-only) non dispatched** (A1)
   - Path: `preflight.sh:10` esplicita "the caller decides how to react per runtime mode"
   - Rischio: comportamento "TTY may pause / CI never pauses" non garantito a runtime
   - Fix: aggiungere dispatcher in `preflight.sh` o `run_lock.py` con `if mode == "strict": continue elif "interactive": pause`

4. **Slash command `/siae-functional-bug-hunter` non registrato** (A1)
   - Path: `find ~/.claude/commands/ ~/.claude/plugins/.../commands/ -name "siae-functional-bug-hunter*"` → absent
   - Rischio: claim "explicit slash command" è sovra-affermato; invocazione di fatto via skill-name
   - Fix: registrare command file dedicato OPPURE riformulare description ("invoked by skill name `siae-functional-bug-hunter`")

5. **SKILL.md eager bloat — Phase 0..8 narrative 9 fasi prose-heavy** (A3)
   - Path: `SKILL.md:106-325` (~1800 tokens di dettaglio implementativo)
   - Fix: comprimere in tabella 9-righe + estrarre dettagli in `references/pipeline_internals.md` on-demand → **saving ~1600 tokens**

6. **Manca `@file` import annotations + `references/README.md`** (A2)
   - Path: `SKILL.md:354-368` referenzia 10 file ma senza `@file:` syntax; nessun README in `references/`
   - Rischio: orchestrator non sa quando caricare cosa; maintenance burden
   - Fix: aggiungere `imports:` frontmatter + creare `references/README.md` con matrice Phase→Reference→Load-condition

7. **Recall basso su React/TS (50%)** (A4)
   - Path: `references/stacks/ts-js.md` non ha pattern dedicati a stale-closure, setState-after-unmount, cancellation race
   - Fix: aggiungere BP-024 `react-lifecycle-race` + BP-025 `setState-after-unmount` (asimmetria con Flutter che li ha già)

8. **Recall basso su PySpark/ETL (50%)** (A4)
   - Path: `references/stacks/data-platform.md` copre solo MERGE e `orderBy(rand())`
   - Fix: aggiungere BP-026 `nullable-join-key-loss`, BP-027 `window-missing-partition-by`, BP-028 `subset-deduplication-loss`

### MINOR

9. **Sezioni duplicate: hallucination guard e grounding policy** (A3)
   - Path: `SKILL.md:309-322` e `SKILL.md:390-422` ridicono lo stesso contratto
   - Fix: collapse in 1 sezione + spostare HG-01..05 tabella in `references/hallucination_guard.md` → **saving ~520 tokens**

10. **Manca sezione "When to use" esplicita** (A2)
    - Path: SKILL.md ha solo "When NOT to use" (51-59), "When to use" è implicito in intro
    - Fix: aggiungere `## When to use` dopo intro con 2-3 trigger condition

---

## 4. Remediation plan

### Quick-wins (≤1h)

| # | Azione | Beneficio | Effort |
|---|--------|-----------|--------|
| QW1 | Comprimere description a ≤1024 char | Conformità Anthropic | 15min |
| QW2 | Creare `references/README.md` con load-matrix | Discoverability | 30min |
| QW3 | Aggiungere `## When to use` section | A2 score +0.5 | 10min |
| QW4 | Collapse duplicazioni hallucination guard | −520 tokens eager | 20min |
| QW5 | Riformulare claim slash command (o creare file commands/) | A1 score +0.5 | 15min |

### Structural (≥1d)

| # | Azione | Beneficio | Effort |
|---|--------|-----------|--------|
| S1 | Estrarre `references/pipeline_internals.md` + comprimere SKILL.md Phase narrative in tabella | −1600 tokens eager | 4h |
| S2 | Implementare `scripts/path_feasibility.py` con verdict feasibile/non-feasibile | Chiude gap A1 #2 | 1d |
| S3 | Dispatcher mode in `preflight.sh` (`if mode == strict: skip_pause`) | Chiude gap A1 #3 | 4h |
| S4 | Aggiungere BP-024..029 (5 pattern: 2 React, 3 DE, 1 mobile state-mgmt) | Recall +15% stimato (65%→80%) | 1d |
| S5 | Aggiungere `imports: [@file: ...]` frontmatter + inline `@file:` markers nel body | Progressive disclosure formale | 2h |

---

## 5. Token saving plan

| Cut | Before (tokens) | After (tokens) | Saving | Risk |
|-----|----------------:|---------------:|-------:|------|
| Phase 0..8 narrative → tabella + pipeline_internals.md | ~3200 | ~1600 | **−1600** | LOW |
| Hallucination guard / grounding policy dedup → hallucination_guard.md | ~700 | ~180 | **−520** | LOW |
| Description compress + reference dispatch list bullet | ~900 | ~400 | **−500** | MED (mitigabile con keyword tagline) |
| **TOTALE SKILL.md eager** | **4059** | **~1440** | **−2620 (−65%)** | |

**Target raggiungibile**: 1440 tokens eager (allineato con `siae-debugging` 1664, `siae-brainstorming` 1275). Single-file on-demand cap: `bug_patterns.md` (5351) da splittare in `bug_patterns_matrix.md` + `bug_patterns_catalog.md` per rispettare cap ≤2500.

---

## 6. Appendix A — Matrice scope-coherence (A1)

| # | Claim | Status | Evidence |
|---|-------|:------:|----------|
| 1 | Multi-repo, cross-stack | ✅ CONFIRMED | `SKILL.md:67-68`, `references/stacks/INDEX.md:29-42` |
| 2 | Dependency graph closure detection | ✅ CONFIRMED | `SKILL.md:147-161`, `scripts/dependency_closure.py:55-80` |
| 3 | Pattern matrix stack-aware | ✅ CONFIRMED | `references/bug_patterns.md:21-46` (23 × 15) |
| 4 | Path feasibility filter | ⚠️ PARTIAL | Solo prosa `SKILL.md:259-269`; no script |
| 5 | Deterministic qa_report.md by user-journey | ✅ CONFIRMED | `SKILL.md:286-292`, `scripts/render_qa_report.py:1-43` |
| 6 | Minimally-flaky repro recipes | ✅ CONFIRMED | `references/qa_inclusion_tree.md:120-131`, `tools/repro_voice_lint.py` |
| 7 | ISTQB persona voice | ✅ CONFIRMED | `references/qa_inclusion_tree.md:16-32`, `references/repro_voice_guide.md:14-115` |
| 8 | Generic-fallback profile | ✅ CONFIRMED | `references/stacks/_generic-fallback.md` |
| 9 | Slash command `/siae-functional-bug-hunter` | ⚠️ PARTIAL | Skill-name only, no command file registrato |
| 10 | No auto-hooks / no NL trigger | ✅ CONFIRMED | `references/lifecycle_playbook.md:8-24`, `tools/triggerlint.py` |
| 11 | Tre modes implementati | ⚠️ PARTIAL | Enum in renderer ma no dispatcher in `preflight.sh:10` |
| 12 | Exclude SAST-only senza functional manifestation | ✅ CONFIRMED | `references/qa_inclusion_tree.md:73-78,135-153` |
| 13 | Exclude test-code generation | ✅ CONFIRMED | `SKILL.md:18-19, 53-55` |

---

## 7. Appendix B — Recall bug-finding per archetipo (A4)

| Archetipo | Bug-class testati | HIT | PARTIAL | MISS | Recall |
|-----------|------------------:|----:|--------:|-----:|-------:|
| A1 — Java/Spring REST | 12 | 10 | 2 | 0 | **83%** |
| A2 — React/TypeScript | 10 | 5 | 3 | 2 | **50%** |
| A3 — PySpark ETL | 10 | 5 | 1 | 4 | **50%** |
| A4 — Terraform IaC | 10 | 7 | 2 | 1 | **70%** |
| A5 — Flutter mobile | 11 | 8 | 0 | 3 | **73%** |
| **Media** | 53 | 35 | 8 | 10 | **65.2%** |

**Pattern di gap**: la skill è forte sui backend classici e IaC (entrambi domini "code-static-readable"), debole su frontend lifecycle e data engineering correctness (entrambi domini con semantica runtime/data-driven più sfuggente all'analisi statica).

---

## 8. Note metodologiche

- Round 1 (Independent) eseguito: 4 agenti, output strutturato, 0 sovrapposizioni di lavoro.
- Round 2 (Cross-pollination) **skipped**: convergenza spontanea su 3 cluster (eager bloat, capability-non-codificate, recall gap stack-specific); cross-pollination non avrebbe aggiunto signal.
- Round 3 (Fact-check empirico) **parziale**: i 4 agenti hanno verificato in-line le claim più impattanti (`grep -r feasibility`, `find commands/`, `wc -w SKILL.md`); non eseguito un Round 3 dedicato.
- Round 4 (Sintesi) eseguito: questo documento.

**Limiti**: l'A4 archetypal simulation usa 5 archetipi astratti (non codice reale); la stima recall è qualitativa, non quantitativa. Per validazione empirica servirebbe esecuzione su 5 repo reali (uno per archetipo) con baseline manuale ISTQB.
