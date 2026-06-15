"""Razionale del rilascio + principali change funzionali (contesto per TechOps).

TechOps spesso perde il "perché funzionale" di un rilascio. Questo modulo produce
un breve paragrafo di contesto con fonte ibrida, in ordine di priorità:

1. **manual**  — testo passato esplicitamente (`--rationale`, o composto dal modello
   nel flusso interattivo `/forge-release-risk`).
2. **pr-body** — descrizione della Pull Request (l'hook PR-open la passa): è il posto
   naturale del "perché". Ripulita dai marker HTML e troncata.
3. **derived** — sintesi deterministica da ticket Jira + feature branch (genesis) +
   numero file, quando non c'è altro.

Ritorna `(None, None)` se non c'è nulla di sensato da dire (sezione omessa).
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_PR_BODY_MAX_CHARS = 800


def _summarize_pr_body(body: str, max_chars: int = _PR_BODY_MAX_CHARS) -> str:
    """Ripulisce il body PR (marker HTML, spazi) e tronca a parola su max_chars."""
    text = _HTML_COMMENT_RE.sub("", body)
    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0].rstrip() + "…"
    return text


def build_narrative(rationale: Optional[str] = None,
                    pr_body: Optional[str] = None,
                    jira_tickets=None,
                    genesis=None,
                    files_changed: int = 0) -> Tuple[Optional[str], Optional[str]]:
    """Costruisce (testo, fonte) del razionale. Fonte: manual | pr-body | derived | None."""
    if rationale and rationale.strip():
        return rationale.strip(), "manual"

    if pr_body and pr_body.strip():
        return _summarize_pr_body(pr_body), "pr-body"

    # Fallback deterministico
    feats = list(getattr(genesis, "user_confirmed", None) or []) if genesis else []
    tickets = sorted(set(jira_tickets or []))
    parts = []
    if feats:
        parts.append("Feature incluse: " + ", ".join(feats) + ".")
    if tickets:
        parts.append("Ticket collegati: " + ", ".join(tickets) + ".")
    if not parts:
        return None, None
    parts.append(f"Il rilascio modifica {files_changed} file.")
    return " ".join(parts), "derived"
