import sys
import io

# Ensure UTF-8 output encoding for Windows PowerShell/CMD
if sys.platform.startswith('win'):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf-8')
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding='utf-8')
import os
import glob
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "r2r_postings_governance.db"
DROP_DIR = BASE_DIR / "data_drop"

def generate_risk_flags(cursor):
    """Automatically evaluates ingested data and populates audit_risk_flags table."""
    print("🔍 Running automated SOX/IFRS governance rule checks...")
    
    cursor.execute("DELETE FROM audit_risk_flags;")
    
    # Rule 1: Segregation of Duties (SoD) Violation
    cursor.execute("""
        INSERT INTO audit_risk_flags (journal_id, risk_rule_code, risk_level, flag_description)
        SELECT journal_id, 'SOD_VIOLATION', 'CRITICAL', 
               'Segregation of Duties breach: Preparer (' || preparer_id || ') approved their own entry.'
        FROM journal_headers
        WHERE preparer_id = approver_id AND approver_id IS NOT NULL AND approver_id != 'None';
    """)

    # Rule 2: Unapproved Batch
    cursor.execute("""
        INSERT INTO audit_risk_flags (journal_id, risk_rule_code, risk_level, flag_description)
        SELECT journal_id, 'UNAPPROVED_BATCH', 'HIGH', 
               'Batch upload or system interface processed without secondary approval.'
        FROM journal_headers
        WHERE approver_id IS NULL OR approver_id = 'None' OR approver_id = '';
    """)

    # Rule 3: Unbalanced Entries
    cursor.execute("""
        INSERT INTO audit_risk_flags (journal_id, risk_rule_code, risk_level, flag_description)
        SELECT h.journal_id, 'UNBALANCED_ENTRY', 'CRITICAL',
               'Ledger imbalance: Total Debits (' || SUM(l.debit_amount) || ') != Total Credits (' || SUM(l.credit_amount) || ').'
        FROM journal_headers h
        JOIN journal_lines l ON h.journal_id = l.journal_id
        GROUP BY h.journal_id
        HAVING SUM(l.debit_amount) != SUM(l.credit_amount);
    """)
    
    print("✅ Risk flags generated successfully!")

def archive_file(file_path, drop_dir, file_name):
    """Safely moves processed files to archive, avoiding naming collisions."""
    archive_dir = drop_dir / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    target_path = archive_dir / file_name
    if target_path.exists():
        # Append a timestamp to prevent FileExistsError
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(file_name)
        target_path = archive_dir / f"{name}_{timestamp}{ext}"
        
    os.rename(file_path, target_path)

def process_drops():
    """Scans data_drop folder for Excel or CSV files and safely loads them into SQLite."""
    if not DROP_DIR.exists():
        os.makedirs(DROP_DIR)
        print(f"📁 Created '{DROP_DIR.name}' folder. Drop your raw files there!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Process Excel files (.xlsx, .xls)
        excel_files = glob.glob(os.path.join(DROP_DIR, "*.xlsx")) + glob.glob(os.path.join(DROP_DIR, "*.xls"))
        for file_path in excel_files:
            file_name = os.path.basename(file_path)
            print(f"🔄 Processing Excel file: {file_name}...")
            
            xl = pd.ExcelFile(file_path)
            sheet_names = [str(s).lower() for s in xl.sheet_names]
            
            if "headers" not in sheet_names or "lines" not in sheet_names:
                print(f"❌ Error in {file_name}: Excel must contain 'Headers' and 'Lines' sheets.")
                continue

            df_headers = pd.read_excel(file_path, sheet_name="Headers")
            df_lines = pd.read_excel(file_path, sheet_name="Lines")

            df_headers.to_sql("journal_headers", conn, if_exists="append", index=False)
            df_lines.to_sql("journal_lines", conn, if_exists="append", index=False)

            generate_risk_flags(cursor)
            conn.commit()

            archive_file(Path(file_path), DROP_DIR, file_name)
            print(f"✅ Successfully ingested & archived {file_name}!\n")

        # 2. Process CSV pairs (*headers.csv and *lines.csv)
        header_csvs = glob.glob(os.path.join(DROP_DIR, "*headers.csv"))
        for h_path in header_csvs:
            h_name = os.path.basename(h_path)
            base_prefix = h_name.replace("headers.csv", "")
            l_name = f"{base_prefix}lines.csv"
            l_path = os.path.join(DROP_DIR, l_name)

            if os.path.exists(l_path):
                print(f"🔄 Processing CSV pair: {h_name} & {l_name}...")
                
                df_headers = pd.read_csv(h_path)
                df_lines = pd.read_csv(l_path)

                df_headers.to_sql("journal_headers", conn, if_exists="append", index=False)
                df_lines.to_sql("journal_lines", conn, if_exists="append", index=False)

                generate_risk_flags(cursor)
                conn.commit()

                archive_file(Path(h_path), DROP_DIR, h_name)
                archive_file(Path(l_path), DROP_DIR, l_name)
                print(f"✅ Successfully ingested & archived CSV pair!\n")

    except Exception as e:
        conn.rollback()
        print(f"❌ Critical error during ingestion: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    process_drops()