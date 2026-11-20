import streamlit as st
import pandas as pd
import sqlite3
import os
import sys
from pathlib import Path
import subprocess
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="R2R Governance & Audit Engine",
    page_icon="🛡️",
    layout="wide"
)

# --- ELITE SAAS CUSTOM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background-color: #09090b;
        color: #f4f4f5;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .saas-metric-card {
        background: linear-gradient(135deg, rgba(24, 24, 27, 0.8) 0%, rgba(9, 9, 11, 0.9) 100%);
        border: 1px solid #27272a;
        padding: 24px;
        border-radius: 14px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.3);
        transition: all 0.2s ease-in-out;
    }
    .saas-metric-card:hover {
        border-color: #3f3f46;
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 12px;
        color: #a1a1aa;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 600;
    }
    .metric-val {
        font-size: 34px;
        font-weight: 700;
        color: #38bdf8;
        margin-top: 8px;
    }

    .agent-box {
        background: rgba(18, 18, 23, 0.9);
        border: 1px solid #27272a;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .agent-box::before {
        content: '';
        position: absolute;
        top: 0; left: 0; width: 100%; height: 3px;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
    }
    .agent-emoji {
        font-size: 36px;
        margin-bottom: 8px;
    }
    .agent-title {
        font-weight: 600;
        font-size: 15px;
        color: #fafafa;
    }
    .agent-desc {
        font-size: 12px;
        color: #71717a;
        margin-top: 4px;
    }

    .pulse-dot {
        height: 8px;
        width: 8px;
        background-color: #34d399;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 0 rgba(52, 211, 153, 0.4);
        animation: pulse 2s infinite;
        margin-right: 6px;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.4); }
        70% { box-shadow: 0 0 0 8px rgba(52, 211, 153, 0); }
        100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
    }

    [data-testid="stSidebar"] {
        background-color: #0c0c0e;
        border-right: 1px solid #27272a;
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "r2r_postings_governance.db"
DROP_DIR = BASE_DIR / "data_drop"
MEMO_PATH = BASE_DIR / "Executive_Audit_Memorandum.md"
EXCEL_REPORT_PATH = BASE_DIR / "R2R_Audit_Executive_Dashboard.xlsx"

# --- TOP HEADER NAVIGATION BAR ---
col_logo, col_status = st.columns([5, 1])
with col_logo:
    st.markdown("### 🛡️ R2R Autonomous Audit & Governance Engine")
    st.markdown("<span style='color: #71717a; font-size: 14px;'>SOX 404 & IFRS Compliance Command Center • Powered by SQL & CrewAI</span>", unsafe_allow_html=True)
with col_status:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh View", use_container_width=True):
        st.rerun()

st.markdown("<div style='margin: 15px 0px; border-bottom: 1px solid #27272a;'></div>", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("### 🎛️ Control Panel")
st.sidebar.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

st.sidebar.markdown("**📁 Raw Dataset Drop Zone**")
uploaded_file = st.sidebar.file_uploader(
    "Upload Raw Kaggle / GL Export (.xlsx, .csv)", 
    type=["xlsx", "xls", "csv"],
    label_visibility="collapsed"
)

if uploaded_file is not None:
    DROP_DIR.mkdir(exist_ok=True)
    raw_file_path = DROP_DIR / uploaded_file.name
    with open(raw_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Staged raw file: {uploaded_file.name}")
    
    if st.sidebar.button("⚡ Refine & Run Ingestion Pipeline", use_container_width=True):
        # --- STEP 1: KAGGLE REFINEMENT STAGE ---
        with st.spinner("Step 1/2: Transforming raw dataset into governance schema..."):
            try:
                if raw_file_path.suffix.endswith(".csv"):
                    df_raw = pd.read_csv(raw_file_path)
                else:
                    df_raw = pd.read_excel(raw_file_path)
                    
                date_col = next((c for c in df_raw.columns if 'date' in c.lower()), df_raw.columns[0])
                desc_col = next((c for c in df_raw.columns if 'desc' in c.lower() or 'memo' in c.lower()), df_raw.columns[1] if len(df_raw.columns) > 1 else df_raw.columns[0])
                account_col = next((c for c in df_raw.columns if 'account' in c.lower() or 'code' in c.lower()), df_raw.columns[2] if len(df_raw.columns) > 2 else df_raw.columns[0])
                debit_col = next((c for c in df_raw.columns if 'debit' in c.lower()), df_raw.columns[3] if len(df_raw.columns) > 3 else df_raw.columns[0])
                credit_col = next((c for c in df_raw.columns if 'credit' in c.lower()), df_raw.columns[4] if len(df_raw.columns) > 4 else df_raw.columns[0])

                df_clean = pd.DataFrame()
                df_clean['posting_date'] = pd.to_datetime(df_raw[date_col], errors='coerce').fillna(pd.Timestamp('2026-03-01')).dt.strftime('%Y-%m-%d')
                df_clean['description'] = df_raw[desc_col].fillna("Standard GL Posting").astype(str)
                df_clean['account_code'] = df_raw[account_col].astype(str)
                df_clean['debit_amount'] = pd.to_numeric(df_raw[debit_col], errors='coerce').fillna(0.0)
                df_clean['credit_amount'] = pd.to_numeric(df_raw[credit_col], errors='coerce').fillna(0.0)

                batch_size = 4
                df_clean['batch_index'] = range(len(df_clean))
                df_clean['journal_id'] = "KAG-" + (1000 + (df_clean['batch_index'] // batch_size)).astype(str)

                headers_list = []
                preparers = ["alice_fin", "bob_acc", "charlie_ctl", "david_erp"]
                approvers = ["bob_acc", "bob_acc", "charlie_ctl", "frank_mgr"]

                for jid, group in df_clean.groupby('journal_id'):
                    idx = len(headers_list) % len(preparers)
                    headers_list.append({
                        "journal_id": jid,
                        "posting_date": group['posting_date'].iloc[0],
                        "posting_type": "Standard",
                        "preparer_id": preparers[idx],
                        "approver_id": preparers[idx] if idx == 1 else approvers[idx]
                    })

                df_headers = pd.DataFrame(headers_list)

                lines_list = []
                for _, row in df_clean.iterrows():
                    lines_list.append({
                        "journal_id": row['journal_id'],
                        "line_id": len(lines_list) + 1,
                        "account_code": row['account_code'],
                        "description": row['description'],
                        "debit_amount": row['debit_amount'],
                        "credit_amount": row['credit_amount']
                    })

                df_lines = pd.DataFrame(lines_list)

                refined_path = DROP_DIR / "refined_governance_batch.xlsx"
                with pd.ExcelWriter(refined_path, engine="openpyxl") as writer:
                    df_headers.to_excel(writer, sheet_name="Headers", index=False)
                    df_lines.to_excel(writer, sheet_name="Lines", index=False)
                    
                st.sidebar.success("✅ Kaggle Data Refined & Staged!")
            except Exception as e:
                st.sidebar.error(f"Refinement Error: {e}")

        # --- STEP 2: INGESTION ENGINE STAGE (Using sys.executable) ---
        with st.spinner("Step 2/2: Executing Ingestion Engine & SQL Rule Triggers..."):
            result = subprocess.run([sys.executable, "ingest_engine.py"], capture_output=True, text=True)
            if result.returncode == 0:
                st.sidebar.success("🚀 Pipeline Complete!")
                time.sleep(1)
                st.rerun()
            else:
                st.sidebar.error(f"Ingestion Error: {result.stderr}")

st.sidebar.markdown("<div style='margin: 15px 0px; border-bottom: 1px solid #27272a;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("**🤖 Crew Mission Control**")
run_crew_btn = st.sidebar.button("🚀 Launch Autonomous Audit Crew", use_container_width=True, type="primary")

# --- DATABASE METRICS ---
if not DB_PATH.exists():
    st.markdown("""
        <div style='background: rgba(24, 24, 27, 0.6); border: 1px dashed #3f3f46; padding: 40px; border-radius: 12px; text-align: center; margin-top: 40px;'>
            <h3 style='color: #a1a1aa;'>👋 Welcome to your Audit Engine</h3>
            <p style='color: #71717a;'>Upload a raw Kaggle or GL dataset using the left sidebar to initialize your database and view live compliance analytics.</p>
        </div>
    """, unsafe_allow_html=True)
else:
    conn = sqlite3.connect(DB_PATH)
    try:
        total_journals = pd.read_sql("SELECT COUNT(DISTINCT journal_id) FROM journal_headers", conn).iloc[0, 0]
        total_flags = pd.read_sql("SELECT COUNT(*) FROM audit_risk_flags", conn).iloc[0, 0]
        critical_flags = pd.read_sql("SELECT COUNT(*) FROM audit_risk_flags WHERE risk_level = 'CRITICAL'", conn).iloc[0, 0]
    except:
        total_journals, total_flags, critical_flags = 0, 0, 0

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
            <div class='saas-metric-card'>
                <div class='metric-label'>Journals Ingested</div>
                <div class='metric-val'>{total_journals}</div>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div class='saas-metric-card'>
                <div class='metric-label'>Audit Risk Flags</div>
                <div class='metric-val' style='color: {"#f87171" if total_flags > 0 else "#34d399"};'>{total_flags}</div>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div class='saas-metric-card'>
                <div class='metric-label'>Critical Exceptions</div>
                <div class='metric-val' style='color: {"#ef4444" if critical_flags > 0 else "#34d399"};'>{critical_flags}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### <span class='pulse-dot'></span> Active Autonomous Agent Crew", unsafe_allow_html=True)
    ag1, ag2, ag3 = st.columns(3)
    
    with ag1:
        st.markdown("""
            <div class='agent-box'>
                <div class='agent-emoji'>🗄️</div>
                <div class='agent-title'>R2R Data Specialist</div>
                <div class='agent-desc'>SQLite Relational Data Ingestion & SQL Verification</div>
            </div>
        """, unsafe_allow_html=True)
    with ag2:
        st.markdown("""
            <div class='agent-box'>
                <div class='agent-emoji'>🕵️‍♂️</div>
                <div class='agent-title'>Forensic Risk Analyst</div>
                <div class='agent-desc'>SOX 404 & IFRS Compliance Exception Evaluation</div>
            </div>
        """, unsafe_allow_html=True)
    with ag3:
        st.markdown("""
            <div class='agent-box'>
                <div class='agent-emoji'>📝</div>
                <div class='agent-title'>Senior Audit Report Writer</div>
                <div class='agent-desc'>Executive Memorandum & Dashboard Generator</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if run_crew_btn:
        st.markdown("#### ⚡ Live Agent Execution Stream")
        stream_container = st.empty()
        
        process = subprocess.Popen(
            [sys.executable, "crew_audit_engine.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        live_logs = "🚀 Initializing CrewAI Execution Pipeline...\n"
        for line in process.stdout:
            live_logs += line
            stream_container.code(live_logs, language="text")
            
        process.wait()
        if process.returncode == 0:
            st.success("✨ Autonomous Audit Crew completed execution successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Execution encountered an error. Check terminal logs above.")

    tab1, tab2, tab3 = st.tabs(["🔍 Risk Exceptions Dashboard", "📊 Ledger Explorer", "📄 Executive Memorandum & Exports"])

    with tab1:
        st.markdown("##### Active Compliance Exceptions & Anomalies")
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
                st.dataframe(df_flags, use_container_width=True, hide_index=True)
            else:
                st.success("🎉 No active compliance breaches found in current database records.")
        except Exception as e:
            st.warning("No audit flags table detected yet. Run ingestion first.")

    with tab2:
        st.markdown("##### General Ledger Data Store")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("**Journal Headers**")
            try:
                st.dataframe(pd.read_sql("SELECT * FROM journal_headers", conn), use_container_width=True, hide_index=True)
            except:
                st.info("No headers available.")
        with col_t2:
            st.markdown("**Journal Line Items**")
            try:
                st.dataframe(pd.read_sql("SELECT * FROM journal_lines", conn), use_container_width=True, hide_index=True)
            except:
                st.info("No lines available.")

    with tab3:
        st.markdown("##### Executive Audit Deliverables & Reports")
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            if st.button("📊 Generate Excel Audit Dashboard Workbook", use_container_width=True):
                excel_res = subprocess.run([sys.executable, "export_engine.py"], capture_output=True, text=True)
                if excel_res.returncode == 0:
                    st.success("Excel Dashboard generated successfully!")
                    st.rerun()
                else:
                    st.error(f"Error: {excel_res.stderr}")
                    
        with col_dl2:
            if EXCEL_REPORT_PATH.exists():
                with open(EXCEL_REPORT_PATH, "rb") as f:
                    st.download_button(
                        label="📥 Download Excel Dashboard (.xlsx)",
                        data=f.read(),
                        file_name="R2R_Audit_Executive_Dashboard.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.info("Click generate above to create the Excel workbook.")

        st.markdown("<div style='margin: 20px 0px; border-bottom: 1px solid #27272a;'></div>", unsafe_allow_html=True)

        if MEMO_PATH.exists():
            with open(MEMO_PATH, "r", encoding="utf-8") as f:
                memo_html = f.read()
            
            with st.expander("👁️ Preview Executive Audit Memorandum", expanded=True):
                st.markdown(memo_html)
                
            st.download_button(
                label="📥 Download Executive Audit Memorandum (.md)",
                data=memo_html,
                file_name="Executive_Audit_Memorandum.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.info("💡 Launch the Autonomous Audit Crew from the sidebar to generate the executive memorandum.")

    conn.close()