# MEMORANDUM

**TO:** Chief Financial Officer (CFO), Audit Committee  
**FROM:** Senior Audit Lead / Office of Internal Audit  
**DATE:** July 1, 2026  
**SUBJECT:** EXECUTIVE AUDIT MEMORANDUM: Forensic Review of Q2 2026 Journal Entry Exceptions & ICFR Deficiencies  

---

### 1. Executive Summary

Internal Audit has completed an expedited forensic review of journal entry exceptions identified during the Q2 period-end close process ending June 30, 2026. Our investigation evaluated ledger integrity, access controls, and adherence to **Sarbanes-Oxley (SOX) Section 404** requirements and **International Financial Reporting Standards (IFRS)**.

Our testing revealed severe, pervasive breakdowns across both IT General Controls (ITGCs) and Automated Application Controls (ITACs), resulting in **$280,000.00** in gross unauthorized and non-compliant financial transactions. Most critically, these failures permitted:
1. An unauthorized user to post and self-approve a **$150,000.00** period-end entry;
2. An IT system administrator to bypass controls and post an **unbalanced mass journal voucher**, corrupting the General Ledger by **$1,000.00**; and
3. An automated payroll batch (**$85,000.00**) to post directly to the ledger with no supervisory validation.

**Audit Assessment:** In aggregate, these deficiencies represent an **indicated Material Weakness in Internal Control over Financial Reporting (ICFR)** under SOX Section 404. Without immediate containment and remediation, management cannot assert that controls over manual and interface journal entries were operating effectively for Q2 2026.

---

### 2. Key Findings Table

The table below outlines the transactions implicated, control failures identified, and associated financial exposure.

| Entry ID | Source / Type | Preparer | Approver | Gross Exposure | Severity | Core Breakdown |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **`JE-STD-002`** | Standard Journal | `rogue_user` | `rogue_user` | **$150,000.00** | **CRITICAL** | **SoD Breach / Self-Approval:** Mutual authorization bypass posted on Q2 close date (June 30). High fraud/earnings-management risk profile. |
| **`JE-MASS-001`** | Mass Data Upload | `system_admin` | *None* | **$45,000.00** | **CRITICAL** | **Privileged Access Abuse & Ledger Imbalance:** IT admin executed operational posting without approval. Debits ($45,000) $\ne$ Credits ($44,000); system accepted an un-equated entry. |
| **`JE-PAY-001`** | Payroll Interface | `workday_interface` | *None* | **$85,000.00** | **HIGH** | **Unreviewed Interface Batch:** Subledger pipeline posted directly to the general ledger without human review, reconciliation, or workflow approval. |
| **TOTAL** | *3 Unique Entries* | — | — | **$280,000.00** | — | *Direct Ledger Imbalance Variance: **$1,000.00*** |

---

### 3. SOX 404 & IFRS Compliance Impact

#### A. SOX Section 404 & ICFR Implications
The identified exceptions breach multiple baseline SOX key controls, necessitating immediate disclosure to the external auditors:
* **Privileged Access Management (ITGC PAM-01 / AC-02):** Permitting `system_admin` direct production ledger posting rights breaches the standard separation between system administration and functional financial operations.
* **Dual-Authorization Enforcement (SOX Key Control FIN-JE-01):** Failure of the ERP system to prevent identical preparer/approver parameters (`preparer_id == approver_id`) invalidates the preventive design of secondary review.
* **Automated Application Controls (SOX Key Control ITAC-GL-01):** Acceptance of an unbalanced transaction ($1,000 net variance) confirms that the core ERP double-entry validation constraint was either misconfigured or programmatically bypassed.
* **Audit Aggregation:** Under COSO framework guidance, the coexistence of ineffective ITGCs (PAM) and defective automated business process controls constitutes a **Material Weakness**, threatening management’s ability to certify Q2/Q3 financial reports.

