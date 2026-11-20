import sys
import io
import sqlite3
import pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Ensure UTF-8 output encoding for Windows PowerShell/CMD
if sys.platform.startswith("win"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "r2r_postings_governance.db"
OUTPUT_REPORT = BASE_DIR / "R2R_Audit_Executive_Dashboard.xlsx"


def generate_excel_audit_report():
    if not DB_PATH.exists():
        print("❌ Database not found. Run your ingestion engine first!")
        return

    print("📊 Extracting audit data from SQLite for Excel generation...")
    conn = sqlite3.connect(DB_PATH)

    # 1. Fetch Summary / KPIs
    df_summary = pd.read_sql("""
        SELECT risk_rule_code, risk_level, COUNT(*) as exception_count
        FROM audit_risk_flags
        GROUP BY risk_rule_code, risk_level
    """, conn)

    # 2. Fetch Detailed Risk Exceptions
    df_exceptions = pd.read_sql("""
        SELECT 
            f.flag_id AS 'Flag ID',
            f.journal_id AS 'Journal ID',
            f.risk_rule_code AS 'Rule Code',
            f.risk_level AS 'Risk Level',
            f.flag_description AS 'Description',
            h.posting_date AS 'Posting Date',
            h.posting_type AS 'Posting Type',
            h.preparer_id AS 'Preparer',
            h.approver_id AS 'Approver'
        FROM audit_risk_flags f
        JOIN journal_headers h ON f.journal_id = h.journal_id
    """, conn)

    # 3. Safely Fetch Full Journal Line-Items
    query_lines = """
        SELECT 
            journal_id AS 'Journal ID',
            line_id AS 'Line ID',
            account_code AS 'Account Code',
            description AS 'Line Description',
            debit_amount AS 'Debit ($)',
            credit_amount AS 'Credit ($)'
        FROM journal_lines
    """
    df_lines = pd.read_sql(query_lines, conn)
    conn.close()

    # Create Workbook using openpyxl
    wb = Workbook()

    # Setup Color Palettes & Styles (Classic Corporate Navy Theme)
    navy_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    white_bold_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=16, bold=True, color="1F4E78")
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="595959")
    regular_font = Font(name="Calibri", size=11)

    critical_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    critical_font = Font(name="Calibri", size=11, bold=True, color="9C0006")
    high_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    high_font = Font(name="Calibri", size=11, bold=True, color="9C6500")

    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # ---------------------------------------------------------
    # TAB 1: Executive Summary Dashboard
    # ---------------------------------------------------------
    ws_summary = wb.active
    if not isinstance(ws_summary, Worksheet):
        ws_summary = wb.create_sheet(title="Executive Summary")
    else:
        ws_summary.title = "Executive Summary"
    ws_summary.sheet_view.showGridLines = True

    ws_summary['A1'] = "R2R Journal Entry Governance & Audit Dashboard"
    ws_summary['A1'].font = title_font
    ws_summary['A2'] = "Automated SOX 404 & IFRS Compliance Testing Results"
    ws_summary['A2'].font = subtitle_font

    ws_summary.append([""])  # Blank row
    ws_summary.append(["Risk Rule Code", "Risk Level", "Exception Count"])

    # Style summary table headers
    for col_num in range(1, 4):
        cell = ws_summary.cell(row=4, column=col_num)
        cell.fill = navy_fill
        cell.font = white_bold_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in df_summary.itertuples(index=False):
        ws_summary.append(list(row))

    # Format data rows
    for row_num in range(5, 5 + len(df_summary)):
        for col_num in range(1, 4):
            cell = ws_summary.cell(row=row_num, column=col_num)
            cell.font = regular_font
            cell.border = thin_border
            if col_num == 3:
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = '#,##0'

    # ---------------------------------------------------------
    # TAB 2: Detailed Exceptions Log
    # ---------------------------------------------------------
    ws_exceptions = wb.create_sheet(title="Risk Exceptions Log")
    ws_exceptions.sheet_view.showGridLines = True

    header_cols_exceptions = [str(col) for col in df_exceptions.columns]
    ws_exceptions.append(header_cols_exceptions)
    for col_num in range(1, len(header_cols_exceptions) + 1):
        cell = ws_exceptions.cell(row=1, column=col_num)
        cell.fill = navy_fill
        cell.font = white_bold_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in df_exceptions.itertuples(index=False):
        ws_exceptions.append(list(row))

    for row_num in range(2, 2 + len(df_exceptions)):
        for col_num in range(1, len(header_cols_exceptions) + 1):
            cell = ws_exceptions.cell(row=row_num, column=col_num)
            cell.font = regular_font
            cell.border = thin_border

            # Highlight Risk Levels
            risk_val = ws_exceptions.cell(row=row_num, column=4).value
            if risk_val == "CRITICAL" and col_num == 4:
                cell.fill = critical_fill
                cell.font = critical_font
            elif risk_val == "HIGH" and col_num == 4:
                cell.fill = high_fill
                cell.font = high_font

    # ---------------------------------------------------------
    # TAB 3: Full Ledger Line Items
    # ---------------------------------------------------------
    ws_lines = wb.create_sheet(title="Ledger Line Items")
    ws_lines.sheet_view.showGridLines = True

    header_cols_lines = [str(col) for col in df_lines.columns]
    ws_lines.append(header_cols_lines)
    for col_num in range(1, len(header_cols_lines) + 1):
        cell = ws_lines.cell(row=1, column=col_num)
        cell.fill = navy_fill
        cell.font = white_bold_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in df_lines.itertuples(index=False):
        ws_lines.append(list(row))

    for row_num in range(2, 2 + len(df_lines)):
        for col_num in range(1, len(header_cols_lines) + 1):
            cell = ws_lines.cell(row=row_num, column=col_num)
            cell.font = regular_font
            cell.border = thin_border

            # Format Debits and Credits as Currency
            if col_num in [5, 6]:
                cell.number_format = '$#,##0.00'
                cell.alignment = Alignment(horizontal="right")

    # ---------------------------------------------------------
    # Auto-Fit Column Widths Across All Sheets
    # ---------------------------------------------------------
    for ws in wb.worksheets:
        for col in ws.columns:
            max_length = 0
            first_cell = col[0]
            if first_cell.column is not None:
                col_letter = get_column_letter(int(first_cell.column))
                for cell in col:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = max(max_length + 4, 12)

    # Save the professional workbook
    wb.save(OUTPUT_REPORT)
    print(f"✅ Executive Excel Report generated successfully: {OUTPUT_REPORT.name}\n")


if __name__ == "__main__":
    generate_excel_audit_report()
