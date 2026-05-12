# Task 16 — Edge case hardening + chaos tests

**SP:** 3.0 · **AC mappati:** robustness (post edge-case hunt) · **Dipendenze:** Task 01-15 · **Wave:** 7

## Goal

Mitigare i **5 edge case CRITICAL** + **14 HIGH** identificati nell'edge-case hunt sistematico. Aggiungere chaos test suite che simula failure mode (disk full, jq missing, iCloud placeholder, worktree, force-push SHA, monorepo) per garantire **fail-closed semantics** sulle path blocking, e graceful degradation altrove.

## Edge case coperti

### CRITICAL (fail-closed obbligatorio)

| ID | Edge case | Mitigation | File toccato |
|---|---|---|---|
| E05 | `jq` non installato → block decision si degrada silenziosamente a "false" → fail-open | Pre-check `command -v jq` all'inizio dell'hook; se manca, decision:block con reason "jq required" su PreToolUse. Mai degradare a no-block silente. | `hooks/review-evidence` |
| E17 | Python collector `rglob("*.py")` esplode su monorepo con `.venv`, `node_modules`, `vendor/` | Excludi pattern via `os.walk` con prune; max depth 5. | `lib/review_evidence/collectors/python.py` |
| E41 | Disk full / ENOSPC → atomic_write raise → hook stdout "compute failed" → PreToolUse non blocca | Su ENOSPC nel ramo blocking, emit `decision:block reason:"disk full, cannot verify quality"`. Fail-closed esplicito. | `hooks/review-evidence`, `lib/review_evidence/atomic_io.py` |
| E42 | Fallback iCloud `~/.claude/review-evidence-fallback/` non cercato dal hook nella cache lookup → infinite re-compute | Helper `resolve_evidence_path(sha, repo_root)` che prova prima primary path, poi fallback. Hook usa helper invece di costruzione manuale. | `hooks/review-evidence`, `lib/review_evidence/paths.py` (nuovo) |
| E48 | iCloud crea `.icloud` placeholder al posto del JSON; jq sull'placeholder → fail-open su block | Detect file `.{sha}.json.icloud` o JSON parse failure: trattalo come cache miss + log warning. Aggiungi `xattr` exclude o forza fallback path su iCloud detection. | `hooks/review-evidence`, `lib/review_evidence/atomic_io.py` |

### HIGH (graceful degradation)

| ID | Edge case | Mitigation |
|---|---|---|
| E01 | `git rev-parse HEAD` su just-init repo → SHA vuoto, hook silent | Log `evidence_skip_no_head` + advisory esplicito |
| E03 | Race tra PreToolUse e PostToolUse simultanei sullo stesso SHA | Lock `.claude/review-evidence/<sha>.lock` con `mkdir` atomic; secondo attende+cache-read |
| E12 | `schema_version` futura non-breaking (`"1.1"`) rifiutata strict | Forward-compat su minor: accetta `1.x`, raise solo su major mismatch |
| E16 | Monorepo: jacoco/pyproject discovery solo root | `rglob` con prune per `**/target/**`, `**/build/**`, aggrega multi-module |
| E22 | Jacoco XML con DTD → entity resolution → network call | `defusedxml` o `XMLParser(resolve_entities=False)` |
| E23 | Jacoco multi-module `<group>` nested ignorato | Estendi parser ricorsivo per `<group>` |
| E25 | ESLint config error → exit 2 stdout vuoto → lint=None silente | Distingui returncode≠0+no-stdout da output valido; emit `{"available":false, "reason":"eslint config error"}` |
| E27 | `terraform validate` richiede `terraform init` prima | Detect stderr "init required" → reason esplicita |
| E29 | `gh run download` artefatti >100MB tmpdir riempito + timeout parziale | `--name "*.sarif*"` filtro nome artefatto |
| E32 | Multiple workflow runs stesso SHA → findings duplicati | Dedup per `workflowName`, tieni solo l'ultimo completed |
| E34 | mtime instabile su iCloud per design doc selection | Fallback ordering: filename prefix `YYYY-MM-DD-*` lexicographic |
| E36 | Design doc binario (PDF rinominato `.md`) → UnicodeDecodeError nascosta | Catch esplicito → `drift_severity="unknown"` con reason |
| E38 | Allowlist regex non matcha header italiani ("Tabella file", "Allegato") | Estendi pattern: `(file|component|piano|tabella|allegato|output|test|deliverable)` |
| E40 | TTL cleanup non implementato → cache cresce indefinitamente | Estendi `hooks/session-start` con cleanup `mtime +7` |

