# Dead Stock Filter App — Deployment Plan
## Python + Streamlit Cloud | Warehouse 090

> **Version:** 2.0 | **Deploy:** Streamlit Community Cloud (free, sleep accepted)
> **Output:** Summary metrics + Detail table + Download as .xlsx

---

## 1. ARCHITECTURE OVERVIEW

```
User (Browser)
        │
        │  Upload .xls / .xlsx file
        ▼
┌─────────────────────────────────────────────────────┐
│              Streamlit Community Cloud              │
│                                                     │
│  upload        logic/            ui/                │
│  ──────────    ─────────────     ────────────────   │
│  .xls/.xlsx →  reader.py    →   summary_card.py     │
│                filter.py    →   detail_table.py     │
│                exporter.py  →   download_button.py  │
└─────────────────────────────────────────────────────┘
        │
        ▼
  Summary metrics + Detail table (5–7k rows) + Download .xlsx
```

---

## 2. PROJECT STRUCTURE

```
deadstock-app/
│
├── app.py                        # Streamlit entry point
│
├── logic/
│   ├── __init__.py
│   ├── reader.py                 # Read .xls and .xlsx files
│   ├── filter.py                 # Core filter logic
│   └── exporter.py               # Export result as .xlsx
│
├── ui/
│   ├── __init__.py
│   ├── summary_card.py           # Metric cards display
│   └── detail_table.py           # Result table display
│
├── tests/
│   ├── test_filter.py            # Unit tests for filter logic
│   └── sample_data.xlsx          # Sample file for testing
│
├── .streamlit/
│   └── config.toml               # UI config + upload size limit
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 3. MODULE SPECIFICATIONS

---

### MODULE A — logic/reader.py

**Purpose:** Read .xls or .xlsx file, normalise and validate input data.

**Input:** File bytes from Streamlit uploader
**Output:** `pd.DataFrame` (normalised) + `meta` dict

**Logic:**
```
1. Detect format from filename extension
   → .xls  : pd.read_excel(engine='xlrd')
   → .xlsx : pd.read_excel(engine='openpyxl')

2. Normalise headers:
   → Strip leading/trailing whitespace
   → Preserve original case (do NOT lowercase — columns have mixed case)

3. Validate required columns:
   Required : Item#, Item name, Age, Opening qty, Closing qty
   Optional : all remaining columns — missing ones filled with NaN

4. Type casting (only columns used in filter logic):
   → Age, Opening qty, Closing qty, Opening val, Closing val
     → pd.to_numeric(errors='coerce')
   → Item# → str  (prevent leading-zero loss)
   → PROV 50%, PROV 100% → NO casting — display only

5. Return:
   → df   : normalised DataFrame
   → meta : { filename, total_rows, skipped_rows, missing_optional_cols }
