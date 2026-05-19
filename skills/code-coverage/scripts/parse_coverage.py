#!/usr/bin/env python3
"""parse_coverage.py — parser deterministico di coverage report.

Sostituisce il pattern fragile `tail -n 100 + grep` con parsing JSON tipato
da reporter standardizzati: --coverage.reporter=json-summary (Vitest/Jest),
--cov-report=json (pytest), JaCoCo XML, etc.

Usage:
    python3 parse_coverage.py <framework> <input-file>

Frameworks supportati:
    vitest, jest, pytest, jacoco, kover, go-test, cargo, dotnet,
    cargo-tarpaulin, cargo-llvm-cov, dotnet-cobertura, lcov

Output (stdout): JSON con schema:
    {
        "global_pct": float,
        "global_branch_pct": float,
        "modules": [
            {"path": str, "lines_pct": float, "branch_pct": float,
             "priority": "P1"|"P2"|"P3"|null, "threshold": float, "status": "PASS"|"FAIL"}
        ],
        "failing": [str],
        "framework": str,
        "error": str | null
    }

Exit code: 0 in tutti i casi (parse error veicolato in JSON `error` field).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_THRESHOLDS = {"P1": 80.0, "P2": 70.0, "P3": 60.0, "default": 70.0}

# Framework → emette branch coverage realmente? Falso per go-test (statements) e
# cargo-tarpaulin (line-only). I parser che emettono branch ma con 0% reale
# devono essere comunque gate-d → vedi parse() loop.
PARSER_EMITS_BRANCH: dict[str, bool] = {
    "vitest": True,
    "jest": True,
    "pytest": True,
    "jacoco": True,
    "kover": True,
    "cargo-llvm-cov": True,
    "cargo": False,
    "cargo-tarpaulin": False,
    "go-test": False,
    "dotnet": True,
    "dotnet-cobertura": True,
    "lcov": True,
}


def parse_vitest_or_jest(data: dict) -> tuple[float, float, list[dict]]:
    total = data.get("total", {})
    global_pct = float(total.get("lines", {}).get("pct", 0))
    global_branch_pct = float(total.get("branches", {}).get("pct", 0))
    modules = []
    for path, metrics in data.items():
        if path == "total":
            continue
        if not isinstance(metrics, dict):
            continue
        branches_block = metrics.get("branches", {})
        lines_pct = float(metrics.get("lines", {}).get("pct", 0))
        branch_pct = float(branches_block.get("pct", 0))
        has_branches = int(branches_block.get("total", 0)) > 0
        modules.append({
            "path": path,
            "lines_pct": lines_pct,
            "branch_pct": branch_pct,
            "has_testable_branches": has_branches,
        })
    return global_pct, global_branch_pct, modules


def parse_pytest_cov(data: dict) -> tuple[float, float, list[dict]]:
    totals = data.get("totals", {})
    global_pct = float(totals.get("percent_covered", 0))
    num_branches = totals.get("num_branches", 0)
    covered_branches = totals.get("covered_branches", 0)
    global_branch_pct = (covered_branches / num_branches * 100) if num_branches else 0.0
    modules = []
    for path, info in data.get("files", {}).items():
        summary = info.get("summary", {})
        nb = summary.get("num_branches", 0)
        cb = summary.get("covered_branches", 0)
        modules.append({
            "path": path,
            "lines_pct": float(summary.get("percent_covered", 0)),
            "branch_pct": (cb / nb * 100) if nb else 0.0,
            "has_testable_branches": nb > 0,
        })
    return global_pct, global_branch_pct, modules


def parse_jacoco_xml(content: str) -> tuple[float, float, list[dict]]:
    line_match = re.search(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', content)
    branch_match = re.search(r'<counter type="BRANCH" missed="(\d+)" covered="(\d+)"', content)
    if not line_match:
        return 0.0, 0.0, []
    line_missed, line_covered = int(line_match.group(1)), int(line_match.group(2))
    line_total = line_missed + line_covered
    global_pct = (line_covered / line_total * 100) if line_total else 0.0
    if branch_match:
        b_missed, b_covered = int(branch_match.group(1)), int(branch_match.group(2))
        b_total = b_missed + b_covered
        global_branch_pct = (b_covered / b_total * 100) if b_total else 0.0
    else:
        global_branch_pct = 0.0
    modules = []
    for pkg in re.finditer(r'<package name="([^"]+)">(.*?)</package>', content, re.DOTALL):
        pkg_name = pkg.group(1)
        pkg_body = pkg.group(2)
        # Rimuovi <class>...</class> e <sourcefile>...</sourcefile> per isolare i
        # counter package-level (che JaCoCo emette dopo i child element). Senza
        # questo strip, il primo regex match cattura un counter method/class-level.
        pkg_body_stripped = re.sub(r'<class\b.*?</class>', '', pkg_body, flags=re.DOTALL)
        pkg_body_stripped = re.sub(
            r'<sourcefile\b.*?</sourcefile>', '', pkg_body_stripped, flags=re.DOTALL
        )
        pkg_line = re.search(
            r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', pkg_body_stripped
        )
        pkg_branch = re.search(
            r'<counter type="BRANCH" missed="(\d+)" covered="(\d+)"', pkg_body_stripped
        )
        if pkg_line:
            pm, pc = int(pkg_line.group(1)), int(pkg_line.group(2))
            pt = pm + pc
            if pkg_branch:
                bm, bc = int(pkg_branch.group(1)), int(pkg_branch.group(2))
                bt = bm + bc
                branch_pct_pkg = (bc / bt * 100) if bt else 0.0
                pkg_has_branches = bt > 0
            else:
                branch_pct_pkg = 0.0
                pkg_has_branches = False
            modules.append({
                "path": pkg_name.replace("/", "."),
                "lines_pct": (pc / pt * 100) if pt else 0.0,
                "branch_pct": branch_pct_pkg,
                "has_testable_branches": pkg_has_branches,
            })
    return global_pct, global_branch_pct, modules


def parse_go_cover(content: str) -> tuple[float, float, list[dict]]:
    modules: dict[str, list[float]] = {}
    global_pct = 0.0
    for line in content.splitlines():
        m = re.match(r'^([^:]+\.go):\d+:\s+\S+\s+(\d+\.?\d*)%', line)
        if m:
            path = m.group(1)
            pct = float(m.group(2))
            modules.setdefault(path, []).append(pct)
            continue
        total_m = re.search(r'^total:\s+\(statements\)\s+(\d+\.?\d*)%', line)
        if total_m:
            global_pct = float(total_m.group(1))
    module_list = [
        {
            "path": p,
            "lines_pct": sum(pcts) / len(pcts),
            "branch_pct": 0.0,
            "has_testable_branches": False,
        }
        for p, pcts in modules.items()
    ]
    return global_pct, 0.0, module_list


def parse_cargo_tarpaulin(data: dict) -> tuple[float, float, list[dict]]:
    files_data = data.get("files", [])
    total_covered = sum(f.get("covered", 0) for f in files_data)
    total_coverable = sum(f.get("coverable", 0) for f in files_data)
    global_pct = (total_covered / total_coverable * 100) if total_coverable else 0.0
    modules = []
    for f in files_data:
        cov = f.get("covered", 0)
        coverable = f.get("coverable", 0)
        modules.append({
            "path": f.get("path", "unknown"),
            "lines_pct": (cov / coverable * 100) if coverable else 0.0,
            "branch_pct": 0.0,
            "has_testable_branches": False,
        })
    return global_pct, 0.0, modules


def parse_cobertura_xml(content: str) -> tuple[float, float, list[dict]]:
    """Parser per Cobertura XML (coverlet .NET, coverage.py xml, Cobertura nativo).

    Schema: root `<coverage line-rate="X" branch-rate="Y">` con `<class filename=...
    line-rate=... branch-rate=...>` annidate sotto `<packages><package><classes>`.
    Usa ElementTree per robustezza, con fallback regex se XML malformato.
    """
    try:
        root = ET.fromstring(content)
        line_rate = float(root.get("line-rate", 0))
        branch_rate = float(root.get("branch-rate", 0))
        global_pct = line_rate * 100
        global_branch_pct = branch_rate * 100
        modules = []
        for cls in root.iter("class"):
            filename = cls.get("filename") or cls.get("name") or "unknown"
            cls_line_rate = float(cls.get("line-rate", 0))
            cls_branch_rate = float(cls.get("branch-rate", 0))
            cls_has_branches = "branch-rate" in cls.attrib
            modules.append({
                "path": filename,
                "lines_pct": cls_line_rate * 100,
                "branch_pct": cls_branch_rate * 100,
                "has_testable_branches": cls_has_branches,
            })
        return global_pct, global_branch_pct, modules
    except ET.ParseError:
        # Fallback regex su XML malformato
        root_match = re.search(
            r'<coverage[^>]*\bline-rate="([0-9.]+)"[^>]*\bbranch-rate="([0-9.]+)"',
            content,
        )
        if not root_match:
            root_match = re.search(
                r'<coverage[^>]*\bbranch-rate="([0-9.]+)"[^>]*\bline-rate="([0-9.]+)"',
                content,
            )
            if root_match:
                branch_rate, line_rate = float(root_match.group(1)), float(root_match.group(2))
            else:
                line_match = re.search(r'<coverage[^>]*\bline-rate="([0-9.]+)"', content)
                line_rate = float(line_match.group(1)) if line_match else 0.0
                branch_rate = 0.0
        else:
            line_rate, branch_rate = float(root_match.group(1)), float(root_match.group(2))
        global_pct = line_rate * 100
        global_branch_pct = branch_rate * 100
        modules = []
        for cls in re.finditer(
            r'<class\b([^>]*)\s*(?:/>|>)',
            content,
        ):
            attrs = cls.group(1)
            fn_m = re.search(r'filename="([^"]+)"', attrs)
            if not fn_m:
                fn_m = re.search(r'\bname="([^"]+)"', attrs)
            lr_m = re.search(r'line-rate="([0-9.]+)"', attrs)
            br_m = re.search(r'branch-rate="([0-9.]+)"', attrs)
            if not fn_m or not lr_m:
                continue
            modules.append({
                "path": fn_m.group(1),
                "lines_pct": float(lr_m.group(1)) * 100,
                "branch_pct": float(br_m.group(1)) * 100 if br_m else 0.0,
                "has_testable_branches": br_m is not None,
            })
        return global_pct, global_branch_pct, modules


def parse_cargo_llvm_cov(data: dict) -> tuple[float, float, list[dict]]:
    """Parser per output `cargo llvm-cov --json`.

    Schema: `{data: [{files: [{filename, summary: {lines: {percent}, branches: {percent}}}],
    totals: {lines: {percent}, branches: {percent}}}]}`.
    """
    data_list = data.get("data", [])
    if not data_list:
        return 0.0, 0.0, []
    first = data_list[0]
    totals = first.get("totals", {})
    global_pct = float(totals.get("lines", {}).get("percent", 0))
    global_branch_pct = float(totals.get("branches", {}).get("percent", 0))
    modules = []
    for f in first.get("files", []):
        summary = f.get("summary", {})
        lines = summary.get("lines", {})
        branches = summary.get("branches", {})
        modules.append({
            "path": f.get("filename", "unknown"),
            "lines_pct": float(lines.get("percent", 0)),
            "branch_pct": float(branches.get("percent", 0)),
            "has_testable_branches": int(branches.get("count", 0)) > 0,
        })
    return global_pct, global_branch_pct, modules


def parse_lcov(content: str) -> tuple[float, float, list[dict]]:
    """Parser per formato lcov.info (Flutter, simplecov-lcov, c8, ecc.).

    Record per file delimitati da `SF:<path>` ... `end_of_record`. Conta
    `LH` (lines hit) / `LF` (lines found) per linee, `BRH`/`BRF` per branch.
    """
    modules: list[dict] = []
    total_lh = 0
    total_lf = 0
    total_brh = 0
    total_brf = 0
    current: dict | None = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("SF:"):
            current = {
                "path": line[3:],
                "lh": 0,
                "lf": 0,
                "brh": 0,
                "brf": 0,
            }
        elif line.startswith("LF:") and current is not None:
            try:
                current["lf"] = int(line[3:])
            except ValueError:
                pass
        elif line.startswith("LH:") and current is not None:
            try:
                current["lh"] = int(line[3:])
            except ValueError:
                pass
        elif line.startswith("BRF:") and current is not None:
            try:
                current["brf"] = int(line[4:])
            except ValueError:
                pass
        elif line.startswith("BRH:") and current is not None:
            try:
                current["brh"] = int(line[4:])
            except ValueError:
                pass
        elif line == "end_of_record" and current is not None:
            lf = current["lf"]
            lh = current["lh"]
            brf = current["brf"]
            brh = current["brh"]
            total_lf += lf
            total_lh += lh
            total_brf += brf
            total_brh += brh
            modules.append({
                "path": current["path"],
                "lines_pct": (lh / lf * 100) if lf else 0.0,
                "branch_pct": (brh / brf * 100) if brf else 0.0,
                "has_testable_branches": brf > 0,
            })
            current = None
    global_pct = (total_lh / total_lf * 100) if total_lf else 0.0
    global_branch_pct = (total_brh / total_brf * 100) if total_brf else 0.0
    return global_pct, global_branch_pct, modules


def parse_jacoco_multi(paths: list[Path]) -> tuple[float, float, list[dict]]:
    """Aggrega multipli jacoco.xml/report.xml (Spring Boot multi-module, Kover).

    Somma i counter root `LINE`/`BRANCH` di ciascun file e concatena i package.
    Riusa `parse_jacoco_xml` per il parsing del singolo file e ricompone i totali
    direttamente dai contatori root (riparseati) per evitare drift su weighted avg.
    """
    total_line_missed = 0
    total_line_covered = 0
    total_branch_missed = 0
    total_branch_covered = 0
    all_modules: list[dict] = []
    for p in paths:
        try:
            content = p.read_text()
        except OSError:
            continue
        # Estrai counter root (primo match dopo l'apertura <report>)
        line_match = re.search(
            r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', content
        )
        branch_match = re.search(
            r'<counter type="BRANCH" missed="(\d+)" covered="(\d+)"', content
        )
        if line_match:
            total_line_missed += int(line_match.group(1))
            total_line_covered += int(line_match.group(2))
        if branch_match:
            total_branch_missed += int(branch_match.group(1))
            total_branch_covered += int(branch_match.group(2))
        _, _, modules = parse_jacoco_xml(content)
        all_modules.extend(modules)
    line_total = total_line_missed + total_line_covered
    branch_total = total_branch_missed + total_branch_covered
    global_pct = (total_line_covered / line_total * 100) if line_total else 0.0
    global_branch_pct = (total_branch_covered / branch_total * 100) if branch_total else 0.0
    return global_pct, global_branch_pct, all_modules


def _glob_to_regex(pattern: str) -> str:
    """Converte glob in regex senza cascade re-replace.

    Bug previo: `.replace("**/", ".*/").replace("**", ".*").replace("*", "[^/]*")`
    re-processava l'asterisco dentro `.*/` gia' sostituito → `**/foo/*.py` diventava
    `.[^/]*/foo/[^/]*.py` (con `.` letterale invece di `.*`).

    Strategia: usa sentinel uniche per `**/` e `**`, sostituisce `*` singolo,
    ripristina sentinel a `.*/` / `.*`.
    """
    SENT_DSTAR_SLASH = "\x00DSTARSLASH\x00"
    SENT_DSTAR = "\x00DSTAR\x00"
    s = pattern.replace("**/", SENT_DSTAR_SLASH).replace("**", SENT_DSTAR)
    s = s.replace("*", "[^/]*")
    return s.replace(SENT_DSTAR, ".*").replace(SENT_DSTAR_SLASH, ".*/")


def assign_priority_and_threshold(
    path: str, priority_rules: dict | None
) -> tuple[str | None, float, float]:
    """Ritorna (priority, line_threshold, branch_threshold).

    branch_threshold viene letto da `min_branch_pct` con fallback a `min_coverage_pct - 10`
    per backward-compat con priority-rules.json senza il nuovo campo.

    Classification: prima match diretto su ``parent_dirs`` (basename del dir
    contenitore, niente glob → niente false-positive su dir intermedie di
    package layout), poi fallback a ``path_patterns`` glob per backward-compat.
    """
    default_line = DEFAULT_THRESHOLDS["default"]
    default_branch = max(0.0, default_line - 10.0)
    if not priority_rules:
        return None, default_line, default_branch
    levels = priority_rules.get("priority_levels", {})

    # parent dir basename (immediato sopra il file)
    dirname = path.rsplit("/", 1)[0] if "/" in path else ""
    parent = dirname.rsplit("/", 1)[-1] if dirname else ""

    # Pass 1: parent_dirs match (preferito)
    if parent:
        for level_name in ("P1", "P2", "P3"):
            level = levels.get(level_name, {})
            if parent in level.get("parent_dirs", []):
                line_thr = float(level.get("min_coverage_pct", default_line))
                branch_thr = float(level.get("min_branch_pct", max(0.0, line_thr - 10.0)))
                return level_name, line_thr, branch_thr
    # Pass 2: path_patterns fallback (backward-compat)
    for level_name in ("P1", "P2", "P3"):
        level = levels.get(level_name, {})
        patterns = level.get("path_patterns", [])
        for pattern in patterns:
            regex = _glob_to_regex(pattern)
            if re.search(regex, path):
                line_thr = float(level.get("min_coverage_pct", default_line))
                branch_thr = float(level.get("min_branch_pct", max(0.0, line_thr - 10.0)))
                return level_name, line_thr, branch_thr
    return None, default_line, default_branch


def load_priority_rules(skill_root: Path) -> dict | None:
    rules_path = skill_root / "assets" / "priority-rules.json"
    if not rules_path.exists():
        return None
    try:
        with open(rules_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def parse(framework: str, input_path: Path, priority_rules: dict | None) -> dict:
    if not input_path.exists():
        return {
            "global_pct": 0.0,
            "global_branch_pct": 0.0,
            "modules": [],
            "failing": [],
            "framework": framework,
            "error": f"Input file does not exist: {input_path}",
        }
    try:
        if framework in ("jacoco", "kover"):
            if input_path.is_dir():
                # Spring Boot multi-module / Kover: aggrega tutti gli XML trovati
                xml_paths = sorted(input_path.rglob("jacoco.xml")) + sorted(
                    input_path.rglob("report.xml")
                )
                if not xml_paths:
                    return {
                        "global_pct": 0.0,
                        "global_branch_pct": 0.0,
                        "modules": [],
                        "failing": [],
                        "framework": framework,
                        "error": (
                            f"Nessun jacoco.xml/report.xml trovato in {input_path}"
                        ),
                    }
                global_pct, branch_pct, modules = parse_jacoco_multi(xml_paths)
            else:
                content = input_path.read_text()
                global_pct, branch_pct, modules = parse_jacoco_xml(content)
        elif framework == "go-test":
            content = input_path.read_text()
            global_pct, branch_pct, modules = parse_go_cover(content)
        elif framework in ("dotnet", "dotnet-cobertura"):
            content = input_path.read_text()
            global_pct, branch_pct, modules = parse_cobertura_xml(content)
        elif framework == "lcov":
            content = input_path.read_text()
            global_pct, branch_pct, modules = parse_lcov(content)
        else:
            with open(input_path) as f:
                data = json.load(f)
            if framework in ("vitest", "jest"):
                global_pct, branch_pct, modules = parse_vitest_or_jest(data)
            elif framework == "pytest":
                global_pct, branch_pct, modules = parse_pytest_cov(data)
            elif framework in ("cargo", "cargo-tarpaulin"):
                global_pct, branch_pct, modules = parse_cargo_tarpaulin(data)
            elif framework == "cargo-llvm-cov":
                global_pct, branch_pct, modules = parse_cargo_llvm_cov(data)
            else:
                return {
                    "global_pct": 0.0,
                    "global_branch_pct": 0.0,
                    "modules": [],
                    "failing": [],
                    "framework": framework,
                    "error": f"Framework non supportato: {framework}",
                }
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "global_pct": 0.0,
            "global_branch_pct": 0.0,
            "modules": [],
            "failing": [],
            "framework": framework,
            "error": f"Parse error: {e}",
        }

    parser_emits_branch = PARSER_EMITS_BRANCH.get(framework, False)
    enriched = []
    failing = []
    for m in modules:
        pri, line_threshold, branch_threshold = assign_priority_and_threshold(m["path"], priority_rules)
        line_ok = m["lines_pct"] >= line_threshold
        # Gate branch: skip se parser non emette branch, OPPURE se il modulo
        # non ha branch testabili (es. data class, getter-only). Distinzione critica:
        #   branch_pct=0 con num_branches=0 == nothing-to-test → PASS legittimo
        #   branch_pct=0 con num_branches>0 == untested branches → FAIL legittimo
        # Backward-compat: se il parser non emette `has_testable_branches`,
        # defaultiamo a `parser_emits_branch` (gate applicato normalmente).
        module_has_branches = m.get("has_testable_branches", parser_emits_branch)
        if not parser_emits_branch or not module_has_branches:
            branch_ok = True
        else:
            branch_ok = m.get("branch_pct", 0.0) >= branch_threshold
        # branch_status: distingue le 3 condizioni che producono branch_ok=True per
        # consentire a Phase 7 di non confondere "parser cieco" con "modulo senza
        # branch da testare". Senza questo flag, go-test/cargo/tarpaulin passerebbero
        # silenziosamente il gate branch creando falsa sicurezza.
        if not parser_emits_branch:
            branch_status = "BRANCH_NOT_MEASURED"
        elif not module_has_branches:
            branch_status = "NO_TESTABLE_BRANCHES"
        else:
            branch_status = "MEASURED"
        status = "PASS" if (line_ok and branch_ok) else "FAIL"
        fail_reason = None
        if not line_ok and not branch_ok:
            fail_reason = "lines+branch"
        elif not line_ok:
            fail_reason = "lines"
        elif not branch_ok:
            fail_reason = "branch"
        enriched.append({
            **m,
            "priority": pri,
            "threshold": line_threshold,
            "branch_threshold": branch_threshold,
            "status": status,
            "fail_reason": fail_reason,
            "branch_status": branch_status,
        })
        if status == "FAIL":
            failing.append(m["path"])

    return {
        "global_pct": round(global_pct, 2),
        "global_branch_pct": round(branch_pct, 2),
        "branch_measured": parser_emits_branch,
        "modules": enriched,
        "failing": failing,
        "framework": framework,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "framework",
        choices=[
            "vitest",
            "jest",
            "pytest",
            "jacoco",
            "kover",
            "go-test",
            "cargo",
            "dotnet",
            "cargo-tarpaulin",
            "cargo-llvm-cov",
            "dotnet-cobertura",
            "lcov",
        ],
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input file o directory (json-summary, lcov, xml, etc.; directory per jacoco multi-module)",
    )
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path skill root (per priority-rules.json)",
    )
    args = parser.parse_args()

    priority_rules = load_priority_rules(args.skill_root)
    result = parse(args.framework, args.input, priority_rules)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
