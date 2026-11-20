import sqlite3
import pandas as pd

DB_NAME = "r2r_postings_governance.db"

def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Create Tables
    cursor.executescript("""
    DROP TABLE IF EXISTS audit_risk_flags;
    DROP TABLE IF EXISTS journal_lines;
    DROP TABLE IF EXISTS journal_headers;

    CREATE TABLE journal_headers (
        journal_id TEXT PRIMARY KEY,
        posting_date DATE NOT NULL,
        posting_type TEXT CHECK(posting_type IN ('STANDARD', 'RECURRING', 'PAYROLL_INTERFACE', 'REVERSAL', 'MASS_DATA')),
        entity_id TEXT NOT NULL,
        preparer_id TEXT NOT NULL,
        approver_id TEXT,
        source_system TEXT DEFAULT 'SAP_S4HANA',
        batch_reference TEXT,
        description TEXT,
        is_manual BOOLEAN NOT NULL DEFAULT 1,
        status TEXT DEFAULT 'PENDING_APPROVAL'
    );

    CREATE TABLE journal_lines (
        line_id INTEGER PRIMARY KEY AUTOINCREMENT,
        journal_id TEXT NOT NULL,
        account_code TEXT NOT NULL,
        cost_center TEXT,
        debit_amount REAL DEFAULT 0.00,
        credit_amount REAL DEFAULT 0.00,
        currency TEXT DEFAULT 'EUR',
        FOREIGN KEY (journal_id) REFERENCES journal_headers(journal_id)
    );

    CREATE TABLE audit_risk_flags (
        flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        journal_id TEXT NOT NULL,
        risk_rule_code TEXT NOT NULL,
        risk_level TEXT CHECK(risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
        flag_description TEXT NOT NULL,
        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (journal_id) REFERENCES journal_headers(journal_id)
    );
    """)
    
    # 2. Insert Mock Data across the 5 Posting Types
    mock_headers = [
        ('JE-STD-001', '2026-06-30', 'STANDARD', 'DE01', 'analyst_a', 'manager_b', 'SAP_S4HANA', None, 'Monthly audit fee accrual', 1, 'PENDING_APPROVAL'),
        ('JE-STD-002', '2026-06-30', 'STANDARD', 'DE01', 'rogue_user', 'rogue_user', 'SAP_S4HANA', None, 'Manual reclassification (SoD Risk)', 1, 'PENDING_APPROVAL'),
        ('JE-REC-001', '2026-06-01', 'RECURRING', 'DE01', 'finance_bot', 'controller_c', 'SAP_S4HANA', 'REC-RENT-2026', 'Frankfurt office rent recurring', 0, 'PENDING_APPROVAL'),
        ('JE-PAY-001', '2026-06-25', 'PAYROLL_INTERFACE', 'DE01', 'workday_interface', None, 'WORKDAY', 'BATCH-PAY-06', 'June 2026 Gross Salary (Unapproved Risk)', 0, 'PENDING_APPROVAL'),
        ('JE-REV-001', '2026-06-01', 'REVERSAL', 'DE01', 'analyst_a', 'manager_b', 'SAP_S4HANA', 'ACC-MAY-01', 'Reversal of May utilities accrual', 1, 'PENDING_APPROVAL'),
        ('JE-MASS-001', '2026-06-30', 'MASS_DATA', 'DE01', 'system_admin', None, 'EXCEL_UPLOAD', 'BATCH-MASS-99', 'High volume IC allocation (Unbalanced Risk)', 1, 'PENDING_APPROVAL')
    ]
    cursor.executemany("INSERT INTO journal_headers VALUES (?,?,?,?,?,?,?,?,?,?,?)", mock_headers)

    mock_lines = [
        ('JE-STD-001', '600000', 'CC-FIN', 5000.00, 0.00),
        ('JE-STD-001', '210000', 'CC-FIN', 0.00, 5000.00),
        ('JE-STD-002', '700000', 'CC-MGT', 150000.00, 0.00),
        ('JE-STD-002', '110000', 'CC-MGT', 0.00, 150000.00),
        ('JE-REC-001', '610000', 'CC-OPS', 12000.00, 0.00),
        ('JE-REC-001', '220000', 'CC-OPS', 0.00, 12000.00),
        ('JE-PAY-001', '650000', 'CC-HR', 85000.00, 0.00),
        ('JE-PAY-001', '230000', 'CC-HR', 0.00, 85000.00),
        ('JE-REV-001', '210000', 'CC-FIN', 3500.00, 0.00),
        ('JE-REV-001', '600000', 'CC-FIN', 0.00, 3500.00),
        # Unbalanced line intentionally planted:
        ('JE-MASS-001', '710000', 'CC-ALL', 45000.00, 0.00),
        ('JE-MASS-001', '720000', 'CC-ALL', 0.00, 44000.00) 
    ]
    cursor.executemany("INSERT INTO journal_lines (journal_id, account_code, cost_center, debit_amount, credit_amount) VALUES (?,?,?,?,?)", mock_lines)
    
    conn.commit()
    conn.close()
    print("Database initialized and populated successfully.")

def run_forensic_audit_rules():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_risk_flags")

    # Rule 1: Segregation of Duties (SoD)
    cursor.execute("""
        INSERT INTO audit_risk_flags (journal_id, risk_rule_code, risk_level, flag_description)
        SELECT journal_id, 'SOD_VIOLATION', 'CRITICAL',
               'Segregation of Duties breach: Preparer (' || preparer_id || ') approved their own entry.'
        FROM journal_headers
        WHERE preparer_id = approver_id AND is_manual = 1;
    """)

    # Rule 2: Unbalanced Batches
    cursor.execute("""
        INSERT INTO audit_risk_flags (journal_id, risk_rule_code, risk_level, flag_description)
        SELECT h.journal_id, 'UNBALANCED_ENTRY', 'CRITICAL',
               'Ledger imbalance: Total Debits (' || SUM(l.debit_amount) || ') != Total Credits (' || SUM(l.credit_amount) || ').'
        FROM journal_headers h
        JOIN journal_lines l ON h.journal_id = l.journal_id
        GROUP BY h.journal_id
        HAVING ROUND(SUM(l.debit_amount), 2) != ROUND(SUM(l.credit_amount), 2);
    """)

    # Rule 3: Unapproved Interfaces / Mass Data
    cursor.execute("""
        INSERT INTO audit_risk_flags (journal_id, risk_rule_code, risk_level, flag_description)
        SELECT journal_id, 'UNAPPROVED_BATCH', 'HIGH',
               'Batch upload or system interface processed without secondary approval.'
        FROM journal_headers
        WHERE posting_type IN ('MASS_DATA', 'PAYROLL_INTERFACE') AND approver_id IS NULL;
    """)

    conn.commit()
    
    print("\n--- AUDIT RISK ENGINE TEST RESULTS ---")
    df_flags = pd.read_sql_query("SELECT * FROM audit_risk_flags", conn)
    print(df_flags.to_string(index=False))
    conn.close()

if __name__ == "__main__":
    initialize_database()
    run_forensic_audit_rules()