```

**Error handling:**
```
→ Empty file          : raise ValueError("File contains no data")
→ Missing required col: raise ValueError(f"Missing required columns: {missing}")
→ All qty values NaN  : raise ValueError("Could not parse numeric data")
```

---

### MODULE B — logic/filter.py

**Purpose:** Filter immobile stock items based on defined conditions.

**Input:** `pd.DataFrame` from reader
**Output:** `pd.DataFrame` (filtered rows only) + `breakdown` dict

**Filter conditions (all must be true simultaneously):**
```python
mask = (
    (df['Age'] > 360) &                              # Stock age over 1 year
    (df['Opening qty'] == df['Closing qty']) &       # No movement in period
    (df['Opening qty'] != 0)                         # Has actual stock quantity
)
```

**Breakdown dict returned:**
```python
{
    'total_rows'    : int,   # Total data rows read
    'blank_rows'    : int,   # Rows with empty Item#
    'invalid_rows'  : int,   # Rows with non-numeric qty/age
    'rejected_age'  : int,   # Rows where Age <= 360
    'rejected_zero' : int,   # Rows where Opening qty = 0
    'rejected_moved': int,   # Rows where Opening qty != Closing qty
    'passed'        : int,   # Items that passed all conditions
}
```

**Columns retained in result:**
```python
KEEP_COLUMNS = [
    "Warehouse", "Style#", "Item#", "Item name",
    "Unit", "Stock zone", "Business area", "Buyer",
    "Account control code", "Item type",
    "reference order number",
    "Opening qty", "Opening val",
    "Closing qty", "Closing val",
    "Receiving date", "Age",
    "361-540 days qty", "361-540 days val",
    ">540 days qty", ">540 days val",
    "Procument group", "Liability", "PO_Pretext"
]
# Note: only keep columns that exist in the uploaded file
```

---

### MODULE C — logic/exporter.py

**Purpose:** Generate downloadable .xlsx result file entirely in memory.

**Input:** filtered `pd.DataFrame` + `summary` dict
**Output:** `bytes` (Excel file, never written to disk)

**Output file structure:**

```
Sheet 1 — "Detail"
  → All KEEP_COLUMNS (only those present in source file)
  → Bold header row, freeze row 1
  → Auto-filter on all columns
  → Conditional formatting on Age column:
      361–540 days → light yellow background  (#FFF2CC)
      > 540 days   → light red background     (#FFE0E0)

Sheet 2 — "Summary"
  → Source filename
  → Processed timestamp (UTC+7)
  → Total immobile items
  → Total Closing qty
  → Total Closing val
  → Items aged 361–540 days (count + total closing val)
  → Items aged > 540 days   (count + total closing val)
  → Filter breakdown (passed / rejected by each condition)
```

**Implementation:**
```python
import io
import pandas as pd

def export_to_xlsx(df_result: pd.DataFrame, summary: dict) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, sheet_name='Detail', index=False)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        # Apply formatting via writer.sheets['Detail']
    output.seek(0)
    return output.getvalue()
```

---

### MODULE D — app.py (Streamlit UI)

**Purpose:** Main application — orchestrates upload, processing, display, download.

**UI Layout:**
```
┌──────────────────────────────────────────────────────────┐
│  Warehouse 090 — Dead Stock Filter                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  STEP 1: UPLOAD FILE                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Drop .xls or .xlsx file here                      │  │
│  │  (Both formats supported)              [Browse...] │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [ ▶  Run Analysis ]                                     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  RESULTS                                                 │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │  6,247   │  │  45,230  │  │  12.3 B  │  │  3,891  │  │
│  │  Immobile│  │ Closing  │  │ Closing  │  │Age >540 │  │
│  │  Items   │  │   Qty    │  │   Val    │  │  Items  │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
│                                                          │
│  ▼ Filter Breakdown (expandable)                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Total rows read      : 52,400                     │  │
│  │  Blank rows skipped   : 120                        │  │
│  │  Invalid data skipped : 3                          │  │
│  │  Rejected  Age ≤ 360  : 38,210                     │  │
│  │  Rejected  Qty = 0    : 4,720                      │  │
│  │  Rejected  Moved      : 3,100                      │  │
│  │  ✅ Passed            : 6,247                      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Detail Table — 6,247 rows  [sortable by column]         │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Warehouse │ Style# │ Item# │ Item name │ Age │ …  │  │
│  │  ─────────────────────────────────────────────   │  │
│  │  [rows highlighted by Age bucket]                  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [ 📥  Download Result (.xlsx) ]                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Session state — prevent re-processing on every widget interaction:**
```python
if 'processed' not in st.session_state:
    st.session_state['processed']   = False
    st.session_state['df_result']   = None
    st.session_state['summary']     = None
    st.session_state['excel_bytes'] = None

# Only run logic when user clicks "Run Analysis"
if st.button("▶ Run Analysis"):
    with st.spinner("Processing..."):
        df, meta        = reader.load(uploaded_file)
        df_result, bkdn = filter.apply(df)
        excel_bytes     = exporter.export_to_xlsx(df_result, summary)

    st.session_state['df_result']   = df_result
    st.session_state['summary']     = build_summary(df_result, bkdn, meta)
    st.session_state['excel_bytes'] = excel_bytes
    st.session_state['processed']   = True
```

**Rendering 5–7k rows:**
```python
# st.dataframe handles large datasets natively via virtual scroll
st.dataframe(
    st.session_state['df_result'],
    height=600,
    use_container_width=True,
    hide_index=True
)
# No pagination needed — Streamlit virtualises the DOM
```

**Download button:**
```python
st.download_button(
    label="📥 Download Result (.xlsx)",
    data=st.session_state['excel_bytes'],
    file_name=f"deadstock_result_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
```

---

### MODULE E — Configuration Files

**.streamlit/config.toml:**
```toml
[theme]
primaryColor             = "#1f77b4"
backgroundColor          = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor                = "#262730"

[server]
maxUploadSize = 200      # MB — sufficient for large source files

[runner]
fastReruns = true
```

**requirements.txt:**
```
streamlit==1.35.0
pandas==2.2.2
xlrd==2.0.1          # REQUIRED — reads legacy .xls format
openpyxl==3.1.2      # Reads .xlsx format
xlsxwriter==3.2.0    # Writes .xlsx output (in-memory)
numpy==1.26.4
```

> ⚠️ `xlrd` is **mandatory** for `.xls` support. Without it, pandas raises an error immediately.
> ⚠️ `requests` is **removed** — Teams notification feature dropped.

**.gitignore:**
```
__pycache__/
*.xls
*.xlsx
.env
venv/
tests/sample_data.xlsx
```

---

## 4. DEPLOY TO STREAMLIT CLOUD

### Step 1 — Push code to GitHub

```bash
git init
git add .
git commit -m "Initial commit — Dead Stock Filter App"
git remote add origin https://github.com/[your-username]/deadstock-app.git
git push -u origin main
```

> ⚠️ Ensure .gitignore excludes all .xls/.xlsx files before committing.

### Step 2 — Create app on Streamlit Cloud

```
1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click "New app"
4. Repository : [your-username]/deadstock-app
5. Branch     : main
6. Main file  : app.py
7. Click "Deploy!"
8. Wait 2–3 minutes for dependency installation
```

### Step 3 — Share with team

```
App URL: https://[your-app-name].streamlit.app
→ Share link via Teams or email
→ No installation required on user machines
→ Works on Chrome, Edge, Safari
```

### Step 4 — Handle App Sleep (free tier)

```
Problem : App sleeps after 12h of no traffic
          First access each morning requires ~60s wake-up time

Solution (free): Use UptimeRobot
  1. Go to uptimerobot.com → Sign up free
  2. Add Monitor:
     Type     : HTTP(s)
     URL      : https://[your-app].streamlit.app
     Interval : Every 30 minutes
  3. App stays awake 24/7
```

---

## 5. IMPLEMENTATION TIMELINE

```
DAY 1 — Core Logic
  ✅ logic/reader.py    Read .xls/.xlsx, validate, normalise
  ✅ logic/filter.py    Filter logic + breakdown dict
  ✅ Test both modules against real Excel file (plain Python, no UI)

DAY 2 — Exporter + UI
  ✅ logic/exporter.py  In-memory .xlsx with 2 sheets + formatting
  ✅ app.py             Upload → process → display → download
  ✅ Full end-to-end test locally (streamlit run app.py)

DAY 3 — Deploy + Validation
  ✅ Push to GitHub
  ✅ Deploy on Streamlit Cloud
  ✅ Test with real data from team
  ✅ Setup UptimeRobot
  ✅ Share link

BUFFER: 1–2 days for real-data edge cases
```

---

## 6. RISKS & MITIGATIONS

| Risk | Likelihood | Mitigation |
|---|---|---|
| `.xls` file too old (Excel 5.0/95 format) | Low | Catch xlrd error, prompt user to re-save as .xlsx |
| RAM exceeded (file > 100MB on 1GB free tier) | Medium | Check file size before processing; warn if > 80MB |
| App sleep during business hours | High without UptimeRobot | Set up UptimeRobot immediately after deploy |
| Column names change in future reports | Medium | reader.py validates and lists any missing columns clearly |
| All numeric columns parse as NaN | Low | reader.py raises clear error with column name |

---

## 7. USER GUIDE (Post-Deploy)

```
1. Open the app URL in Chrome or Edge
   → If you see "This app has gone to sleep"
   → Click "Yes, get this app back up!" and wait ~60 seconds

2. Click "Browse files" and select your .xls or .xlsx file

3. Click "▶ Run Analysis"
   → Processing typically completes in under 10 seconds

4. Review results:
   → 4 metric cards at the top (items, qty, val, age >540)
   → Expand "Filter Breakdown" to see how rows were classified
   → Scroll through the detail table (sortable by any column)
   → Rows highlighted in yellow = Age 361–540 days
   → Rows highlighted in red    = Age > 540 days

5. Download:
   → Click "📥 Download Result (.xlsx)"
   → File contains 2 sheets: Detail + Summary
   → Filename format: deadstock_result_YYYYMMDD_HHMM.xlsx
```