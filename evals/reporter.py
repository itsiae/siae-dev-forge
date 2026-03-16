#!/usr/bin/env python3
"""
reporter.py — Genera report HTML autocontenuto da risultati eval.
"""

import json
import time
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>DevForge Eval Report — {date}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2em; background: #f5f5f5; }}
h1 {{ color: #1a1a2e; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; background: white; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #1a1a2e; color: white; }}
tr:nth-child(even) {{ background: #f9f9f9; }}
.score-high {{ background: #c8e6c9; font-weight: bold; }}
.score-mid {{ background: #fff9c4; }}
.score-low {{ background: #ffcdd2; font-weight: bold; }}
.details {{ display: none; background: #fafafa; padding: 1em; margin: 0.5em 0; border-left: 3px solid #1a1a2e; }}
.toggle {{ cursor: pointer; color: #1a1a2e; text-decoration: underline; }}
.summary-box {{ background: white; padding: 1em; margin: 1em 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.pass {{ color: #2e7d32; font-weight: bold; }}
.fail {{ color: #c62828; font-weight: bold; }}
</style>
</head>
<body>
<h1>🔨 DevForge — Eval Report</h1>
<p>Data: {date} | Modello: {model} | Durata: {elapsed}s</p>
{summary_section}
{detail_sections}
<script>
function toggle(id) {{
  var el = document.getElementById(id);
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}}
</script>
</body>
</html>"""


def _score_class(score: float) -> str:
    if score >= 0.80:
        return "score-high"
    elif score >= 0.50:
        return "score-mid"
    return "score-low"


def _pass_label(passed: bool) -> str:
    return '<span class="pass">PASS</span>' if passed else '<span class="fail">FAIL</span>'


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;"))


def generate_report(all_results: list[dict], output_path: Path) -> Path:
    """Genera report HTML da lista di risultati eval.

    Args:
        all_results: lista di result schema (output di L1/L2/L3)
        output_path: path dove salvare il file HTML

    Returns:
        path al file HTML generato
    """
    date = time.strftime("%Y-%m-%d %H:%M")
    models = set(r.get("model", "?") for r in all_results)
    total_elapsed = sum(r.get("metadata", {}).get("elapsed_s", 0) for r in all_results)

    # Summary table
    rows = []
    for r in all_results:
        s = r.get("summary", {})
        skill = _escape_html(r.get("skill", "?"))
        level = r.get("level", "?")
        total = s.get("total", 0)
        passed = s.get("passed", 0)
        failed = total - passed

        if level == "L1":
            score_str = f"P:{s.get('precision', 0):.2f} R:{s.get('recall', 0):.2f}"
            score_val = (s.get("precision", 0) + s.get("recall", 0)) / 2
        else:
            score_str = f"{s.get('avg_score', 0):.3f}" if "avg_score" in s else f"{passed}/{total}"
            score_val = s.get("avg_score", passed / total if total > 0 else 0)

        css = _score_class(score_val)
        pass_fail = _pass_label(failed == 0)
        div_id = f"{r.get('skill', 'x')}_{level}"

        rows.append(
            f'<tr><td>{skill}</td><td>{level}</td>'
            f'<td class="{css}">{score_str}</td>'
            f'<td>{passed}/{total}</td><td>{pass_fail}</td>'
            f'<td><span class="toggle" onclick="toggle(\'{div_id}\')">dettagli</span></td></tr>'
        )

    summary_html = (
        '<div class="summary-box">'
        f'<h2>Riepilogo — {len(all_results)} eval run</h2>'
        '<table><tr><th>Skill</th><th>Level</th><th>Score</th>'
        '<th>Pass/Total</th><th>Status</th><th></th></tr>'
        + "\n".join(rows)
        + '</table></div>'
    )

    # Detail sections
    detail_parts = []
    for r in all_results:
        skill = r.get("skill", "?")
        level = r.get("level", "?")
        div_id = f"{skill}_{level}"
        detail_rows = []
        for res in r.get("results", []):
            query = _escape_html(res.get("query", res.get("name", ""))[:120])
            ws = res.get("weighted_score", 0)
            css = _score_class(ws)
            pf = _pass_label(res.get("pass", False))
            reasoning = _escape_html(res.get("grader_reasoning", "")[:300])
            scores_str = _escape_html(", ".join(
                f"{s['name']}:{s['score']}" for s in res.get("scores", [])
            ))
            error = res.get("error", "")
            error_str = f" ⚠️ {_escape_html(error)}" if error else ""
            detail_rows.append(
                f'<tr><td>{query}</td><td class="{css}">{ws:.3f}</td>'
                f'<td>{pf}</td><td>{scores_str}</td>'
                f'<td>{reasoning}{error_str}</td></tr>'
            )

        detail_parts.append(
            f'<div id="{div_id}" class="details">'
            f'<h3>{_escape_html(skill)} — {level}</h3>'
            '<table><tr><th>Query</th><th>Score</th><th>Status</th>'
            '<th>Scores</th><th>Reasoning</th></tr>'
            + "\n".join(detail_rows)
            + '</table></div>'
        )

    html = HTML_TEMPLATE.format(
        date=date,
        model=", ".join(models),
        elapsed=round(total_elapsed, 1),
        summary_section=summary_html,
        detail_sections="\n".join(detail_parts),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path