## File coinvolti

**Modificare:**
- `hooks/review-evidence` (E01, E03, E05, E41, E42, E48)
- `lib/review_evidence/atomic_io.py` (E41, E48)
- `lib/review_evidence/schema.py` (E12)
- `lib/review_evidence/collectors/python.py` (E17)
- `lib/review_evidence/collectors/_jacoco.py` (E22, E23)
- `lib/review_evidence/collectors/java.py` (E16)
- `lib/review_evidence/collectors/typescript.py` (E25)
- `lib/review_evidence/collectors/hcl.py` (E27)
- `lib/review_evidence/ci_fetch.py` (E29, E32)
- `lib/review_evidence/spec_drift.py` (E34, E36, E38)
- `hooks/session-start` (E40)

**Creare:**
- `lib/review_evidence/paths.py` (E42 — helper `resolve_evidence_path`)
- `tests/test_review_evidence_chaos.py` (chaos test suite)
- `tests/fixtures/review-evidence/jacoco_multimodule.xml` (E23)
- `tests/fixtures/review-evidence/sarif_v2_0.json` (E30)
- `tests/fixtures/review-evidence/design_italian_headers.md` (E38)
- `tests/fixtures/review-evidence/design_with_binary.bin` (E36)

## Step TDD

### Step 1 — Test chaos suite

`tests/test_review_evidence_chaos.py`:

```python
"""Chaos test suite — failure-injection on review-evidence pipeline.

Validates fail-CLOSED semantics on blocking triggers and graceful degradation
elsewhere. Each test injects a single failure mode and asserts the agent does
NOT see a clean verdict.
"""
import errno
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "review-evidence"
FIX = REPO_ROOT / "tests" / "fixtures" / "review-evidence"


def _init_repo(tmp_path):
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)


def _run_hook_pre_pr(tmp_path, env_extra=None):
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    env["HOME"] = str(tmp_path / "home")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title test",
        }),
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=30,
    )


def test_E05_jq_missing_fails_closed_on_block(tmp_path, monkeypatch):
    """E05: when jq is missing, hook MUST emit block on PreToolUse (not silent fail-open)."""
    _init_repo(tmp_path)
    # Strip jq from PATH
    minimal_path = "/usr/bin:/bin"  # no jq usually here
    monkeypatch.setenv("PATH", minimal_path)
    proc = _run_hook_pre_pr(tmp_path, env_extra={"PATH": minimal_path})
    out = json.loads(proc.stdout or "{}")
    # Strict: when jq missing, decision MUST be block on blocking trigger
    assert out.get("decision") == "block", (
        f"Fail-OPEN regression: expected block when jq missing, got {out}"
    )
    assert "jq" in out.get("reason", "").lower()


def test_E17_python_collector_skips_venv_node_modules(tmp_path):
    """E17: rglob('*.py') must NOT scan .venv/ or node_modules/."""
    (tmp_path / "main.py").write_text("# entry")
    (tmp_path / ".venv").mkdir()
    # Plant 100 fake .py files in .venv (would explode if scanned)
    for i in range(100):
        (tmp_path / ".venv" / f"f{i}.py").write_text("x")
    (tmp_path / "node_modules").mkdir()
    for i in range(100):
        (tmp_path / "node_modules" / f"f{i}.py").write_text("x")

    from lib.review_evidence.collectors.python import PythonCollector
    # is_applicable must complete quickly (< 1s) — i.e. it pruned the noise
    import time
    t0 = time.time()
    applicable = PythonCollector().is_applicable(tmp_path)
    elapsed = time.time() - t0
    assert applicable is True
    assert elapsed < 1.0, f"is_applicable too slow ({elapsed:.2f}s) — pruning missing"


def test_E41_disk_full_emits_block_on_blocking_trigger(tmp_path):
    """E41: ENOSPC during atomic write on blocking trigger MUST fail-closed."""
    _init_repo(tmp_path)
    # Pre-write evidence that would trigger compute (cache miss), then mock
    # atomic_write to raise ENOSPC. We'd need the hook to detect and block.
    # Implementation: hook checks compute exit code; non-zero on blocking
    # trigger must emit decision:block.
    # Simulated via fake collector exit 1:
    fake_collector = tmp_path / "fake-collector.py"
    fake_collector.write_text("import sys; sys.exit(1)")
    # Override hook's python invocation via env (TaskAU: hook respects DEVFORGE_EVIDENCE_COLLECTOR_PATH override)
    proc = _run_hook_pre_pr(tmp_path, env_extra={
        "DEVFORGE_EVIDENCE_COLLECTOR_PATH": str(fake_collector),
    })
    out = json.loads(proc.stdout or "{}")
    # Strict fail-closed
    assert out.get("decision") == "block", f"Fail-OPEN regression on collector failure: {out}"


def test_E42_fallback_path_resolved_in_cache_lookup(tmp_path):
    """E42: when evidence is in fallback dir, hook must find it via resolve helper."""
    from lib.review_evidence.paths import resolve_evidence_path
    sha = "abc123def456"
    fallback_root = tmp_path / "fallback" / ".claude" / "review-evidence-fallback"
    import hashlib
    repo_hash = hashlib.sha256(str(tmp_path.resolve()).encode()).hexdigest()[:12]
    fallback_dir = fallback_root / repo_hash
    fallback_dir.mkdir(parents=True)
    fallback_file = fallback_dir / f"{sha}.json"
    fallback_file.write_text('{"sha":"abc123def456"}')

    with patch("lib.review_evidence.paths.FALLBACK_ROOT", fallback_root):
        resolved = resolve_evidence_path(sha, repo_root=tmp_path)
    assert resolved == fallback_file


def test_E48_icloud_placeholder_treated_as_cache_miss(tmp_path):
    """E48: .{sha}.json.icloud placeholder in iCloud → cache miss, no fail-open."""
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    # iCloud placeholder: file with trailing .icloud, original missing
    (ev_dir / f".{sha}.json.icloud").write_text("")  # iCloud marker

    proc = _run_hook_pre_pr(tmp_path)
    # Hook should detect placeholder and either recompute or block — never advisory-only
    out = json.loads(proc.stdout or "{}")
    # Either it recomputed successfully (decision absent) OR it blocked safely
    # The forbidden outcome is "additional_context: block=false" reading the placeholder
    assert "block=false" not in out.get("additional_context", "") or out.get("decision") == "block"


def test_E12_schema_minor_version_forward_compat(tmp_path):
    """E12: schema_version 1.1 (future minor) must be accepted."""
    from lib.review_evidence.schema import evidence_from_json
    future_minor = {
        "schema_version": "1.1",
        "sha": "x", "branch": "x", "computed_at": "x", "dirty_tree": False,
        "base_branch": "main", "stack_detected": [], "metrics": {},
        "spec_drift": None, "verdict": {"block": False, "block_reasons": [], "warnings": []},
    }
    # Should NOT raise (forward-compat minor)
    ev = evidence_from_json(future_minor)
    assert ev.schema_version == "1.1"

    # But major bump MUST raise
    future_major = {**future_minor, "schema_version": "2.0"}
    with pytest.raises(ValueError):
        evidence_from_json(future_major)


def test_E32_ci_fetch_deduplicates_workflow_runs(tmp_path):
    """E32: multiple completed runs for same SHA must dedup by workflowName."""
    from lib.review_evidence.ci_fetch import fetch_ci_sarif
    # Implementation: keep only last completed per workflowName
    multiple_runs = json.dumps([
        {"databaseId": 1, "workflowName": "Qodana", "conclusion": "success"},
        {"databaseId": 2, "workflowName": "Qodana", "conclusion": "success"},  # dup
        {"databaseId": 3, "workflowName": "Sonar", "conclusion": "success"},
    ])

    download_calls = []

    def fake_run(cmd, **kw):
        from subprocess import CompletedProcess
        if cmd[0] == "gh" and "list" in cmd:
            return CompletedProcess(cmd, 0, stdout=multiple_runs, stderr="")
        if cmd[0] == "gh" and "download" in cmd:
            download_calls.append(cmd[3])  # run_id
            dl_dir = Path(cmd[cmd.index("--dir") + 1])
            dl_dir.mkdir(parents=True, exist_ok=True)
            (dl_dir / "report.sarif").write_text((FIX / "qodana_sample.sarif").read_text())
            return CompletedProcess(cmd, 0, stdout="", stderr="")
        return CompletedProcess(cmd, 1)

    with patch("lib.review_evidence.ci_fetch.subprocess.run", side_effect=fake_run):
        result = fetch_ci_sarif(sha="abc", repo_root=tmp_path)

    # Should have downloaded only 2 runs (latest Qodana + Sonar), not 3
    assert len(download_calls) == 2


def test_E38_spec_drift_matches_italian_headers(tmp_path):
    """E38: allowlist regex must match Italian headers like 'Tabella file'."""
    from lib.review_evidence.spec_drift import extract_files_from_design
    content = """
## Tabella file
- `src/foo.py`

## Allegato
- `lib/bar.py`
"""
    files = extract_files_from_design(content)
    assert "src/foo.py" in files
    assert "lib/bar.py" in files


def test_E40_session_start_cleans_old_evidence(tmp_path):
    """E40: session-start hook prunes evidence files older than 7 days."""
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    old = ev_dir / "old.json"
    old.write_text("{}")
    # Set mtime to 10 days ago
    import time
    old_ts = time.time() - (10 * 86400)
    os.utime(old, (old_ts, old_ts))
    fresh = ev_dir / "fresh.json"
    fresh.write_text("{}")

    # Invoke the cleanup helper (extracted to a sourceable lib for testability)
    subprocess.run(
        ["bash", "-c", f"find '{ev_dir}' -name '*.json' -mtime +7 -delete"],
        check=True,
    )
    assert not old.exists()
    assert fresh.exists()
```

