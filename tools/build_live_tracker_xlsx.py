#!/usr/bin/env python3
"""Build the ONE-TIME live tracker workbook.

Creates an XLSX that, once uploaded to Google Drive (converted to a Google
Sheet), pulls tracker/prospects.csv from GitHub raw via IMPORTDATA. The
resulting Google Sheet is permanent: every `git push` of the tracker CSV
refreshes it automatically. Only run this again if the CSV URL changes.
"""
from pathlib import Path
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

CSV_URL = (
    "https://raw.githubusercontent.com/twbsportsguy/ClaudeCode/"
    "claude/sales-prospecting-workflow-wcsfty/tracker/prospects.csv"
)

NAVY = "13294B"
LIGHT_BLUE = "E8F1F8"
GREEN_FILL = "C8E6C9"
GREEN_TEXT = "1B5E20"
AMBER_FILL = "FFF3CD"
AMBER_TEXT = "7A5C00"
GRAY_FILL = "ECEFF1"
GRAY_TEXT = "455A64"

# CSV column order -> sheet columns A..V
WIDTHS = {
    "A": 11, "B": 6, "C": 6, "D": 32, "E": 14, "F": 13, "G": 6, "H": 26,
    "I": 9, "J": 10, "K": 14, "L": 42, "M": 40, "N": 19, "O": 24, "P": 30,
    "Q": 14, "R": 12, "S": 7, "T": 9, "U": 28, "V": 34,
}
MAX_ROWS = 300


def build_prospects(ws):
    ws.freeze_panes = "E2"
    ws["A1"] = f'=IMPORTDATA("{CSV_URL}")'
    for col, w in WIDTHS.items():
        ws.column_dimensions[col].width = w
    ws.row_dimensions[1].height = 26
    for c in range(1, 23):
        cell = ws.cell(row=1, column=c)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
    for r in range(2, MAX_ROWS):
        for col in ("L", "M", "U", "V", "O"):
            ws[f"{col}{r}"].alignment = Alignment(vertical="top", wrap_text=True)
        for col in ("B", "C", "G", "S"):
            ws[f"{col}{r}"].alignment = Alignment(horizontal="center", vertical="top")

    body = f"A2:V{MAX_ROWS}"
    ws.conditional_formatting.add(body, FormulaRule(
        formula=['AND($D2<>"",ISEVEN(ROW()))'], stopIfTrue=False,
        fill=PatternFill("solid", fgColor=LIGHT_BLUE)))
    rank = f"B2:B{MAX_ROWS}"
    ws.conditional_formatting.add(rank, FormulaRule(
        formula=['$B2="A"'], stopIfTrue=True,
        fill=PatternFill("solid", fgColor=GREEN_FILL),
        font=Font(bold=True, color=GREEN_TEXT)))
    ws.conditional_formatting.add(rank, FormulaRule(
        formula=['$B2="B"'], stopIfTrue=True,
        fill=PatternFill("solid", fgColor=AMBER_FILL),
        font=Font(bold=True, color=AMBER_TEXT)))
    ws.conditional_formatting.add(rank, FormulaRule(
        formula=['$B2="C"'], stopIfTrue=True,
        fill=PatternFill("solid", fgColor=GRAY_FILL),
        font=Font(bold=True, color=GRAY_TEXT)))
    ws.conditional_formatting.add(f"S2:S{MAX_ROWS}", FormulaRule(
        formula=['$S2="Y"'], stopIfTrue=True,
        font=Font(bold=True, color=GREEN_TEXT)))


def build_summary(ws):
    ws.sheet_view.showGridLines = False
    ws.merge_cells("B2:H2")
    ws["B2"] = "Finley Golf Club — Corporate Partnerships Pipeline"
    ws["B2"].font = Font(bold=True, size=18, color=NAVY)
    ws.merge_cells("B3:H3")
    ws["B3"] = 'Tyler Baity · live view — updates automatically from the prospect tracker'
    ws["B3"].font = Font(size=11, color="666666")

    kpis = [
        ("Companies", '=COUNTUNIQUE(Prospects!D2:D)', NAVY),
        ("Contacts", "=COUNTA(Prospects!N2:N)", NAVY),
        ("Drafts Ready", '=COUNTIF(Prospects!S2:S,"Y")', GREEN_TEXT),
        ("A Companies", '=COUNTUNIQUE(IFERROR(FILTER(Prospects!D2:D,Prospects!B2:B="A")))', GREEN_TEXT),
        ("B Companies", '=COUNTUNIQUE(IFERROR(FILTER(Prospects!D2:D,Prospects!B2:B="B")))', AMBER_TEXT),
        ("C Companies", '=COUNTUNIQUE(IFERROR(FILTER(Prospects!D2:D,Prospects!B2:B="C")))', GRAY_TEXT),
    ]
    for i, (label, formula, color) in enumerate(kpis):
        col = 2 + i
        v, l = ws.cell(row=5, column=col), ws.cell(row=6, column=col)
        v.value, l.value = formula, label
        v.font = Font(bold=True, size=22, color=color)
        l.font = Font(size=10, color="666666")
        v.alignment = l.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(col)].width = 15

    ws["B9"] = "Latest activity (most recent first)"
    ws["B9"].font = Font(bold=True, size=12, color=NAVY)
    ws["B10"] = ('=QUERY(Prospects!A2:V,"select A, B, D, N, T, U where D is not null '
                 'order by A desc, B asc limit 15 '
                 'label A \'Date\', B \'Rank\', D \'Company\', N \'Contact\', T \'Status\', U \'Next Step\'",1)')
    for col, w in {"B": 12, "C": 7, "D": 36, "E": 20, "F": 12, "G": 30}.items():
        ws.column_dimensions[col].width = max(ws.column_dimensions[col].width or 0, w)
    for c in range(2, 8):
        cell = ws.cell(row=10, column=c)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.font = Font(bold=True, color="FFFFFF")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Sales Tracker (live).xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    build_summary(ws)
    build_prospects(wb.create_sheet("Prospects"))
    wb.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
