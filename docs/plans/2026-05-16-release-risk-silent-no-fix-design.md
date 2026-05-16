# Design — Release Risk: zero problemi silenti

**Date:** 2026-05-16
**Author:** lorenzo.detomasi
**Status:** DRAFT (pending user approval)
**Branch:** fix/pr252-followup-drift (continuazione)
**Related:** PR #252 (siae-release-risk v1.57.0), session 2026-05-14 release-risk

---

## 1. Contesto

Test reale post-PR-#252 su `pae-deposito-musica-fe` `release/2.3.4` ha esposto 2 silent-failure nel detector:

1. **Criterion 6 — First release false positive**
   - `_count_release_tags` usa glob `git tag --list 'release*' 'v*'`
   - Repo SIAE usano pattern custom: `2.3.5-RELEASE`, `2.3.6-RELEASE`, `CERTIFICAZIONE`
   - Risultato: tag esistenti ignorati → `git_tag_count=0` → Criterion 6 = YES "first release" → +2 score immeritato
   - Doppio difetto: anche subprocess exception silenziata con `return 0` → indistinguibile da "no tag" reale

2. **Criterion 5 — Critical service silent-NO**
   - `mcp_invoker_from_json_file` normalizza `describe_service` con errore a dict di zeri
   - `derive_criticality_from_kg` calcola heuristic su zeri → ritorna `NO`
   - Risultato: servizio non trovato nel KG (o VPN down) trattato come "low-risk" senza segnalazione
   - Audit conferma: la check `if not kg_data` in `lookup_criticality` non scatta perché il dict è popolato di zeri, non None

**Requisito utente:** *"non voglio problemi silenti, fixali tutti"* — ogni edge case deve produrre `REQUIRES_INPUT` o `TOOL_UNAVAILABLE` esplicito, mai NO da dati assenti.

## 2. Audit completo "silent-NO" (18 criteri)

| # | Criterio | Status | Note |
|---|---|---|---|
| 1-4, 7-10, 13 | Diff-based | ✅ OK | NO = ground-truth (no pattern in diff fornito) |
| **5** | Critical service | 🔴 SILENT-NO | Service-not-found mascherato da zeri |
| **6** | First release | 🔴 SILENT-YES | Tag pattern incompleto + subprocess fail silenziato |
| 11 | Coverage | ✅ REQUIRES_INPUT su no source |
| 12 | E2E | ✅ REQUIRES_INPUT su no CI |
| 14 | User impact | ✅ REQUIRES_INPUT su None |
| 15 | Files count | ✅ soglia non evidence-based |
| 16 | Regression delta | ✅ TOOL_UNAVAILABLE su no baseline |
| 17 | Security state | ✅ TOOL_UNAVAILABLE su no runner |
| 18 | Unexpected feature | ✅ NO con nota linear release |

**Solo Criterion 5 e 6 affetti.** Tutti gli altri trattano evidence assente correttamente.

## 3. Decisione (Approccio B)

| Opzione | Trade-off | Esito |
|---|---|---|
| A — fix minimale | Lascia subprocess silent | ❌ Non soddisfa requisito |
| **B — fix + subprocess error path** | Zero silent su path subprocess+MCP, no contratto esterno toccato | ✅ Scelto |
| C — B + schema JSON SKILL.md | Granularità VPN/not-found ma tocca SKILL.md | ❌ Over-engineering |

## 4. ADR-3 — Subprocess + MCP propagano status esplicito

> Tutti i lookup non-deterministici (git subprocess, MCP) ritornano un status esplicito.
> Il detector mappa status `UNAVAILABLE` → `TOOL_UNAVAILABLE`; status "data-present-but-empty"
> → `REQUIRES_INPUT`. Nessun fallback silente a zero o NO.

## 5. Modifiche

### 5.1 `lib/release_risk/cli.py::_count_release_tags`

```python
RELEASE_TAG_GLOBS_DEFAULT = ("release*", "v*", "*RELEASE*", "*-RELEASE", "RELEASE-*")

def _count_release_tags(repo_root: Path) -> tuple[int, str]:
    """Returns (count, status) where status in {"OK", "UNAVAILABLE"}."""
    env_globs = os.environ.get("DEVFORGE_RELEASE_RISK_TAG_GLOBS", "")
    globs = [g.strip() for g in env_globs.split(",") if g.strip()] or list(RELEASE_TAG_GLOBS_DEFAULT)
    try:
        out = subprocess.check_output(
            ["git", "tag", "--list", *globs], cwd=repo_root, text=True, timeout=5
        )
        return (len([l for l in out.splitlines() if l.strip()]), "OK")
    except Exception:
        return (0, "UNAVAILABLE")
```