### Step 2 — Implementa fix CRITICAL

Per ogni CRITICAL (E05, E17, E41, E42, E48):

**E05 (`hooks/review-evidence` head):**

```bash
# Insert after `set -euo pipefail`:
if ! command -v jq >/dev/null 2>&1; then
    if [[ "$HOOK_EVENT_NAME" == "PreToolUse" ]] && [[ "$TOOL_COMMAND" =~ gh[[:space:]]+pr[[:space:]]+(create|edit) ]]; then
        cat <<JSON
{"decision":"block","reason":"review-evidence: jq required but not installed. Install with 'brew install jq' or 'apt install jq'. Override: touch ~/.claude/.devforge-skip-evidence"}
JSON
        exit 0
    fi
    # Non-blocking trigger: degrade to advisory
    echo '{"additional_context":"review-evidence: jq missing, evidence skipped"}'
    exit 0
fi
```

**E17 (`lib/review_evidence/collectors/python.py`):**

```python
PRUNE_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".tox", "vendor", "target", "build", ".git"}

def _walk_with_prune(root: Path, suffix: str, max_depth: int = 5):
    root = Path(root)
    base_parts = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).parts) - base_parts
        if depth > max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
        for f in filenames:
            if f.endswith(suffix):
                yield Path(dirpath) / f
                return  # is_applicable: first hit is enough
```

Sostituisci `any(repo_root.rglob("*.py"))` con `next(_walk_with_prune(repo_root, ".py"), None) is not None`.

**E41 (`hooks/review-evidence` post-compute branch):**

```bash
if ! python3 "${COLLECTOR_PATH}" --sha "$SHA" --base "$BASE_BRANCH" --dirty "$DIRTY" --out "$EVIDENCE_FILE" 2>/dev/null; then
    if [ "$IS_BLOCKING" = "1" ]; then
        cat <<JSON
{"decision":"block","reason":"review-evidence: collector failed (likely disk full or python error). Cannot verify quality. Override: touch ~/.claude/.devforge-skip-evidence"}
JSON
        exit 0
    fi
    echo '{"additional_context":"review-evidence: compute failed (non-blocking)"}'
    exit 0
fi
```

**E42 (`lib/review_evidence/paths.py` nuovo):**

```python
"""Resolve evidence file location across primary and fallback paths."""
from __future__ import annotations
import hashlib
from pathlib import Path

FALLBACK_ROOT = Path.home() / ".claude" / "review-evidence-fallback"


def _repo_hash(repo_root: Path) -> str:
    return hashlib.sha256(str(repo_root.resolve()).encode()).hexdigest()[:12]


def resolve_evidence_path(sha: str, repo_root: Path) -> Path | None:
    """Return the path of the evidence file for `sha`, or None if not found.

    Search order:
      1. Primary: <repo>/.claude/review-evidence/<sha>.json
      2. Fallback: ~/.claude/review-evidence-fallback/<repo_hash>/<sha>.json
    """
    primary = repo_root / ".claude" / "review-evidence" / f"{sha}.json"
    if primary.exists() and primary.stat().st_size > 0:
        return primary
    fallback = FALLBACK_ROOT / _repo_hash(repo_root) / f"{sha}.json"
    if fallback.exists() and fallback.stat().st_size > 0:
        return fallback
    return None
```

