"""Pubblicazione della scorecard release-risk su Confluence (account tecnico).

Auth: API token Atlassian (Basic email:token) di un'utenza tecnica dedicata →
abilita la pubblicazione automatica anche in contesti headless/CI (l'OAuth
per-utente del client MCP non è accessibile al processo Python).

Idempotenza: UNA pagina per rilascio (titolo deterministico) → find-by-title,
poi create o update (version bump). Re-run sullo stesso rilascio aggiorna la
pagina esistente, niente duplicati.

Fail-open: nessuna eccezione propagata al chiamante; gli errori (config assente,
rete giù, HTTP non-2xx) sono restituiti come dict {"published": False, ...}.
Non deve MAI rompere il flusso assess (file md locale + commento PR restano).

HTTP injettabile (`http_fn`) per i test — stesso pattern di `mcp_invoker` in
kg_lookup. Default: urllib (stdlib, zero dipendenze esterne).
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

# Default SIAE (siae-portfolio): space TechOps + cartella Rilasci. Overridabili via env.
DEFAULT_SPACE_ID = "222527493"      # space TechOps
DEFAULT_PARENT_ID = "670793729"     # cartella (folder) Rilasci
DEFAULT_SPACE_KEY = "TechOps"
DEFAULT_TIMEOUT_SEC = 8


@dataclass
class ConfluenceConfig:
    base_url: str          # es. https://siae-portfolio.atlassian.net/wiki
    email: str             # account tecnico
    api_token: str
    space_id: str = DEFAULT_SPACE_ID
    parent_id: str = DEFAULT_PARENT_ID
    space_key: str = DEFAULT_SPACE_KEY
    timeout: int = DEFAULT_TIMEOUT_SEC


def config_from_env(env: Optional[dict] = None) -> Optional[ConfluenceConfig]:
    """Costruisce la config dalle env var DEVFORGE_CONFLUENCE_*.

    Ritorna None (publish disattivato, fail-open) se manca uno dei 3 obbligatori:
    DEVFORGE_CONFLUENCE_BASE_URL, _EMAIL, _API_TOKEN.
    """
    env = os.environ if env is None else env
    base = env.get("DEVFORGE_CONFLUENCE_BASE_URL")
    email = env.get("DEVFORGE_CONFLUENCE_EMAIL")
    token = env.get("DEVFORGE_CONFLUENCE_API_TOKEN")
    if not (base and email and token):
        return None
    try:
        timeout = int(env.get("DEVFORGE_CONFLUENCE_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC)))
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_SEC
    return ConfluenceConfig(
        base_url=base.rstrip("/"),
        email=email,
        api_token=token,
        space_id=env.get("DEVFORGE_CONFLUENCE_SPACE_ID", DEFAULT_SPACE_ID),
        parent_id=env.get("DEVFORGE_CONFLUENCE_PARENT_ID", DEFAULT_PARENT_ID),
        space_key=env.get("DEVFORGE_CONFLUENCE_SPACE_KEY", DEFAULT_SPACE_KEY),
        timeout=timeout,
    )


def _format_date(raw: str) -> str:
    """ISO date (YYYY-MM-DD...) → gg-mm-aaaa. Best-effort: ritorna raw se non parsabile."""
    try:
        y, m, d = raw[:10].split("-")
        return f"{d}-{m}-{y}"
    except (ValueError, AttributeError):
        return raw or ""


def build_page_title(report) -> str:
    """Titolo deterministico: 'gg-mm-aaaa — <servizio>[ v<versione>]'."""
    raw = report.identification.get("date") or report.generated_at or ""
    date_str = _format_date(raw)
    version = (report.identification.get("version") or "").strip()
    title = f"{date_str} — {report.service}"
    if version and version.lower() != "unknown":
        title += f" v{version}"
    return title


def _auth_header(cfg: ConfluenceConfig) -> str:
    raw = f"{cfg.email}:{cfg.api_token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _default_http(method, url, headers, body, timeout):
    """Transport di default via urllib (stdlib). Ritorna (status_code, dict)."""
    import urllib.request
    import urllib.error

    data = body.encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            txt = resp.read().decode("utf-8") or "{}"
            return resp.status, json.loads(txt)
    except urllib.error.HTTPError as e:
        try:
            txt = e.read().decode("utf-8")
            payload = json.loads(txt) if txt else {}
        except Exception:
            payload = {}
        return e.code, payload


def _page_url(cfg: ConfluenceConfig, payload: dict) -> Optional[str]:
    links = payload.get("_links") or {}
    webui = links.get("webui")
    if webui:
        return f"{cfg.base_url}{webui}"
    pid = payload.get("id")
    return f"{cfg.base_url}/pages/{pid}" if pid else None


def _err(reason: str) -> dict:
    return {"published": False, "action": "error", "url": None, "reason": reason}


def publish_scorecard(report, storage_body: str, title: str,
                      cfg: ConfluenceConfig, http_fn=None) -> dict:
    """Pubblica/aggiorna la scorecard su Confluence. Fail-open (mai solleva).

    Ritorna dict: {published: bool, action: created|updated|error, url, reason}.
    """
    http = http_fn or _default_http
    headers = {
        "Authorization": _auth_header(cfg),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        # 1) find-by-title nello space
        find_url = (f"{cfg.base_url}/api/v2/pages"
                    f"?space-id={cfg.space_id}&title={quote(title)}")
        status, payload = http("GET", find_url, headers, None, cfg.timeout)
        if not (200 <= status < 300):
            return _err(f"find HTTP {status}")
        results = payload.get("results") or []

        if results:
            # 2a) update: bump version
            page_id = str(results[0].get("id"))
            page_url = f"{cfg.base_url}/api/v2/pages/{page_id}"
            s2, p2 = http("GET", page_url, headers, None, cfg.timeout)
            if not (200 <= s2 < 300):
                return _err(f"get HTTP {s2}")
            current_ver = (p2.get("version") or {}).get("number") or 1
            put_body = json.dumps({
                "id": page_id,
                "status": "current",
                "title": title,
                "spaceId": cfg.space_id,
                "body": {"representation": "storage", "value": storage_body},
                "version": {"number": current_ver + 1,
                            "message": "release-risk auto-update"},
            })
            s3, p3 = http("PUT", page_url, headers, put_body, cfg.timeout)
            if not (200 <= s3 < 300):
                return _err(f"update HTTP {s3}")
            return {"published": True, "action": "updated",
                    "url": _page_url(cfg, p3) or _page_url(cfg, {"id": page_id}),
                    "reason": None}

        # 2b) create sotto la cartella Rilasci
        post_url = f"{cfg.base_url}/api/v2/pages"
        post_body = json.dumps({
            "spaceId": cfg.space_id,
            "status": "current",
            "title": title,
            "parentId": cfg.parent_id,
            "body": {"representation": "storage", "value": storage_body},
        })
        s4, p4 = http("POST", post_url, headers, post_body, cfg.timeout)
        if not (200 <= s4 < 300):
            return _err(f"create HTTP {s4}")
        return {"published": True, "action": "created",
                "url": _page_url(cfg, p4), "reason": None}

    except Exception as e:  # fail-open totale
        return _err(f"{type(e).__name__}: {e}")
