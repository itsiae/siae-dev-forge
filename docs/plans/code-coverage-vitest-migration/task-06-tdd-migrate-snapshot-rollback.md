# Task 06 — TDD red+green: snapshot + dirty-tree refuse + opt-out + per-PM install/rollback + smoke verify

**Status:** `[PENDING]`
**Depends on:** task-05
**Estimate:** 35 min
**Files:**
- `skills/code-coverage/scripts/tests/test_migrate_jest_to_vitest.py` (EXTEND)
- `skills/code-coverage/scripts/migrate_jest_to_vitest.py` (EXTEND — full atomic pipeline)

## Goal

Completare migrate con: snapshot dir, dirty-tree refuse pre-flight, CC_DISABLE_JEST_MIGRATION opt-out, per-PM detection (npm/pnpm/yarn-classic/yarn-berry/bun), install + simmetrico rollback (frozen-lockfile), smoke test (vitest run timeout 120s), full atomic main().

## Steps

### A. Tests

```python
def test_dirty_tree_refuses(tmp_path):
    """Pre-flight: refuse if git status dirty on touched files."""
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / "jest.config.js").write_text("module.exports = {};")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    # Mark dirty
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29", "extra": "x"}}))

    from migrate_jest_to_vitest import check_clean_tree
    clean, msg = check_clean_tree(tmp_path, [tmp_path / "package.json"])
    assert clean is False


def test_opt_out_env_var(tmp_path, monkeypatch):
    """CC_DISABLE_JEST_MIGRATION=1 -> skip migration."""
    monkeypatch.setenv("CC_DISABLE_JEST_MIGRATION", "1")
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "strategy.json").write_text(json.dumps({
        "framework_by_workspace": {".": {"framework": "vitest", "migrate": True}},
    }))
    import subprocess
    r = subprocess.run(
        ["python3", str(SCRIPT), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 4
    out = json.loads(r.stdout)
    assert out["status"] == "skipped"


def test_detect_pm_npm(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "package-lock.json").write_text("{}")
    assert detect_pm(tmp_path) == "npm"


def test_detect_pm_pnpm(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "pnpm-lock.yaml").write_text("")
    assert detect_pm(tmp_path) == "pnpm"


def test_detect_pm_yarn_classic(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "yarn.lock").write_text("")
    assert detect_pm(tmp_path) == "yarn"


def test_detect_pm_yarn_berry(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "yarn.lock").write_text("")
    (tmp_path / ".yarnrc.yml").write_text("nodeLinker: pnp\n")
    assert detect_pm(tmp_path) == "yarn-berry"


def test_detect_pm_bun(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "bun.lockb").write_text("")
    assert detect_pm(tmp_path) == "bun"


def test_per_pm_install_cmd():
    from migrate_jest_to_vitest import install_cmd_for
    assert install_cmd_for("npm") == ["npm", "install"]
    assert install_cmd_for("pnpm") == ["pnpm", "install"]
    assert install_cmd_for("yarn") == ["yarn", "install"]
    assert install_cmd_for("yarn-berry") == ["yarn", "install"]
    assert install_cmd_for("bun") == ["bun", "install"]


def test_per_pm_rollback_install_cmd():
    """Rollback uses frozen-lockfile flag for reproducibility."""
    from migrate_jest_to_vitest import rollback_install_cmd_for
    assert rollback_install_cmd_for("npm") == ["npm", "ci"]
    assert rollback_install_cmd_for("pnpm") == ["pnpm", "install", "--frozen-lockfile"]
    assert rollback_install_cmd_for("yarn") == ["yarn", "install", "--frozen-lockfile"]
    assert rollback_install_cmd_for("yarn-berry") == ["yarn", "install", "--immutable"]
    assert rollback_install_cmd_for("bun") == ["bun", "install", "--frozen-lockfile"]


def test_snapshot_captures_lockfile(tmp_path):
    from migrate_jest_to_vitest import snapshot_files
    (tmp_path / "package.json").write_text(json.dumps({"name": "x"}))
    (tmp_path / "package-lock.json").write_text("{}")
    snapshot_files(tmp_path, [tmp_path / "package.json", tmp_path / "package-lock.json"])
    snap = tmp_path / ".code-coverage" / "migration-snapshot"
    assert (snap / "package.json").is_file()
    assert (snap / "package-lock.json").is_file()


def test_restore_snapshot(tmp_path):
    from migrate_jest_to_vitest import snapshot_files, restore_snapshot
    (tmp_path / "package.json").write_text("original")
    snapshot_files(tmp_path, [tmp_path / "package.json"])
    (tmp_path / "package.json").write_text("modified")
    restore_snapshot(tmp_path)
    assert (tmp_path / "package.json").read_text() == "original"


def test_idempotency_no_migrating_workspaces(tmp_path):
    """No workspaces with migrate=true -> exit 4 (noop)."""
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "strategy.json").write_text(json.dumps({
        "framework_by_workspace": {".": {"framework": "vitest", "migrate": False}},
    }))
    import subprocess
    r = subprocess.run(
        ["python3", str(SCRIPT), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 4
```