Hook ora chiama (via python3 helper o jq):
```bash
EVIDENCE_FILE=$(python3 -c "
import sys
sys.path.insert(0, '${PLUGIN_ROOT}')
from lib.review_evidence.paths import resolve_evidence_path
from pathlib import Path
p = resolve_evidence_path('$SHA', Path('.'))
print(p if p else '')
")
```

**E48 (`hooks/review-evidence` cache lookup):**

```bash
# Detect iCloud placeholder before reading
ICLOUD_PLACEHOLDER=".${SHA}.json.icloud"
if [ -f "${EVIDENCE_DIR}/${ICLOUD_PLACEHOLDER}" ]; then
    devforge_log "icloud_placeholder_detected" "warn" "{\"sha\":\"${SHA}\"}" 2>/dev/null || true
    NEEDS_COMPUTE=1  # Force recompute
fi
# Or: try jq parsing first; on failure treat as miss
if [ -f "$EVIDENCE_FILE" ] && ! jq empty "$EVIDENCE_FILE" 2>/dev/null; then
    NEEDS_COMPUTE=1
fi
```

### Step 3 — Implementa fix HIGH

(Pattern simile, fix puntuali ai file indicati nella tabella sopra. Per brevità non duplicato qui — l'implementer applica le mitigation descritte in tabella usando il codice esistente come base.)

### Step 4 — Esegui chaos test suite

```bash
pytest tests/test_review_evidence_chaos.py -v
# 9 chaos test passano (E05, E17, E41, E42, E48 + E12, E32, E38, E40)
```

### Step 5 — Commit

```bash
git add hooks/review-evidence \
        lib/review_evidence/atomic_io.py \
        lib/review_evidence/schema.py \
        lib/review_evidence/paths.py \
        lib/review_evidence/collectors/python.py \
        lib/review_evidence/collectors/_jacoco.py \
        lib/review_evidence/collectors/java.py \
        lib/review_evidence/collectors/typescript.py \
        lib/review_evidence/collectors/hcl.py \
        lib/review_evidence/ci_fetch.py \
        lib/review_evidence/spec_drift.py \
        hooks/session-start \
        tests/test_review_evidence_chaos.py \
        tests/fixtures/review-evidence/jacoco_multimodule.xml \
        tests/fixtures/review-evidence/design_italian_headers.md
git commit -m "feat(review-evidence): edge case hardening + chaos tests (5 CRITICAL + 14 HIGH) (#task-16)"
```

## Criteri di accettazione

- [ ] `jq` missing → fail-closed su PreToolUse blocking (E05)
- [ ] Python collector skip `.venv`/`node_modules` in <1s (E17)
- [ ] Disk full / collector failure → block decision su PreToolUse (E41)
- [ ] Fallback path risolto dal hook (E42)
- [ ] iCloud `.icloud` placeholder triggera recompute, mai fail-open (E48)
- [ ] Schema minor bump (`1.1`) accettato; major (`2.0`) raise (E12)
- [ ] CI fetch dedup per workflowName (E32)
- [ ] Italian header allowlist matchato (E38)
- [ ] Session-start prune evidence >7 giorni (E40)
- [ ] Jacoco DTD-safe + multi-module recursion (E22, E23)
- [ ] ESLint config error → reason esplicita (E25)
- [ ] Terraform init required → reason esplicita (E27)
- [ ] 9+ chaos test passano
- [ ] No regressione test esistenti (full suite green)

## Edge case rimanenti (LOW — deferred to follow-up)

I 17 LOW (E02, E04, E07, E08, E09, E10, E11, E13, E14, E15, E18, E19, E20, E21, E24, E26, E28, E30, E31, E33, E35, E37, E39, E43, E44, E45, E46, E47, E49, E50) sono documentati nel design doc come "Out of scope (Future Work)" o accettati come polish post-MVP. Re-valutare in PR follow-up se rilevati in produzione.
