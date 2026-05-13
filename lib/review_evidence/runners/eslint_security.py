"""ESLint security plugin runner (TS/JS)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings

_JS_GLOBS = ("*.ts", "*.tsx", "*.js", "*.jsx")


class EslintSecurityRunner:
    name = "eslint-security"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        if not (repo_root / "package.json").exists():
            return False
        for pattern in _JS_GLOBS:
            for _ in repo_root.rglob(pattern):
                return True
        return False

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                [
                    "npx",
                    "--no-install",
                    "eslint",
                    ".",
                    "--format",
                    "json",
                    "--no-eslintrc",
                    "--plugin",
                    "security",
                    "--rule",
                    '{"security/detect-eval-with-expression":"error",'
                    '"security/detect-non-literal-fs-filename":"warn"}',
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            errors = sum(f.get("errorCount", 0) for f in data)
            warnings = sum(f.get("warningCount", 0) for f in data)
            # eslint-security: errors → high, warnings → medium (no critical)
            return SecurityFindings(high=errors, medium=warnings)
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(EslintSecurityRunner())