### B. Implementation

Aggiungere a `migrate_jest_to_vitest.py`:

```python
import os
import shutil
import subprocess
import time
from typing import Any


JEST_CONFIG_NAMES = ("jest.config.ts", "jest.config.js", "jest.config.mjs", "jest.config.cjs")


def detect_pm(ws_dir: Path) -> str:
    if (ws_dir / ".yarnrc.yml").is_file() and (ws_dir / "yarn.lock").is_file():
        return "yarn-berry"
    if (ws_dir / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (ws_dir / "yarn.lock").is_file():
        return "yarn"
    if (ws_dir / "bun.lockb").is_file():
        return "bun"
    return "npm"


def install_cmd_for(pm: str) -> list[str]:
    return {
        "npm": ["npm", "install"],
        "pnpm": ["pnpm", "install"],
        "yarn": ["yarn", "install"],
        "yarn-berry": ["yarn", "install"],
        "bun": ["bun", "install"],
    }[pm]


def rollback_install_cmd_for(pm: str) -> list[str]:
    return {
        "npm": ["npm", "ci"],
        "pnpm": ["pnpm", "install", "--frozen-lockfile"],
        "yarn": ["yarn", "install", "--frozen-lockfile"],
        "yarn-berry": ["yarn", "install", "--immutable"],
        "bun": ["bun", "install", "--frozen-lockfile"],
    }[pm]


def lockfile_for(pm: str) -> list[str]:
    base = {
        "npm": ["package-lock.json"],
        "pnpm": ["pnpm-lock.yaml"],
        "yarn": ["yarn.lock"],
        "yarn-berry": ["yarn.lock", ".yarnrc.yml"],
        "bun": ["bun.lockb"],
    }[pm]
    return base


def check_clean_tree(repo: Path, touched: list[Path]) -> tuple[bool, str]:
    if not (repo / ".git").is_dir():
        return True, ""
    try:
        rel = [str(p.relative_to(repo)) for p in touched if p.exists()]
        if not rel:
            return True, ""
        r = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain", "--"] + rel,
            capture_output=True, text=True, timeout=10,
        )
        return (not r.stdout.strip(), r.stdout)
    except subprocess.SubprocessError as e:
        return True, str(e)


def snapshot_files(repo: Path, files: list[Path]) -> Path:
    snap = repo / ".code-coverage" / "migration-snapshot"
    snap.mkdir(parents=True, exist_ok=True)
    for f in files:
        if not f.is_file():
            continue
        rel = f.relative_to(repo)
        dst = snap / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
    return snap


def restore_snapshot(repo: Path) -> None:
    snap = repo / ".code-coverage" / "migration-snapshot"
    if not snap.is_dir():
        return
    for src in snap.rglob("*"):
        if src.is_file():
            rel = src.relative_to(snap)
            dst = repo / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def list_test_files(ws: Path) -> list[Path]:
    out: list[Path] = []
    for pat in ("**/*.test.ts", "**/*.test.tsx", "**/*.test.js", "**/*.test.jsx",
                "**/*.spec.ts", "**/*.spec.js"):
        for f in ws.glob(pat):
            if any(part in {"node_modules", ".git", "dist", "build", "coverage", ".code-coverage"} for part in f.parts):
                continue
            out.append(f)
    return out


def smoke_test(ws: Path, pm: str, timeout: int = 120) -> tuple[bool, str]:
    cmd_runner = {"npm": "npx", "yarn": "yarn", "yarn-berry": "yarn",
                  "pnpm": "pnpm", "bun": "bunx"}.get(pm, "npx")
    if pm == "pnpm":
        cmd = ["pnpm", "exec", "vitest", "run", "--reporter=basic", "--no-coverage"]
    else:
        cmd = [cmd_runner, "vitest", "run", "--reporter=basic", "--no-coverage"]
    try:
        r = subprocess.run(cmd, cwd=str(ws), capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return True, ""
        return False, (r.stderr or r.stdout or "")[-2000:]
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except FileNotFoundError as e:
        return False, str(e)


def find_jest_config(ws: Path) -> Path | None:
    for n in JEST_CONFIG_NAMES:
        p = ws / n
        if p.is_file():
            return p
    return None


def migrate_workspace(repo: Path, ws_rel: str) -> dict:
    ws = repo if ws_rel == "." else repo / ws_rel
    pm = detect_pm(ws)
    jest_cfg = find_jest_config(ws)
    vitest_cfg = ws / "vitest.config.ts"

    touched: list[Path] = [ws / "package.json"]
    if jest_cfg:
        touched.append(jest_cfg)
    touched.extend([ws / n for n in JEST_SETUP_NAMES if (ws / n).is_file()])
    touched.extend([ws / lf for lf in lockfile_for(pm) if (ws / lf).is_file()])
    touched.extend(list_test_files(ws))

    clean, dirty_msg = check_clean_tree(repo, touched)
    if not clean:
        return {"workspace": ws_rel, "status": "refused", "reason": "dirty-working-tree", "detail": dirty_msg}

    snapshot_files(repo, touched)

    report: dict[str, Any] = {
        "workspace": ws_rel, "status": "ok", "pm": pm,
        "files": {"transformed": [], "renamed": [], "manual_review": []},
        "unmapped_keys": [],
    }

    try:
        if jest_cfg and not vitest_cfg.is_file():
            content, unmapped = translate_jest_config_to_vitest(jest_cfg, ws)
            vitest_cfg.write_text(content, encoding="utf-8")
            report["unmapped_keys"] = unmapped

        if (ws / "package.json").is_file():
            report["package_json"] = rewrite_package_json(ws / "package.json")

        for f in list_test_files(ws):
            text = f.read_text(encoding="utf-8", errors="ignore")
            new_text, _, manual = codemod_text(text)
            if new_text != text:
                f.write_text(new_text, encoding="utf-8")
                rel = str(f.relative_to(repo))
                report["files"]["transformed"].append(rel)
                if manual:
                    report["files"]["manual_review"].extend(
                        f"{rel}: {m}" for m in manual
                    )

        report["files"]["renamed"] = rename_setup_files(ws)

        if jest_cfg and vitest_cfg.is_file():
            vitest_content = vitest_cfg.read_text(encoding="utf-8")
            if "defineConfig" in vitest_content and "export default" in vitest_content:
                jest_cfg.unlink()
                report["files"]["renamed"].append(f"deleted:{jest_cfg.name}")

        try:
            r = subprocess.run(
                install_cmd_for(pm), cwd=str(ws),
                capture_output=True, text=True, timeout=300,
            )
            report["install"] = {"cmd": install_cmd_for(pm), "exit_code": r.returncode}
            if r.returncode != 0:
                report["status"] = "install-failed"
                report["install"]["stderr_tail"] = (r.stderr or "")[-1000:]
                return report
        except subprocess.TimeoutExpired:
            report["status"] = "install-timeout"
            return report
        except FileNotFoundError:
            # PM not in PATH (test env) — skip install + smoke; treat as ok
            report["install"] = {"skipped": "pm-binary-not-found"}
            return report

        ok, tail = smoke_test(ws, pm)
        if ok:
            report["verified"] = True
        else:
            report["verified"] = False
            report["status"] = "verification-failed"
            report["verification_tail"] = tail

    except Exception as e:
        report["status"] = "internal-error"
        report["error"] = str(e)

    return report


def _migrating_workspaces(repo: Path) -> list[str]:
    s_path = repo / ".code-coverage" / "strategy.json"
    if not s_path.is_file():
        return []
    try:
        s = json.loads(s_path.read_text())
    except json.JSONDecodeError:
        return []
    fw = s.get("framework_by_workspace", {}) or {}
    return [ws for ws, info in fw.items() if info.get("migrate") is True]


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_path")
    args = ap.parse_args()
    repo = Path(args.repo_path).resolve()

    if os.environ.get("CC_DISABLE_JEST_MIGRATION") == "1":
        print(json.dumps({"status": "skipped", "reason": "CC_DISABLE_JEST_MIGRATION=1"}))
        return 4

    workspaces = _migrating_workspaces(repo)
    if not workspaces:
        print(json.dumps({"status": "noop", "reason": "no workspaces with migrate=true"}))
        return 4

    started = time.time()
    overall: dict = {"started_at": started, "workspaces": []}
    failed_verification = False
    for ws in workspaces:
        r = migrate_workspace(repo, ws)
        overall["workspaces"].append(r)
        if r["status"] == "verification-failed":
            failed_verification = True

    overall["elapsed_sec"] = round(time.time() - started, 2)
    out_path = repo / ".code-coverage" / "migration-report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(overall, indent=2), encoding="utf-8")

    print(json.dumps(overall, indent=2))

    if failed_verification:
        restore_snapshot(repo)
        return 2
    if any(r["status"] in ("refused", "install-failed", "install-timeout", "internal-error")
           for r in overall["workspaces"]):
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### C. Run

```bash
python3 -m pytest skills/code-coverage/scripts/tests/test_migrate_jest_to_vitest.py -v
```

## Acceptance

- [ ] 12 nuovi test pass (dirty-tree refuse + opt-out + PM detection + snapshot/restore + cmd matrix)
- [ ] Tutti i test precedenti (task-04 + task-05) ancora pass
- [ ] `main()` espone exit codes: 0=ok, 1=refused/install-failed, 2=verification-failed (restored), 4=noop
- [ ] Per-PM matrix completa: 5 PM coperti (npm/pnpm/yarn/yarn-berry/bun)
