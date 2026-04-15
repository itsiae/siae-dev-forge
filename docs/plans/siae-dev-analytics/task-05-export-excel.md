# Task 05 — export_excel.py (4 sheet + formatting)

**Goal:** Export report in Excel `.xlsx` con 4 sheet (Summary, Per Developer, Raw Data, Data Sources), conditional formatting, header confidenziale.

**AC coperti:** AC06, AC07

**Dipendenze:** Task 1

**Tempo stimato:** 30 min

---

## File coinvolti

- `skills/siae-dev-analytics/scripts/export_excel.py` (nuovo)
- `skills/siae-dev-analytics/tests/test_export_excel.py` (nuovo)

## Step 1 — TDD: Scrivi test PRIMA

Crea `tests/test_export_excel.py`:

```python
"""Test per export_excel.py."""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
from openpyxl import load_workbook

import export_excel as ee


@pytest.fixture
def sample_kpis_df() -> pd.DataFrame:
    """DataFrame con 3 dev + 14 colonne (11 KPI + 3 score)."""
    data = {
        "pr_cycle_time_p50": {"alice": 30.0, "bob": 7.0, "carol": 20.0},
        "lead_time_to_merge_p50": {"alice": 39.5, "bob": 13.5, "carol": 21.0},
        "pr_throughput_weekly": {"alice": 0.47, "bob": 0.47, "carol": 0.23},
        "time_to_first_review_p50": {"alice": 13.0, "bob": 1.5, "carol": 2.0},
        "deploy_frequency_monthly": {"alice": 1.0, "bob": 1.0, "carol": 0.0},
        "review_comments_p50": {"alice": 3.5, "bob": 1.5, "carol": 1.0},
        "rework_ratio": {"alice": 0.0, "bob": 0.0, "carol": 0.0},
        "test_presence_rate": {"alice": 0.5, "bob": 0.5, "carol": 1.0},
        "verification_rate": {"alice": 0.5, "bob": 0.5, "carol": 0.0},
        "design_driven_rate": {"alice": 0.5, "bob": 0.5, "carol": 0.0},
        "revert_rate": {"alice": 0.0, "bob": 0.5, "carol": 0.0},
        "velocity_score": {"alice": -0.2, "bob": 0.5, "carol": -0.3},
        "quality_score": {"alice": 0.3, "bob": -0.5, "carol": 0.2},
        "roi_index": {"alice": -0.06, "bob": -0.25, "carol": -0.06},
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_prs_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"repo": "itsiae/r", "number": 1, "author": "alice", "cycle_time_hours": 4.0},
        {"repo": "itsiae/r", "number": 2, "author": "bob", "cycle_time_hours": 6.0},
    ])


@pytest.fixture
def sample_source_report() -> dict:
    return {
        "github": True,
        "s3_devforge": False,
        "s3_blend": False,
        "mode": "GITHUB-ONLY",
    }


def test_export_creates_file(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """Export produce file xlsx."""
    out = tmp_path / "report.xlsx"
    ee.export(
        kpis_df=sample_kpis_df,
        raw_prs=sample_prs_df,
        source_report=sample_source_report,
        window=("2026-03-01", "2026-03-31"),
        output_path=out,
    )
    assert out.exists()
    assert out.stat().st_size > 0


def test_export_has_4_sheets(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """Xlsx contiene 4 sheet: Summary, Per Developer, Raw Data, Data Sources."""
    out = tmp_path / "report.xlsx"
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out)
    wb = load_workbook(out)
    assert set(wb.sheetnames) == {"Summary", "Per Developer", "Raw Data", "Data Sources"}


def test_summary_has_mode_and_window(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """Summary contiene mode e finestra."""
    out = tmp_path / "report.xlsx"
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out)
    wb = load_workbook(out)
    summary = wb["Summary"]
    text = " ".join(str(c.value) for row in summary.iter_rows() for c in row if c.value)
    assert "GITHUB-ONLY" in text
    assert "2026-03-01" in text
    assert "2026-03-31" in text


def test_summary_has_confidential_header(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """Summary ha header CONFIDENZIALE."""
    out = tmp_path / "report.xlsx"
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out)
    wb = load_workbook(out)
    text = " ".join(str(c.value) for row in wb["Summary"].iter_rows() for c in row if c.value)
    assert "CONFIDENZIALE" in text.upper()


def test_per_developer_has_all_kpi_columns(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """Sheet Per Developer ha 14 colonne KPI + 1 col dev."""
    out = tmp_path / "report.xlsx"
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out)
    wb = load_workbook(out)
    header = [c.value for c in wb["Per Developer"][1]]
    assert "dev" in header
    for kpi in ["pr_cycle_time_p50", "velocity_score", "quality_score", "roi_index"]:
        assert kpi in header


def test_data_sources_sheet_declares_mode(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """Data Sources elenca quali fonti sono usate."""
    out = tmp_path / "report.xlsx"
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out)
    wb = load_workbook(out)
    text = " ".join(str(c.value) for row in wb["Data Sources"].iter_rows() for c in row if c.value)
    assert "github" in text.lower()
    assert "s3" in text.lower() or "telemetry" in text.lower()
    assert "GITHUB-ONLY" in text


def test_raw_data_contains_prs(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """Sheet Raw Data contiene PR raw."""
    out = tmp_path / "report.xlsx"
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out)
    wb = load_workbook(out)
    ws = wb["Raw Data"]
    # header + 2 righe dati
    assert ws.max_row >= 3


def test_anonymize_replaces_logins(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """anonymize=True → nessun login originale nel file."""
    out = tmp_path / "report.xlsx"
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out, anonymize=True)
    wb = load_workbook(out)
    all_text = ""
    for sheet in wb.sheetnames:
        for row in wb[sheet].iter_rows():
            for cell in row:
                if cell.value:
                    all_text += str(cell.value) + " "
    assert "alice" not in all_text
    assert "bob" not in all_text
    assert "carol" not in all_text


def test_reproducibility_same_input_same_checksum(tmp_path, sample_kpis_df, sample_prs_df, sample_source_report):
    """Stesso input → stesso file (escludendo metadata timestamp)."""
    import hashlib
    out1 = tmp_path / "r1.xlsx"
    out2 = tmp_path / "r2.xlsx"
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out1, generated_at="2026-04-15T00:00:00Z")
    ee.export(sample_kpis_df, sample_prs_df, sample_source_report,
              ("2026-03-01", "2026-03-31"), out2, generated_at="2026-04-15T00:00:00Z")
    # Openpyxl include metadata auto — testiamo che le cell values coincidano
    from openpyxl import load_workbook
    wb1 = load_workbook(out1)
    wb2 = load_workbook(out2)
    for sheet in wb1.sheetnames:
        vals1 = [c.value for row in wb1[sheet].iter_rows() for c in row]
        vals2 = [c.value for row in wb2[sheet].iter_rows() for c in row]
        assert vals1 == vals2, f"sheet {sheet} differs"
```

