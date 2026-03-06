#!/usr/bin/env python3
"""
DevForge Pre-Flight Card Generator

Genera pre-flight card perfettamente allineate con bordi colorati ANSI,
emoji contestuali, larghezza adattiva e wrapping automatico.

Uso da CLI (JSON su stdin):

  echo '{
    "level": "ALTO",
    "skill": "siae-finishing-branch",
    "context": [
      {"emoji": "\ud83c\udf3f", "label": "Branch", "value": "feature/PROJ-123-add-login"},
      {"emoji": "\ud83c\udfaf", "label": "Target", "value": "sviluppo"}
    ],
    "actions": [
      {"emoji": "\ud83d\ude80", "label": "Push branch + apertura PR", "path": "origin/feature/PROJ-123"}
    ],
    "reason": "Branch pronto, test verdi",
    "ifno": "Il branch resta locale"
  }' | python3 design-system/generate-card.py

Uso da CLI (argomenti):

  python3 design-system/generate-card.py \\
    --level MEDIO \\
    --skill siae-qa \\
    --context '\\ud83d\\udce1 Tier attivo:Tier 1 MCP' \\
    --context '\\ud83c\\udfab Story Jira:PROJ-456' \\
    --reason 'Il tier determina come si sincronizzano TC' \\
    --ifno 'Workflow QA non inizia'

Flags:
  --no-color    Disabilita colori ANSI (per output in file .md)
"""

import argparse
import json
import sys
import unicodedata


# ── Configurazione ──────────────────────────────────────────────

MIN_WIDTH = 60
MAX_WIDTH = 100

LEVELS = {
    "MEDIO": {
        "emoji": "\U0001f7e1",
        "label": "MEDIO",
        "subtitle": "reversibile",
        "color": "\033[33m",
        "border": {"top": ("\u2554", "\u2550", "\u2557"),
                   "mid": ("\u2560", "\u2550", "\u2563"),
                   "bot": ("\u255a", "\u2550", "\u255d"),
                   "side": "\u2551"},
    },
    "ALTO": {
        "emoji": "\U0001f534",
        "label": "ALTO",
        "subtitle": "difficile da annullare",
        "color": "\033[31m",
        "border": {"top": ("\u250f", "\u2501", "\u2513"),
                   "mid": ("\u2523", "\u2501", "\u252b"),
                   "bot": ("\u2517", "\u2501", "\u251b"),
                   "side": "\u2503"},
    },
    "CRITICO": {
        "emoji": "\U0001f6a8",
        "label": "CRITICO",
        "subtitle": "irreversibile",
        "color": "\033[1;31m",
        "border": {"top": ("\u250f", "\u2501", "\u2513"),
                   "mid": ("\u2523", "\u2501", "\u252b"),
                   "bot": ("\u2517", "\u2501", "\u251b"),
                   "side": "\u2503"},
    },
}

RESET = "\033[0m"


# ── Utilita' Unicode ────────────────────────────────────────────

def char_width(c):
    """Larghezza display: East Asian Wide/Fullwidth = 2, altrimenti 1."""
    if unicodedata.east_asian_width(c) in ("W", "F"):
        return 2
    return 1


def str_width(s):
    """Larghezza display totale di una stringa."""
    return sum(char_width(c) for c in s)


def pad_right(s, width):
    """Padda una stringa a destra fino a width display chars."""
    current = str_width(s)
    return s + " " * max(0, width - current)


# ── Wrapping ────────────────────────────────────────────────────

def tokenize(text):
    """Splitta su spazi. Token lunghi con / vengono spezzati su /."""
    raw_words = text.split(" ")
    tokens = []
    for w in raw_words:
        if w == "":
            tokens.append("")
            continue
        if "/" in w and str_width(w) > 40:
            parts = w.split("/")
            for i, p in enumerate(parts):
                tokens.append(p + "/" if i < len(parts) - 1 else p)
        else:
            tokens.append(w)
    return tokens


def wrap_line(text, max_inner):
    """Wrappa una riga mantenendo l'indent di continuazione allineato al valore."""
    if str_width(text) <= max_inner:
        return [text]

    colon_pos = text.find(":")
    if colon_pos != -1:
        after_colon = text[colon_pos + 1:]
        spaces_after = len(after_colon) - len(after_colon.lstrip(" "))
        cont_indent = " " * (colon_pos + 1 + spaces_after)
    else:
        stripped = text.lstrip(" ")
        cont_indent = " " * (len(text) - len(stripped))

    if len(cont_indent) < 2:
        cont_indent = "  "

    tokens = tokenize(text)
    lines = []
    current = ""

    for t in tokens:
        if t == "":
            current = current + " " if current else " "
            continue

        sep = "" if (current.endswith(" ") or current.endswith("/") or not current) else " "
        test = current + sep + t

        if str_width(test) > max_inner and current.strip():
            lines.append(current)
            current = cont_indent + t
        else:
            current = test

    if current:
        lines.append(current)

    return lines


# ── Generatore Card ─────────────────────────────────────────────

