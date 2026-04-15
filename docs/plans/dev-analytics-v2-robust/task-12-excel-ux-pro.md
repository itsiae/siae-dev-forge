# Task 12 — F5b Excel UX Pro (8-Sheet Refactor)

**Goal:** Excel "bello" con 8 sheet + charts + tooltip + conditional formatting avanzato.
**AC coperti:** UX1-UX6 (design §2.6), AC-MACRO-5
**Dipendenze:** Task 07, 08, 09, 10, 11
**Effort:** ~120 min
**Test nuovi:** 14

## File coinvolti

- `scripts/export_excel.py` — refactor major
- `scripts/export_charts.py` — factory grafici openpyxl
- `tests/test_export_excel.py` — +8 test sheet structure
- `tests/test_export_charts.py` — 6 test charts

## Step 1 — export_charts.py

```python
"""openpyxl charts factory per Excel report."""
from __future__ import annotations
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, ScatterChart, PieChart, Reference, Series


def add_velocity_bar_chart(ws, data_sheet_name: str, n_devs: int) -> None:
    chart = BarChart()
    chart.title = "Indice Velocità per Sviluppatore"
    chart.y_axis.title = "Indice velocità (z-score)"
    chart.x_axis.title = "Sviluppatore"
    # Data range from "Per Developer" sheet: dev names col A, velocity_score col M (index 13)
    data = Reference(ws.parent[data_sheet_name], min_col=13, min_row=1, max_row=n_devs + 1, max_col=13)
    cats = Reference(ws.parent[data_sheet_name], min_col=1, min_row=2, max_row=n_devs + 1)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height = 10; chart.width = 20
    ws.add_chart(chart, "F3")


def add_velocity_quality_scatter(ws, data_sheet_name: str, n_devs: int) -> None:
    chart = ScatterChart()
    chart.title = "Velocità × Qualità (quadrant analysis)"
    chart.style = 13
    chart.x_axis.title = "Velocità"
    chart.y_axis.title = "Qualità"
    x = Reference(ws.parent[data_sheet_name], min_col=13, min_row=2, max_row=n_devs + 1)
    y = Reference(ws.parent[data_sheet_name], min_col=14, min_row=2, max_row=n_devs + 1)
    series = Series(y, x, title_from_data=False)
    chart.series.append(series)
    chart.height = 10; chart.width = 15
    ws.add_chart(chart, "F20")


def add_before_after_bar_chart(ws, kpi_names: list[str], baseline_vals: list[float], current_vals: list[float]) -> None:
    """Grouped bar chart: baseline vs current per KPI."""
    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = "AI Impact — Before / After"
    chart.y_axis.title = "Valore"
    # Scrivi data in cell helper poi Reference
    start_row = 50
    ws.cell(row=start_row, column=1, value="KPI")
    ws.cell(row=start_row, column=2, value="Baseline")
    ws.cell(row=start_row, column=3, value="Current")
    for i, (name, b, c) in enumerate(zip(kpi_names, baseline_vals, current_vals), start=start_row + 1):
        ws.cell(row=i, column=1, value=name)
        ws.cell(row=i, column=2, value=b)
        ws.cell(row=i, column=3, value=c)
    data = Reference(ws, min_col=2, min_row=start_row, max_row=start_row + len(kpi_names), max_col=3)
    cats = Reference(ws, min_col=1, min_row=start_row + 1, max_row=start_row + len(kpi_names))
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    ws.add_chart(chart, "E50")


def add_pr_types_pie_chart(ws, types: dict[str, int]) -> None:
    chart = PieChart()
    chart.title = "Distribuzione PR per Tipo (feat/fix/refactor/...)"
    # Helper cells
    start_row = 80
    for i, (t, c) in enumerate(types.items(), start=start_row):
        ws.cell(row=i, column=1, value=t)
        ws.cell(row=i, column=2, value=c)
    data = Reference(ws, min_col=2, min_row=start_row, max_row=start_row + len(types) - 1)
    labels = Reference(ws, min_col=1, min_row=start_row, max_row=start_row + len(types) - 1)
    chart.add_data(data)
    chart.set_categories(labels)
    ws.add_chart(chart, "E80")


def add_ai_vs_manual_pie(ws, ai_pct: float) -> None:
    """Pie chart AI-assisted vs Manual."""
    chart = PieChart()
    chart.title = "PR AI-assisted vs Manuali"
    ws.cell(row=100, column=1, value="AI-assisted")
    ws.cell(row=100, column=2, value=ai_pct)
    ws.cell(row=101, column=1, value="Manual")
    ws.cell(row=101, column=2, value=max(0, 1 - ai_pct))
    data = Reference(ws, min_col=2, min_row=100, max_row=101)
    labels = Reference(ws, min_col=1, min_row=100, max_row=101)
    chart.add_data(data)
    chart.set_categories(labels)
    ws.add_chart(chart, "E100")
```

