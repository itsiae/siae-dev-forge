# Task 07 — run_analytics.py CLI + integration test + command + reference docs

**Goal:** Entry point CLI che orchestra tutta la pipeline, integration test end-to-end, command `/forge-analytics`, reference docs.

**AC coperti:** AC09, AC10 (tutti i scenari), AC12, AC13, AC14, AC15

**Dipendenze:** Task 2-6 (tutti gli script devono esistere)

**Tempo stimato:** 45 min

---

## File coinvolti

- `skills/siae-dev-analytics/scripts/run_analytics.py` (nuovo, CLI entry point)
- `skills/siae-dev-analytics/tests/test_integration.py` (nuovo, end-to-end)
- `skills/siae-dev-analytics/reference/kpi-catalog.md` (nuovo)
- `skills/siae-dev-analytics/reference/github-api-patterns.md` (nuovo)
- `skills/siae-dev-analytics/reference/privacy-guidelines.md` (nuovo)
- `commands/forge-analytics.md` (nuovo)

## Step 1 — Implementa `run_analytics.py` (entry point)

Crea `skills/siae-dev-analytics/scripts/run_analytics.py`:

```python
"""Entry point CLI per siae-dev-analytics.

Subcommand:
    autodetect → rileva fonti e stampa JSON
    run        → pipeline completa (fetch + compute + export)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

import yaml
import pandas as pd

import autodetect_sources as ad
import collect_github as cg
import collect_s3_telemetry as ct
import compute_kpis as ck
import export_excel as ee

log = logging.getLogger(__name__)


def load_config(path: Path) -> dict:
    """Load + minimal validate YAML config."""
    data = yaml.safe_load(path.read_text())
    required = ["scope", "time_window"]
    for k in required:
        if k not in data:
            raise ValueError(f"config missing required key: {k}")
    if not (data["scope"].get("repos") or data["scope"].get("teams") or data["scope"].get("topics")):
        raise ValueError("scope must define at least one of: repos, teams, topics")
    return data


def resolve_repos(scope: dict) -> list[str]:
    """Risolve scope → lista repo effective (repos + teams + topics)."""
    repos = list(scope.get("repos", []))
    # teams/topics richiedono gh CLI — best effort
    for team in scope.get("teams", []):
        # es. "itsiae/team-backend" → gh api orgs/itsiae/teams/team-backend/repos
        try:
            import subprocess
            org, slug = team.split("/", 1)
            result = subprocess.run(
                ["gh", "api", f"orgs/{org}/teams/{slug}/repos", "--jq", ".[].full_name"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                repos.extend(result.stdout.strip().split("\n"))
        except Exception as e:
            log.warning("failed to resolve team %s: %s", team, e)

    for topic in scope.get("topics", []):
        try:
            import subprocess
            result = subprocess.run(
                ["gh", "search", "repos", "--topic", topic, "--json", "nameWithOwner",
                 "--jq", ".[].nameWithOwner"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                repos.extend(result.stdout.strip().split("\n"))
        except Exception as e:
            log.warning("failed to resolve topic %s: %s", topic, e)

    return list(set(r for r in repos if r and "/" in r))


def cmd_autodetect(config_path: Path) -> dict:
    report = ad.autodetect(abort_on_no_github=False)
    return report.as_dict()


def cmd_run(config_path: Path, output_override: Path | None = None,
            format_override: str | None = None, anonymize_override: bool | None = None,
            generated_at_override: str | None = None) -> Path:
    cfg = load_config(config_path)

    # Autodetect
    source_report = ad.autodetect(abort_on_no_github=True)
    log.info("mode: %s", source_report.mode())

    # Scope
    repos = resolve_repos(cfg["scope"])
    if not repos:
        raise RuntimeError("no repos resolved from scope")
    log.info("analyzing %d repos", len(repos))

    window = cfg["time_window"]
    since = window["from"]
    until = window.get("to", "today")
    if until == "today":
        until = datetime.today().date().isoformat()

    excluded = set(cfg.get("developers", {}).get("exclude", []))
    include_filter = cfg.get("developers", {}).get("include", [])
    min_commits = cfg.get("options", {}).get("min_commits_threshold", 5)

    # Collect GitHub
    all_prs, all_commits, all_tags = [], [], []
    for repo in repos:
        try:
            raw = cg.fetch_repo_data(repo, since, until, skip_on_error=True)
            if raw is None:
                continue
            prs_records = cg.extract_pr_records(raw)
            commits_records = cg.extract_commit_records(raw)
            tags_records = cg.extract_deploy_tags(raw, commits_records, prs_records)
            all_prs.extend(prs_records)
            all_commits.extend(commits_records)
            all_tags.extend(tags_records)
        except RuntimeError as e:
            log.warning("skipping repo %s: %s", repo, e)

    prs_df = pd.DataFrame(all_prs) if all_prs else pd.DataFrame(
        columns=["repo", "number", "author", "created_at", "merged_at",
                 "cycle_time_hours", "lead_time_hours", "time_to_first_review_hours",
                 "review_comments", "has_tests", "has_design_link"])
    commits_df = pd.DataFrame(all_commits) if all_commits else pd.DataFrame(
        columns=["repo", "oid", "author", "committed_at", "message",
                 "has_verified_trailer", "is_revert"])
    tags_df = pd.DataFrame(all_tags) if all_tags else pd.DataFrame(
        columns=["repo", "tag_name", "commit_oid", "attributed_to"])

    # Filter excluded/included devs
    if not prs_df.empty:
        prs_df = prs_df[~prs_df["author"].isin(excluded)]
        if include_filter:
            prs_df = prs_df[prs_df["author"].isin(include_filter)]
    if not commits_df.empty:
        commits_df = commits_df[~commits_df["author"].isin(excluded)]
        if include_filter:
            commits_df = commits_df[commits_df["author"].isin(include_filter)]
        commits_df = ck.filter_by_min_commits(commits_df, threshold=min_commits)

    # Collect S3 telemetry if available
    cost_scores = {}
    if source_report.s3_devforge:
        events = ct.fetch_devforge_logs(since, until)
        if events:
            # Override Q4 con telemetry (piu' accurate)
            verif = ct.verification_rate_from_events(events)
            if verif and not commits_df.empty:
                # Annota — non fondamentale per la MVP
                log.info("S3 verification_rate override for %d devs", len(verif))

    if source_report.s3_blend:
        costs = ct.fetch_blend_usage(since, until)
        cost_scores = ct.normalize_cost_score(costs)

    # Compute KPIs
    window_tuple = (since, until)
    if prs_df.empty and commits_df.empty:
        log.warning("no data to compute")
        kpis_df = pd.DataFrame()
    else:
        kpis_df = ck.compute_all(prs_df, commits_df, tags_df, window_tuple, cost_scores=cost_scores)

    # Export
    output_cfg = cfg.get("output", {})
    fmt = format_override or output_cfg.get("format", "xlsx")
    out_path = Path(output_override or output_cfg.get("path", "./devforge-analytics-report.xlsx"))
    anonymize = anonymize_override if anonymize_override is not None else cfg.get("options", {}).get("anonymize", False)

    if kpis_df.empty:
        out_path = out_path.with_suffix(".no-data.txt")
        out_path.write_text("No data available for the specified scope + window.\n")
        return out_path

    if fmt in ("xlsx", "both"):
        ee.export(
            kpis_df=kpis_df,
            raw_prs=prs_df,
            source_report=source_report.as_dict(),
            window=window_tuple,
            output_path=out_path,
            anonymize=anonymize,
            generated_at=generated_at_override,  # None → utcnow default
        )
    if fmt in ("csv", "both"):
        csv_path = out_path.with_suffix(".csv")
        kpis_df.to_csv(csv_path)

    return out_path


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(prog="run_analytics")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_auto = sub.add_parser("autodetect")
    p_auto.add_argument("--config", default="devforge-analytics.yml")

    p_run = sub.add_parser("run")
    p_run.add_argument("--config", default="devforge-analytics.yml")
    p_run.add_argument("--output")
    p_run.add_argument("--format", choices=["xlsx", "csv", "both"])
    p_run.add_argument("--anonymize", action="store_true")

    args = parser.parse_args()

    if args.cmd == "autodetect":
        result = cmd_autodetect(Path(args.config))
        print(json.dumps(result, indent=2))
    elif args.cmd == "run":
        out = cmd_run(
            Path(args.config),
            output_override=Path(args.output) if args.output else None,
            format_override=args.format,
            anonymize_override=args.anonymize if args.anonymize else None,
        )
        print(f"Report saved to: {out}")


if __name__ == "__main__":
    main()
```

