#!/usr/bin/env python3
"""
autoresearch.py — Ottimizzazione iterativa description skill via Bedrock.

Metodo Karpathy autoresearch adattato per DevForge:
  1. Baseline (trigger eval approssimato via Bedrock)
  2. Identifica punto debole
  3. Genera variante (un cambio alla volta)
  4. A/B test via Bedrock
  5. Keep/revert
  6. Ripeti fino a target o max iterazioni

Uso:
    python3 evals/autoresearch.py --skill siae-brainstorming
    python3 evals/autoresearch.py --skill siae-brainstorming --max-iter 8 --target 0.92
    python3 evals/autoresearch.py --skill siae-brainstorming --validate
    python3 evals/autoresearch.py --skill siae-brainstorming --dry-run

Richiede: boto3, credenziali AWS con accesso Bedrock eu-west-1.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import boto3
    from botocore.config import Config as BotoConfig
except ImportError:
    print("Errore: boto3 richiesto. Installa con: pip install boto3", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent

# ── Modelli Bedrock ──────────────────────────────────────────────────────────
EVALUATOR_MODEL = os.environ.get("AUTORESEARCH_MODEL", "eu.anthropic.claude-opus-4-6-v1")
GENERATOR_MODEL = os.environ.get("AUTORESEARCH_MODEL", "eu.anthropic.claude-opus-4-6-v1")

# ── Colori terminale ─────────────────────────────────────────────────────────
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[97m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"

    @staticmethod
    def disable():
        for attr in dir(C):
            if attr.isupper() and not attr.startswith("_"):
                setattr(C, attr, "")


# ── Bedrock Client ───────────────────────────────────────────────────────────
def _get_bedrock_client():
    region = os.environ.get("AWS_REGION", "eu-west-1")
    config = BotoConfig(
        region_name=region,
        read_timeout=120,
        retries={"max_attempts": 2, "mode": "adaptive"},
    )
    return boto3.client("bedrock-runtime", config=config)


def _call_bedrock(prompt: str, model: str, temperature: float = 0) -> str:
    client = _get_bedrock_client()
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    })
    try:
        response = client.invoke_model(
            modelId=model,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        result = json.loads(response["body"].read())
        parts = [c["text"] for c in result.get("content", []) if c.get("type") == "text"]
        return "\n".join(parts).strip()
    except Exception as e:
        raise RuntimeError(f"Bedrock invoke_model fallito ({model}): {e}")


# ── Lettura skill e eval set ─────────────────────────────────────────────────
def read_skill_description(skill_name: str) -> str | None:
    """Legge description dal frontmatter SKILL.md."""
    import re
    skill_md = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
    if not skill_md.exists():
        return None
    content = skill_md.read_text()
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    frontmatter = parts[1]
    lines = frontmatter.split("\n")
    desc_lines = []
    in_desc = False
    desc_indent = 0
    for line in lines:
        if not in_desc:
            m = re.match(r'^description:\s*(.*)', line)
            if m:
                value = m.group(1).strip()
                if value in (">", "|", ">-", "|-"):
                    in_desc = True
                    continue
                else:
                    return value.strip("\"'") or None
        else:
            if line.strip() == "":
                desc_lines.append("")
                continue
            current_indent = len(line) - len(line.lstrip())
            if desc_indent == 0:
                desc_indent = current_indent
            if current_indent >= desc_indent and desc_indent > 0:
                desc_lines.append(line[desc_indent:])
            else:
                break
    if desc_lines:
        while desc_lines and desc_lines[-1] == "":
            desc_lines.pop()
        return " ".join(l for l in desc_lines if l != "").strip() or None
    return None


def read_all_skill_descriptions() -> dict[str, str]:
    """Legge tutte le description delle skill per contesto al valutatore."""
    skills = {}
    skills_dir = PLUGIN_ROOT / "skills"
    for d in sorted(skills_dir.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            desc = read_skill_description(d.name)
            if desc:
                skills[d.name] = desc
    return skills


def load_eval_set(skill_name: str) -> list[dict] | None:
    """Carica trigger eval set da eval-sets/ o trigger-evals/."""
    path1 = SCRIPT_DIR / "eval-sets" / skill_name / "trigger.json"
    path2 = SCRIPT_DIR / "trigger-evals" / f"{skill_name}.json"
    for p in (path1, path2):
        if p.exists():
            return json.loads(p.read_text())
    return None


# ── Trigger Eval via Bedrock (approssimato) ──────────────────────────────────
TRIGGER_EVAL_PROMPT = """Sei il router di skill di un plugin Claude Code chiamato "siae-devforge".
Il plugin ha {skill_count} skill. Ogni skill ha un campo "description" che descrive
QUANDO deve essere attivata.

