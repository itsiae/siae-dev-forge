#!/usr/bin/env python3
"""
analyze-token-usage.py — Analizza il token usage di una sessione Claude Code

Parsa il file .jsonl della sessione e produce un breakdown dei costi per agent/subagent.
Utile per ottimizzare le skill che usano tanti token (specialmente subagent-development).

UTILIZZO:
    python3 tests/analyze-token-usage.py <session.jsonl>
    python3 tests/analyze-token-usage.py ~/.claude/sessions/<session-id>.jsonl

OUTPUT ESEMPIO:
    Agent             Description                    Msgs   Input   Output   Cache    Cost
    ─────────────────────────────────────────────────────────────────────────────────────
    main              Main session (coordinatore)    34     27k     3,996    1,213k   $4.09
    3380c209          Implementer Task 1              1      2k     787      24,989   $0.09
    a91f3b12          Spec-Reviewer Task 1            1      1k     412       8,234   $0.04
    b23e1c45          Code-Quality-Reviewer Task 1    1      1k     398       7,891   $0.04
    ─────────────────────────────────────────────────────────────────────────────────────
    TOTAL                                             37     31k     5,593    1,255k   $4.26
"""
from __future__ import annotations

import importlib.util
import json
import sys
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any

# Single source of truth per i prezzi: deleghiamo al core token-collector.
# Il filename ha un trattino → import via importlib (pattern test_anti_bloat_lint.py).
_core_path = Path(__file__).parent.parent / "lib" / "token-collector.py"
_spec = importlib.util.spec_from_file_location("token_collector", _core_path)
_tc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tc)


def cost_for_usage(event: dict, usage: dict) -> float:
    """Costo in EUR via core token-collector (single source of truth)."""
    metrics = _tc.usage_tokens(usage)
    model = _tc.extract_model(event)
    return _tc.usage_cost_eur(metrics, model)


def load_session(filepath: str) -> list[dict]:
    """Carica un file di sessione .jsonl"""
    events = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def extract_usage(event: dict) -> dict | None:
    """Estrae i dati di usage da un evento della sessione"""
    # Struttura Claude Code .jsonl
    # Gli eventi di usage sono in message.usage o direttamente in usage
    usage = None

    if event.get("type") == "message":
        usage = event.get("usage")
    elif "message" in event:
        usage = event["message"].get("usage")
    elif "usage" in event:
        usage = event["usage"]

    return usage


def format_number(n: int) -> str:
    """Formatta un numero con k per migliaia"""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.0f}k"
    return str(n)