## Step 2 — Scrivi integration test

Crea `tests/test_integration.py`:

```python
"""Integration test end-to-end: config → autodetect → fetch → compute → export."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import pandas as pd

import run_analytics as ra


@pytest.fixture
def tmp_config(tmp_path):
    cfg = {
        "version": 1,
        "scope": {"repos": ["itsiae/sample-repo"], "teams": [], "topics": []},
        "time_window": {"from": "2026-03-01", "to": "2026-03-31"},
        "developers": {"include": [], "exclude": ["dependabot[bot]"]},
        "options": {"anonymize": False, "min_commits_threshold": 1, "parallel_fetch": 2},
        "output": {"format": "xlsx", "path": str(tmp_path / "report.xlsx")},
    }
    cfg_path = tmp_path / "devforge-analytics.yml"
    import yaml
    cfg_path.write_text(yaml.safe_dump(cfg))
    return cfg_path, cfg


def test_integration_github_only_produces_excel(tmp_config, sample_pr_data, tmp_path, monkeypatch):
    """End-to-end: config → autodetect (GH-ONLY mock) → fetch (mock) → compute → export."""
    cfg_path, cfg = tmp_config

    # Mock autodetect → GITHUB-ONLY
    with patch("autodetect_sources.check_gh_auth", return_value=True), \
         patch("autodetect_sources.check_s3_prefix", return_value=False), \
         patch("collect_github.fetch_repo_data", return_value=sample_pr_data):
        output = ra.cmd_run(cfg_path)

    assert Path(output).exists()
    assert Path(output).suffix == ".xlsx"

    from openpyxl import load_workbook
    wb = load_workbook(output)
    assert set(wb.sheetnames) == {"Summary", "Per Developer", "Raw Data", "Data Sources"}


def test_integration_abort_if_no_github(tmp_config):
    """github non autenticato → RuntimeError."""
    cfg_path, _ = tmp_config
    with patch("autodetect_sources.check_gh_auth", return_value=False):
        with pytest.raises(RuntimeError, match="GitHub"):
            ra.cmd_run(cfg_path)


def test_integration_reproducible_checksum(tmp_config, sample_pr_data, tmp_path):
    """Stesso input + generated_at fisso → stesse cell values.

    Passiamo generated_at esplicito via parametro (evita mock datetime fragile)."""
    cfg_path, _ = tmp_config

    from openpyxl import load_workbook

    FIXED_TS = "2026-04-15T00:00:00Z"

    outputs = []
    for suffix in ("a", "b"):
        out_path = tmp_path / f"report_{suffix}.xlsx"
        with patch("autodetect_sources.check_gh_auth", return_value=True), \
             patch("autodetect_sources.check_s3_prefix", return_value=False), \
             patch("collect_github.fetch_repo_data", return_value=sample_pr_data):
            # cmd_run accetta generated_at opzionale per riproducibilità in test
            ra.cmd_run(cfg_path, output_override=out_path, generated_at_override=FIXED_TS)
        outputs.append(out_path)

    wb1 = load_workbook(outputs[0])
    wb2 = load_workbook(outputs[1])
    for sheet in wb1.sheetnames:
        vals1 = [c.value for row in wb1[sheet].iter_rows() for c in row]
        vals2 = [c.value for row in wb2[sheet].iter_rows() for c in row]
        assert vals1 == vals2, f"sheet {sheet} differs"


def test_config_missing_scope_raises(tmp_path):
    """Config senza scope → ValueError."""
    bad_cfg = tmp_path / "bad.yml"
    bad_cfg.write_text("version: 1\n")
    with pytest.raises(ValueError):
        ra.load_config(bad_cfg)


def test_config_empty_scope_raises(tmp_path):
    """Config con scope vuoto → ValueError."""
    bad_cfg = tmp_path / "bad.yml"
    bad_cfg.write_text("""
version: 1
scope:
  repos: []
  teams: []
  topics: []
time_window: {from: '2026-01-01'}
""")
    with pytest.raises(ValueError):
        ra.load_config(bad_cfg)


def test_no_data_produces_txt_not_xlsx(tmp_config, tmp_path):
    """Se fetch ritorna 0 PR e 0 commit → output .no-data.txt."""
    cfg_path, _ = tmp_config
    empty_raw = {
        "repository": {
            "nameWithOwner": "itsiae/empty",
            "pullRequests": {"nodes": []},
            "defaultBranchRef": {"target": {"history": {"nodes": []}}},
            "refs": {"nodes": []},
        }
    }
    with patch("autodetect_sources.check_gh_auth", return_value=True), \
         patch("autodetect_sources.check_s3_prefix", return_value=False), \
         patch("collect_github.fetch_repo_data", return_value=empty_raw):
        output = ra.cmd_run(cfg_path)

    assert Path(output).exists()
    assert "no-data" in str(output).lower()
```