Data una query utente, devi decidere quale skill (se nessuna, rispondi "NONE")
verrebbe attivata.

## Skill disponibili

{skills_list}

## Query utente

"{query}"

## Istruzioni

Rispondi SOLO con il nome della skill che verrebbe attivata (es. "siae-brainstorming")
oppure "NONE" se nessuna skill matcha. Una sola parola, nessuna spiegazione."""


def evaluate_trigger(
    query: str,
    all_descriptions: dict[str, str],
    target_skill: str,
    model: str = EVALUATOR_MODEL,
) -> dict:
    """Valuta se una query triggera la skill target via Bedrock."""
    skills_list = "\n".join(
        f"- **{name}**: {desc}" for name, desc in all_descriptions.items()
    )
    prompt = TRIGGER_EVAL_PROMPT.format(
        skill_count=len(all_descriptions),
        skills_list=skills_list,
        query=query,
    )
    try:
        response = _call_bedrock(prompt, model, temperature=0)
        triggered_skill = response.strip().lower().replace('"', '').replace("'", "")
        return {
            "triggered": target_skill in triggered_skill,
            "actual_skill": triggered_skill,
        }
    except Exception as e:
        print(f"  {C.RED}WARN{C.RESET} eval fallito: {e}", file=sys.stderr)
        return {"triggered": False, "actual_skill": "ERROR"}


def run_bedrock_eval(
    skill_name: str,
    eval_set: list[dict],
    all_descriptions: dict[str, str],
    runs: int = 1,
    model: str = EVALUATOR_MODEL,
) -> dict:
    """Esegue trigger eval completo via Bedrock. Restituisce precision/recall/accuracy."""
    results = []
    for item in eval_set:
        triggers = 0
        actuals = []
        for _ in range(runs):
            r = evaluate_trigger(item["query"], all_descriptions, skill_name, model)
            if r["triggered"]:
                triggers += 1
            actuals.append(r["actual_skill"])
        trigger_rate = triggers / runs
        should = item["should_trigger"]
        results.append({
            "query": item["query"][:80],
            "should_trigger": should,
            "trigger_rate": trigger_rate,
            "pass": (trigger_rate >= 0.5) if should else (trigger_rate < 0.5),
            "actual": max(set(actuals), key=actuals.count) if actuals else None,
        })

    pos = [r for r in results if r["should_trigger"]]
    neg = [r for r in results if not r["should_trigger"]]
    tp = sum(1 for r in pos if r["pass"])
    fn = len(pos) - tp
    fp = sum(1 for r in neg if not r["pass"])
    tn = len(neg) - fp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

    failed_queries = [r for r in results if not r["pass"]]

    return {
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "accuracy": round(accuracy, 2),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "failed": failed_queries,
        "results": results,
    }


# ── Generatore varianti description ─────────────────────────────────────────
GENERATOR_PROMPT = """Sei un esperto di routing skill per Claude Code plugin.

Il plugin "siae-devforge" ha {skill_count} skill. Quando l'utente scrive una query, Claude Code
legge la "description" di ogni skill e decide quale attivare. La description e' l'UNICO fattore
che determina il routing.

## Il problema
La skill "{skill_name}" perde query che dovrebbe catturare — vengono "rubate" da altre skill.

## Skill target
Nome: {skill_name}
Description corrente: "{current_description}"

## Metriche attuali
Precision: {precision} | Recall: {recall} | Accuracy: {accuracy}

## Diagnosi
{weakness}

## Query che DOVEVANO triggerare {skill_name} ma sono andate ad altre skill
{failed_queries}

## Description delle skill che rubano query (i "ladri")
{thief_descriptions}

