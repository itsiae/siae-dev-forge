---
status: draft
created: 2026-05-13
revised: 2026-05-13 (iter 1 + iter 2 + iter 3 spec-review — B1 coverage formula + B2 SP reconcile + B3 hook layout + W1 MVP reduce 11→5 runner + W2-W5; iter 2 F1 stale 11-runner + F2 BLOCK enum SEVERELY_DEGRADED + F3 budget esempio numerico; iter 3 cosmetic stale + frontmatter)
topic: review-evidence-v2-scoring
owner: lodetomasi
priority: high
sp_human: 30.0
sp_augmented: 12.5
predecessor: docs/plans/2026-05-12-review-evidence-hook-design.md
---

# Design — Review Evidence v2: Regression-Based Scoring + Reviewer Gatekeeper

## North star

> Voglio che gli sviluppatori SIAE facciano ZERO bug usando DevForge.

97% reduction asintotica via 5 layer: **enforcement pre-commit / detection pre-merge / detection pre-deploy / recovery runtime / culture loop**. Questo design copre **layer 1+2 hard enforcement**, sostituendo soft-block bypassabile con scoring deterministico + reviewer agent come gatekeeper finale **non-overridable sui hard floor**.

## Contesto

`review-evidence v1` (PR #241 merged, commit `1a4f11c`) produce evidence JSON con verdict `block:bool + block_reasons:list`. Stop. Gli sviluppatori SIAE possono bypassare via `~/.claude/.devforge-skip-evidence` con tracking abuse 5/day. Adoption SIAE: **890 repo portfolio, 19% CI, 48% Qodana, 11% JUnit** (fonte: Confluence DevSecOps "Repo overview" 2025-11-10). Il sistema attuale non blocca davvero, perché:

1. **Soft block bypassabile** — un dev frustrato bypassa, gate diventa teatro
2. **No regression awareness** — soglie assolute penalizzano repo legacy (score basso permanente), non incentivano miglioramento
3. **No reviewer integration** — verdict è binario block/pass, niente giudizio qualitativo per casi borderline
4. **Tool fragility** — review-evidence v1 dipende da Qodana per CI quality (commerciale, 48% adoption, non garantito su nuovi repo)

## Obiettivo

Sostituire schema v1 binary-verdict con **scoring v2 regression-based + 2-layer enforcement**:

```
hooks/review-evidence (pre-push trigger)
        │
        ▼
score = compute_scores(PR_HEAD) - compute_scores(baseline)
        │
        ▼
┌─────────────────────────────────────────────┐
│ Layer A — HARD FLOOR automatico             │
│ Score abs sotto floor?                       │
│   YES → BLOCK no-review (NON-OVERRIDABLE)   │
└─────────────────────────────────────────────┘
        │ no
        ▼
┌─────────────────────────────────────────────┐
│ Layer B — REGRESSION CHECK                   │
│ Delta sotto HARD_REGRESSION_BUDGET?          │
│   YES → BLOCK                                │
│ Delta sotto WARN_REGRESSION_BUDGET?          │
│   YES → REVIEWER HANDOFF                     │
│   NO → AUTO_APPROVE                          │
└─────────────────────────────────────────────┘
        │
        ▼
code-reviewer agent (only if handoff)
        │
        ▼
APPROVED → push procede
REJECTED → BLOCK con reason umano
```

Tool stack 100% OSS (no Qodana / SonarQube commercial dependency).

## Decisioni chiave

| Decisione | Scelta | Razionale |
|---|---|---|
| Approccio architetturale | A — Extension review-evidence v1→v2 (incremental) | Riusa investimento PR #241, schema v1 ha già forward-compat, time-to-deliver minimo |
| S3 bucket baseline cache | NEW `itsiae-review-evidence-baseline-prod` (eu-west-1) | Ownership chiaro, separato da artifacts CI generic |
| Split delivery | 2 PR (foundation 13 SP + advanced 20 SP + Terraform 1.5 SP) | Review chunks digeribili, time-to-value PR-A immediato |
| Cache invalidation strategy | Key = main HEAD SHA (no TTL) | Edge A1 fix — TTL produce baseline staleness |
| Hard floor overridability | NON-overridable da reviewer agent (only human admin via BREAK-GLASS) | Edge F1 fix — auto-override = floor inutile |
| Budget snapshot timing | At PR_OPEN_TIME (non runtime read) | Edge E1 fix — admin change retroactive evil |
| Bot PR detection | Label `bot-pr` OR user `dependabot[bot]` skippa discipline check | Edge C1 fix — bot mai blocked |
| Vendored exclude paths | `.venv/ venv/ node_modules/ __pycache__/ .tox/ vendor/ target/ build/ .git/` | Edge B7 fix — exclude da scoring |
| Score components missing | Re-weight altre dim su 1.0 totale + marker `missing_components` | Edge D6 fix — graceful degradation |
| Empty PR (docs only) | Auto-pass + log only | Edge C4 fix |
| Revert PR | Detect via commit message `Revert "..."` → skip regression, only hard_floor | Edge C3 fix |

## Architettura

```
┌──────────────────────────────────────────────────────────────────┐
│ hooks/review-evidence (bash, extended v2)                        │
│  • SHA detect + dirty flag (existing)                            │
│  • Trigger: PreToolUse gh push|pr create|edit                    │
│  • Invoke scoring orchestrator                                   │
│  • Hard floor enforcement (NON-overridable)                      │
│  • Regression handoff to reviewer agent                          │
└──────────────────────────────────────────────────────────────────┘
                              │ python3 subprocess
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ lib/review_evidence/collector.py (existing, extended)            │
│  • Stack detect (existing)                                       │
│  • Dispatch collectors (existing)                                │
│  • NEW: Dispatch runners                                          │
│  • NEW: Compute scores (call scoring.py)                          │
│  • NEW: Fetch baseline (call baseline_cache.py)                   │
│  • NEW: Compute deltas + regression verdict                       │
│  • Atomic write evidence v2                                       │
└──────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────────────┐
        ▼                     ▼                             ▼
┌─────────────────┐  ┌──────────────────┐    ┌──────────────────────────┐
│ collectors/      │  │ runners/ (NEW)   │    │ checks/ (NEW unique     │
│ (existing v1)    │  │ 5 MVP runner     │    │ DevForge)               │
│ - python.py     │  │ - bandit.py      │    │ - arch_drift.py         │
│ - typescript.py │  │ - vulture.py     │    │ - skill_adoption.py     │
│ - java.py       │  │ - pyright.py     │    │                         │
│ - hcl.py        │  │ - pip_audit.py   │    │ (existing v1:           │
│                 │  │ - spotbugs.py    │    │  spec_drift.py)         │
│                 │  │ - mvn_deps.py    │    └──────────────────────────┘
│                 │  │ - eslint_sec.py  │
│                 │  │ - ts_unused.py   │
│                 │  │ - npm_audit.py   │
│                 │  │ - tfsec.py       │
│                 │  │ - checkov.py     │
│                 │  │ - gitleaks.py    │
│                 │  │ (12 total)       │
│                 │  └──────────────────┘
        │                     │                             │
        └─────────────────────┼─────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ lib/review_evidence/scoring.py (NEW)                             │
│  • 5 score functions (security, quality, coverage, spec, disc)   │
│  • Weighted overall                                              │
│  • min_dim_score floor check                                     │
│  • Re-weighting on missing components                            │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ lib/review_evidence/baseline_cache.py (NEW)                      │
│  • S3 backend (boto3) — bucket itsiae-review-evidence-baseline   │
│  • Local fallback for dev-without-AWS                            │
│  • Cache key = `${repo_full_name}/${main_HEAD_SHA}.json`         │
│  • Read: GetObject, miss → compute on-the-fly                    │
│  • Write: PutObject after main commit (CI workflow on-push)      │
│  • OIDC IAM role per GitHub Actions read+write                   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ lib/review_evidence/regression.py (NEW)                          │
│  • Snapshot budget at PR_OPEN_TIME (read .devforge-scores.yml)   │
│  • Compute deltas dim-by-dim                                     │
│  • Classify: BLOCK / REVIEWER_HANDOFF / AUTO_APPROVE              │
│  • Hard floor check (separato, non-overridable)                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ agents/code-reviewer.md (extended v2 — Step 0.5 + 0.6)          │
│  • Step 0.5 (existing v1) — load evidence                         │
│  • Step 0.6 (NEW) — gatekeeper logic:                             │
│      - if hard_floor_breach: emit "decision: block" subito        │
│      - if reviewer_handoff: do qualitative review w/ context     │
│      - if auto_approve: emit "decision: approve" with summary     │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                .claude/review-evidence/<sha>.json  (schema v2)
```

## Schema v2 (extension v1 forward-compat)

`lib/review_evidence/schema.py` aggiunge dataclass NUOVE (compatibili con v1, vecchio reader ignora i campi nuovi):

```python
@dataclass
class ScoreCard:
    security: float            # 0-100
    quality: float
    coverage: float
    spec_compliance: float
    discipline: float
    overall: float             # weighted average
    weights_used: dict[str, float]
    missing_components: list[str]  # dim con runner failed/missing


@dataclass
class RegressionVerdict:
    block_dimensions: list[str]   # delta <= hard regression budget
    warn_dimensions: list[str]    # delta <= warn budget
    improved_dimensions: list[str]  # delta > 0
    hard_floor_breaches: list[str]  # security < 60, etc — NON OVERRIDABLE
    decision: str  # "AUTO_APPROVE" | "REVIEWER_HANDOFF" | "BLOCK_HARD_FLOOR" | "BLOCK_REGRESSION" | "SEVERELY_DEGRADED"  # 5 valori — F2 iter2 fix
    reason: str


@dataclass
class ReviewerVerdict:
    status: str   # "APPROVED" | "REJECTED" | "PENDING" | "NOT_INVOKED"
    reason: str
    invoked_at: Optional[str]
    block: bool


@dataclass
class EvidenceV2(Evidence):
    # Extends v1 Evidence with v2-only fields (all Optional for back-compat)
    base_sha: Optional[str] = None
    baseline_scores: Optional[ScoreCard] = None
    current_scores: Optional[ScoreCard] = None
    deltas: Optional[dict[str, float]] = None
    regression_verdict: Optional[RegressionVerdict] = None
    reviewer_verdict: Optional[ReviewerVerdict] = None
    budget_snapshot_at: Optional[str] = None  # ISO timestamp PR_OPEN_TIME
    baseline_synthetic: bool = False  # True if no baseline (first PR, new repo)
```

`schema_version` bump da `"1.0"` → `"2.0"`. Forward-compat hint v1 (PR #241 CRITICAL-1 fix) → v1 clients leggono v2 con extra field ignorati.

## Scoring algorithm (5 formule esplicite)

```python
# lib/review_evidence/scoring.py

def score_security(findings: SecurityFindings) -> float:
    """100 − penalties, clamp [0, 100]. Combina output dei 5 MVP runner
    (bandit, eslint-security, gitleaks, pip-audit, npm-audit). Follow-up
    runner (tfsec, checkov, find-sec-bugs, mvn-deps) aggregati post-MVP."""
    penalty = (
        findings.critical * 30
        + findings.high * 10
        + findings.medium * 3
        + findings.low * 1
    )
    return max(0.0, 100.0 - penalty)


def score_quality(findings: QualityFindings) -> float:
    """Combina lint errors + complexity over-threshold + dead code."""
    penalty = (
        findings.lint_errors * 5
        + findings.complexity_files_over_threshold * 10
        + findings.dead_code_blocks * 2
        + findings.type_errors * 4  # pyright/ts
    )
    return max(0.0, 100.0 - penalty)


def score_coverage(cov: CoverageMetric, baseline_synthetic: bool = False) -> float | None:
    """Score 0-100 with anti-gaming penalty.

    Two INDEPENDENT signals (intentionally not "double penalty for same event"):
    1. coverage % (base) — quanto del codice e' coperto vs untouched
    2. lines_covered absolute (penalty) — anti-gaming: dev cancella test,
       lines_covered scende anche se % sale (perche' denominatore shrink).

    Edge cases:
    - cov is None or line_pct is None → return None (signal missing component,
      orchestrator re-weights altre dim).
    - baseline_synthetic=True (first PR, B1 fix): skip penalty, return base.
    - baseline_lines_covered is None: same as synthetic, return base.

    EDGE C5 fix: solo se base E lines drop BOTH happen, double penalty
    INTENTIONAL (worst case: refactor scuro che peggiora qualita' e nasconde
    test rimossi). Penalty capped at 20pt to evitare over-penalty.
    """
    if cov is None or cov.line_pct is None:
        return None
    base = min(cov.line_pct, cov.branch_pct or cov.line_pct)
    if baseline_synthetic or cov.baseline_lines_covered is None:
        return base
    lines_drop = max(0, cov.baseline_lines_covered - cov.current_lines_covered)
    penalty = min(20.0, lines_drop * 0.5)
    return max(0.0, base - penalty)


def score_spec_compliance(drift: SpecDrift, arch: ArchDrift) -> float:
    """100 − unplanned_files × 3 − arch_violations × 15."""
    return max(0.0,
        100.0 - len(drift.unplanned_files) * 3 - len(arch.violations) * 15
    )


def score_discipline(adoption: SkillAdoption) -> float:
    """100 − (no_brainstorming?40:0) − (no_TDD?30:0) − (no_verification?30:0).

    EDGE C1: bot-pr label skippa = sempre 100."""
    if adoption.is_bot_pr:
        return 100.0
    penalty = (
        (40 if not adoption.brainstorming_done else 0)
        + (30 if not adoption.tdd_cycle_seen else 0)
        + (30 if not adoption.verification_run else 0)
    )
    return max(0.0, 100.0 - penalty)


def compute_overall(scores: dict[str, float | None], weights: dict[str, float]) -> tuple[float, bool]:
    """Σ score_i × weight_i. Re-weight on missing (edge D6).

    Returns: (overall_score, severely_degraded_flag)

    Verify sum(weights) ≈ 1.0 ± 0.01 (edge E4).

    EDGE D6 EXTENDED: if len(available) < 2 → severely_degraded=True.
    Caller MUST skip hard_floor enforcement (don't block on broken tooling)
    and emit warning "DevForge runners non disponibili: <missing>".
    """
    available = {k: v for k, v in scores.items() if v is not None}
    if not available:
        return 0.0, True  # severely degraded
    if len(available) < 2:
        # Only 0-1 valid dim → tooling broken, return best-effort but flag
        single_score = next(iter(available.values()))
        return single_score, True
    available_weights = {k: weights.get(k, 0.0) for k in available}
    norm = sum(available_weights.values())
    if norm == 0:
        return 0.0, True
    weighted = sum(score * weights.get(k, 0.0) / norm for k, score in available.items())
    return round(weighted, 2), False
```

## Hard floors + regression budget (default, repo-overridable)

`.devforge-scores.yml` (repo-level, opzionale):

```yaml
schema_version: 1
weights:
  security: 0.30        # sum ≈ 1.0 ± 0.01 validated
  quality: 0.20
  coverage: 0.20
  spec_compliance: 0.15
  discipline: 0.15

hard_floors:           # absolute, NON-overridable by reviewer
  security: 60
  coverage: 50
  overall: 55
  min_dim: 40          # ANY dim < this = block (edge E5)

regression_budget:
  hard_block:          # delta <= these = BLOCK
    security: -2       # F3 iter2: equivale a "1 medium nuova vuln (-3) → BLOCK"
                       # OR "1 high (-10) → BLOCK"
                       # Coerente con "zero bug" north star, ma nota: 1 nuovo
                       # finding di severity medium basta a bloccare.
                       # Override per repo legacy via .devforge-scores.yml repo-locale.
    coverage: -5       # pp (percentage points) line/branch
    quality: -5        # equivale a "1 lint error (-5) o 0.5 nuovo complexity over (-10/2)"
    spec_compliance: -10  # ~3 unplanned files o 1 arch violation
    discipline: -20    # tollera dimenticanze (1 skill saltata = -30/-40)
  warn_reviewer:       # delta <= these = REVIEWER_HANDOFF (warn)
    security: 0        # qualsiasi regressione invoca reviewer
    coverage: -2       # pp
    quality: -2
    spec_compliance: -5
    discipline: -10

ignore_paths:
  - "node_modules/"
  - "vendor/"
  - "**/*.gen.py"      # generated code
  - "**/*_pb2.py"      # protobuf generated
```

**Override env var:** `DEVFORGE_SCORES_CONFIG_PATH` per testing.

## Baseline cache (S3)

```python
# lib/review_evidence/baseline_cache.py

S3_BUCKET = os.getenv("DEVFORGE_BASELINE_S3_BUCKET", "itsiae-review-evidence-baseline-prod")
S3_REGION = os.getenv("DEVFORGE_BASELINE_S3_REGION", "eu-west-1")


def baseline_key(repo_full_name: str, main_sha: str) -> str:
    """e.g. itsiae/siae-dev-forge/abc123def456.json"""
    return f"{repo_full_name}/{main_sha}.json"


def fetch_baseline(repo: str, main_sha: str) -> Optional[ScoreCard]:
    """Read from S3, returns None on cache miss.
    Edge D3: cache server-side, NOT modifiable from dev local."""
    try:
        client = boto3.client("s3", region_name=S3_REGION)
        resp = client.get_object(Bucket=S3_BUCKET, Key=baseline_key(repo, main_sha))
        return ScoreCard(**json.loads(resp["Body"].read()))
    except client.exceptions.NoSuchKey:
        return None
    except (BotoCoreError, ClientError, NoCredentialsError):
        # Edge D2: fail-soft if AWS unreachable (dev locale senza creds)
        return _local_fallback_baseline(repo, main_sha)


def store_baseline(repo: str, main_sha: str, scores: ScoreCard) -> None:
    """Called by CI workflow on main commit only. OIDC IAM role required."""
    ...
```

**Terraform module** (`infra/terraform/review-evidence-baseline/`):

```hcl
resource "aws_s3_bucket" "baseline" {
  bucket = "itsiae-review-evidence-baseline-prod"

  lifecycle_rule {
    enabled = true
    transition { days = 30 storage_class = "GLACIER" }
    expiration { days = 90 }
  }
}

resource "aws_iam_role" "github_actions_baseline" {
  # OIDC trust policy for itsiae/* repos
  ...
}
```

## Hook layout (clarification post B3 spec-review)

`hooks/review-evidence` resta **single executable bash file** (no directory split). Le funzioni v2 (parse regression verdict, emit decision per branch) sono **inline** nello stesso file o sourceate da `hooks/lib/review-evidence-v2.sh` per leggibilità — MA il file `hooks/review-evidence` deve restare invocabile come `bash hooks/review-evidence` (path coerente con `hooks.json` esistente). NON creare `hooks/review-evidence/` directory.

## Hook bash extension (v2)

```bash
# hooks/review-evidence (extension)

# Existing v1 logic stays (cache lookup, dirty flag, jq check, bypass).

# NEW v2: after evidence written, parse regression_verdict
DECISION=$(jq -r '.regression_verdict.decision // empty' "$EVIDENCE_FILE" 2>/dev/null || echo "")

case "$DECISION" in
    BLOCK_HARD_FLOOR)
        # NON-OVERRIDABLE — only admin BREAK-GLASS via repo flag
        REASON=$(jq -r '.regression_verdict.reason' "$EVIDENCE_FILE")
        cat <<JSON
{"decision":"block","reason":"review-evidence v2: hard floor breach — ${REASON}. NOT overridable by reviewer. Admin BREAK-GLASS: commit msg contains 'BREAK-GLASS: <jira-id>' + 2 reviewer approvals + post-mortem within 48h."}
JSON
        exit 0
        ;;
    BLOCK_REGRESSION)
        REASON=$(jq -r '.regression_verdict.reason' "$EVIDENCE_FILE")
        cat <<JSON
{"decision":"block","reason":"review-evidence v2: regression block — ${REASON}. Override via `export DEVFORGE_SKIP_EVIDENCE=1` (breakglass session-scoped) (tracked, abuse 5/day)."}
JSON
        exit 0
        ;;
    REVIEWER_HANDOFF)
        # Don't block. Emit advisory + agent will be invoked downstream.
        cat <<JSON
{"additional_context":"review-evidence v2: regression in warn zone — code-reviewer agent will gatekeep. ${REASON}"}
JSON
        ;;
    SEVERELY_DEGRADED)
        # F2 iter2 fix: tooling broken (runner missing, AWS unreachable).
        # Skip hard_floor block (dev non punito), reviewer gatekeeper invoked
        # for qualitative review. Warning visibile a dev.
        MISSING=$(jq -r '.scorecard.missing_components | join(",")' "$EVIDENCE_FILE" 2>/dev/null || echo "unknown")
        cat <<JSON
{"additional_context":"review-evidence v2: SEVERELY_DEGRADED — DevForge runners parzialmente non disponibili: ${MISSING}. Hard floor SKIP. Reviewer agent gestira qualitative review. Fix tools to restore enforcement."}
JSON
        ;;
    AUTO_APPROVE|"")
        # No block, emit advisory summary (W2 fix — Step 0.6 generates review comment)
        SCORE=$(jq -r '.scorecard.overall // "n/a"' "$EVIDENCE_FILE" 2>/dev/null)
        cat <<JSON
{"additional_context":"review-evidence v2: AUTO_APPROVE (overall=${SCORE}). Reviewer agent emette advisory summary."}
JSON
        ;;
esac
```

## Reviewer agent integration (Step 0.6)

`agents/code-reviewer.md` esistente Step 0.5 (load evidence v1) viene esteso con Step 0.6:

```markdown
## Step 0.6 — Gatekeeper Logic (v2 scoring)

Dopo Step 0.5 evidence-loading, controlla `regression_verdict.decision`:

| Decision | Behavior |
|---|---|
| `AUTO_APPROVE` | **W2 fix:** emetti review SUMMARY advisory (no full 6-point), include score card markdown + 1-line judgment qualitativo. Decision finale = approve, MA reviewer comment generato comunque (no buchi naming/intent). |
| `BLOCK_HARD_FLOOR` | NON-OVERRIDABLE. Emit "decision: block" subito. Agent NON può overrule (hard floors sono enforcement absoluto). |
| `BLOCK_REGRESSION` | Emit "decision: block". Reasons in regression_verdict.reason. Agent può commentare ma NON overrule senza BREAK-GLASS. |
| `REVIEWER_HANDOFF` | Procedi con review qualitativa full 6-point. Verdict APPROVED / REJECTED. |
| `SEVERELY_DEGRADED` (D6 ext.) | Skip hard_floor enforcement. Reviewer fa review qualitativa standard + nota "DevForge runners parzialmente non disponibili: <missing>". Dev non punito per tooling broken. |

**Reviewer can NEVER override hard_floor_breaches.** Solo human admin via repo flag `.devforge-break-glass-<jira-id>` + 2 reviewer approvals.
```

## arch_drift detection algorithm (W3 spec)

```python
# lib/review_evidence/checks/arch_drift.py

def detect_arch_drift(repo_root: Path, changed_files: list[str]) -> ArchDrift:
    """Detect architectural violations vs explicit rules.

    MVP: only forbidden-path check (no layer-hierarchy AST parsing — too brittle).

    Reads .devforge-arch.yml in repo root:

        forbidden_paths:
          - from: "src/api/"
            to: "src/db/"
            reason: "api must go through service layer"
          - from: "src/test/"
            to: "src/main/"
            reason: "test code cannot bleed into prod"
        forbidden_imports:
          - module: "internal_only"
            allowed_from: ["src/internal/"]

    For each changed file:
      - Parse imports (Python: ast.parse; TS: regex tsserver-free; Java: regex)
      - Match against rules
      - Emit ArchViolation per breach
    """
    rules_path = repo_root / ".devforge-arch.yml"
    if not rules_path.exists():
        return ArchDrift(violations=[], rules_file_present=False)

    rules = yaml.safe_load(rules_path.read_text())
    violations = []
    for f in changed_files:
        for rule in rules.get("forbidden_paths", []):
            if f.startswith(rule["from"]):
                # Parse imports
                imports = _extract_imports(repo_root / f)
                for imp in imports:
                    if imp.startswith(rule["to"]):
                        violations.append(ArchViolation(
                            file=f, import_=imp, rule=rule
                        ))
    return ArchDrift(violations=violations, rules_file_present=True)
```

**Score:** `100 - len(violations) * 15`. **No rules file** → 100 (neutral, no false positive su repo che non hanno arch policy).

## skill_adoption detection signal (W4 spec)

```python
# lib/review_evidence/checks/skill_adoption.py

def detect_skill_adoption(repo_root: Path, pr_open_time: datetime) -> SkillAdoption:
    """Detect if dev used DevForge skill chain (brainstorming → TDD → verification).

    Signal sources (in order of precedence):
    1. ~/.claude/projects/<project>/devforge-state/activity.jsonl
       - Contains skill invocation events (brainstorming, tdd_cycle, verification_run)
       - Filter by PR_OPEN_TIME - 7d
    2. docs/plans/<topic>/overview.md exists with status:approved frontmatter
       AND modified_at within PR_OPEN_TIME - 7d → brainstorming_done=True
    3. git log --grep "test:" --since "<PR_OPEN_TIME - 7d>" returns >=1 commit
       → tdd_cycle_seen=True (proxy debole, accept)
    4. Bot PR detection: github_user="dependabot[bot]" OR label "bot-pr"
       → is_bot_pr=True, all skill checks skipped, score=100

    Fallback if activity.jsonl missing (dev senza DevForge):
      - score = 50 (neutral, no penalty no reward)
      - marker discipline_signal_missing=True
      - Reviewer agent flag: "Cannot validate DevForge skill adoption"
    """
    ...
```

**Score:** vedi formula `score_discipline` sopra. **Missing signal** → 50 (neutral), no false negative su dev senza DevForge installato.

## Edge case coverage (40 identificati, mappati)

| ID | Categoria | Status | Mitigation |
|---|---|---|---|
| **CRITICAL 8** | | | |
| A1 | Baseline cache invalidation | ✅ COVERED | Key = SHA, no TTL (`baseline_cache.py`) |
| B1+B7 | Coverage gaming | ✅ COVERED | `score_coverage` checks absolute `lines_covered` |
| B3 | Config file change | ✅ COVERED | `.devforge-scores.yml` modify in PR requires override + reviewer flag |
| D3+D5 | Cache server-side + IAM | ✅ COVERED | S3 + OIDC IAM, no dev-local trust |
| E1 | Budget snapshot at PR_OPEN | ✅ COVERED | `budget_snapshot_at` field in v2 |
| E5 | min_dim_score hard floor | ✅ COVERED | `hard_floors.min_dim: 40` |
| F1 | Reviewer can't override floors | ✅ COVERED | Hard-coded in Step 0.6 logic |
| C5 | Combined lines_covered + % | ✅ COVERED | `score_coverage` formula |
| **HIGH 17 (selezione)** | | | |
| A2 | Force-push main | ✅ COVERED | Detect via `git cat-file -e`, fallback recompute |
| A3 | Squash-merge main | ✅ COVERED | Re-use cache if diff-empty vs new SHA |
| A5 | Long-running branch | ✅ COVERED | Baseline = merge-base, not HEAD |
| A6 | First commit / repo nuovo | ✅ COVERED | `baseline_synthetic: true` marker |
| A8 | PR target ≠ main | ✅ COVERED | Baseline = `git diff <target>...HEAD` |
| B2 | Test removed from main | ✅ COVERED | Baseline_diff su files toccati dal PR |
| C1 | Dependabot bot PR | ✅ COVERED | Label `bot-pr` → discipline skip |
| C2 | Hotfix branch off-tagged | ✅ COVERED | `git merge-base HEAD <target>` |
| C3 | Revert PR | ✅ COVERED | Detect `Revert "..."` commit msg → only hard_floor |
| C4 | Empty PR docs-only | ✅ COVERED | Auto-pass + log |
| D2 | Dev senza gh CLI | ✅ COVERED | Local fallback + marker `baseline_local_only` |
| D6 | Score component missing | ✅ COVERED | Re-weight + marker |
| E2 | Refactor riduce file | ✅ COVERED | Combined: `lines_covered` not drop AND `%` not drop |
| E4 | Weight sum ≠ 1.0 | ✅ COVERED | Validate `sum ≈ 1.0 ± 0.01` at config load |
| F3 | Reviewer loop infinito | ✅ COVERED | Cache reviewer verdict per `<head_sha, base_sha>` |
| F4 | 10 push consecutivi → 10 review | ✅ COVERED | Debounce 60s |
| **LOW 15 (selezione)** | | | |
| A4 | Concurrent PR race | DEFERRED | Snapshot at PR_OPEN already handles 80% |
| A7 | Skip-CI commit | DEFERRED | Recompute baseline async post-skip (future) |
| B6 | Trivial test gaming | DEFERRED | Mutation testing follow-up |
| C6 | Multi-stack PR partial | ✅ COVERED | Marker `partial_score: true` |
| C7 | First PR new dev | ✅ COVERED | Discipline = new code only |
| D1 | 890 repo × cache | ✅ COVERED | S3 + glacier 30d + LRU |
| D4 | TZ midnight edge | ✅ COVERED | UTC always |
| E3 | Locale formatting | ✅ COVERED | JSON dot only, UI converts |
| F2 | Reviewer timeout | ✅ COVERED | Fallback `decision: handoff_human`, blocca |
| Altri 6 LOW | acknowledged backlog | DEFERRED | Out-of-scope MVP |

**Coverage finale:** 8/8 CRITICAL + 17/17 HIGH + 9/15 LOW = **34/40 (85%) mitigati nel design**. 6 LOW deferred a follow-up PR.

## Testing strategy

| Test | Pattern | File |
|---|---|---|
| Schema v2 dataclass | Roundtrip JSON + forward-compat | `tests/test_review_evidence_schema_v2.py` |
| Score algorithm 5 formule | Unit + edge values (0, 100, missing) | `tests/test_review_evidence_scoring.py` |
| Runner registry | Mock subprocess per ogni tool | `tests/test_review_evidence_runners_*.py` (12 file) |
| Baseline cache S3 | `moto` mock S3 | `tests/test_review_evidence_baseline_cache.py` |
| Baseline cache local fallback | tmp_path | idem |
| Regression compute | Param: ogni dim × budget × hard_floor | `tests/test_review_evidence_regression.py` |
| Hard floor non-overridable | Reviewer agent contract test | `tests/test_review_evidence_floor_non_overridable.py` |
| Reviewer agent Step 0.6 | Markdown grep + scenario simulate | `tests/test_review_evidence_reviewer_step_06.py` |
| Budget snapshot | Param: admin changes budget after PR open | `tests/test_review_evidence_budget_snapshot.py` |
| Edge cases (40) | Chaos suite ampliata | `tests/test_review_evidence_chaos_v2.py` |
| E2E full pipeline | hook → orchestrator → S3 → agent | `tests/test_review_evidence_e2e_v2.py` |

Coverage target: ≥85% su `lib/review_evidence/v2/*` (sopra il 80% v1).

## Acceptance criteria (incl. 8 CRITICAL bloccanti)

1. **CRITICAL — Cache key SHA-based, no TTL** (A1)
2. **CRITICAL — Coverage anti-gaming: lines_covered absolute** (B1+B7)
3. **CRITICAL — Config file change require override** (B3)
4. **CRITICAL — Baseline cache S3 + OIDC IAM** (D3+D5)
5. **CRITICAL — Budget snapshot at PR_OPEN_TIME** (E1)
6. **CRITICAL — min_dim_score hard floor** (E5)
7. **CRITICAL — Hard floor non-overridable by reviewer agent** (F1)
8. **CRITICAL — Combined lines_covered + coverage% gate** (C5)
9. Schema v2 forward-compat con v1 clients (verified test)
10. 5 score formule produce 0-100 + weighted overall
11. 5 OSS runner MVP integrati (bandit, gitleaks, pip-audit, npm-audit, eslint-security), ognuno graceful su tool missing
12. Reviewer agent Step 0.6 implementato con **5 decision branch** (AUTO_APPROVE, REVIEWER_HANDOFF, BLOCK_HARD_FLOOR, BLOCK_REGRESSION, SEVERELY_DEGRADED) — F2 iter2 fix
13. Hook bash chain v1 stays unchanged (no regression PR #241)
14. Test coverage ≥85% su `lib/review_evidence/`
15. ENV_VARS.md aggiornato (10+ nuove env DEVFORGE_BASELINE_*)
16. CHANGELOG.md entry v1.55.0
17. Terraform module deployed (S3 + IAM OIDC)
18. .devforge-scores.yml example template + json schema
19. Docs `commands/forge-score.md` (NEW skill on-demand)

## Stima Storia Punti (post W1 MVP reduce 11→5 runner, riconciliata B2)

**PR-A foundation (~13 SP umano):**

| Componente | Umano | Augmented |
|---|---|---|
| Schema v2 dataclass + forward-compat | 1.5 | 0.5 |
| Score algorithm 5 formule (con B1 coverage fix) | 3.0 | 1.0 |
| 5 runner MVP (bandit, gitleaks, pip-audit, npm-audit, eslint-security) | 3.5 | 1.5 |
| Hook bash v2 extension (regression decision branch + W2 advisory) | 2.0 | 1.0 |
| `.devforge-scores.yml` parser + validation (B3+E4) | 1.5 | 0.5 |
| arch_drift check con .devforge-arch.yml (W3 spec) | 1.5 | 0.5 |
| Test foundation | 2.0 | 1.0 |
| Docs partial (ENV_VARS, CHANGELOG entry draft) | 0.5 | 0.5 |
| **PR-A TOTALE** | **15.5** | **6.5** |

**PR-B advanced (~14 SP umano):**

| Componente | Umano | Augmented |
|---|---|---|
| Baseline cache S3 + local fallback | 3.0 | 1.0 |
| skill_adoption check (W4 spec) | 1.5 | 0.5 |
| Budget snapshot at PR_OPEN_TIME (E1) | 1.5 | 0.5 |
| Hard floor logic non-overridable (F1+E5) | 1.0 | 0.5 |
| Reviewer agent Step 0.6 (5 decision branch incluso SEVERELY_DEGRADED + W2 advisory) | 1.5 | 0.5 |
| Edge case mitigation (40 cases test coverage) | 3.0 | 1.5 |
| E2E test full pipeline | 1.5 | 1.0 |
| Docs final (forge-score skill, README) | 1.0 | 0.5 |
| **PR-B TOTALE** | **14.0** | **6.0** |

**Terraform module (~0.5 SP umano):**

| Componente | Umano | Augmented |
|---|---|---|
| S3 bucket + lifecycle (semplice resource) | 0.5 | 0.5 |
| IAM OIDC role + trust policy itsiae/* (potrebbe già esistere in itsiae IaC) | 0.5 | 0.5 |
| **Terraform TOTALE** | **0.5** | **0.5** *(combined)* |

**GRAN TOTALE: 30.0 SP umano / 12.5 SP augmented.** (Era stima preliminare 38, sceso a 30 dopo W1 MVP reduce + Terraform smaller scope.)

## Runner OSS — MVP vs follow-up

**MVP (5 runner, PR-A):**
- `bandit` — Python security (CWE coverage)
- `gitleaks` — secret scan cross-stack
- `pip-audit` — Python deps vuln
- `npm-audit` — TS/JS deps vuln
- `eslint-plugin-security` — TS/JS security

**Follow-up (out of scope MVP, future PR):**
- `vulture` — Python dead code (not "zero bug" core, quality polish)
- `pyright` — Python type errors (overlapping con CI pipeline)
- `ts-unused-exports` — TS dead exports (idem vulture)
- `spotbugs + find-sec-bugs` — Java security (covered da Qodana SARIF v1 fetch)
- `mvn dependency-check` — Java deps vuln (covered da SARIF v1)
- `tfsec` — HCL security (può venire da pr-gate v1)
- `checkov` — HCL security (idem tfsec)

Razionale W1: MVP focus su "5 categorie" del goal utente (security + secret + deps + security cross-stack + coverage gate). Restanti runner sono "polish / quality enhancement" non-core per zero-bug. Spostati a PR-D follow-up.

## Rischi

| ID | Descrizione | Mitigazione |
|---|---|---|
| R1 | S3 setup blocked by AWS approval delay SIAE | Local-only fallback in PR-A, S3 PR-B (asincrono) |
| R2 | 5 runner MVP = 5 versioni tool da pinare, ecosystem instabilità (era 11 pre-W1 reduce) | Pin esatti in `requirements-runners.txt` + nightly test |
| R3 | Reviewer agent costo invocation × N push | Debounce 60s + cache verdict per `<head, base>` (edge F3+F4) |
| R4 | Baseline ricomputation costo on main avanzamento | CI workflow background async + S3 cache |
| R5 | Repo legacy con score basso → regression sempre PASS | Hard floor `min_dim: 40` + `overall: 55` cattura (edge E5) |
| R6 | Adoption blocked: dev SIAE non installa runner OSS | `forge-score-doctor` skill diagnostica + setup script unico |
| R7 | iCloud tax pre-push lentezza | Cache local + S3 server-side, no full re-compute every push |

## ADR

- **ADR-1** Extension v1 → v2 (vs rewrite). Riusa schema, hook, agent.
- **ADR-2** Score 0-100 con weighted overall (vs binary block/pass).
- **ADR-3** Regression-based budget (vs absolute thresholds). SonarQube model.
- **ADR-4** Hard floor non-overridable da reviewer agent. Only admin BREAK-GLASS.
- **ADR-5** OSS runner stack (no Qodana/Sonar commercial). 5 MVP runner gratis (bandit, gitleaks, pip-audit, npm-audit, eslint-security); 7 espandibili a follow-up (W1 iter1 fix).
- **ADR-6** S3 baseline cache, key = main HEAD SHA, no TTL.
- **ADR-7** Budget snapshot at PR_OPEN_TIME, no retroactive policy changes.
- **ADR-8** 2 PR split (foundation + advanced) per time-to-value.
- **ADR-9** Bot PR (Dependabot) skippa discipline check via label.
- **ADR-10** Schema v2 forward-compat con v1 clients (additive only).

## Allineamento gh CLI + siae-gh-actions (interface compatibility)

Lo scoring v2 resta **100% DevForge-local hook** (zero server-side workflow in questa iniziativa). MA i pattern di output, naming e severity sono **mutuati da gh CLI + `itsiae/siae-gh-actions@v3.0.0`** così che:
- Output JSON DevForge sia ingestable da un futuro workflow CI senza re-mapping
- Dev abituati a `gh` / GitHub Actions trovano stessa terminologia
- Le env var override locali matchano le `vars.X` repo-level già usate da SIAE

### Convenzioni adottate

| Area | Pattern SIAE / gh CLI | Adozione DevForge v2 |
|---|---|---|
| Coverage threshold env | `vars.TEST_COVERAGE_PERCENTAGE` (siae-gh-actions/check-test-coverage-var.yaml) | `DEVFORGE_EVIDENCE_MIN_COVERAGE` (esistente v1) — stesso semantic, env-var locale invece di repo var |
| Severity bucket | SARIF 2.1.0 `error/warning/note/none` (gh run download artefatti) | `critical/high/medium/low` interno → mapping SARIF preservato in `_sarif.py` v1 |
| Workflow output | `::error::`, `::warning::`, `::notice::` (GitHub Actions workflow commands) | Hook bash emette stessi prefissi su stderr se `GITHUB_ACTIONS=true` env presente (no-op locale, format-compat futuro CI) |
| Check status | `conclusion: success/failure/neutral/skipped/cancelled` (gh run list --json) | `evidence.regression_verdict.decision` mapping 1:1: `AUTO_APPROVE→success, BLOCK_*→failure, REVIEWER_HANDOFF→action_required, ...` |
| Run identifier | `databaseId` numerico (gh run list) | `evidence.sha` (git SHA, stesso ruolo di unique id per fetch) |
| Authorization gate | `check-run-authorization.yaml` per ruolo utente | Future: env `DEVFORGE_AUTHORIZED_USERS` con stessa semantica (out of scope MVP) |
| Coverage variable name | `TEST_COVERAGE_PERCENTAGE` | Re-export DevForge thresholds come env-compatible: `export TEST_COVERAGE_PERCENTAGE=$min_coverage` quando hook emette score |
| JSON output schema | Action workflow `outputs:` typed (string/boolean/number) | `evidence.scorecard` dataclass tipi corrispondenti |
| PR comment format | `gh pr comment $N --body "$MARKDOWN"` con tabella score | `commands/forge-score.md` skill on-demand stampa stesso markdown localmente |

### Studio reference `gh` CLI

Sequenze prese a riferimento per consistency:

```bash
# Pattern gh: fetch PR meta
gh pr view 241 --json baseRefName,headRefName,labels,user
# DevForge equivalent (local, no gh dependency for offline dev):
git rev-parse --abbrev-ref HEAD
git config --get branch.$(git rev-parse --abbrev-ref HEAD).merge

# Pattern gh: detect bot user
gh pr view --json user --jq '.user.login'  # "dependabot[bot]"
# DevForge equivalent:
git log -1 --format='%an'   # commit author
# (label-based detection delegate al human reviewer in DevForge-local, no GitHub API call)

# Pattern gh: status check post
gh api -X POST repos/$OWNER/$REPO/check-runs -f name=review-evidence -f conclusion=success ...
# DevForge equivalent:
# - JSON output to stdout for Claude Code envelope
# - No external API call (DevForge è hook locale)
```

### Pattern dei workflow `siae-gh-actions` adottati

Lo studio di `siae-gh-actions/{pytest-coverage,check_secrets,qodana-scan-generic}.yaml` ha indicato:

1. **Env block top-level** per costanti riusabili. DevForge usa `DEVFORGE_EVIDENCE_*` in modo equivalente, documentate in `hooks/ENV_VARS.md`.
2. **`gh pr comment`** per feedback al dev. DevForge `commands/forge-score.md` produce stesso markdown copy-paste per `gh pr comment`.
3. **`permissions: pull-requests: write contents: read`** principle of least privilege — DevForge non chiama GitHub API direttamente, ma documenta che SE in futuro lo facesse, segue stesso pattern.
4. **`secrets: inherit`** — non applicabile (hook locale), ma struttura env file `.env.devforge` segue stesso "non-empty validation" di `check_secrets.yaml`.
5. **`workflow_call` outputs typed** — DevForge schema v2 dataclass è typed equivalent.

### Out of scope: server-side workflow contribuito a siae-gh-actions

Una **eventuale PR-C futura** contribuirà un workflow reusable `REVIEW_EVIDENCE_V2_CI.yaml` a `itsiae/siae-gh-actions@v3.x` che gira lo stesso scoring server-side. Non parte di questa iniziativa: il design e l'output JSON sono già compatibili (additive), quindi PR-C è zero-friction sul futuro. Per ora **hook locale = canonical enforcement**.

## Out of scope (Future Work)

- **Mutation testing weight in coverage score** (edge B6 — usa stryker / mutmut / pitest)
- **CI integration server-side via GitHub Actions** workflow reusable (PR-C future)
- **Adoption dashboard** in `siae-dev-analytics` per visualizzare score history
- **Multi-team weights** (team Java può preferire weights diversi vs team frontend)
- **Real-time score** in PR description auto-updated via bot comment
- **SARIF v2 schema export** per integrazione con Qodana esistente (interop, not replacement)