#### B. IFRS & Financial Reporting Standards Impact
* **IAS 1 (Presentation of Financial Statements):** Mandates a fair presentation of financial performance and compliance with foundational double-entry accounting ($\text{Assets} = \text{Liabilities} + \text{Equity}$). Posting `JE-MASS-001` with unequal debits and credits creates an inherently unreliable Trial Balance and corrupts balance sheet integrity.
* **IAS 19 (Employee Benefits):** Uncontrolled auto-posting of `JE-PAY-001` without independent reconciliation against payroll disbursement registers undermines the cut-off, completeness, and accuracy of payroll expense recognition.
* **Conceptual Framework for Financial Reporting:** The documented entries compromise the **faithful representation** and **neutrality** of reported earnings, exposing the company to audit adjustments and restatement risks.

---

### 4. Recommended Remediation Actions

Management must execute a phased remediation plan to contain existing exposures and enforce strict systemic controls prior to financial statement finalization.

```
   PHASE 1: CONTAINMENT (0 - 24 Hours)
   ├── Reverse & Rebalance JE-MASS-001 ($1,000 GL delta)
   ├── Substantive Forensic Testing on JE-STD-002 ($150,000)
   └── Retroactive Gross-to-Net Payroll Reconciliation ($85,000)
                              │
                              ▼
   PHASE 2: TECHNICAL CONTROLS (24 - 72 Hours)
   ├── Implement Automated ERP Hard-Stop (Block Self-Approval)
   ├── Implement Database Balance Validation Constraint (Debits == Credits)
   └── Revoke All Financial Posting Entitlements from IT Admin Accounts
                              │
                              ▼
   PHASE 3: GOVERNANCE & INTERFACE PROTOCOLS (30 Days)
   ├── Reconfigure Workday Interface to "Park/Stage" for Review
   └── Institute Bi-Weekly SoD Conflict & Privileged Audit Logging
```

#### Phase 1: Immediate Containment Actions (Execute within 24 Hours)
1. **Rebalance General Ledger (`JE-MASS-001`):** Direct Corporate Controllership to post an authorized, balanced adjusting entry to eliminate the $1,000 out-of-balance condition and establish line-item support for the underlying $44,000/$45,000 lines.
2. **Substantively Audit `JE-STD-002`:** Quarantine the $150,000 transaction. Internal Audit will perform forensic verification of underlying vendor invoices, contracts, and banking trails to confirm valid business purpose and rule out fraudulent conversion.
3. **Retroactive Reconciliation (`JE-PAY-001`):** Direct the Payroll Accounting Manager to execute a detailed gross-to-net reconciliation between the Workday source extract and General Ledger balances for the $85,000 batch.

#### Phase 2: Technical Systemic Remediation (Execute within 72 Hours)
1. **Automate ERP Preventative Hard-Stops:**
   * Deploy system logic blocking submission when `Preparer_ID == Approver_ID`.
   * Enforce system-level constraint: $\sum \text{Debits} \ne \sum \text{Credits} \rightarrow \text{Abort Posting}$.
2. **Revoke Incompatible Entitlements:**
   * Strip IT Administrative roles (`system_admin`) of operational posting capabilities (`JE_CREATE`, `JE_POST`). Restrict system accounts to maintenance functions in non-production environments.
   * Conduct an immediate review of ERP role assignments to identify and resolve any latent SoD conflicts across all accounting personnel.

#### Phase 3: Governance & Architecture Enhancement (Execute within 30 Days)
1. **Redesign Interface Staging:** Reconfigure the Workday automated batch integration pipeline to land in an unposted "Parked/Staged" status, requiring positive verification by an accounting manager prior to ledger commitment.
2. **Establish Continuous Monitoring:** Configure automated exception logging to generate real-time alerts to the Internal Audit Lead for any off-hours, mass, or out-of-workflow journal entries.

---

**Distribution List:**  
* Audit Committee Members  
* Chief Financial Officer  
* Lead Partner, External Audit  
* VP, Financial Controller  
* Chief Information Security Officer (CISO)