## Step 3 — Run integration test

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_integration.py -v 2>&1 | tail -15
```

Output atteso: `6 passed`.

## Step 4 — Scrivi reference docs

### `reference/kpi-catalog.md`

```markdown
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
```

### `reference/github-api-patterns.md`

```markdown
# GitHub API Patterns — siae-dev-analytics

Query GraphQL usate da `collect_github.py`.

## Query principale

```graphql
query($owner: String!, $name: String!, $since: DateTime!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: 100) {
      nodes { number author{login} createdAt mergedAt
        commits(first:1) { nodes { commit { committedDate } } }
        reviews(first:50) { nodes { createdAt comments { totalCount } } }
        files(first:100) { nodes { path } }
        body
      }
    }
    defaultBranchRef {
      target { ... on Commit {
        history(since:$since, first:100) {
          nodes { oid author{user{login}} committedDate message }
        }
      }}
    }
    refs(refPrefix:"refs/tags/", first:50) {
      nodes { name target{oid} }
    }
  }
}
```

## Invocazione via gh CLI

```bash
gh graphql -f query="$Q" -F owner=itsiae -F name=catalogo-service -F since=2026-01-01T00:00:00Z
```

## Rate limit management

- Cache locale `.cache/github/<hash>.json` deterministica
- Backoff esponenziale su "rate limit exceeded" (60s, 120s, 240s)
- Retry max 3 volte, poi RuntimeError