## Step 2 — Run test, verifica che falliscono

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_export_excel.py -v 2>&1 | tail -10
```

Output atteso: `ModuleNotFoundError: No module named 'export_excel'`.

## Step 3 — Implementa `export_excel.py`

Crea `skills/siae-dev-analytics/scripts/export_excel.py`:

```python
"""Export KPI report in Excel xlsx con 4 sheet + conditional formatting."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.utils import get_column_letter


def _anonymize_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.index = [hashlib.sha256(str(i).encode()).hexdigest()[:8] for i in df.index]
    return df


def _anonymize_column(s: pd.Series) -> pd.Series:
    return s.apply(lambda v: hashlib.sha256(str(v).encode()).hexdigest()[:8])


def export(
    kpis_df: pd.DataFrame,
    raw_prs: pd.DataFrame,
    source_report: dict,
    window: tuple[str, str],
    output_path: Path,
    *,
    anonymize: bool = False,
    generated_at: str | None = None,
) -> Path:
    """Export DataFrame KPI in xlsx 4-sheet."""
    generated_at = generated_at or datetime.utcnow().isoformat() + "Z"

    if anonymize:
        kpis_df = _anonymize_index(kpis_df)
        if "author" in raw_prs.columns:
            raw_prs = raw_prs.copy()
            raw_prs["author"] = _anonymize_column(raw_prs["author"])

    wb = Workbook()

    # ── Sheet 1: Summary ─────────────────────────────────
    ws = wb.active
    ws.title = "Summary"

    bold = Font(bold=True, size=12)
    title_fill = PatternFill("solid", fgColor="FFF3CD")

    ws["A1"] = "CONFIDENZIALE — Dati Personali SIAE"
    ws["A1"].font = Font(bold=True, color="CC0000", size=14)
    ws["A1"].fill = title_fill
    ws.merge_cells("A1:D1")

    ws["A3"] = "DevForge Dev Analytics Report"
    ws["A3"].font = bold
    ws["A4"] = "Generated at:"; ws["B4"] = generated_at
    ws["A5"] = "Mode:"; ws["B5"] = source_report.get("mode", "UNKNOWN")
    ws["A6"] = "Window:"; ws["B6"] = f"{window[0]} → {window[1]}"
    ws["A7"] = "Developers:"; ws["B7"] = len(kpis_df)
    ws["A8"] = "Anonymized:"; ws["B8"] = "YES" if anonymize else "NO"

    # Top/Bottom 5 ROI
    ws["A10"] = "Top 5 ROI Index"; ws["A10"].font = bold
    top5 = kpis_df.sort_values("roi_index", ascending=False).head(5)
    ws["A11"] = "Dev"; ws["B11"] = "ROI"; ws["C11"] = "Velocity"; ws["D11"] = "Quality"
    for i, (dev, row) in enumerate(top5.iterrows(), start=12):
        ws[f"A{i}"] = dev
        ws[f"B{i}"] = round(row["roi_index"], 3)
        ws[f"C{i}"] = round(row["velocity_score"], 3)
        ws[f"D{i}"] = round(row["quality_score"], 3)

    bottom_start = 12 + len(top5) + 2
    ws[f"A{bottom_start}"] = "Bottom 5 ROI Index"; ws[f"A{bottom_start}"].font = bold
    bottom5 = kpis_df.sort_values("roi_index", ascending=True).head(5)
    ws[f"A{bottom_start+1}"] = "Dev"; ws[f"B{bottom_start+1}"] = "ROI"
    ws[f"C{bottom_start+1}"] = "Velocity"; ws[f"D{bottom_start+1}"] = "Quality"
    for i, (dev, row) in enumerate(bottom5.iterrows(), start=bottom_start + 2):
        ws[f"A{i}"] = dev
        ws[f"B{i}"] = round(row["roi_index"], 3)
        ws[f"C{i}"] = round(row["velocity_score"], 3)
        ws[f"D{i}"] = round(row["quality_score"], 3)

    for col_idx in range(1, 5):
        ws.column_dimensions[get_column_letter(col_idx)].width = 20

    # ── Sheet 2: Per Developer ───────────────────────────
    ws2 = wb.create_sheet("Per Developer")
    cols = ["dev"] + list(kpis_df.columns)
    ws2.append(cols)
    for c in range(1, len(cols) + 1):
        ws2.cell(row=1, column=c).font = bold

    for dev, row in kpis_df.iterrows():
        ws2.append([dev] + [round(v, 3) if isinstance(v, (int, float)) else v for v in row])

    # Conditional formatting su z-score columns (velocity_score, quality_score, roi_index)
    n_rows = len(kpis_df) + 1
    for score_col in ["velocity_score", "quality_score", "roi_index"]:
        if score_col in cols:
            c_idx = cols.index(score_col) + 1
            col_letter = get_column_letter(c_idx)
            rng = f"{col_letter}2:{col_letter}{n_rows}"
            rule = ColorScaleRule(
                start_type="min", start_color="FF6B6B",
                mid_type="num", mid_value=0, mid_color="FFEB9C",
                end_type="max", end_color="63BE7B",
            )
            ws2.conditional_formatting.add(rng, rule)

    ws2.freeze_panes = "B2"
    for col_idx in range(1, len(cols) + 1):
        ws2.column_dimensions[get_column_letter(col_idx)].width = 18

    # ── Sheet 3: Raw Data ────────────────────────────────
    ws3 = wb.create_sheet("Raw Data")
    if not raw_prs.empty:
        ws3.append(list(raw_prs.columns))
        for c in range(1, len(raw_prs.columns) + 1):
            ws3.cell(row=1, column=c).font = bold
        for _, row in raw_prs.iterrows():
            ws3.append([str(v) if v is not None else "" for v in row])
    else:
        ws3["A1"] = "No raw data available"

    # ── Sheet 4: Data Sources ────────────────────────────
    ws4 = wb.create_sheet("Data Sources")
    ws4["A1"] = "Data Sources Declaration"
    ws4["A1"].font = Font(bold=True, size=14)
    ws4["A3"] = "Mode:"; ws4["B3"] = source_report.get("mode", "UNKNOWN")
    ws4["A4"] = "Generated at:"; ws4["B4"] = generated_at

    ws4["A6"] = "Source"; ws4["B6"] = "Available"; ws4["C6"] = "Notes"
    for c in range(1, 4):
        ws4.cell(row=6, column=c).font = bold

    ws4.append(["GitHub", "YES" if source_report.get("github") else "NO",
                "Ground truth — gh graphql"])
    ws4.append(["S3 devforge-logs", "YES" if source_report.get("s3_devforge") else "NO",
                "DevForge telemetry events"])
    ws4.append(["S3 blend-usage", "YES" if source_report.get("s3_blend") else "NO",
                "Bedrock+Anthropic token blend"])

    ws4["A12"] = "KPI calculability per mode:"; ws4["A12"].font = bold
    mode = source_report.get("mode", "UNKNOWN")
    if mode == "FULL":
        ws4["A13"] = "11/11 KPI + ROI with real cost_score"
    elif mode == "HYBRID":
        ws4["A13"] = "11/11 KPI, ROI = velocity × quality (cost=1)"
    elif mode == "GITHUB-ONLY":
        ws4["A13"] = "11/11 KPI, Q4 best-effort (commit trailer), ROI = velocity × quality"
    else:
        ws4["A13"] = f"Mode {mode} — check configuration"

    for col_idx in range(1, 4):
        ws4.column_dimensions[get_column_letter(col_idx)].width = 25

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--kpis", required=True, help="CSV path con KPI")
    parser.add_argument("--prs", required=True, help="CSV path con PR raw")
    parser.add_argument("--sources", required=True, help="JSON path con source report")
    parser.add_argument("--from", dest="window_from", required=True)
    parser.add_argument("--to", dest="window_to", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--anonymize", action="store_true")
    args = parser.parse_args()

    kpis = pd.read_csv(args.kpis, index_col=0)
    prs = pd.read_csv(args.prs)
    sources = json.loads(Path(args.sources).read_text())
    out = export(kpis, prs, sources, (args.window_from, args.window_to),
                 Path(args.out), anonymize=args.anonymize)
    print(f"Report saved to: {out}")
```

## Step 4 — Run test, verifica che passano

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_export_excel.py -v 2>&1 | tail -15
```

Output atteso: `9 passed`.

## Step 5 — Commit

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
git add skills/siae-dev-analytics/scripts/export_excel.py \
        skills/siae-dev-analytics/tests/test_export_excel.py
git commit -m "feat(skill): add export_excel for siae-dev-analytics [Task 5/7]

- 4 sheet: Summary (Top/Bottom ROI), Per Developer (14 col), Raw Data, Data Sources
- ConditionalFormatting ColorScale su z-score columns
- Header CONFIDENZIALE, freeze pane, column width
- anonymize=True → SHA256[:8] su index + author
- Riproducibile: stesso input + generated_at → stesso contenuto cell
- 9 test pytest pass

AC06, AC07"
```

## Criteri di accettazione Task 5

- [ ] `export()` produce xlsx con 4 sheet esatti
- [ ] Summary ha header CONFIDENZIALE + Top/Bottom 5 ROI
- [ ] Per Developer ha freeze_panes, 14 colonne KPI, conditional formatting su score
- [ ] Data Sources dichiara mode (FULL/HYBRID/GITHUB-ONLY) e calcolabilità
- [ ] `anonymize=True` → nessun login originale nel file
- [ ] Riproducibilità: stesso input + generated_at fisso → stesse cell values
- [ ] 9 test pytest pass
- [ ] Commit conventional

## Verifica

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_export_excel.py -v --tb=short
```

Output atteso: `9 passed`.