## Regole della description (da skill-template.md)
- La description dice QUANDO usare la skill, non COSA fa
- Formato: prima frase = scope, poi "Trigger:" con condizioni di attivazione
- Puoi aggiungere "NON usare per:" con esclusioni esplicite per disambiguare
- Max 3 righe, max 300 caratteri
- Fai UN SOLO cambio rispetto alla description corrente

## Strategie di miglioramento (in ordine di priorita')
1. DISAMBIGUAZIONE: aggiungi "NON usare per: X" se una skill specifica ruba query
   Es: "NON usare per: operazioni git generiche (usa siae-git-workflow)"
2. DIFFERENZIATORE: riformula lo scope per marcare il confine con skill simili
   Es: "SOLO per configurazione ambiente git (.gitconfig, hooks, LFS)" vs "per operazioni git"
3. KEYWORD MIRATE: aggiungi 2-3 keyword specifiche che catturano i casi mancati
   NON aggiungere liste lunghe di keyword — peggiorano la precision

## Anti-pattern (NON fare)
- NON aggiungere piu' di 5 keyword per iterazione — causa keyword stuffing
- NON allungare la description oltre 3 righe
- NON rimuovere parti che funzionano (precision 1.00 = le keyword attuali funzionano)
- NON generalizzare troppo — "qualsiasi codice" cattura tutto ma ruba da altre skill

## Changelog iterazioni precedenti
{changelog}

Rispondi SOLO con la nuova description. Nessun apice, nessuna spiegazione, nessun commento."""


def generate_variant(
    skill_name: str,
    current_desc: str,
    metrics: dict,
    weakness: str,
    failed_queries: list[dict],
    changelog: list[dict],
    all_descriptions: dict[str, str] | None = None,
    model: str = GENERATOR_MODEL,
) -> str:
    """Genera una variante migliorata della description."""
    # Identifica le skill "ladre" e le loro description
    thief_counts: dict[str, int] = {}
    for q in failed_queries:
        actual = q.get("actual", "")
        if actual and actual != skill_name:
            thief_counts[actual] = thief_counts.get(actual, 0) + 1

    thief_str = ""
    if thief_counts and all_descriptions:
        for thief, count in sorted(thief_counts.items(), key=lambda x: -x[1]):
            desc = all_descriptions.get(thief, "?")
            thief_str += f"- {thief} (ruba {count} query): \"{desc[:150]}\"\n"
    if not thief_str:
        thief_str = "(nessun ladro identificato)"

    failed_str = "\n".join(
        f"- \"{q['query']}\" → andata a: {q.get('actual', '?')}"
        for q in failed_queries[:8]
    )
    changelog_str = "\n".join(
        f"- Iter {c['iter']}: {c['change']} → {c['outcome']} (Acc {c['acc']})"
        for c in changelog
    ) or "Nessuna iterazione precedente."

    prompt = GENERATOR_PROMPT.format(
        skill_name=skill_name,
        skill_count=len(all_descriptions) if all_descriptions else "?",
        current_description=current_desc,
        precision=metrics["precision"],
        recall=metrics["recall"],
        accuracy=metrics["accuracy"],
        weakness=weakness,
        failed_queries=failed_str,
        thief_descriptions=thief_str,
        changelog=changelog_str,
    )
    response = _call_bedrock(prompt, model, temperature=0.3)
    # Pulisci eventuali apici o righe extra
    cleaned = response.strip().strip('"').strip("'").strip("`")
    return cleaned


# ── Output visuale ───────────────────────────────────────────────────────────
def print_banner(skill_name: str):
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════════════════════╗
║  🔬 AUTORESEARCH — {skill_name:<44}║
║  🔨 DevForge · Ottimizzazione Iterativa Skill                    ║
╚══════════════════════════════════════════════════════════════════╝{C.RESET}
""")


def progress_bar(value: float, width: int = 20) -> str:
    """Genera barra progresso ASCII."""
    filled = int(value * width)
    empty = width - filled
    if value >= 0.90:
        color = C.GREEN
    elif value >= 0.75:
        color = C.YELLOW
    else:
        color = C.RED
    return f"{color}{'▪' * filled}{'░' * empty}{C.RESET}"


def print_baseline(metrics: dict, target: float):
    print(f"  {C.BOLD}BASELINE{C.RESET}")
    print(f"  Precision: {metrics['precision']:.2f}  Recall: {metrics['recall']:.2f}  "
          f"Accuracy: {metrics['accuracy']:.2f}")
    print(f"  Target:    Acc >= {target:.2f}")
    print(f"  {progress_bar(metrics['accuracy'])}")
    print()


