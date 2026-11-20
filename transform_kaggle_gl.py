import pandas as pd
from pathlib import Path

# Path to your downloaded Kaggle file (adjust name if yours is slightly different)
INPUT_FILE = Path("data_drop/General_Ledger.xlsx") # or .csv
OUTPUT_FILE = Path("data_drop/formatted_kaggle_batch.xlsx")

if not INPUT_FILE.exists():
    print(f"❌ Could not find {INPUT_FILE}. Make sure it's placed in the 'data_drop/' folder!")
    exit()

print("🔄 Reading and transforming Kaggle General Ledger dataset...")

# Read the raw file (handling both Excel and CSV)
if INPUT_FILE.suffix.endswith(".csv"):
    df_raw = pd.read_csv(INPUT_FILE)
else:
    df_raw = pd.read_excel(INPUT_FILE)

# Print columns to help you see what Kaggle named them
print(f"Original columns found: {list(df_raw.columns)}")

# --- MAPPING & CLEANING ---
# (Modify these column name strings if your Kaggle file uses different labels)
date_col = next((c for c in df_raw.columns if 'date' in c.lower()), df_raw.columns[0])
desc_col = next((c for c in df_raw.columns if 'desc' in c.lower() or 'memo' in c.lower()), df_raw.columns[1])
account_col = next((c for c in df_raw.columns if 'account' in c.lower() or 'code' in c.lower()), df_raw.columns[2])
debit_col = next((c for c in df_raw.columns if 'debit' in c.lower()), df_raw.columns[3])
credit_col = next((c for c in df_raw.columns if 'credit' in c.lower()), df_raw.columns[4])

# Standardize column names into a unified dataframe
df_clean = pd.DataFrame()
df_clean['posting_date'] = pd.to_datetime(df_raw[date_col]).dt.strftime('%Y-%m-%d')
df_clean['description'] = df_raw[desc_col].fillna("Standard GL Posting")
df_clean['account_code'] = df_raw[account_col].astype(str)
df_clean['debit_amount'] = pd.to_numeric(df_raw[debit_col], errors='coerce').fillna(0.0)
df_clean['credit_amount'] = pd.to_numeric(df_raw[credit_col], errors='coerce').fillna(0.0)

# --- GROUP INTO JOURNAL BATCHES ---
# Since Kaggle data is row-by-row, we bundle every 4 lines into a unique "Journal ID" 
# and assign mock preparers/approvers to trigger your SOX rules (like SoD violations).
batch_size = 4
df_clean['batch_index'] = range(len(df_clean))
df_clean['journal_id'] = "KAG-" + (1000 + (df_clean['batch_index'] // batch_size)).astype(str)

# Build Headers Dataframe
headers_list = []
preparers = ["alice_fin", "bob_acc", "charlie_ctl", "david_erp"]
approvers = ["bob_acc", "bob_acc", "charlie_ctl", "frank_mgr"] # Note: index 1 has SoD violation (prep == appr)

for jid, group in df_clean.groupby('journal_id'):
    idx = len(headers_list) % len(preparers)
    headers_list.append({
        "journal_id": jid,
        "posting_date": group['posting_date'].iloc[0],
        "posting_type": "Standard",
        "preparer_id": preparers[idx],
        "approver_id": preparers[idx] if idx == 1 else approvers[idx] # Force an SoD violation on some batches
    })

df_headers = pd.DataFrame(headers_list)

# Build Lines Dataframe
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

# Save as the final multi-sheet Excel file your ingestion engine expects
with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    df_headers.to_excel(writer, sheet_name="Headers", index=False)
    df_lines.to_excel(writer, sheet_name="Lines", index=False)

print(f"✅ Success! Transformed Kaggle data saved to: {OUTPUT_FILE}")
print("You can now run your ingestion engine or drop this file via your Streamlit UI!")