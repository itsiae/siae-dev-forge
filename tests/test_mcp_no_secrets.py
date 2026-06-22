"""Guardrail: il .mcp.json versionato non deve contenere segreti in chiaro.

Regressione storica (2026-06-22): ES_PASSWORD e ORACLE_PASSWORD erano committati
in chiaro nel .mcp.json e distribuiti nella cache di ogni installazione del plugin.
Fix: i segreti diventano riferimenti a variabili d'ambiente ${VAR}. Questo test
impedisce di reintrodurli e verifica che il file resti JSON valido.
"""
import json
import re
from pathlib import Path

import pytest

MCP_JSON = Path(__file__).resolve().parents[1] / ".mcp.json"

# Chiavi env che NON devono mai contenere un valore literal nel file versionato.
SECRET_KEY_RE = re.compile(r"(PASSWORD|SECRET|TOKEN|ACCESS_KEY|API_KEY)", re.IGNORECASE)
# Un valore "sicuro" è un riferimento a variabile d'ambiente: ${VAR} o $VAR (eventuale prefisso/suffisso).
ENV_REF_RE = re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}|\$[A-Z_][A-Z0-9_]*")


def _load():
    with open(MCP_JSON, encoding="utf-8") as f:
        return json.load(f)


def _iter_strings(obj):
    """Yield ricorsivamente ogni valore stringa dentro dict/list (env, args, command, url...)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)


# Segreto inline in una stringa: "password=valore" / "--token: valore" con valore non-${VAR}.
INLINE_SECRET_RE = re.compile(
    r"(?i)(password|secret|token|api[-_]?key|access[-_]?key)\s*[=:]\s*(?!\$\{)(\S+)"
)


def test_mcp_json_is_valid_json():
    """Il .mcp.json deve restare parseable (un edit malformato romperebbe tutti gli MCP)."""
    data = _load()
    assert "mcpServers" in data, "manca la chiave mcpServers"


def test_no_secret_literals_in_env():
    """Ogni env key che assomiglia a un segreto deve essere un riferimento ${VAR}, mai un literal."""
    data = _load()
    offenders = []
    for server, cfg in data.get("mcpServers", {}).items():
        for key, value in (cfg.get("env") or {}).items():
            if not isinstance(value, str):
                continue
            if SECRET_KEY_RE.search(key) and not ENV_REF_RE.fullmatch(value):
                offenders.append(f"{server}.env.{key}={value!r}")
    assert not offenders, (
        "Segreti in chiaro nel .mcp.json versionato (usa ${VAR}): " + "; ".join(offenders)
    )


def test_no_secret_literals_in_args_or_command():
    """Segreti possono nascondersi anche in args/command, non solo in env.
    Es. args: ["--password", "s3cret"] o command "... --token=abc". Copre l'intero
    config (ricorsivo): nessun valore deve contenere un secret inline literal, e nessun
    flag-segreto in args deve essere seguito da un valore non-${VAR}."""
    data = _load()
    offenders = []
    flag_re = re.compile(r"(?i)(password|secret|token|api[-_]?key|access[-_]?key)")
    for server, cfg in data.get("mcpServers", {}).items():
        # 1. secret inline in qualsiasi stringa del server (env esclusa: già coperta sopra)
        for s in _iter_strings({k: v for k, v in cfg.items() if k != "env"}):
            if INLINE_SECRET_RE.search(s):
                offenders.append(f"{server}: inline secret in {s!r}")
        # 2. coppie (flag-segreto, valore) negli args: ["--password", "literal"]
        args = cfg.get("args") or []
        for i in range(len(args) - 1):
            cur, nxt = args[i], args[i + 1]
            if isinstance(cur, str) and isinstance(nxt, str) \
                    and flag_re.search(cur) and not ENV_REF_RE.fullmatch(nxt):
                offenders.append(f"{server}: args flag {cur!r} -> literal {nxt!r}")
    assert not offenders, "Possibile segreto in chiaro fuori da env: " + "; ".join(offenders)


@pytest.mark.parametrize(
    "server,key,expected",
    [
        ("elasticsearch", "ES_PASSWORD", "${ES_PASSWORD}"),
        ("siae-sport-oracle", "ORACLE_PASSWORD", "${ORACLE_PASSWORD}"),
    ],
)
def test_known_secrets_are_env_refs(server, key, expected):
    """I due segreti noti devono essere esattamente i riferimenti env attesi."""
    data = _load()
    env = data["mcpServers"][server].get("env", {})
    assert env.get(key) == expected, f"{server}.{key} atteso {expected}, trovato {env.get(key)!r}"