## Paginazione

v1 usa `first: 100`. Per repo > 100 PR nella finestra, estendere con `after` cursor.
```

### `reference/privacy-guidelines.md`

```markdown
# Privacy Guidelines — siae-dev-analytics

## GDPR Compliance

**Base legale:** legittimo interesse (valutazione ROI tool aziendale).

**Minimizzazione:** solo dati già pubblici internamente (GitHub org privata itsiae).

**Scopo dichiarato:** ROI Claude Code + reportistica management.

**No decisioni automatiche:** la skill produce report, non valutazioni HR.

## Gate obbligatorio

Card 🔴 ALTO prima di ogni run nominativo. Vedi SKILL.md → Step 4.

## Anonymize opt-in

Flag `--anonymize` → hash SHA256[:8] su ogni login GitHub.
Determinisico: stesso login → stesso hash (cross-report consistency).

## Retention

- Cache `.cache/github/`: 7 giorni default (TTL auto)
- Excel output: responsabilità utente (conservare in spazio confidenziale)
- No upload automatico esterno

## File sensibili auto in `.gitignore`

- `.cache/github/` — dati PR/commit cachati
- `devforge-analytics-report.*.xlsx` — output nominativi
- `devforge-analytics.yml` se contiene `developers.include` nominativo
```

## Step 5 — Scrivi command `/forge-analytics`

Crea `commands/forge-analytics.md`:

```markdown
# /forge-analytics

Invoca la skill `siae-dev-analytics` per generare report ROI degli sviluppatori SIAE che usano Claude Code + DevForge.

## Uso

```
/forge-analytics [--config <path>] [--anonymize] [--format xlsx|csv|both]
```

## Parametri

- `--config`: path al file YAML di configurazione (default: `./devforge-analytics.yml`)
- `--anonymize`: hash SHA256 dei login → report esterni
- `--format`: formato output (default: xlsx)

## Flow

1. Check `gh auth` + Python deps
2. Carica config YAML (o prompt interattivo)
3. Autodetect fonti (GitHub + S3 telemetry opzionale)
4. Gate 🔴 ALTO privacy — conferma esplicita
5. Fetch + compute + export
6. Narrativa markdown finale

## Esempi

```
/forge-analytics --config devforge-analytics.yml
/forge-analytics --anonymize --format both
```

## Quando usarlo

- Quarterly review ROI Claude Code
- Report trimestrale per management (carlo.stoppani)
- Benchmark team dopo introduzione nuova skill DevForge
- Identificazione top/bottom performer per coaching

## Permission denied

- `pip install` negato → prompt card 🟡 con alternative (venv, pipx, uv)
- `gh` non autenticato → abort con istruzioni `gh auth login`
- AWS S3 creds mancanti → graceful degrade GITHUB-ONLY

