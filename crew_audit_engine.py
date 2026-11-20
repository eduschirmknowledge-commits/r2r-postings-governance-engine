import sys
import io
import os
from pathlib import Path
import sqlite3

# Ensure UTF-8 output encoding for Windows PowerShell/CMD (satisfies Pylance typing)
if sys.platform.startswith("win"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

# 1. Resolve path to your SQLite DB
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "r2r_postings_governance.db"

# 2. Configure Gemini LLM (Active & Valid Key from .env)
gemini_llm = LLM(
    model="gemini/gemini-3.8-flash",
    api_key=os.environ.get("GOOGLE_API_KEY"),
    temperature=0.2
)

# 3. Define a Custom Tool for SQLite Data Extraction
@tool("Extract Risk Exceptions")
def extract_risk_flags() -> str:
    """Queries SQLite database to fetch journal entries flagged for forensic/SOX risk."""
    if not DB_PATH.exists():
        return "Database file not found."
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        f.flag_id, f.journal_id, f.risk_rule_code, f.risk_level, f.flag_description,
        h.posting_date, h.posting_type, h.preparer_id, h.approver_id,
        SUM(l.debit_amount) as total_debit, SUM(l.credit_amount) as total_credit
    FROM audit_risk_flags f
    JOIN journal_headers h ON f.journal_id = h.journal_id
    JOIN journal_lines l ON h.journal_id = l.journal_id
    GROUP BY f.flag_id;
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "No audit risk flags found in the database."
        
        output = []
        for r in rows:
            output.append(
                f"Flag ID: {r[0]} | Journal: {r[1]} | Rule: {r[2]} | Risk: {r[3]}\n"
                f"Description: {r[4]} | Date: {r[5]} | Type: {r[6]}\n"
                f"Preparer: {r[7]} | Approver: {r[8]} | Debit: ${r[9]:,.2f} | Credit: ${r[10]:,.2f}\n"
                "--------------------------------------------------"
            )
        return "\n".join(output)
    except Exception as e:
        conn.close()
        return f"Error executing query: {str(e)}"

# 4. Define the 3 CrewAI Agents
data_specialist = Agent(
    role="R2R Data Specialist",
    goal="Extract and verify raw risk flags and ledger anomalies from the SQLite governance database.",
    backstory=(
        "You are a database engineer specializing in financial ledger forensics. "
        "Your job is to pull validated risk data from deterministic SQL checks."
    ),
    tools=[extract_risk_flags],
    llm=gemini_llm,
    verbose=True
)

forensic_analyst = Agent(
    role="Forensic Risk Analyst",
    goal="Evaluate flagged journal entries against SOX 404, Segregation of Duties (SoD), and IFRS standards.",
    backstory=(
        "You are a Senior Internal Audit Manager. You examine extracted ledger exceptions, "
        "identify compliance breaches (e.g., self-approval, weekend postings, unbalancing), "
        "and assess total financial exposure."
    ),
    llm=gemini_llm,
    verbose=True
)

report_writer = Agent(
    role="Senior Audit Report Writer",
    goal="Synthesize risk findings into a formal Executive Audit Memorandum for the CFO and Audit Committee.",
    backstory=(
        "You are an executive auditor skilled at writing concise, high-impact audit reports. "
        "You turn technical forensic observations into clear management recommendations."
    ),
    llm=gemini_llm,
    verbose=True
)

# 5. Define Sequential Tasks
task_extract = Task(
    description="Use the 'Extract Risk Exceptions' tool to retrieve all active flags from r2r_postings_governance.db.",
    expected_output="A clean list of all flagged journal entries with preparer, approver, and financial figures.",
    agent=data_specialist
)

task_analyze = Task(
    description=(
        "Analyze the extracted data from task_extract. Categorize each finding by risk severity (High/Medium/Low), "
        "check for Segregation of Duties (SoD) violations where preparer_id equals approver_id, and map to SOX controls."
    ),
    expected_output="A structured breakdown of control breaches, financial risk amounts, and root-cause analyses.",
    agent=forensic_analyst,
    context=[task_extract]
)

task_report = Task(
    description=(
        "Draft a formal Executive Audit Memorandum based on the analysis. Include an Executive Summary, "
        "Key Findings Table, SOX/IFRS Compliance Impact, and Recommended Remediation Actions."
    ),
    expected_output="A complete Markdown-formatted Executive Audit Memorandum ready for CFO review.",
    agent=report_writer,
    context=[task_analyze],
    output_file="Executive_Audit_Memorandum.md"
)

# 6. Assemble and Kick Off Crew
r2r_audit_crew = Crew(
    agents=[data_specialist, forensic_analyst, report_writer],
    tasks=[task_extract, task_analyze, task_report],
    process=Process.sequential,
    memory=False,
    verbose=True
)

if __name__ == "__main__":
    print("🚀 Starting R2R Governance & Audit Crew via Gemini...")
    result = r2r_audit_crew.kickoff()
    print("\n✅ Audit Run Completed! Memorandum saved to Executive_Audit_Memorandum.md\n")
