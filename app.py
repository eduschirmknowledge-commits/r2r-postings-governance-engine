import sys
import os
import sqlite3
import subprocess
from pathlib import Path
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="R2R Governance & Audit Engine",
    page_icon="🛡️",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "r2r_postings_governance.db"
DROP_DIR = BASE_DIR / "data_drop"
MEMO_PATH = BASE_DIR / "Executive_Audit_Memorandum.md"
EXCEL_REPORT_PATH = BASE_DIR / "R2R_Audit_Executive_Dashboard.xlsx"

# App Title & Header
st.title("🛡️ R2R Journal Entry Governance & Audit Engine")
st.markdown("Automated SOX 404 & IFRS Compliance Testing powered by Deterministic SQL Rules & AI Agents.")

# Sidebar Controls
st.sidebar.header("📁 Data Ingestion Zone")
uploaded_file = st.sidebar.file_uploader(
    "Upload Raw Journal Export (Excel or CSV)", 
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is not None:
    DROP_DIR.mkdir(exist_ok=True)
    file_path = DROP_DIR / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Successfully uploaded: {uploaded_file.name}")
    
    if st.sidebar.button("🚀 Run Ingestion & Audit Engine"):
        with st.spinner("Processing ingestion and running SOX rules..."):
            result = subprocess.run([sys.executable, "ingest_engine.py"], capture_output=True, text=True)
            if result.returncode == 0:
                st.sidebar.success("Ingestion & Rules Completed!")
            else:
                st.sidebar.error(f"Error: {result.stderr}")

# Main Dashboard Layout
if not DB_PATH.exists():
    st.warning("⚠️ No database found. Please upload a journal file using the sidebar to begin.")
else:
    conn = sqlite3.connect(DB_PATH)
    
    # Fetch KPIs safely cast to int
    try:
        df_kpi_rules = int(pd.read_sql("SELECT COUNT(*) FROM audit_risk_flags", conn).iloc[0, 0])
        df_kpi_journals = int(pd.read_sql("SELECT COUNT(DISTINCT journal_id) FROM journal_headers", conn).iloc[0, 0])
        df_critical = int(pd.read_sql("SELECT COUNT(*) FROM audit_risk_flags WHERE risk_level = 'CRITICAL'", conn).iloc[0, 0])
    except Exception:
        df_kpi_rules, df_kpi_journals, df_critical = 0, 0, 0

    # Display KPI Metrics (Guaranteed int values for st.metric)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Journals Analyzed", df_kpi_journals)
    col2.metric("Total Audit Risk Flags", df_kpi_rules)
    col3.metric("Critical Risk Exceptions", df_critical)

    st.divider()

    # Tabs for Data and Reports
    tab1, tab2, tab3 = st.tabs(["📋 Risk Exceptions Log", "📊 Ledger Data Explorer", "🤖 AI Executive Memorandum"])

    with tab1:
        st.subheader("Active Compliance & Audit Risk Exceptions")
        try:
            df_flags = pd.read_sql("""
                SELECT 
                    f.flag_id AS 'Flag ID',
                    f.journal_id AS 'Journal ID',
                    f.risk_rule_code AS 'Rule Code',
                    f.risk_level AS 'Risk Level',
                    f.flag_description AS 'Description',
                    h.posting_date AS 'Posting Date',
                    h.preparer_id AS 'Preparer',
                    h.approver_id AS 'Approver'
                FROM audit_risk_flags f
                JOIN journal_headers h ON f.journal_id = h.journal_id
            """, conn)
            if not df_flags.empty:
                st.dataframe(df_flags, width='stretch')
            else:
                st.info("No risk exceptions currently flagged.")
        except Exception as e:
            st.error(f"Could not load risk flags: {str(e)}")

    with tab2:
        st.subheader("General Ledger Journal Headers & Lines")
        try:
            df_headers = pd.read_sql("SELECT * FROM journal_headers", conn)
            st.markdown("**Journal Headers**")
            st.dataframe(df_headers, width='stretch')
            
            df_lines = pd.read_sql("SELECT * FROM journal_lines", conn)
            st.markdown("**Journal Line Items**")
            st.dataframe(df_lines, width='stretch')
        except Exception as e:
            st.error(f"Could not load ledger data: {str(e)}")

    with tab3:
        st.subheader("AI Executive Audit Memorandum")
        col_exec1, col_exec2 = st.columns([2, 1])
        
        with col_exec1:
            if st.button("🤖 Run AI Agent Crew (Forensic Analysis & Memo Generation)"):
                with st.spinner("AI agents are analyzing risk exceptions and drafting the memo..."):
                    crew_res = subprocess.run([sys.executable, "crew_audit_engine.py"], capture_output=True, text=True)
                    if crew_res.returncode == 0:
                        st.success("AI Audit Memorandum successfully generated!")
                    else:
                        st.error(f"Crew Execution Error: {crew_res.stderr}")

        with col_exec2:
            if st.button("📊 Generate Excel Audit Report"):
                excel_res = subprocess.run([sys.executable, "export_engine.py"], capture_output=True, text=True)
                if excel_res.returncode == 0:
                    st.success("Excel Dashboard generated!")
                else:
                    st.error(f"Excel Export Error: {excel_res.stderr}")

        st.divider()

        # Display Memorandum if it exists
        if MEMO_PATH.exists():
            with open(MEMO_PATH, "r", encoding="utf-8") as f:
                memo_content = f.read()
            st.markdown(memo_content)
            
            st.download_button(
                label="📥 Download Executive Audit Memorandum (.md)",
                data=memo_content,
                file_name="Executive_Audit_Memorandum.md",
                mime="text/markdown"
            )
        else:
            st.info("Click the button above to run the AI agent crew and generate the executive memo.")

        # Download Excel Report button if it exists
        if EXCEL_REPORT_PATH.exists():
            with open(EXCEL_REPORT_PATH, "rb") as f:
                excel_bytes = f.read()
            st.download_button(
                label="📥 Download Executive Excel Dashboard (.xlsx)",
                data=excel_bytes,
                file_name="R2R_Audit_Executive_Dashboard.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    conn.close()