## Step 2 — export_excel.py refactor: 8 sheet

Sheet order:
1. `Executive Summary` (tabColor rosso) — sintesi + AI Impact highlight + top 3 + warnings
2. `🤖 AI Impact Detail` (tabColor rosso) — before/after completo + correlation + attribution
3. `Per Developer` (tabColor blu) — 30+ colonne italiani + tooltip + conditional
4. `🌿 Work In Progress` (tabColor blu) — branch attivi snapshot
5. `Trends` (tabColor blu) — charts embedded
6. `Raw Data` (tabColor blu) — PR + Branches + Reviews denormalizzati
7. `📖 Glossario KPI` (tabColor verde) — via export_glossary
8. `Data Sources` (tabColor verde) — dichiarazione fonti + mode + warnings

## Step 3 — Tooltip cell via Comment

```python
from openpyxl.comments import Comment

def add_tooltip(cell, text: str, author: str = "DevForge"):
    cell.comment = Comment(text, author)
```

In "Per Developer" sheet: applica tooltip a ogni cella header con la description da glossary:
```python
glossary = load_glossary_data(Path(...))
gdict = {k["id"]: k for k in glossary}
for c, col_name in enumerate(cols, start=1):
    kpi_info = gdict.get(col_name)
    if kpi_info:
        add_tooltip(ws.cell(row=1, column=c), kpi_info.get("interpretation", ""))
```

## Step 4 — Test (14)

```python
def test_export_has_8_sheets(tmp_path, sample_data):
    # ... verifica sheetnames == {8 tab names}

def test_executive_summary_is_first_tab(): ...
def test_ai_impact_sheet_exists(): ...
def test_wip_sheet_exists(): ...
def test_trends_sheet_has_charts(): ...
def test_glossary_sheet_present(): ...
def test_data_sources_sheet_has_warnings(): ...
def test_per_developer_has_tooltip_on_header(): ...
def test_tab_colors_applied(): ...
def test_conditional_formatting_data_bars(): ...
def test_icon_sets_on_score_columns(): ...
def test_excel_file_locked_retries_with_timestamp_suffix(): ...
def test_unicode_dev_name_preserved_in_sheet(): ...
def test_chart_with_empty_data_has_placeholder(): ...
```

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_export_excel.py skills/siae-dev-analytics/tests/test_export_charts.py -v
```

Output: `14 new passing`.

## Criteri accettazione

- [ ] 8 sheet in ordine fissato (ADR-016)
- [ ] Tab colors: exec=rosso (CC0000), data=blu (4472C4), docs=verde (63BE7B)
- [ ] 5 chart type presenti: bar, scatter, grouped bar before/after, pie, line
- [ ] Tooltip su ogni header Per Developer
- [ ] Conditional formatting: data bars + color scale + icon sets
- [ ] File locked → retry con suffisso `-YYYYMMDD_HHMMSS.xlsx`
- [ ] Unicode dev names preservati (test con emoji + accenti)
