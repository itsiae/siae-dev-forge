#!/usr/bin/env bash
# detect_stacks.sh — phase 1 stack detector.
#
# Walks one or more roots (absolute paths) and emits a JSON inventory
# of detected analysis units and their stack ids. Read-only: it never
# writes inside the target roots.
#
# Output: JSON to stdout with shape:
#   { "units": [ { "unit_id": "...", "root": "...", "stack_ids": [...], "manifests": [...] }, ... ] }
#
# Falls back to scripts/_json_helpers.py when jq is unavailable.
#
# Usage:
#   scripts/detect_stacks.sh /abs/path/repoA /abs/path/repoB

set -u

if [ "$#" -lt 1 ]; then
  echo '{"error":"no roots provided","units":[]}'
  exit 2
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo '{"error":"python3 required","units":[]}'
  exit 2
fi

# We delegate to Python for everything that benefits from structured data
# (file walking, glob matching, JSON emission). Bash here is just the
# entry point.

ROOTS_JSON="$($PY - "$@" <<'PYIN'
import json, sys
print(json.dumps(sys.argv[1:]))
PYIN
)"

# Patterns are kept in sync with references/stacks/INDEX.md.
# Each line: <stack_id>::<glob>
PATTERN_LIST=$(cat <<'PATTERNS'
java::pom.xml
java::build.gradle
java::build.gradle.kts
java::settings.gradle
java::settings.gradle.kts
kotlin::build.gradle.kts
scala::build.sbt
scala::build.sc
typescript-javascript::package.json
typescript-javascript::tsconfig.json
typescript-javascript::pnpm-workspace.yaml
typescript-javascript::turbo.json
typescript-javascript::nx.json
python::pyproject.toml
python::requirements.txt
python::setup.py
python::setup.cfg
python::Pipfile
go::go.mod
go::go.work
rust::Cargo.toml
swift::Package.swift
swift::Podfile
ruby::Gemfile
ruby::Gemfile.lock
dotnet::*.csproj
dotnet::*.sln
dotnet::global.json
flutter-dart::pubspec.yaml
terraform-hcl::*.tf
terraform-hcl::terragrunt.hcl
aws-serverless::template.yaml
aws-serverless::template.yml
aws-serverless::cdk.json
aws-serverless::serverless.yml
aws-serverless::*.asl.json
data-platform::dbt_project.yml
data-platform::airflow.cfg
PATTERNS
)

export ROOTS_JSON PATTERN_LIST

"$PY" - <<'PYEND'
import fnmatch
import json
import os
import sys
from pathlib import Path

roots = json.loads(os.environ["ROOTS_JSON"])
patterns = []
for line in os.environ["PATTERN_LIST"].splitlines():
    line = line.strip()
    if not line or "::" not in line:
        continue
    sid, glob = line.split("::", 1)
    patterns.append((sid, glob))

# Default exclusions — applied as path-component blacklists.
EXCLUDE_DIRS = {
    ".git", "node_modules", "vendor", "target", "dist", "build",
    ".terraform", "__pycache__", ".idea", ".vscode", ".gradle",
    ".next", ".turbo", ".pnpm-store",
}

MAX_FILES_PER_UNIT = 10000

units = []
for root in roots:
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        units.append({
            "unit_id": "missing:" + os.path.basename(root),
            "root": root,
            "stack_ids": [],
            "manifests": [],
            "error": "not a directory",
        })
        continue

    stack_hits: dict[str, list[str]] = {}
    file_count = 0
    cap_hit = False
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs in-place to avoid descending
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            file_count += 1
            if file_count > MAX_FILES_PER_UNIT:
                cap_hit = True
                break
            for sid, glob in patterns:
                if fnmatch.fnmatch(fn, glob):
                    rel = os.path.relpath(os.path.join(dirpath, fn), root)
                    stack_hits.setdefault(sid, []).append(rel)
        if cap_hit:
            break

    if not stack_hits:
        stack_ids = ["_generic"]
        manifests = []
    else:
        stack_ids = sorted(stack_hits.keys())
        manifests = []
        for sid in stack_ids:
            for rel in stack_hits[sid][:25]:  # keep manifests list bounded
                manifests.append({"stack_id": sid, "path": rel})

    units.append({
        "unit_id": "single:" + os.path.basename(root),
        "root": root,
        "stack_ids": stack_ids,
        "manifests": manifests,
        "file_count": file_count,
        "cap_hit": cap_hit,
    })

json.dump({"units": units}, sys.stdout, indent=2, sort_keys=True)
sys.stdout.write("\n")
PYEND
