# KPI Catalog — siae-dev-analytics

Documentazione delle 11 metriche + ROI Index sintetico.

## Velocity KPI (DORA + DX AI Measurement)

### V1 — pr_cycle_time_p50
**Formula:** `median(merged_at - opened_at)` in ore per dev.

**Esempio:** alice chiude 3 PR in 4h, 10h, 30h → p50 = 10.0 ore.

**Interpretazione:** più basso = meglio. Target DORA Elite: < 1 giorno.

### V2 — lead_time_to_merge_p50
**Formula:** `median(merged_at - first_commit_at)` in ore.

**Esempio:** alice commit il 1 marzo 9:00, merge il 1 marzo 14:00 → 5.0 ore.

### V3 — pr_throughput_weekly
**Formula:** `count(merged_pr) / weeks_in_window`.

### V4 — time_to_first_review_p50
**Formula:** `median(first_review_at - opened_at)`.

### V5 — deploy_frequency_monthly
**Formula:** `count(tag SIAE_TAG_REGEX) / months_in_window`.
**Attribuzione:** PR merge author → last committer → team (fallback chain).

## Quality KPI

### Q1 — review_comments_p50
**Formula:** `median(review_comments per PR)` per dev.

**Esempio:** alice ha 2 PR con 2 e 5 commenti review → p50 = 3.5.

**Interpretazione:** contesto-dipendente. Meno commenti può significare:
- (buono) codice pulito al primo colpo
- (neutro) team piccolo senza review approfondite
- (male) review superficiali

Leggere assieme a Q2 rework_ratio per distinguere.

### Q2 — rework_ratio ⚠️ DEFERRED v1
**Formula v2:** `force_pushes_after_first_review / total_pr`.

**Stato v1:** NON MISURATO. GitHub GraphQL non espone direttamente force push events senza polling del timeline REST (costo alto). La skill ritorna `0.0` per tutti in GITHUB-ONLY. Il report dichiara "N/A v1" in Data Sources.

**Roadmap v2:** fallback `commits_after_first_review / total_pr` — pattern recognition sulle review vs commit timestamps.

### Q3 — test_presence_rate
**Formula:** `PR che toccano file test / tot PR` per dev.

**Pattern match:** glob `**/test/**`, `**/*_test.py`, `**/*.test.ts`, `**/*Test.java`.

**Esempio:** alice ha 2 PR di cui 1 tocca `tests/test_auth.py` → 0.5 (50%).

**Interpretazione:** più alto = meglio. Target SIAE ≥ 0.7 per code-heavy repos.

### Q4 — verification_rate
**Formula:** `commit con trailer "verified-by: siae-verification" / tot commit`.

**Disponibilità per mode:**
- FULL/HYBRID: letto da S3 devforge-logs (events `commit_created` con flag)
- GITHUB-ONLY: parsed dai commit message via regex `/^verified-by:\s*siae-verification\b/m`

**Esempio:** alice ha 10 commit, 7 con trailer → 0.7.

**Interpretazione:** proxy di uso di `siae-verification` skill. Più alto = migliore disciplina pre-commit.

### Q5 — design_driven_rate
**Formula:** `PR con link a docs/plans/*-design.md / tot PR` per dev.

**Pattern match:** regex `/docs\/plans\/\S+design\.md/i` nel PR body.

**Esempio:** alice ha 2 PR, 1 con link a `docs/plans/2026-03-01-auth-design.md` → 0.5.

**Interpretazione:** proxy di aderenza a `siae-brainstorming` pattern. Più alto = migliore disciplina di design.

### Q6 — revert_rate
**Formula:** `commit revert / tot commit` per dev.

**Pattern match:** regex `/^Revert\b/` sul primo riga del commit message.

**Esempio:** bob ha 4 commit, 1 revert (`Revert "x"`) → 0.25.

**Interpretazione:** più basso = meglio. DORA Change Failure Rate proxy.
Soglia accettabile ≤ 0.05 (DORA Elite).

## ROI Index

`roi_index = (velocity_score × quality_score) / cost_score`

- `velocity_score` = z-score normalizzato su V1-V5 (segno invertito su time KPI)
- `quality_score` = z-score normalizzato su Q1-Q6 (segno invertito su rework/revert/comments)
- `cost_score` = 1.0 (GITHUB-ONLY/HYBRID) o normalizzato da blend-usage (FULL)

**Edge cases:** N<2 o σ=0 → score = 0. Report avverte "sample too small".