def print_table_header():
    print(f"  {C.BOLD}{'Iter':>4}  {'Cambio':<40} {'P':>5} {'R':>5} {'Acc':>5} "
          f"{'Δ':>6}  {'Progresso':<22} {'Esito'}{C.RESET}")
    print(f"  {'━' * 110}")


def print_table_row(iteration: int, change: str, metrics: dict, delta: float, outcome: str):
    # Colore delta
    if delta > 0:
        delta_str = f"{C.GREEN}+{delta:.2f}{C.RESET}"
    elif delta < 0:
        delta_str = f"{C.RED}{delta:.2f}{C.RESET}"
    else:
        delta_str = f"{C.DIM} 0.00{C.RESET}"

    # Emoji esito
    if outcome == "WIN":
        outcome_str = f"{C.GREEN}✓ WIN{C.RESET}"
    elif outcome == "REVERT":
        outcome_str = f"{C.RED}⟲ REVERT{C.RESET}"
    elif outcome == "TIE":
        outcome_str = f"{C.YELLOW}— TIE{C.RESET}"
    elif outcome == "TARGET":
        outcome_str = f"{C.GREEN}{C.BOLD}🎯 TARGET{C.RESET}"
    else:
        outcome_str = f"{C.DIM}{outcome}{C.RESET}"

    bar = progress_bar(metrics["accuracy"])
    change_short = change[:38] + ".." if len(change) > 40 else change

    print(f"  {iteration:>4}  {change_short:<40} {metrics['precision']:>5.2f} "
          f"{metrics['recall']:>5.2f} {metrics['accuracy']:>5.2f} "
          f"{delta_str:>15}  {bar}  {outcome_str}")


def print_final_report(
    skill_name: str,
    original_desc: str,
    best_desc: str,
    baseline: dict,
    best: dict,
    changelog: list[dict],
    rules: list[str],
):
    print(f"\n{'━' * 70}")
    print(f"{C.BOLD}  REPORT FINALE — {skill_name}{C.RESET}")
    print(f"{'━' * 70}\n")

    print(f"  {C.DIM}Description originale:{C.RESET}")
    print(f"    \"{original_desc[:120]}\"")
    print(f"  {C.BOLD}Description ottimizzata:{C.RESET}")
    print(f"    \"{best_desc[:120]}\"")
    print()

    dp = best["precision"] - baseline["precision"]
    dr = best["recall"] - baseline["recall"]
    da = best["accuracy"] - baseline["accuracy"]

    print(f"  {'Metrica':<12} {'Baseline':>10} {'Finale':>10} {'Delta':>10}")
    print(f"  {'─' * 44}")
    print(f"  {'Precision':<12} {baseline['precision']:>10.2f} {best['precision']:>10.2f} "
          f"{C.GREEN if dp >= 0 else C.RED}{dp:>+10.2f}{C.RESET}")
    print(f"  {'Recall':<12} {baseline['recall']:>10.2f} {best['recall']:>10.2f} "
          f"{C.GREEN if dr >= 0 else C.RED}{dr:>+10.2f}{C.RESET}")
    print(f"  {'Accuracy':<12} {baseline['accuracy']:>10.2f} {best['accuracy']:>10.2f} "
          f"{C.GREEN if da >= 0 else C.RED}{da:>+10.2f}{C.RESET}")
    print()

    if rules:
        print(f"  {C.BOLD}Regole estratte:{C.RESET}")
        for i, rule in enumerate(rules, 1):
            print(f"    {i}. {rule}")
        print()

    # Conteggio esiti
    wins = sum(1 for c in changelog if c["outcome"] == "WIN")
    reverts = sum(1 for c in changelog if c["outcome"] == "REVERT")
    ties = sum(1 for c in changelog if c["outcome"] == "TIE")
    print(f"  Iterazioni: {len(changelog)} | "
          f"{C.GREEN}WIN: {wins}{C.RESET} | "
          f"{C.RED}REVERT: {reverts}{C.RESET} | "
          f"{C.YELLOW}TIE: {ties}{C.RESET}")
    print()


