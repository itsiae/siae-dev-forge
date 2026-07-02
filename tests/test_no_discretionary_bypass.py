"""Doc↔code guard: i 9 bypass discrezionali sono rimossi da codice e ENV_VARS.md.

Colma il gap di test_env_vars_doc_sync.py (che copre solo DEVFORGE_EVIDENCE_*).
Verifica anche che i kill-switch globali/admin NON siano stati rimossi per sbaglio.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).parent.parent
ENV_VARS = REPO / "hooks" / "ENV_VARS.md"

REMOVED = [
    "DEVFORGE_SKIP_BRAINSTORMING",
    "DEVFORGE_SKIP_BLIND_REVIEW",
    "DEVFORGE_SKIP_EVIDENCE",
    "DEVFORGE_SKIP_RETRO_GATE",
    "DEVFORGE_SKIP_GIT_GATE",
    "DEVFORGE_FORCE_STOP",
    "DEVFORGE_SKIP_PREMORTEM",
    "DEVFORGE_SKIP_UPDATE",
    "DEVFORGE_SKIP_TRAILER_HOOK",
]

# Kill-switch presenti nel codice bash (regression guard: non rimossi per sbaglio).
KILLSWITCHES_IN_CODE = [
    "DEVFORGE_ENFORCEMENT_OFF",
    "DEVFORGE_USE_SESSION_SCOPE",
    "DEVFORGE_RELEASE_RISK_DISABLED",
]
# BREAK_GLASS_REGEX e' un override admin via commit-message: vive solo in
# ENV_VARS.md (non in codice bash). Verificato che resti documentato.


def _functional_files():
    """Hook eseguibili (no .md) + lib/*.sh. Esclude .archived (sottodir)."""
    files = [p for p in (REPO / "hooks").iterdir()
             if p.is_file() and p.suffix != ".md"]
    files += list((REPO / "lib").glob("*.sh"))
    return files


def test_removed_vars_absent_from_functional_code():
    for f in _functional_files():
        txt = f.read_text(errors="ignore")
        for var in REMOVED:
            assert var not in txt, f"{var} ancora presente in {f.name}"


def test_removed_vars_absent_from_env_vars_doc():
    txt = ENV_VARS.read_text()
    for var in REMOVED:
        assert var not in txt, f"{var} ancora documentata in ENV_VARS.md"


def test_toolfail_breakglass_documented():
    assert "DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS" in ENV_VARS.read_text(), \
        "il nuovo breakglass tool-fail non e' documentato in ENV_VARS.md"


def test_killswitches_preserved_in_code():
    blob = "".join(f.read_text(errors="ignore") for f in _functional_files())
    for ks in KILLSWITCHES_IN_CODE:
        assert ks in blob, f"kill-switch {ks} rimosso per sbaglio dal codice"


def test_break_glass_regex_still_documented():
    assert "DEVFORGE_BREAK_GLASS_REGEX" in ENV_VARS.read_text(), \
        "BREAK_GLASS_REGEX (admin) non deve essere rimosso da ENV_VARS.md"


def test_brainstorm_complexity_flag_cannot_bypass_iac():
    """DEVFORGE_BRAINSTORM_COMPLEXITY agisce solo sulla classificazione:
    force-trivial non deve silenziare un file IaC (.tf/.hcl), che resta
    sempre non-trivial nella libreria pura (Task 08). L'override va letto
    SOLO nel hook (brainstorming-gate) e loggato, mai in file-taxonomy.sh.
    """
    lib_taxonomy = (REPO / "lib" / "file-taxonomy.sh").read_text()
    assert "devforge_change_is_trivial" in lib_taxonomy, \
        "devforge_change_is_trivial mancante in lib/file-taxonomy.sh (Task 08 non applicato)"
    assert "DEVFORGE_BRAINSTORM_COMPLEXITY" not in lib_taxonomy, \
        "DEVFORGE_BRAINSTORM_COMPLEXITY non deve comparire nella libreria pura: " \
        "l'override va gestito solo nel hook, altrimenti force-trivial rischia di " \
        "bypassare il carve-out IaC/path-sensibile"

    gate = (REPO / "hooks" / "brainstorming-gate").read_text()
    assert "DEVFORGE_BRAINSTORM_COMPLEXITY" in gate, \
        "il hook non legge il flag di override della complessita'"
    assert "brainstorm_complexity_override" in gate, \
        "l'uso del flag non e' loggato (manca l'evento brainstorm_complexity_override)"