def analyze_session(filepath: str) -> None:
    """Analizza una sessione e stampa il report"""
    if not os.path.exists(filepath):
        print(f"Errore: file non trovato: {filepath}", file=sys.stderr)
        sys.exit(1)

    events = load_session(filepath)

    if not events:
        print(f"Errore: nessun evento trovato in {filepath}", file=sys.stderr)
        sys.exit(1)

    # Raccogli statistiche per agent
    # La sessione principale è "main", i subagent hanno ID univoci
    agents: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "messages": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "cost": 0.0,
        "description": "",
    })

    current_agent = "main"

    for event in events:
        event_type = event.get("type", "")

        # Rileva cambio di contesto agent (Task tool launch)
        if event_type == "tool_use" and event.get("name") == "Task":
            # Un nuovo subagent viene lanciato
            agent_id = event.get("id", "unknown")[:8]
            description = ""
            if "input" in event:
                description = event["input"].get("description", "")[:40]
            agents[agent_id]["description"] = description
            current_agent = agent_id

        # Rileva fine di un subagent
        if event_type == "tool_result" and event.get("tool_use_id", "").startswith("toolu_"):
            current_agent = "main"

        # Raccogli usage
        usage = extract_usage(event)
        if usage:
            agent = agents[current_agent]
            agent["messages"] += 1
            agent["input_tokens"] += usage.get("input_tokens", 0)
            agent["output_tokens"] += usage.get("output_tokens", 0)
            agent["cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
            agent["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)
            agent["cost"] += cost_for_usage(event, usage)

    if not agents:
        print("Nessun dato di usage trovato nella sessione.")
        print("Nota: il file .jsonl potrebbe avere un formato diverso.")
        sys.exit(0)

    # Calcola totali
    totals = {
        "messages": sum(a["messages"] for a in agents.values()),
        "input_tokens": sum(a["input_tokens"] for a in agents.values()),
        "output_tokens": sum(a["output_tokens"] for a in agents.values()),
        "cache_creation_tokens": sum(a["cache_creation_tokens"] for a in agents.values()),
        "cache_read_tokens": sum(a["cache_read_tokens"] for a in agents.values()),
        "cost": sum(a["cost"] for a in agents.values()),
    }

    # Stampa report
    print(f"\n📊 Token Usage Analysis — {os.path.basename(filepath)}")
    print(f"   Evento totali nel file: {len(events)}")
    print()

    col_widths = {
        "agent": 12,
        "desc": 38,
        "msgs": 6,
        "input": 8,
        "output": 8,
        "cache": 8,
        "cost": 8,
    }

    header = (
        f"{'Agent':<{col_widths['agent']}}  "
        f"{'Description':<{col_widths['desc']}}  "
        f"{'Msgs':>{col_widths['msgs']}}  "
        f"{'Input':>{col_widths['input']}}  "
        f"{'Output':>{col_widths['output']}}  "
        f"{'Cache':>{col_widths['cache']}}  "
        f"{'Cost(€)':>{col_widths['cost']}}"
    )

    separator = "─" * len(header)

    print(header)
    print(separator)

    # Main prima, poi subagent ordinati per costo decrescente
    agent_list = [(k, v) for k, v in agents.items()]
    main_agents = [(k, v) for k, v in agent_list if k == "main"]
    sub_agents = sorted(
        [(k, v) for k, v in agent_list if k != "main"],
        key=lambda x: x[1]["cost"],
        reverse=True
    )

    for agent_id, data in main_agents + sub_agents:
        desc = data["description"] or ("Sessione principale" if agent_id == "main" else "—")
        cache_total = data["cache_creation_tokens"] + data["cache_read_tokens"]
        print(
            f"{agent_id:<{col_widths['agent']}}  "
            f"{desc:<{col_widths['desc']}}  "
            f"{data['messages']:>{col_widths['msgs']}}  "
            f"{format_number(data['input_tokens']):>{col_widths['input']}}  "
            f"{format_number(data['output_tokens']):>{col_widths['output']}}  "
            f"{format_number(cache_total):>{col_widths['cache']}}  "
            f"€{data['cost']:>{col_widths['cost']-1}.2f}"
        )

    print(separator)
    cache_total = totals["cache_creation_tokens"] + totals["cache_read_tokens"]
    print(
        f"{'TOTAL':<{col_widths['agent']}}  "
        f"{'':>{col_widths['desc']}}  "
        f"{totals['messages']:>{col_widths['msgs']}}  "
        f"{format_number(totals['input_tokens']):>{col_widths['input']}}  "
        f"{format_number(totals['output_tokens']):>{col_widths['output']}}  "
        f"{format_number(cache_total):>{col_widths['cache']}}  "
        f"€{totals['cost']:>{col_widths['cost']-1}.2f}"
    )

    print()

    # Insights automatici
    if sub_agents:
        most_expensive = max(sub_agents, key=lambda x: x[1]["cost"])
        main_cost = agents["main"]["cost"]
        sub_cost = totals["cost"] - main_cost
        sub_pct = (sub_cost / totals["cost"] * 100) if totals["cost"] > 0 else 0

        print("💡 Insights:")
        print(f"   Subagent cost: €{sub_cost:.2f} ({sub_pct:.0f}% del totale)")
        print(f"   Subagent più costoso: {most_expensive[0]} (€{most_expensive[1]['cost']:.2f})")

        if sub_pct > 60:
            print(f"   ⚠️  I subagent usano >{sub_pct:.0f}% dei token — considera di ridurre il contesto passato ai subagent")

    print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 tests/analyze-token-usage.py <session.jsonl>")
        print("     python3 tests/analyze-token-usage.py ~/.claude/sessions/<id>.jsonl")
        sys.exit(1)

    analyze_session(sys.argv[1])
