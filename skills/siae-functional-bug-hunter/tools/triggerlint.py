#!/usr/bin/env python3
"""triggerlint.py — validates the SKILL.md YAML `description` field.

Quality Bar #2 (REDEFINED — see lifecycle_playbook.md history): the
original spec required 12+ phrasings + 8+ distinct lemmas. The owner
opted to strip auto-trigger phrasings so the skill activates only via
the explicit slash command. This linter enforces the redefined
criteria:

  1. description.length(words) <= MAX_WORDS                 (default 200)
  2. third-person (no first/second-person pronouns)
  3. no imperative trigger lists (forbidden imperative tokens absent
     when used as standalone triggers)
  4. all required Tier-1 stack names mentioned explicitly
  5. literal phrase "Invocation is manual only" is present

Usage:
    python3 tools/triggerlint.py <path-to-SKILL.md>

Exit code: 0 on PASS, 1 on FAIL. Each failure prints a single line to
stdout describing the rule violated.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_WORDS = 200

# We require these stack labels to appear textually somewhere in the
# description. Each tuple is (canonical-label, accepted-alternatives).
REQUIRED_STACKS = [
    ("Java", ["Java", "JVM"]),
    ("TypeScript", ["TypeScript", "Typescript"]),
    ("JavaScript", ["JavaScript", "Javascript"]),
    ("Python", ["Python"]),
    ("Go", ["Go"]),
    ("Rust", ["Rust"]),
    ("Kotlin", ["Kotlin"]),
    ("Swift", ["Swift"]),
    ("Ruby", ["Ruby"]),
    (".NET", [".NET", "dotnet", "C#"]),
    ("Scala", ["Scala"]),
    ("Flutter", ["Flutter", "Dart"]),
    ("Terraform", ["Terraform", "HCL"]),
    ("AWS serverless", ["AWS serverless", "SAM", "CDK"]),
    ("data platforms", ["data platform", "data platforms", "dbt", "Airflow", "Spark"]),
]

FORBIDDEN_IMPERATIVES_PATTERN = re.compile(
    r"(?:^|[\s\.,;:\-])(?:find\s+bugs?|trova\s+bug|hunt\s+\w+|scopri\s+\w+|"
    r"controlla\s+\w+|analizza\s+\w+|review\s+da\s+QA|mappa\s+rischi|"
    r"ispeziona\s+\w+|cerca\s+bug)\b",
    re.IGNORECASE,
)

FIRST_SECOND_PERSON = re.compile(
    r"\b(?:I|me|my|mine|we|us|our|ours|you|your|yours)\b",
    re.IGNORECASE,
)

MANUAL_ONLY_PHRASE = "invocation is manual only"


def extract_description(skill_md: str) -> str | None:
    """Pull the YAML `description` field from the frontmatter."""
    # frontmatter is between the first two lines that are exactly '---'
    lines = skill_md.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None

    in_desc = False
    buf: list[str] = []
    for raw in lines[1:end]:
        # description begins with `description:` and may be folded (`>`)
        # or inline. We accept both.
        if raw.startswith("description:"):
            in_desc = True
            after = raw[len("description:"):].lstrip()
            # If the value is `>` or `|`, the actual text starts next line
            if after in (">", "|", ">-", "|-", ">+", "|+"):
                continue
            if after:
                buf.append(after.strip())
            continue
        if not in_desc:
            continue
        # The description block ends at the next top-level key (no leading space).
        if raw and not raw[0].isspace():
            break
        buf.append(raw.strip())
    if not buf:
        return None
    return " ".join(s for s in buf if s)


def count_words(text: str) -> int:
    return len([t for t in re.split(r"\s+", text.strip()) if t])


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: triggerlint.py <SKILL.md>\n")
        return 2
    path = Path(argv[0])
    if not path.is_file():
        sys.stderr.write(f"file not found: {argv[0]}\n")
        return 2
    text = path.read_text(encoding="utf-8")
    desc = extract_description(text)
    if desc is None:
        print("FAIL: description field not found in YAML frontmatter")
        return 1

    failures: list[str] = []

    # Rule 1 — word cap
    n = count_words(desc)
    if n > MAX_WORDS:
        failures.append(f"R1 word-cap: {n} words > {MAX_WORDS}")

    # Rule 2 — third-person
    pron_match = FIRST_SECOND_PERSON.search(desc)
    if pron_match:
        failures.append(
            f"R2 third-person: first/second-person pronoun found: '{pron_match.group(0)}'"
        )

    # Rule 3 — no imperative trigger lists
    imp_match = FORBIDDEN_IMPERATIVES_PATTERN.search(desc)
    if imp_match:
        failures.append(
            f"R3 no-imperative-triggers: forbidden phrasing: "
            f"'{imp_match.group(0).strip()}'"
        )

    # Rule 4 — required Tier-1 stack names
    missing_stacks = []
    for canonical, alts in REQUIRED_STACKS:
        if not any(alt.lower() in desc.lower() for alt in alts):
            missing_stacks.append(canonical)
    if missing_stacks:
        failures.append(
            "R4 tier-1-stacks: missing names: " + ", ".join(missing_stacks)
        )

    # Rule 5 — "manual only" phrase
    if MANUAL_ONLY_PHRASE not in desc.lower():
        failures.append(
            f"R5 manual-only: literal phrase '{MANUAL_ONLY_PHRASE}' not found"
        )

    if failures:
        for f in failures:
            print(f)
        return 1

    print(f"PASS triggerlint: {n} words, all 5 redefined rules satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