def generate_card(level, skill, context, actions, reason, ifno, use_color=True):
    """Genera una pre-flight card perfettamente allineata.

    Args:
        level: 'MEDIO', 'ALTO', 'CRITICO'
        skill: nome della skill (es. 'siae-qa')
        context: lista di dict {"emoji", "label", "value"}
        actions: lista di dict {"emoji", "label", "path"}
        reason: stringa motivazione
        ifno: stringa alternativa se rifiutato
        use_color: True per ANSI colors, False per plain text

    Returns:
        stringa con la card completa
    """
    cfg = LEVELS[level]
    color = cfg["color"] if use_color else ""
    reset = RESET if use_color else ""
    b = cfg["border"]
    side = b["side"]

    # ── Costruisci righe di contenuto ──

    header = f'  \U0001f528 DevForge \u2014 {cfg["emoji"]} {cfg["label"]} ({cfg["subtitle"]}) \u00b7 {skill}'

    context_rows = []
    for item in context:
        context_rows.append(f'  {item["emoji"]} {item["label"]}:{" " * max(1, 18 - str_width(item["label"]) - 1)}{item["value"]}')

    action_rows = []
    for i, item in enumerate(actions, 1):
        action_rows.append(f'  {i}. {item["emoji"]} Azione:{" " * 6}{item["label"]}')
        action_rows.append(f'     \U0001f4c2 File/Path:   {item["path"]}')

    footer_rows = [
        f'  \U0001f4a1 Perche\':         {reason}',
        f'  \U0001f6ab Se NO:            {ifno}',
    ]

    # ── Calcola larghezza adattiva ──

    all_content = [header] + context_rows + action_rows + footer_rows
    max_content_w = max(str_width(r) for r in all_content)
    inner = max(MIN_WIDTH - 2, min(max_content_w + 4, MAX_WIDTH - 2))

    # ── Wrappa righe che eccedono ──

    def expand(rows):
        result = []
        for r in rows:
            result.extend(wrap_line(r, inner))
        return result

    header_lines = wrap_line(header, inner)
    context_rows = expand(context_rows)
    action_rows = expand(action_rows)
    footer_rows = expand(footer_rows)

    # ── Rendering ──

    def hline(chars):
        left, fill, right = chars
        return f"{color}{left}{fill * inner}{right}{reset}"

    def row(text):
        padded = pad_right(text, inner)
        return f"{color}{side}{reset}{padded}{color}{side}{reset}"

    lines = []
    lines.append(hline(b["top"]))
    for h in header_lines:
        lines.append(row(h))

    if context_rows:
        lines.append(hline(b["mid"]))
        for r in context_rows:
            lines.append(row(r))

    if action_rows:
        lines.append(hline(b["mid"]))
        for r in action_rows:
            lines.append(row(r))

    lines.append(hline(b["mid"]))
    for r in footer_rows:
        lines.append(row(r))
    lines.append(hline(b["bot"]))

    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────

def parse_context_arg(s):
    """Parsa '📡 Tier attivo:Tier 1 MCP' → dict."""
    parts = s.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Formato context non valido: {s!r} — usa 'EMOJI Label:Value'")
    label_part = parts[0].strip()
    value = parts[1].strip()
    # Primo char e' emoji (potrebbe essere multi-codepoint)
    # Splitta su primo spazio dopo l'emoji
    tokens = label_part.split(" ", 1)
    if len(tokens) == 2:
        emoji, label = tokens
    else:
        emoji, label = "", tokens[0]
    return {"emoji": emoji, "label": label, "value": value}


def parse_action_arg(s):
    """Parsa '🚀 Push branch:origin/feature/X' → dict."""
    parts = s.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Formato action non valido: {s!r} — usa 'EMOJI Label:Path'")
    label_part = parts[0].strip()
    path = parts[1].strip()
    tokens = label_part.split(" ", 1)
    if len(tokens) == 2:
        emoji, label = tokens
    else:
        emoji, label = "", tokens[0]
    return {"emoji": emoji, "label": label, "path": path}


def main():
    parser = argparse.ArgumentParser(description="DevForge Pre-Flight Card Generator")
    parser.add_argument("--level", choices=["MEDIO", "ALTO", "CRITICO"],
                        help="Livello di rischio")
    parser.add_argument("--skill", help="Nome della skill")
    parser.add_argument("--context", action="append", default=[],
                        help="Campo contesto: 'EMOJI Label:Value' (ripetibile)")
    parser.add_argument("--action", action="append", default=[],
                        help="Azione: 'EMOJI Label:Path' (ripetibile)")
    parser.add_argument("--reason", help="Motivazione (Perche')")
    parser.add_argument("--ifno", help="Alternativa (Se NO)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disabilita colori ANSI")

    args = parser.parse_args()

    # Se stdin ha dati, usa JSON
    if not sys.stdin.isatty():
        data = json.load(sys.stdin)
        level = data["level"]
        skill = data["skill"]
        context = data.get("context", [])
        actions = data.get("actions", [])
        reason = data["reason"]
        ifno = data["ifno"]
        use_color = not data.get("no_color", False) and not args.no_color
    else:
        if not all([args.level, args.skill, args.reason, args.ifno]):
            parser.error("Richiesti: --level, --skill, --reason, --ifno")
        level = args.level
        skill = args.skill
        context = [parse_context_arg(c) for c in args.context]
        actions = [parse_action_arg(a) for a in args.action]
        reason = args.reason
        ifno = args.ifno
        use_color = not args.no_color

    print(generate_card(level, skill, context, actions, reason, ifno, use_color))


if __name__ == "__main__":
    main()