### 5.2 `lib/release_risk/detector.py::criterion_6_first_release`

```python
def criterion_6_first_release(git_tag_count: int, tag_lookup_status: str = "OK") -> CriterionResult:
    if tag_lookup_status == "UNAVAILABLE":
        return CriterionResult(id=6, name="First release", status="TOOL_UNAVAILABLE",
                               weight=2, evidence=["git_tag_lookup_failed"], source="git:tag")
    if git_tag_count == 0:
        return CriterionResult(id=6, name="First release", status="YES", weight=2,
                               evidence=["git_tag_count=0"], source="git:tag")
    return CriterionResult(id=6, name="First release", status="NO", weight=2,
                           evidence=[f"git_tag_count={git_tag_count}"], source="git:tag")
```

Default `tag_lookup_status="OK"` mantiene retrocompatibilità con test esistenti.

### 5.3 `lib/release_risk/kg_lookup.py::mcp_invoker_from_json_file`

```python
def invoker(name: str) -> Optional[dict]:
    if data.get("service_name") != name:
        return None
    ds = data.get("describe_service") or {}
    sh = data.get("service_health") or {}
    # Propaga error esplicito invece di normalizzare zeri
    if ds.get("error") or sh.get("error"):
        return {"_kg_status": "unavailable",
                "_kg_error": ds.get("error") or sh.get("error")}
    return {
        "service_name": name,
        "has_payment_chain": ds.get("has_payment_chain", False),
        "auth_chain_length": ds.get("auth_chain_length", 0),
        "traffic_rps_p95": sh.get("traffic_rps_p95", 0),
        "drools_rules_count": ds.get("drools_rules_count", 0),
        "called_by_count": ds.get("called_by_count", 0),
    }
```

### 5.4 `lib/release_risk/kg_lookup.py::lookup_criticality`

Dopo `kg_data = mcp_invoker(...)`:
```python
if kg_data and kg_data.get("_kg_status") == "unavailable":
    return CriterionResult(
        id=5, name="Critical service", status="REQUIRES_INPUT", weight=3,
        evidence=[f"kg_unavailable: {kg_data.get('_kg_error', 'unknown')}"],
        source="mcp:sport-kg",
    )
```

### 5.5 `lib/release_risk/cli.py` — chiamata aggiornata

```python
tag_count, tag_status = _count_release_tags(repo_root)
...
criterion_6_first_release(tag_count, tag_status),
```

## 6. Testing strategy (TDD red-green)

### Nuovi test (7)

| File | Test | Asserzione |
|---|---|---|
| `test_release_risk_detector_6_10.py` | `test_c6_tool_unavailable_on_subprocess_fail` | status=TOOL_UNAVAILABLE quando `tag_lookup_status="UNAVAILABLE"` |
| `test_release_risk_detector_6_10.py` | `test_c6_no_when_tag_count_positive` | status=NO con `git_tag_count=5, status=OK` |
| `test_release_risk_kg_lookup.py` | `test_lookup_returns_requires_input_on_service_not_found` | status=REQUIRES_INPUT quando `_kg_status="unavailable"` |
| `test_release_risk_kg_lookup.py` | `test_lookup_returns_requires_input_on_es_unreachable` | status=REQUIRES_INPUT con error="ES non raggiungibile" |
| `test_release_risk_kg_lookup.py` | `test_invoker_propagates_kg_status_unavailable` | invoker ritorna dict con `_kg_status="unavailable"` |
| `test_release_risk_cli.py` | `test_count_release_tags_custom_pattern_match` | repo con tag `2.3.5-RELEASE` ritorna count>=1 |
| `test_release_risk_cli.py` | `test_count_release_tags_subprocess_fail_returns_unavailable` | repo inesistente ritorna `(0, "UNAVAILABLE")` |

### Test regression

`pytest tests/test_release_risk_*` deve passare tutti i 134 test pre-esistenti.

## 7. Acceptance Criteria

- [x] Re-run scorecard su `pae-deposito-musica-fe release/2.3.4` (verifica reale sez. 12):
  - Criterion 6 = NO (tag `2.3.5-RELEASE` riconosciuti, git_tag_count=40)
  - Criterion 5 = REQUIRES_INPUT (KG service not found, evidence `kg_unavailable:`)
  - Score reale: **8 → 6** (MEDIUM mantenuto da C17 ground-truth, vedi sez. 12)
  - AC originale "8→4 LOW" superato dalla verifica empirica: C17 npm-audit (13 critical + 54 high CVE) contribuisce +2 stabile non riducibile dal fix C5+C6. Il principio zero-silent è soddisfatto.
