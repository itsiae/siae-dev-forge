"""REQ-13/14/15 — identificazione piattaforma applicativa + storage gerarchico.

La piattaforma (sport, pop, pae, ciam, …) è derivata dal nome servizio (che l'hook
ricava da `basename($REPO_ROOT)`), così l'identificazione è automatica "da contesto"
(REQ-13) e funziona sia in modalità manuale che hook PR (REQ-16/17).

Single source of truth: ``PLATFORM_PREFIXES`` (allineato a ``KG_PREFIXES`` in
kg_lookup.py, dove più prefissi confluiscono sulla stessa piattaforma applicativa).
Estendibile a runtime via env ``DEVFORGE_RELEASE_RISK_PLATFORM_MAP`` — config-as-code,
nessuna dipendenza esterna (stdlib only).

Regola ``resolve_platform`` (deterministica, fail-safe — MAI solleva):
  1. override esplicito (``--platform``) → ``slug(override)``;
  2. match del prefisso PIÙ LUNGO in ``PLATFORM_PREFIXES`` → piattaforma canonica
     (es. ``digital-channels-sport-`` vince su ``sport-``);
  3. fallback: primo token del servizio prima del primo ``-`` → ogni famiglia ha la
     sua cartella, niente bucket ``unknown`` condiviso (rispetta la separazione REQ-14).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

# Piattaforma canonica → prefissi servizio. Allineato a KG_PREFIXES (kg_lookup.py).
PLATFORM_PREFIXES: dict[str, tuple[str, ...]] = {
    "sport": ("sport-", "digital-channels-sport-", "esb-sport-"),
    "pop": ("pop-",),
    "pae": ("pae-",),
    "ciam": ("ciam-", "esb-sso-"),
    "dol": ("dol-be", "dol-"),
    "mag": ("mag-concertini-", "mag-"),
    "portal": ("portal-apigateway-", "portal-"),
    "ttpp": ("ttpp-",),
}

_SLUG_RE = re.compile(r"[^a-z0-9._-]+")


def _slug(value: str) -> str:
    """Slug filesystem-safe e lowercase. Mai vuoto."""
    s = (value or "").strip().lower().replace("/", "_").replace(":", "_")
    s = _SLUG_RE.sub("-", s).strip("-_")
    return s[:80] or "unknown"


def _load_env_overrides(env: Optional[dict] = None) -> dict[str, tuple[str, ...]]:
    """Parsa ``DEVFORGE_RELEASE_RISK_PLATFORM_MAP`` = ``plat:pref1|pref2;plat2:pref3``.

    Best-effort: entry malformate ignorate, mai solleva.
    """
    env = os.environ if env is None else env
    raw = (env.get("DEVFORGE_RELEASE_RISK_PLATFORM_MAP") or "").strip()
    if not raw:
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        name, prefs = entry.split(":", 1)
        prefixes = tuple(p.strip().lower() for p in prefs.split("|") if p.strip())
        if name.strip() and prefixes:
            out[name.strip().lower()] = prefixes
    return out


def resolve_platform(service: str, override: Optional[str] = None,
                     env: Optional[dict] = None) -> str:
    """Identifica la piattaforma applicativa dal nome servizio (REQ-13). Mai solleva."""
    if override and str(override).strip():
        return _slug(str(override))
    svc = (service or "").strip().lower()
    if not svc:
        return "unknown"

    table = dict(PLATFORM_PREFIXES)
    table.update(_load_env_overrides(env))  # env estende/sovrascrive i default

    best_platform: Optional[str] = None
    best_len = -1
    for platform, prefixes in table.items():
        for pref in prefixes:
            if svc.startswith(pref) and len(pref) > best_len:
                best_platform, best_len = platform, len(pref)
    if best_platform:
        return best_platform

    # Fallback: primo token → separazione per famiglia (REQ-14), niente catch-all.
    token = svc.split("-", 1)[0]
    return _slug(token)


def release_slug(service: str, version: Optional[str], branch: str) -> str:
    """Slug della release: ``<service>-<version>`` o ``<service>-<branch>`` se version unknown."""
    v = (version or "").strip()
    if v and v.lower() != "unknown":
        return _slug(f"{service}-{v}")
    return _slug(f"{service}-{branch}")


def scorecard_path(repo_root, service: str, version: Optional[str], branch: str,
                   override: Optional[str] = None) -> tuple[Path, str]:
    """Path gerarchico ``docs/releases/<platform>/<release>/scorecard.md`` (REQ-15).

    Ritorna ``(path, platform)``.
    """
    platform = resolve_platform(service, override)
    rel = release_slug(service, version, branch)
    path = Path(repo_root) / "docs" / "releases" / platform / rel / "scorecard.md"
    return path, platform
