"""Guard test per i 3 file canonici SIAE (REQ-DF-01/02/06).

Verifica: esistenza, sezioni `## ` attese, budget byte (<=1800 ciascuno,
allineato a hooks/session-start head -c per file), e anti-leak
(no email personali salvo whitelist git@github.com, no path macchina
/Users/, no IP salvo whitelist proxy corporate 10.255.1.241).

Vedi precedente: docs/plans/2026-06-24-siae-global-rules-injection/task-01.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = REPO_ROOT / "skills" / "using-devforge" / "reference"

EXPECTED_FILES = {
    "siae-environments.md": {
        "## Discrimina il contesto PRIMA di applicare gli ambienti",
        "## Cloud/AWS — ordine ambienti",
        "## SPORT/PAE/POP — ordine ambienti",
        "## Regola anti-confusione",
        "## Se la fonte non è disponibile",
    },
    "siae-plan-deploy.md": {
        "## Disambiguazione obbligatoria (collisione di nomi)",
        "## PLAN — checklist standard",
        "## PLAN+DEPLOY — progressione ambienti",
        "## Deviazioni",
    },
    "siae-multirepo.md": {
        "## Ruoli",
        "## Regola di routing",
        "## Naming (verificato su org `itsiae`, 2026-07-01)",
        "## Cross-cutting",
    },
}

MAX_BYTES = 1800
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IP_RE = re.compile(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}")
ALLOWED_IP = "10.255.1.241"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_exists(filename):
    assert (REFERENCE_DIR / filename).is_file(), f"missing {filename}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_has_expected_sections(filename):
    content = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
    headers = {line.strip() for line in content.splitlines() if line.startswith("## ")}
    missing = EXPECTED_FILES[filename] - headers
    assert not missing, f"{filename} missing sections: {missing}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_under_byte_budget(filename):
    size = (REFERENCE_DIR / filename).stat().st_size
    assert size <= MAX_BYTES, f"{filename} is {size} bytes, budget is {MAX_BYTES}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_no_leaked_email(filename):
    content = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
    emails = [e for e in EMAIL_RE.findall(content) if e != "git@github.com"]
    assert not emails, f"{filename} leaks personal email(s): {emails}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_no_leaked_machine_path(filename):
    content = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
    assert "/Users/" not in content, f"{filename} leaks a machine-local path"
    assert "OneDrive" not in content, f"{filename} leaks a machine-local path"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_only_whitelisted_ip(filename):
    content = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
    ips = sorted(set(IP_RE.findall(content)))
    disallowed = [ip for ip in ips if ip != ALLOWED_IP]
    assert not disallowed, f"{filename} contains non-whitelisted IP(s): {disallowed}"