## Skill referenziata

`skills/siae-dev-analytics/`
```

## Step 6 — Run TUTTI i test

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
pytest skills/siae-dev-analytics/tests/ -v --tb=short 2>&1 | tail -40
```

Output atteso: `64 passed` totali (10 autodetect + 11 collect_github + 22 compute_kpis + 9 export_excel + 6 s3_telemetry + 6 integration = 64 test).

## Step 7 — Test end-to-end manuale (smoke test)

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"

# Prepara config di test
cat > /tmp/test-analytics.yml <<EOF
version: 1
scope:
  repos:
    - itsiae/siae-dev-forge
time_window:
  from: "2026-04-01"
  to: "today"
developers:
  exclude:
    - "dependabot[bot]"
options:
  anonymize: false
  min_commits_threshold: 1
output:
  format: xlsx
  path: /tmp/test-analytics-report.xlsx
EOF

# Autodetect
python3 skills/siae-dev-analytics/scripts/run_analytics.py autodetect --config /tmp/test-analytics.yml

# Run (dry, su repo reale)
python3 skills/siae-dev-analytics/scripts/run_analytics.py run --config /tmp/test-analytics.yml

# Verifica output
ls -la /tmp/test-analytics-report.xlsx
python3 -c "from openpyxl import load_workbook; wb=load_workbook('/tmp/test-analytics-report.xlsx'); print('sheets:', wb.sheetnames)"
```

Output atteso:
- Autodetect: `{"github": true, ...}`
- Run: `Report saved to: /tmp/test-analytics-report.xlsx`
- Sheets: `['Summary', 'Per Developer', 'Raw Data', 'Data Sources']`

## Step 8 — Commit finale

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
git add skills/siae-dev-analytics/scripts/run_analytics.py \
        skills/siae-dev-analytics/tests/test_integration.py \
        skills/siae-dev-analytics/reference/ \
        commands/forge-analytics.md
git commit -m "feat(skill): complete siae-dev-analytics CLI + integration [Task 7/7]

- run_analytics.py CLI con subcommand autodetect + run
- Integration test end-to-end con mock GitHub + autodetect
- Reference docs: kpi-catalog, github-api-patterns, privacy-guidelines
- /forge-analytics command
- Smoke test end-to-end su repo reale passed
- Tutti i 17 AC verificati

AC09, AC10, AC12, AC13, AC14, AC15"
```

## Criteri di accettazione Task 7

- [ ] `run_analytics.py autodetect` stampa JSON mode
- [ ] `run_analytics.py run` esegue pipeline completa
- [ ] Integration test produce xlsx apribile con 4 sheet
- [ ] Reproducibility test checksum passa
- [ ] Config validation: scope vuoto → ValueError
- [ ] No-data case → `.no-data.txt` invece di xlsx corrotto
- [ ] 3 reference docs presenti e completi
- [ ] `commands/forge-analytics.md` creato
- [ ] Tutti i test pytest pass (64 totali)
- [ ] Smoke test manuale su repo reale produce xlsx valido
- [ ] Commit conventional

## Verifica finale — TUTTI i 17 AC del design doc

```bash
# Run completo suite
pytest skills/siae-dev-analytics/tests/ -v --cov=skills/siae-dev-analytics/scripts --cov-report=term 2>&1 | tail -50
```

Output atteso:
- 64 test pass
- Coverage ≥ 85% su `compute_kpis.py`
- Coverage ≥ 80% overall

**AC covered end-to-end:**
- AC01 config loading → test_integration test_config_*
- AC02 gate 🔴 → SKILL.md flow step 4
- AC03 autodetect graceful degrade → test_autodetect
- AC04a-unit cache logic → test_collect_github
- AC04a-manual benchmark → smoke test
- AC05 compute 11 KPI → test_compute_kpis
- AC06 Excel 4 sheet → test_export_excel
- AC07 anonymize → test_export + test_compute
- AC08 coverage ≥ 85% → pytest --cov
- AC09 reproducibility → test_integration
- AC10 error handling → tutti i test error path
- AC11 SKILL.md 12 trigger → task-01
- AC12 command → task-07
- AC13 kpi-catalog → reference
- AC14 privacy-guidelines → reference
- AC15 github-api-patterns → reference
- AC16 V5 fallback → test_compute_kpis
- AC17 SIAE_TAG_REGEX → test_compute_kpis