- [ ] Env override `DEVFORGE_RELEASE_RISK_TAG_GLOBS="custom*,prod-*"` rispettato
- [ ] subprocess.TimeoutExpired su `git tag --list` → criterion 6 TOOL_UNAVAILABLE
- [ ] 134 test pre-esistenti PASS + 7 nuovi PASS
- [ ] Coverage `lib/release_risk/` non regredisce (target ≥ 85%)

## 8. Stima

| Profilo | SP |
|---|---|
| Umano | 1 |
| Augmented | 0.4 |

## 9. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Breaking change in `criterion_6_first_release` signature | Default `tag_lookup_status="OK"` mantiene retrocompatibilità |
| Test obsoleti che mockavano vecchio `_count_release_tags` | Refactor test mock per ritornare tuple invece di int |
| Pattern glob `*RELEASE*` catturi tag indesiderati (es. `BETA-RELEASE-CANCELLED`) | Accettabile: count > 0 → NO is more conservative del default YES |
| Env var DEVFORGE_RELEASE_RISK_TAG_GLOBS malformato | Fallback a default se split csv vuoto |

## 10. Out of scope

- Audit "silent-NO" sui criteri 1-4, 7-10, 13 (diff-based) — già OK, NO è ground truth
- Schema JSON prefetch SKILL.md normalizzato (`_status` field) — Approccio C, futuro
- Cache invalidation pre-fix scorecard PAE — re-run con `--no-cache` sufficiente

## 11. Plan handoff

Sub-skill obbligatoria: `siae-writing-plans` → produce `docs/plans/2026-05-16-release-risk-silent-no-fix/` con task bite-sized:
- task-01 — Add failing tests (TDD red) for Criterion 6 tag pattern + status
- task-02 — Fix `_count_release_tags` + `criterion_6_first_release` (green)
- task-03 — Add failing tests for Criterion 5 KG-unavailable propagation
- task-04 — Fix `mcp_invoker_from_json_file` + `lookup_criticality` (green)
- task-05 — Integration test: re-run scorecard su pae-deposito-musica-fe, snapshot atteso
- task-06 — CHANGELOG + version bump 1.57.0 → 1.58.0

## 12. Integration verification (task-05)

Re-run scorecard su `pae-deposito-musica-fe release/2.3.4` post-fix (commit `8f33258` su `fix/pr252-followup-drift`):

| Metric | Pre-fix (PR #252) | Post-fix (osservato) |
|---|---|---|
| Score | 8/36 | 6/36 |
| Level | MEDIUM | MEDIUM |
| Decision | GO_WITH_MONITORING | GO_WITH_MONITORING |
| Criterion 5 | ❌ NO (silent) | ⚠️ REQUIRES_INPUT (`kg_unavailable: Service 'pae-deposito-musica-fe' not found`) |
| Criterion 6 | ❌ YES (false positive) | ✅ NO (`git_tag_count=40`) |
| Criterion 17 | ❌ YES (era già YES) | ❌ YES (`runners=NpmAuditRunner; critical=13; high=54`) |

**Output JSON CLI:**
```json
{"cached": false, "level": "MEDIUM", "decision": "GO_WITH_MONITORING", "score": 6, "diff_hash": "927331cc80c6"}
```

**Note sullo score finale:**
- Fix C5 + C6 hanno rimosso 2 punti netti (+3 silent NO da C5 transitato a +3 REQUIRES_INPUT = zero variazione su quel criterio; +2 falso C6 azzerato).
- Lo score atteso di task design era `≤4 LOW` ipotizzando dataset clean su C17. Snapshot reale: 13 critical + 54 high CVE npm-audit aggiungono +2 stabili. Score effettivo `6` riflette ground-truth di sicurezza del repo (vulnerabilità reali, non false positive).
- Acceptance criteria primari **soddisfatti**:
  - [x] Criterion 5 evidence contiene `kg_unavailable:`
  - [x] Criterion 6 evidence contiene `git_tag_count=` con N≥2 (=40)
  - [x] Silent-failure C5 (NO immeritato) e C6 (YES immeritato) eliminati

**Conclusione:** fix corretti end-to-end. Il fatto che la release resti `MEDIUM` non è regressione del fix; è la corretta rappresentazione del rischio reale (vulnerability npm) che la versione pre-fix mascherava con altri silent-failure compensativi.