# ── Estrazione regole ────────────────────────────────────────────────────────
RULES_PROMPT = """Analizza questo changelog di ottimizzazione autoresearch e estrai regole riutilizzabili.

## Skill: {skill_name}
## Changelog
{changelog}

## Istruzioni
Estrai 2-5 regole universali (applicabili a qualsiasi skill description) basate sull'evidenza.
Ogni regola deve avere:
- La regola stessa (imperativa, concisa)
- L'evidenza (da quale iterazione e con quale delta)

Rispondi con un JSON array di stringhe, es:
["Regola 1 — evidenza: iter N, Δ+x.xx", "Regola 2 — evidenza: iter N"]
Nessun altro testo."""


def extract_rules(skill_name: str, changelog: list[dict]) -> list[str]:
    """Estrae regole universali dal changelog via Bedrock."""
    if not changelog:
        return []
    cl_str = "\n".join(
        f"Iter {c['iter']}: {c['change']} → {c['outcome']} "
        f"(P={c['p']:.2f} R={c['r']:.2f} Acc={c['acc']:.2f})"
        for c in changelog
    )
    prompt = RULES_PROMPT.format(skill_name=skill_name, changelog=cl_str)
    try:
        response = _call_bedrock(prompt, GENERATOR_MODEL, temperature=0)
        # Parse JSON
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception:
        return [f"Estrazione regole fallita — analizza manualmente il changelog"]


def save_rules(skill_name: str, rules: list[str], changelog: list[dict]):
    """Append regole in evals/workspace/autoresearch-rules.md."""
    rules_file = SCRIPT_DIR / "workspace" / "autoresearch-rules.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {skill_name} — {timestamp}\n\n"
    for i, rule in enumerate(rules, 1):
        entry += f"{i}. {rule}\n"
    entry += "\n"

    with open(rules_file, "a") as f:
        f.write(entry)

    print(f"  {C.GREEN}Regole salvate in:{C.RESET} {rules_file.relative_to(PLUGIN_ROOT)}")


