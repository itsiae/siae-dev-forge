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

    # -- Sheet 1: Summary -------------------------------------------------
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

    # -- Sheet 2: Per Developer -------------------------------------------
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

    # -- Sheet 3: Raw Data ------------------------------------------------
    ws3 = wb.create_sheet("Raw Data")
    if not raw_prs.empty:
        ws3.append(list(raw_prs.columns))
        for c in range(1, len(raw_prs.columns) + 1):
            ws3.cell(row=1, column=c).font = bold
        for _, row in raw_prs.iterrows():
            ws3.append([str(v) if v is not None else "" for v in row])
    else:
        ws3["A1"] = "No raw data available"

    # -- Sheet 4: Data Sources --------------------------------------------
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
