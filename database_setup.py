from pathlib import Path
import sqlite3

# 1. Get the exact folder where this Python script lives
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "r2r_postings_governance.db"

# 2. Connect to SQLite (this will create the file right here if it doesn't exist)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 3. Create the core R2R governance tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS journal_headers (
    journal_id TEXT PRIMARY KEY,
    posting_date TEXT NOT NULL,
    posting_type TEXT NOT NULL,
    preparer_id TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    is_manual INTEGER DEFAULT 1
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS journal_lines (
    line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id TEXT,
    account_number TEXT NOT NULL,
    debit_amount REAL NOT NULL,
    credit_amount REAL NOT NULL,
    FOREIGN KEY (journal_id) REFERENCES journal_headers (journal_id)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS audit_risk_flags (
    flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id TEXT,
    risk_rule_code TEXT,
    risk_level TEXT,
    flag_description TEXT,
    FOREIGN KEY (journal_id) REFERENCES journal_headers (journal_id)
);
""")

# Commit changes and close connection properly
conn.commit()
conn.close()

print(f"Database successfully created and tables initialized at: {DB_PATH}")