def save_changelog(skill_name: str, changelog: list[dict], baseline: dict, best_desc: str):
    """Salva changelog JSON in evals/workspace/."""
    workspace = SCRIPT_DIR / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H%M%S")
    path = workspace / f"autoresearch_{skill_name}_{timestamp}.json"
    data = {
        "skill": skill_name,
        "timestamp": timestamp,
        "baseline": baseline,
        "best_description": best_desc,
        "iterations": changelog,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  {C.GREEN}Changelog salvato in:{C.RESET} {path.relative_to(PLUGIN_ROOT)}")


# ── Logica principale ────────────────────────────────────────────────────────
def identify_weakness(metrics: dict) -> str:
    """Identifica il punto debole principale con analisi dei ladri."""
    # Conta quali skill rubano le query
    thief_counts: dict[str, int] = {}
    for q in metrics.get("failed", []):
        actual = q.get("actual", "")
        if actual and q.get("should_trigger"):
            thief_counts[actual] = thief_counts.get(actual, 0) + 1

    thieves = ""
    if thief_counts:
        top = sorted(thief_counts.items(), key=lambda x: -x[1])[:3]
        thieves = " Skill che rubano query: " + ", ".join(f"{s} ({c}x)" for s, c in top) + "."

    if metrics["recall"] < metrics["precision"]:
        return (f"Recall basso ({metrics['recall']:.2f}): la skill non triggera su "
                f"{metrics['fn']} query dovute.{thieves} "
                f"Serve disambiguazione o differenziatori, NON keyword stuffing.")
    elif metrics["precision"] < metrics["recall"]:
        return (f"Precision bassa ({metrics['precision']:.2f}): la skill triggera su "
                f"{metrics['fp']} query non dovute. Servono esclusioni esplicite.")
    else:
        return (f"Precision e recall bilanciate ({metrics['precision']:.2f}). "
                f"Migliora entrambe incrementalmente.")


def run_autoresearch(
    skill_name: str,
    max_iter: int = 6,
    target: float = 0.90,
    runs: int = 1,
    dry_run: bool = False,
    no_color: bool = False,
):
    """Loop principale autoresearch."""
    if no_color:
        C.disable()

    print_banner(skill_name)

    # 1. Carica dati
    original_desc = read_skill_description(skill_name)
    if not original_desc:
        print(f"  {C.RED}ERRORE:{C.RESET} SKILL.md non trovata o senza description per {skill_name}")
        sys.exit(1)

    eval_set = load_eval_set(skill_name)
    if not eval_set:
        print(f"  {C.RED}ERRORE:{C.RESET} Eval set trigger non trovato per {skill_name}")
        print(f"  Crea: evals/eval-sets/{skill_name}/trigger.json")
        sys.exit(1)

    all_descs = read_all_skill_descriptions()
    print(f"  Skill: {C.BOLD}{skill_name}{C.RESET}")
    print(f"  Query: {len(eval_set)} ({sum(1 for q in eval_set if q['should_trigger'])} "
          f"should-trigger, {sum(1 for q in eval_set if not q['should_trigger'])} should-not)")
    print(f"  Description: \"{original_desc[:80]}...\"")
    print(f"  Max iterazioni: {max_iter} | Target: Acc >= {target:.2f}")
    print(f"  Modello eval: {EVALUATOR_MODEL.split('/')[-1]}")
    print()

    if dry_run:
        print(f"  {C.YELLOW}DRY RUN — non eseguo eval, solo struttura.{C.RESET}")
        return

    # 1b. Verifica credenziali Bedrock con una chiamata di test
    print(f"  {C.CYAN}Verifica credenziali Bedrock...{C.RESET}", end=" ", flush=True)
    try:
        _call_bedrock("Rispondi solo: OK", EVALUATOR_MODEL, temperature=0)
        print(f"{C.GREEN}OK{C.RESET}")
    except RuntimeError as e:
        print(f"{C.RED}FALLITO{C.RESET}")
        print(f"  {C.RED}ERRORE:{C.RESET} {e}")
        print(f"  Verifica credenziali AWS: aws sts get-caller-identity")
        sys.exit(1)
    print()

    # 2. Baseline
    print(f"  {C.CYAN}Esecuzione baseline...{C.RESET}", flush=True)
    baseline = run_bedrock_eval(skill_name, eval_set, all_descs, runs=runs)
    print_baseline(baseline, target)

    if baseline["accuracy"] >= target:
        print(f"  {C.GREEN}{C.BOLD}La skill e' gia' al target! Niente da ottimizzare.{C.RESET}")
        return

    # 2b. Analisi ladri — cross-skill disambiguation
    changelog = []
    thief_counts: dict[str, int] = {}
    for q in baseline["failed"]:
        actual = q.get("actual", "")
        if actual and q.get("should_trigger"):
            thief_counts[actual] = thief_counts.get(actual, 0) + 1

    if thief_counts:
        top_thief, top_count = max(thief_counts.items(), key=lambda x: x[1])
        total_miss = sum(1 for q in baseline["failed"] if q.get("should_trigger"))
        steal_pct = top_count / total_miss if total_miss > 0 else 0

        print(f"  {C.BOLD}ANALISI DISAMBIGUAZIONE{C.RESET}")
        for thief, count in sorted(thief_counts.items(), key=lambda x: -x[1]):
            thief_desc = all_descs.get(thief, "?")[:80]
            print(f"    {C.RED}{thief}{C.RESET} ruba {count} query — \"{thief_desc}...\"")

        if steal_pct >= 0.5:
            print(f"\n  {C.YELLOW}⚠ {top_thief} ruba {top_count}/{total_miss} query ({steal_pct:.0%}).{C.RESET}")
            print(f"  {C.YELLOW}  Strategia: cross-skill — ottimizzare ENTRAMBE le description.{C.RESET}")

            # Genera una description restrittiva per il ladro
            thief_desc = all_descs.get(top_thief, "")
            try:
                cross_prompt = f"""Il plugin siae-devforge ha un problema di disambiguazione:
la skill "{top_thief}" ruba {top_count} query che dovrebbero andare a "{skill_name}".

Description attuale di {top_thief}: "{thief_desc}"
Description attuale di {skill_name}: "{original_desc}"

Query rubate:
{chr(10).join(f'- "{q["query"]}"' for q in baseline["failed"] if q.get("should_trigger") and q.get("actual") == top_thief)}

Riscrivi la description di {top_thief} aggiungendo SOLO una esclusione:
"NON usare per: [specifico di {skill_name}] (usa {skill_name})."

Regole:
- Mantieni TUTTO il testo originale della description
- Aggiungi SOLO l'esclusione alla fine
- Max una riga aggiuntiva

Rispondi SOLO con la nuova description di {top_thief}. Nessuna spiegazione."""
                thief_new_desc = _call_bedrock(cross_prompt, GENERATOR_MODEL, temperature=0.2)
                thief_new_desc = thief_new_desc.strip().strip('"').strip("'").strip("`")

                # Testa con la description del ladro modificata
                test_descs = all_descs.copy()
                test_descs[top_thief] = thief_new_desc
                cross_metrics = run_bedrock_eval(skill_name, eval_set, test_descs, runs=runs)
                cross_delta = cross_metrics["accuracy"] - baseline["accuracy"]

                if cross_delta > 0.02:
                    print(f"  {C.GREEN}Cross-skill fix funziona: Acc {baseline['accuracy']:.2f} → "
                          f"{cross_metrics['accuracy']:.2f} (+{cross_delta:.2f}){C.RESET}")
                    print(f"  {C.DIM}Modifica suggerita per {top_thief}:{C.RESET}")
                    print(f"    \"{thief_new_desc[:120]}...\"")
                    # Usa la description del ladro modificata come base per il loop
                    all_descs[top_thief] = thief_new_desc
                    # Ricalcola baseline con il ladro corretto
                    baseline = cross_metrics
                    best_metrics = baseline.copy()
                    print(f"  {C.CYAN}Nuovo baseline con cross-fix: "
                          f"P={baseline['precision']:.2f} R={baseline['recall']:.2f} "
                          f"Acc={baseline['accuracy']:.2f}{C.RESET}")
                    if baseline["accuracy"] >= target:
                        print(f"\n  {C.GREEN}{C.BOLD}Target raggiunto con cross-skill fix!{C.RESET}")
                        # Salva e report
                        changelog.append({
                            "iter": 0, "change": f"cross-skill: restrict {top_thief}",
                            "description": thief_new_desc,
                            "p": baseline["precision"], "r": baseline["recall"],
                            "acc": baseline["accuracy"], "delta": cross_delta, "outcome": "CROSS-FIX",
                        })
                        rules = extract_rules(skill_name, changelog)
                        print_final_report(skill_name, original_desc, original_desc,
                                         {"precision": baseline["precision"], "recall": baseline["recall"],
                                          "accuracy": baseline["accuracy"]},
                                         baseline, changelog, rules)
                        save_changelog(skill_name, changelog, baseline, original_desc)
                        if rules:
                            save_rules(skill_name, rules, changelog)
                        print(f"\n  {C.BOLD}AZIONE RICHIESTA:{C.RESET}")
                        print(f"  Aggiorna description di {C.RED}{top_thief}{C.RESET} in "
                              f"skills/{top_thief}/SKILL.md")
                        return
                else:
                    print(f"  {C.DIM}Cross-skill fix non efficace (Δ={cross_delta:+.2f}). "
                          f"Procedo con loop standard.{C.RESET}")
            except RuntimeError as e:
                print(f"  {C.DIM}Cross-skill analysis fallita: {e}{C.RESET}")
        print()

    # 3. Loop
    print_table_header()
    print_table_row(0, "— (baseline)", baseline, 0.0, "base")

    current_desc = original_desc
    best_desc = original_desc
    best_metrics = baseline.copy()
    consecutive_target = 0
    plateau_count = 0

    for iteration in range(1, max_iter + 1):
        # Identifica punto debole
        weakness = identify_weakness(best_metrics)

        # Genera variante
        try:
            candidate = generate_variant(
                skill_name, current_desc, best_metrics,
                weakness, best_metrics["failed"], changelog,
                all_descriptions=all_descs,
            )
        except RuntimeError as e:
            print(f"\n  {C.RED}ERRORE generazione variante:{C.RESET} {e}")
            print(f"  {C.YELLOW}Verifica credenziali AWS e riprova.{C.RESET}")
            break

        if candidate == current_desc or not candidate:
            print_table_row(iteration, "(nessun cambio generato)", best_metrics, 0.0, "SKIP")
            plateau_count += 1
            if plateau_count >= 3:
                print(f"\n  {C.YELLOW}PLATEAU: 3 iterazioni senza cambiamenti. Stop.{C.RESET}")
                break
            continue

        # Calcola descrizione del cambio (diff testuale semplificato)
        change_desc = candidate[:60] if len(candidate) < 80 else candidate[:57] + "..."

        # Testa variante: sostituisci description nel contesto
        test_descs = all_descs.copy()
        test_descs[skill_name] = candidate
        new_metrics = run_bedrock_eval(skill_name, eval_set, test_descs, runs=runs)

        delta = new_metrics["accuracy"] - best_metrics["accuracy"]

        if delta > 0.02:
            # B vince
            outcome = "WIN"
            current_desc = candidate
            best_desc = candidate
            best_metrics = new_metrics
            plateau_count = 0
            if new_metrics["accuracy"] >= target:
                consecutive_target += 1
                if consecutive_target >= 1:  # Singola conferma per velocita'
                    outcome = "TARGET"
            else:
                consecutive_target = 0
        elif delta < -0.02:
            # A vince — revert
            outcome = "REVERT"
            plateau_count += 1
        else:
            # Tie
            outcome = "TIE"
            plateau_count += 1

        changelog.append({
            "iter": iteration,
            "change": change_desc,
            "description": candidate,
            "p": new_metrics["precision"],
            "r": new_metrics["recall"],
            "acc": new_metrics["accuracy"],
            "delta": delta,
            "outcome": outcome,
        })

        print_table_row(iteration, change_desc, new_metrics, delta, outcome)

        if outcome == "TARGET":
            break

        if plateau_count >= 3:
            print(f"\n  {C.YELLOW}PLATEAU: 3 iterazioni senza miglioramento. Stop.{C.RESET}")
            break

    # 4. Report finale
    rules = extract_rules(skill_name, changelog)
    print_final_report(skill_name, original_desc, best_desc, baseline, best_metrics, changelog, rules)

    # 5. Salva
    save_changelog(skill_name, changelog, baseline, best_desc)
    if rules:
        save_rules(skill_name, rules, changelog)

    # 6. Suggerimento applicazione
    if best_desc != original_desc:
        print(f"\n  {C.BOLD}Per applicare la description ottimizzata:{C.RESET}")
        print(f"  Aggiorna il campo 'description' in skills/{skill_name}/SKILL.md")
        print(f"\n  {C.DIM}Per validare con il vero router Claude Code:{C.RESET}")
        print(f"  python3 evals/runner.py --skill {skill_name} --ab-test "
              f"--description-b \"{best_desc[:80]}...\"")
    else:
        print(f"\n  {C.DIM}Nessun miglioramento trovato. Considera:{C.RESET}")
        print(f"  - Ampliare l'eval set con piu' query diverse")
        print(f"  - Rivedere la struttura della skill (non solo description)")


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="🔬 DevForge Autoresearch — Ottimizzazione iterativa skill description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--skill", required=True, help="Nome skill target (es. siae-brainstorming)")
    parser.add_argument("--max-iter", type=int, default=6, help="Max iterazioni (default: 6)")
    parser.add_argument("--target", type=float, default=0.90, help="Target accuracy (default: 0.90)")
    parser.add_argument("--runs", type=int, default=1, help="Run per query (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Solo validazione struttura, no eval")
    parser.add_argument("--no-color", action="store_true", help="Disabilita colori terminale")
    parser.add_argument("--validate", action="store_true",
                        help="Dopo autoresearch, lancia validazione con runner.py (claude -p)")

    args = parser.parse_args()

    os.chdir(PLUGIN_ROOT)

    run_autoresearch(
        skill_name=args.skill,
        max_iter=args.max_iter,
        target=args.target,
        runs=args.runs,
        dry_run=args.dry_run,
        no_color=args.no_color,
    )

    if args.validate and not args.dry_run:
        print(f"\n  {C.CYAN}Lancio validazione con runner.py (claude -p)...{C.RESET}")
        import subprocess
        cmd = [
            sys.executable, str(SCRIPT_DIR / "runner.py"),
            "--skill", args.skill, "--level", "L1",
            "--runs", "3", "--verbose",
        ]
        subprocess.run(cmd, cwd=str(PLUGIN_ROOT))


if __name__ == "__main__":
    main()
