# Task 11 — F5a Excel Glossary Sheet

**Goal:** Sheet "📖 Glossario KPI" con formula + buono-se + benchmark industria per tutti i KPI.
**AC coperti:** UX1, AC-MACRO-5
**Dipendenze:** Task 07, 08 (KPI definiti)
**Effort:** ~30 min
**Test nuovi:** 5

## File coinvolti

- `scripts/export_glossary.py` — funzione `write_glossary_sheet`
- `reference/kpi-glossary-data.yaml` — popolamento completo
- `tests/test_export_glossary.py` — 5 test

## Step 1 — kpi-glossary-data.yaml (popolamento)

```yaml
version: 1
kpi:
  - id: pr_cycle_time_p50
    label_it: "Tempo mediano PR (h)"
    formula: "median(merged_at − opened_at) in ore"
    interpretation: "Tempo da apertura PR a merge. Riflette velocità review + merge team."
    good_if: "< 24 ore (DORA Elite)"
    benchmark: "DORA 2023: Elite <1gg, High <1sett, Medium <1mese, Low >1mese"
  - id: lead_time_to_merge_p50
    label_it: "Lead time mediano (h)"
    formula: "median(merged_at − first_commit_at)"
    interpretation: "Tempo dal primo commit al merge — include development + review."
    good_if: "< 48 ore"
    benchmark: "DORA: dipende tier team"
  - id: pr_throughput_weekly
    label_it: "PR per settimana"
    formula: "count(merged_pr) / weeks_in_window"
    interpretation: "Volume output. Varia con complexity PR — leggere insieme a net_loc."
    good_if: "> 3 PR/sett per dev junior-mid"
    benchmark: "Industry average: 2-5 PR/sett"
  # ... (continua per tutti i 68 KPI)
  - id: ai_velocity_multiplier
    label_it: "Moltiplicatore AI"
    formula: "median(manual_cycle_time) / median(ai_cycle_time)"
    interpretation: "Quante volte più veloce il lavoro AI-assisted vs manuale."
    good_if: "> 1.5x"
    benchmark: "Studi Claude Code 2025: 1.5-3x su task boilerplate, 1.2-1.5x su logica complessa"
  - id: roi_v2_index
    label_it: "Indice ROI v2"
    formula: "(features_shipped × complexity × compliance) / (cost × seasonality_adj)"
    interpretation: "Valore prodotto per euro AI speso, aggiustato qualità + periodo lavorativo."
    good_if: "> 1.0 (break-even); > 2.0 ottimo"
    benchmark: "N/A — metrica custom SIAE"
```

Completa YAML con **tutti i 68 KPI** (uso implementer: copy-paste template sopra e replicare con valori appropriati dal design doc §5).

## Step 2 — export_glossary.py

```python
"""Sheet 'Glossario KPI' per Executive Excel report."""
from __future__ import annotations
from pathlib import Path
import yaml
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


def load_glossary_data(yaml_path: Path) -> list[dict]:
    """Carica glossario da YAML. Empty list se file mancante."""
    if not yaml_path.exists():
        return []
    try:
        data = yaml.safe_load(yaml_path.read_text())
        return data.get("kpi", []) if data else []
    except Exception:
        return []


def write_glossary_sheet(wb: Workbook, glossary: list[dict]) -> None:
    """Scrive sheet 'Glossario KPI' come tab secondario verde."""
    ws = wb.create_sheet("📖 Glossario KPI")
    ws.sheet_properties.tabColor = "63BE7B"  # verde

    bold = Font(bold=True, size=12)
    header_fill = PatternFill("solid", fgColor="E8F5E9")

    ws["A1"] = "Glossario KPI — DevForge Dev Analytics"
    ws["A1"].font = Font(bold=True, size=14, color="0D6E3D")
    ws.merge_cells("A1:E1")

    headers = ["KPI", "Nome italiano", "Formula", "Interpretazione", "Buono se", "Benchmark industria"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c, value=h)
        cell.font = bold
        cell.fill = header_fill

    for i, kpi in enumerate(glossary, start=4):
        ws.cell(row=i, column=1, value=kpi.get("id", ""))
        ws.cell(row=i, column=2, value=kpi.get("label_it", ""))
        ws.cell(row=i, column=3, value=kpi.get("formula", ""))
        ws.cell(row=i, column=4, value=kpi.get("interpretation", ""))
        ws.cell(row=i, column=5, value=kpi.get("good_if", ""))
        ws.cell(row=i, column=6, value=kpi.get("benchmark", ""))
        ws.row_dimensions[i].height = 40
        for c in range(1, 7):
            ws.cell(row=i, column=c).alignment = Alignment(wrap_text=True, vertical="top")

    widths = [25, 30, 35, 45, 20, 30]
    for c, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w

    ws.freeze_panes = "A4"
```

## Step 3 — Test (5)

```python
def test_load_glossary_data_returns_list():
    glossary = eg.load_glossary_data(Path("skills/siae-dev-analytics/reference/kpi-glossary-data.yaml"))
    assert isinstance(glossary, list)
    assert len(glossary) >= 60  # tutti i 68 KPI almeno 60 popolati

def test_load_glossary_missing_file_returns_empty():
    assert eg.load_glossary_data(Path("/nonexistent/path.yaml")) == []

def test_write_glossary_sheet_creates_tab(tmp_path):
    from openpyxl import Workbook, load_workbook
    wb = Workbook()
    eg.write_glossary_sheet(wb, [{"id": "test_kpi", "label_it": "Test", "formula": "x", "interpretation": "y", "good_if": "z", "benchmark": "w"}])
    out = tmp_path / "t.xlsx"
    wb.save(out)
    wb2 = load_workbook(out)
    assert "📖 Glossario KPI" in wb2.sheetnames

def test_glossary_sheet_has_6_columns(tmp_path):
    from openpyxl import Workbook, load_workbook
    wb = Workbook()
    eg.write_glossary_sheet(wb, [])
    out = tmp_path / "t.xlsx"
    wb.save(out)
    wb2 = load_workbook(out)
    ws = wb2["📖 Glossario KPI"]
    headers = [c.value for c in ws[3]]
    assert len(headers) == 6 and "Formula" in headers

def test_glossary_malformed_yaml_returns_empty(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not yaml: {[}")
    assert eg.load_glossary_data(bad) == []
```

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_export_glossary.py -v
```

Output: `5 passed`.

## Criteri accettazione

- [ ] `kpi-glossary-data.yaml` popolato con ≥ 60 KPI (target 68)
- [ ] Sheet creata con tab verde
- [ ] 6 colonne: KPI, Nome, Formula, Interpretazione, Buono se, Benchmark
- [ ] Wrap text abilitato per celle descrittive
- [ ] Malformed YAML → empty, no crash
