# SafarSync AI — Revised Implementation Plan
## Streamlit Community Cloud Edition (100% Free, Zero Local Dependencies)

**Prepared for:** Afraz Hassan  
**Date:** 29 August 2026  
**Target hosting:** Streamlit Community Cloud (free tier)  
**Budget:** $0 — everything free  

---

# Part 1 — Why the Original Plan Needs Changes

## The Problem: Tesseract OCR Cannot Run on Streamlit Community Cloud

The original plan uses **Tesseract OCR** (`pytesseract`) as the local OCR engine. This requires installing the Tesseract system binary on your machine. Streamlit Community Cloud is a **containerized cloud environment** — you **cannot** install system-level packages like Tesseract on it.

### What breaks on Community Cloud

| Component | Works on Cloud? | Why |
|---|---|---|
| `pytesseract` | **NO** | Requires Tesseract binary installed on the OS |
| `.env` file | **NO** | Community Cloud uses its own secrets dashboard, not `.env` files |
| `python-dotenv` | Partially | Works locally, but on Cloud the `.env` file does not exist |
| SQLite (`safarsync.db`) | **Yes, but ephemeral** | Database is wiped on every app restart (app sleeps after 12h inactivity) |
| `streamlit` | **Yes** | Native support |
| `openai`, `pandas`, `plotly`, `fpdf2`, `pillow` | **Yes** | Pure Python packages, no system dependencies |

## The Solution: Replace Tesseract with OCR.space (Cloud OCR)

**OCR.space** is a free, cloud-based OCR API that requires no system installation.

- **25,000 free API calls/month** — register with email to get a key
- Pure HTTP API — works anywhere, including Streamlit Community Cloud
- Supports printed text in English and Urdu
- No system binary needed — just an HTTP request via `requests`

### New receipt pipeline

```text
Receipt image (uploaded by user)
        ↓
Pillow: validate, resize, correct orientation
        ↓
OCR.space API: extract raw text from image
        ↓
qwen-plus-character: interpret raw text → structured JSON
        ↓
Python validation
        ↓
Human review (editable form)
        ↓
Save to SQLite
```

### Why this two-stage approach is strong

| Stage | Tool | Job |
|---|---|---|
| **1. Read** | OCR.space | Extract visible text from the image (pure OCR, no AI) |
| **2. Understand** | `qwen-plus-character` | Structure the raw text into typed, validated JSON fields |

This separation means:
- OCR.space does what it is designed for — text extraction from images.
- Qwen does what it excels at — understanding unstructured text and producing structured output.
- You **save your Qwen token quota** for text tasks (insights, maintenance advice, Ask SafarSync).
- No need to test or depend on a Qwen image/vision model.

---

# Part 2 — Complete Revised Architecture

```text
┌──────────────────────────────────────────────────┐
│              STREAMLIT COMMUNITY CLOUD            │
│                                                   │
│  Dashboard | Scan Receipt | Add Expense           │
│  Logbook | Maintenance | Ask SafarSync | Vehicles │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│              APPLICATION LOGIC                    │
│                                                   │
│  config.py        analytics.py    maintenance.py  │
│  ai_client.py     anomaly.py      pdf_report.py   │
│  receipt_scanner.py  validation.py  demo_data.py  │
│  insights.py                                      │
└──────────┬─────────────────────┬─────────────────┘
           │                     │
           ▼                     ▼
┌──────────────────┐   ┌──────────────────────────┐
│    SQLite DB     │   │    External APIs          │
│  (ephemeral,     │   │                          │
│   seeded on      │   │  1. OCR.space (OCR)      │
│   startup)       │   │  2. Alibaba DashScope    │
│                  │   │     (Qwen text models)    │
└──────────────────┘   └──────────────────────────┘
```

### Key differences from the original plan

| Original | Revised |
|---|---|
| Tesseract OCR (local binary) | OCR.space cloud OCR API |
| `.env` file for secrets | `st.secrets` on Cloud, `.env` locally |
| Persistent SQLite database | Ephemeral SQLite + auto-seed demo data on startup |
| `pytesseract` in requirements | `requests` added for OCR.space API calls |
| No deployment config | `.streamlit/` config + `packages.txt` not needed |

---

# Part 3 — Revised Project Structure

```text
safarsync-ai/
│
├── .env                        # LOCAL development only (never committed)
├── .gitignore
├── .streamlit/
│   └── config.toml             # Streamlit app configuration
├── README.md
├── requirements.txt
│
├── app.py                      # Main Streamlit entry point
├── config.py                   # Centralized configuration (secrets-aware)
├── ai_client.py                # Shared Alibaba Qwen client
├── database.py                 # SQLite CRUD
├── receipt_scanner.py          # OCR.space + Qwen text interpretation (NO Tesseract)
├── validation.py               # Data validation
├── analytics.py                # Fuel efficiency + spending analytics
├── maintenance.py              # Maintenance schedule engine
├── anomaly.py                  # Expense anomaly detection
├── insights.py                 # AI insight generator
├── pdf_report.py               # PDF vehicle history export
├── demo_data.py                # Demo data seeder
│
├── tests/
│   ├── test_database.py
│   ├── test_validation.py
│   ├── test_analytics.py
│   └── test_maintenance.py
│
└── safarsync.db                # Created at runtime (gitignored)
```

---

# Part 4 — Revised `requirements.txt`

```text
streamlit
openai
python-dotenv
pandas
plotly
fpdf2
pillow
requests
pytest
```

### What changed

| Removed | Reason |
|---|---|
| `pytesseract` | Requires Tesseract binary — cannot run on Community Cloud |

| Added | Reason |
|---|---|
| `requests` | For OCR.space cloud OCR API calls |

---

# Part 5 — Configuration Strategy (Secrets That Work Everywhere)

## The challenge

- **Locally:** You use a `.env` file with `python-dotenv`.
- **On Streamlit Cloud:** There is no `.env` file. You use Streamlit's built-in secrets manager (`st.secrets`).

## The solution: `config.py` reads from both

`config.py` will try `st.secrets` first (for Cloud), then fall back to environment variables (for local `.env`).

```python
# Conceptual example — config.py will handle this automatically
def get_secret(key: str) -> str:
    # Try Streamlit secrets first (works on Community Cloud)
    try:
        import streamlit as st
        value = st.secrets.get(key, "")
        if value:
            return value
    except Exception:
        pass

    # Fall back to environment variable (works locally with .env)
    return os.getenv(key, "")
```

This means:
- **Locally:** Create `.env` as before → `python-dotenv` loads it → `os.getenv()` works.
- **On Cloud:** Add secrets in Streamlit dashboard → `st.secrets` returns them.

### Streamlit Cloud secrets setup

When deploying on Streamlit Community Cloud, you will add these secrets in the app settings:

```toml
DASHSCOPE_API_KEY = "sk-ws-..."
DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
OCR_SPACE_API_KEY = "your_free_key"
```

---

# Part 6 — Handling Ephemeral SQLite on Community Cloud

Streamlit Community Cloud containers are **ephemeral**. The filesystem resets when:
- The app sleeps after 12 hours of inactivity.
- You push a new commit to GitHub.
- Streamlit restarts the container for maintenance.

### Strategy: Auto-seed demo data on startup

```python
# In app.py — runs on every app start
database.init_db()

# If the database is empty (fresh container), seed demo data
vehicles = database.get_vehicles()
if not vehicles:
    demo_data.seed_demo_data()
```

This ensures:
- The app **always works** when someone opens it, even on a fresh container.
- Judges see a populated dashboard immediately.
- During your local development, your data persists normally.

### For the hackathon demo

This is perfectly acceptable because:
1. The demo is about **showing the product**, not enterprise data persistence.
2. You can always show the local version for persistent data demos.
3. The Cloud version showcases the deployed, accessible-anywhere app.

---

# Part 7 — Complete Step-by-Step Build Instructions

## PHASE 1: Environment Setup

### Step 1 — Verify Python

Open your terminal:

```bash
python --version
```

You need Python 3.11 or newer.

---

### Step 2 — Activate virtual environment

Your project folder already has a `venv`. Activate it:

```bash
cd c:\Users\A.H\OneDrive\Desktop\GitHub\safarsync-ai
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

---

### Step 3 — Update `requirements.txt`

Replace the contents of `requirements.txt` with:

```text
streamlit
openai
python-dotenv
pandas
plotly
fpdf2
pillow
requests
pytest
```

Install:

```bash
pip install -r requirements.txt
```

Validate:

```bash
python -c "import streamlit, openai, dotenv, pandas, plotly, fpdf, PIL, requests; print('All packages OK')"
```

Expected: `All packages OK`

---

### Step 4 — Verify `.env`

Your `.env` should contain (you have already added the OCR.space key):

```env
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
OCR_SPACE_API_KEY=your_ocr_space_key_here
```

**Do NOT paste your real API keys into Qoder or any chat.**

---

### Step 5 — Verify `.gitignore`

Your `.gitignore` should contain:

```gitignore
.env
venv/
__pycache__/
*.pyc
*.db
.streamlit/secrets.toml
```

Validate:

```bash
git status
```

`.env` must NOT appear as an untracked file.

---

### Step 6 — Test Alibaba API (already done)

You already have `test_qwen.py` and `ai_client.py`. Confirm they work:

```bash
python test_qwen.py
```

Expected: `SafarSync API test successful.`

---

### Step 7 — Test `qwen-flash-character`

Modify `test_qwen.py` to use `qwen-flash-character` instead of `qwen-plus-character`. Run again. Both models should work.

---

### Step 8 — Test OCR.space API

Before building the receipt scanner, verify that OCR.space works with your key.

Create a temporary `test_ocr_space.py`:

```text
PROJECT: SafarSync AI

Create ONLY a temporary file named test_ocr_space.py.

Purpose:
Test OCR.space API with a receipt image.

Requirements:
1. Load OCR_SPACE_API_KEY from .env.
2. Read an image path from sys.argv[1].
3. Validate that the image exists.
4. Open the image with Pillow, resize if larger than 2000px.
5. Send the image to OCR.space API:
   POST https://api.ocr.space/parse/image
   Headers: apikey = OCR_SPACE_API_KEY
   Body: file = image bytes
   Parameters: language=eng, isOverlayRequired=false
6. Print the extracted text (ParsedResults[0].ParsedText).
7. Never print the API key.
8. Handle: missing key, missing file, API error, empty result.
9. Do not modify any other file.

Usage:
python test_ocr_space.py test_receipt.jpg
```

Run:

```bash
python test_ocr_space.py test_receipt.jpg
```

**Validation:** The output should contain visible text from the receipt — amounts, dates, vendor names, fuel type. If the text is extracted correctly, OCR.space is confirmed as your OCR engine.

Test with at least:
1. Clear printed receipt
2. Dark/low-light receipt
3. Slightly blurry receipt

Delete the temporary test file after testing.

---

## PHASE 2: Core Backend Modules

### Step 9 — Create project structure

```text
PROJECT: SafarSync AI

Create the following project structure.

Files:
app.py
config.py
ai_client.py
database.py
receipt_scanner.py
validation.py
analytics.py
maintenance.py
anomaly.py
insights.py
pdf_report.py
demo_data.py

Folder:
tests/

Inside tests create:
tests/test_database.py
tests/test_validation.py
tests/test_analytics.py
tests/test_maintenance.py

Also create:
.streamlit/config.toml

Rules:
1. Do not implement features yet.
2. Do not create a database.
3. Do not modify .env.
4. Do not add paid services.
5. Add a short module docstring to each Python file.
6. Do not create Streamlit UI yet.
7. Do not implement AI yet.
8. Run: python -m compileall .
9. Fix all syntax errors.
```

---

### Step 10 — Build `config.py` (secrets-aware)

```text
PROJECT: SafarSync AI

Implement ONLY config.py.

Do not modify any other file.

Requirements:

1. Create a get_secret(key: str) -> str function that:
   a. First tries streamlit's st.secrets (for Community Cloud).
   b. Falls back to os.getenv() (for local .env).
   c. Returns empty string if key not found anywhere.

2. Use python-dotenv to load .env for local development.

3. Read these secrets:
   DASHSCOPE_API_KEY
   DASHSCOPE_BASE_URL
   OCR_SPACE_API_KEY

4. Define model constants:
   QWEN_PLUS_CHARACTER = "qwen-plus-character"
   QWEN_FLASH_CHARACTER = "qwen-flash-character"

5. Provide clear configuration errors.
6. Never print any API key.
7. Add type hints.
8. Add beginner-friendly comments.
9. Do not make any API call.

Run: python -m compileall config.py
```

---

### Step 11 — Build `ai_client.py` (updated to use config.py)

```text
PROJECT: SafarSync AI

Implement ONLY ai_client.py.

Do not modify any other file.

Import configuration from config.py using get_secret().

Requirements:

1. Create one reusable OpenAI-compatible client.
2. Read API key using config.get_secret("DASHSCOPE_API_KEY").
3. Read base URL using config.get_secret("DASHSCOPE_BASE_URL").

Create:

get_client() -> OpenAI

Create:

ask_text(
    prompt: str,
    model: str = QWEN_PLUS_CHARACTER,
    max_tokens: int = 500
) -> str

Requirements:
- Call Alibaba Cloud Model Studio
- Return only assistant text
- Handle authentication errors
- Handle network errors
- Handle API errors
- Never print the API key
- Use a reasonable timeout (30 seconds)
- Use type hints
- Add docstrings

Do NOT create ask_vision().
Receipt OCR is handled by OCR.space, not by an AI image model.

Run: python -m compileall ai_client.py
```

Validate by running:

```bash
python ai_client.py
```

Expected: a successful text response.

---

### Step 12 — Build `database.py`

```text
PROJECT: SafarSync AI

Implement ONLY database.py.

Do not modify other files.

Use sqlite3 only.

Database: safarsync.db

Table vehicles:
id INTEGER PRIMARY KEY AUTOINCREMENT
name TEXT NOT NULL
registration_number TEXT
created_at TEXT NOT NULL

Table records:
id INTEGER PRIMARY KEY AUTOINCREMENT
vehicle_id INTEGER NOT NULL
record_type TEXT NOT NULL
date TEXT NOT NULL
amount_pkr REAL
liters REAL
odometer_km INTEGER
description TEXT
vendor_name TEXT
source TEXT
confidence TEXT
raw_ocr_json TEXT
created_at TEXT NOT NULL

Create:
init_db()
add_vehicle(name, registration_number="")
get_vehicles()
add_record(...)
get_records(vehicle_id, record_type=None)
get_record_by_id(record_id)
update_record(record_id, ...)
delete_record(record_id)

Requirements:
1. Use parameterized SQL.
2. Return rows as dictionaries.
3. Safely close connections.
4. Add type hints.
5. Add docstrings.
6. Handle empty database.
7. Do not add Streamlit.
8. Do not add AI.
9. Foreign key records.vehicle_id -> vehicles.id.
10. Add:

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")

Run:
python database.py
python -m compileall database.py
```

Validate:

```bash
python database.py
```

Expected: `Database initialized successfully!`

---

### Step 13 — Test database

```text
PROJECT: SafarSync AI

Implement ONLY tests/test_database.py.

Do not modify database.py.

Use a temporary test database.

Test:
1. Database initialization.
2. Add vehicle.
3. Add multiple vehicles.
4. Get vehicles.
5. Add fuel record.
6. Add maintenance record.
7. Add insurance record.
8. Get records.
9. Filter records by vehicle.
10. Filter records by record_type.
11. Get record by ID.
12. Update record.
13. Delete record.
14. Empty vehicle.
15. Invalid data handling.
16. SQL-injection-like input.
17. Database connections close correctly.

After creating tests run:
pytest -q
```

---

### Step 14 — Build `receipt_scanner.py` (OCR.space — NO Tesseract, NO AI image model)

This is the **most changed module** from the original plan.

```text
PROJECT: SafarSync AI

Implement ONLY receipt_scanner.py.

Do not modify other files.

IMPORTANT:
- Do NOT use pytesseract or any local OCR.
- Do NOT use any AI image/vision model for OCR.
- Use OCR.space as the sole OCR engine.
- Use qwen-plus-character only for TEXT interpretation (stage 2).

Build a two-stage cloud-based receipt scanning pipeline.

Function 1:

extract_text_from_image(image_path: str) -> dict

Pipeline:
1. Validate file exists.
2. Open image using Pillow.
3. Correct orientation when possible (EXIF).
4. Resize oversized images (max 2000px on longest side).
5. Send image to OCR.space API:
   POST https://api.ocr.space/parse/image
   Headers: apikey = config.get_secret("OCR_SPACE_API_KEY")
   Body: file = image bytes (multipart form upload)
   Parameters:
     language = eng
     isOverlayRequired = false
     detectOrientation = true
     scale = true
6. Extract text from ParsedResults[0].ParsedText.
7. If OCR.space fails or returns empty text, return error gracefully.
8. Return:

{
    "raw_text": "...",
    "warnings": [],
    "ocr_engine": "ocr_space"
}

Function 2:

parse_receipt_text(raw_text: str) -> dict

Use ai_client.ask_text() with model qwen-plus-character.

Send the OCR text to Qwen with this instruction:

"You are SafarSync AI's receipt-data extraction assistant.
Use ONLY the supplied OCR text.
Never invent information.
Return ONLY valid JSON.

Schema:
{
  "record_type": "fuel | maintenance | insurance | unknown",
  "date": "YYYY-MM-DD or null",
  "amount_pkr": number or null,
  "liters": number or null,
  "odometer_km": integer or null,
  "description": "string or null",
  "vendor_name": "string or null",
  "confidence": "high | medium | low",
  "warnings": []
}

Rules:
- Missing information must be null.
- Uncertain information must have low confidence.
- Do not guess hidden numbers.
- Normalize obvious dates.
- Normalize currency into numeric PKR.
- Keep warnings short."

Requirements:
1. Parse JSON from model response.
2. If extra text surrounds JSON, extract the JSON object.
3. Handle malformed JSON.
4. Return errors safely.
5. Save raw model response in raw_response.
6. Do not save to database.
7. Do not add Streamlit.
8. Handle:
   - missing file
   - invalid image
   - OCR.space API unavailable
   - OCR.space returns empty text
   - missing OCR_SPACE_API_KEY
   - Qwen API unavailable
9. Add a command-line test:
   python receipt_scanner.py image.jpg
10. Print OCR text and parsed JSON.

Run: python -m compileall receipt_scanner.py
```

Validate with real receipts:
1. Clear printed receipt
2. Dark receipt
3. Slightly blurry receipt

All three must run without crashing.

---

### Step 15 — Build `validation.py`

```text
PROJECT: SafarSync AI

Implement ONLY validation.py and tests/test_validation.py.

Create:

validate_receipt(data: dict) -> dict

Validate:
record_type: fuel / maintenance / insurance / unknown
amount_pkr: null or >= 0
liters: null or > 0
odometer_km: null or >= 0
date: null or valid YYYY-MM-DD
confidence: high / medium / low
warnings: list

Return:
{
  "valid": True or False,
  "errors": [],
  "warnings": [],
  "data": {}
}

Do not crash on malformed input.

Test:
1. Valid record
2. Negative amount
3. Zero liters
4. Negative odometer
5. Invalid date
6. Invalid record_type
7. Missing optional values
8. Low confidence
9. Malformed dictionary

Run: pytest -q
```

---

### Step 16 — Build `analytics.py`

```text
PROJECT: SafarSync AI

Implement ONLY analytics.py and tests/test_analytics.py.

Do not modify database.py.

Create:

calculate_fuel_efficiency(vehicle_id: int) -> list[dict]

Formula:
(current odometer - previous odometer) / current liters

Skip:
- missing odometer
- missing liters
- zero distance
- negative distance

Return warnings for skipped records.

Create:

monthly_spending_summary(vehicle_id: int) -> list[dict]

Group by: YYYY-MM and record_type

Create:

total_cost_per_km(vehicle_id: int) -> float | None

Formula:
total spending / (max odometer - min odometer)

Create:

get_summary_metrics(vehicle_id: int) -> dict

Return:
total_spend, fuel_spend, maintenance_spend, insurance_spend,
average_fuel_efficiency, total_distance, cost_per_km

Requirements:
- No divide-by-zero
- Safe empty results
- Type hints
- Docstrings

Run: pytest -q
```

---

### Step 17 — Build `maintenance.py`

```text
PROJECT: SafarSync AI

Implement ONLY maintenance.py and tests/test_maintenance.py.

Use:

MAINTENANCE_SCHEDULE_KM = {
    "oil_change": 5000,
    "air_filter": 10000,
    "brake_check": 15000,
    "tire_rotation": 8000
}

Create:

check_due_maintenance(vehicle_id: int) -> list[dict]

For every service:
1. Find current odometer.
2. Find latest matching maintenance record.
3. Calculate km since service.
4. Determine status: not_due / due_soon / overdue / unknown

Return: type, interval, km_since_last, status, overdue_by

Create:

get_ai_maintenance_advice(vehicle_id: int) -> str

1. Calculate maintenance status in Python.
2. Get recent fuel efficiency from analytics.py.
3. Send verified values to qwen-plus-character.
4. Ask for 2-4 sentences.
5. Model must use only supplied facts, not invent numbers.
6. Provide fallback response if API fails.

Create tests for:
- no service, not due, due soon, overdue, missing odometer

Run: pytest -q
```

---

### Step 18 — Build `anomaly.py`

```text
PROJECT: SafarSync AI

Implement ONLY anomaly.py.

Create:

find_anomalies(vehicle_id: int) -> list[dict]

Detect:
1. Fuel amount significantly above recent average.
2. Fuel liters significantly above recent average.
3. Significant fuel-efficiency decline.
4. Maintenance cost significantly above recent average.

Rules:
1. Use Python calculations only.
2. Do not use AI to calculate anomalies.
3. Do not flag anomalies with insufficient history.
4. Never crash.
5. Return: type, severity, message, record_id

Severity: info, warning, high

Run: python -m compileall anomaly.py
```

---

### Step 19 — Build `insights.py`

```text
PROJECT: SafarSync AI

Implement ONLY insights.py.

Create:

get_vehicle_insight(vehicle_id: int) -> str

This function:
1. Calls analytics.get_summary_metrics() to get verified numbers.
2. Calls maintenance.check_due_maintenance() to get maintenance status.
3. Calls anomaly.find_anomalies() to get any anomalies.
4. Builds a compact text summary of verified facts.
5. Sends the facts to qwen-plus-character via ai_client.ask_text().
6. Asks for a short, user-friendly insight (under 120 words).
7. Returns the AI-generated insight text.

Prompt rules:
- Use only supplied facts
- Do not invent measurements
- Do not diagnose mechanical failures
- Keep output under 120 words
- Mention specific numbers
- Prioritize actionable information

If AI fails, return a simple text summary of the Python-calculated facts.

Run: python -m compileall insights.py
```

---

### Step 20 — Build `pdf_report.py`

```text
PROJECT: SafarSync AI

Implement ONLY pdf_report.py.

Use fpdf2.

Create:

generate_logbook_pdf(vehicle_id: int, output_path: str) -> str

PDF must contain:
1. Vehicle name
2. Registration number
3. Generation date
4. Total spending
5. Record count
6. Date range
7. Records table:
   date, type, amount PKR, odometer, description, vendor

Sort newest first.

Handle:
- empty records
- long descriptions
- invalid output path

Never generate a blank invalid PDF.

Run: python -m compileall pdf_report.py
```

Validate:
- Generate PDF with records → open → verify totals.
- Generate PDF for empty vehicle → must still open.

---

### Step 21 — Build `demo_data.py`

```text
PROJECT: SafarSync AI

Implement ONLY demo_data.py.

Create:

seed_demo_data() -> int

Create 1 demo vehicle.

At least:
10 fuel records
5 maintenance records
1 insurance record

Requirements:
1. Dates span several months.
2. Odometer readings increase logically.
3. Fuel spending is realistic for Pakistan.
4. At least one maintenance item is overdue.
5. At least one fuel-efficiency decline exists.
6. At least one anomaly exists.
7. source="demo"
8. Do not duplicate data when run repeatedly.
   (Check if demo vehicle already exists before seeding.)
9. Use database.py.
10. Do not add UI.

Run: python -m compileall demo_data.py
```

---

## PHASE 3: Streamlit UI

### Step 22 — Build `app.py`

**Only start after `pytest -q` passes.**

```text
PROJECT: SafarSync AI

Implement ONLY app.py.

Do not rewrite business logic.

Import and use:
config.py, database.py, receipt_scanner.py, validation.py,
analytics.py, maintenance.py, anomaly.py, insights.py,
pdf_report.py, demo_data.py, ai_client.py

STARTUP:
- Initialize database with database.init_db().
- If no vehicles exist, auto-seed demo data.
- This ensures the app works on Streamlit Community Cloud
  even after container restarts.

Pages:
1. Dashboard
2. Scan Receipt
3. Add Expense
4. Vehicle Logbook
5. Maintenance
6. Ask SafarSync
7. Manage Vehicles

GLOBAL:
- Active vehicle in st.session_state.
- Vehicle selector in sidebar.
- Friendly errors (no raw traceback).

MANAGE VEHICLES:
- Add vehicle
- Select vehicle

ADD EXPENSE:
- Fuel, maintenance, insurance forms

SCAN RECEIPT:
1. Upload image.
2. Save temporary file.
3. Run receipt_scanner.extract_text_from_image().
4. Run receipt_scanner.parse_receipt_text().
5. Validate AI result.
6. Show editable fields.
7. Do not save automatically.
8. Save only after Save button.
9. source="ai_scan"
10. Store confidence and raw_ocr_json.

DASHBOARD:
Show:
- total spend, fuel spend, maintenance spend
- average km/L, cost/km, latest odometer
Charts:
- fuel efficiency trend (plotly)
- monthly spending by category (plotly)
Show anomaly alerts.
Show AI insight card from insights.py.

MAINTENANCE:
- Status table
- AI advice button
- PDF download

LOGBOOK:
- Searchable records
- Record type filter
- Newest first
- Edit and delete

ASK SAFARSYNC:
- Text input
- Calculate/retrieve verified facts in Python
- Send relevant verified facts to qwen-plus-character
- Show answer

Design:
- Clean, professional, beginner-friendly
- Proper PKR formatting
- Useful empty states
- Never show raw errors to user

Run: python -m compileall app.py
```

---

### Step 23 — Create `.streamlit/config.toml`

Create the folder `.streamlit/` and inside it create `config.toml`:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[server]
headless = true
```

---

## PHASE 4: Local Testing

### Step 24 — Run full test suite

```bash
pytest -q
```

All tests must pass.

### Step 25 — Compile check

```bash
python -m compileall .
```

No syntax errors.

### Step 26 — Fresh installation test

Stop Streamlit. Delete `safarsync.db`. Start again:

```bash
streamlit run app.py
```

Expected:
- No crash.
- Demo data is auto-seeded.
- Dashboard shows populated data.

### Step 27 — Test vehicle management

Create: `Honda Civic 2019`, registration `LEA-1234`.

Confirm vehicle saves, appears in selector, becomes active.

### Step 28 — Test manual fuel entry

Enter:
- Date: 2026-08-20
- Amount: 4500
- Liters: 32.5
- Odometer: 84000
- Vendor: PSO

Save. Open Logbook. Verify record.

### Step 29 — Test receipt scanning

Go to Scan Receipt. Upload a real receipt.

Expected flow:
```text
Upload → OCR processing → Qwen interpretation →
Extracted fields → Editable review → Save → Logbook
```

### Step 30 — Test human correction

If Qwen returns amount 4500, change it to 4550. Save. Open Logbook. Must show 4550.

### Step 31 — Test receipt failures

Test all:
- Clear receipt, blurry receipt, dark receipt
- Missing amount, date, odometer
- Very large image
- Empty OCR result
- AI API unavailable

For every case: no crash, no raw traceback, no invented values.

### Step 32 — Test vehicle isolation

Create Vehicle A and Vehicle B. Add records to A. Switch to B. B must be empty.

### Step 33 — Test maintenance

Create oil change at 78000 km, current odometer 84520 km.
Expected: 6520 km since service, 1520 km overdue.

### Step 34 — Test dashboard

Verify all metrics manually. Compare chart values with hand calculations.

### Step 35 — Test anomaly detection

Add an unusually large fuel transaction (8500 PKR when normal is 4000-4500). Anomaly warning must appear.

### Step 36 — Test Ask SafarSync

Ask: "How much did I spend on fuel?"
Calculate answer yourself. Compare.

### Step 37 — Test AI failure

Temporarily make API unavailable. Test:
- Maintenance page
- Ask SafarSync
- Scan Receipt

Expected: friendly error, app still works, manual entry works, dashboard works.

---

## PHASE 5: Deploy to Streamlit Community Cloud

### Step 38 — Prepare your GitHub repository

Make sure everything is committed and pushed:

```bash
git add .
git commit -m "feat: complete SafarSync AI for cloud deployment"
git push
```

Confirm these files are NOT in Git:
- `.env`
- `safarsync.db`
- `venv/`
- `__pycache__/`
- `.streamlit/secrets.toml`

---

### Step 39 — Deploy on Streamlit Community Cloud

1. Go to: **https://share.streamlit.io/**
2. Sign in with your GitHub account.
3. Click **"New app"**.
4. Fill in:
   - **Repository:** `safarsync-ai`
   - **Main file path:** `app.py`
   - **App name:** `safarsync-ai` (or any name you prefer)
5. Click **"Advanced settings"**.
6. In the **Secrets** section, add:

```toml
DASHSCOPE_API_KEY = "your_actual_api_key_here"
DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
OCR_SPACE_API_KEY = "your_ocr_space_key_here"
```

7. Click **Deploy**.

Wait 2-5 minutes. Your app will be live at:

```text
https://safarsync-ai.streamlit.app
```

---

### Step 40 — Validate the deployed app

1. Open the URL.
2. Confirm:
   - App loads without errors.
   - Demo data is auto-seeded.
   - Dashboard shows metrics.
   - Scan Receipt works (image upload + AI extraction).
   - Ask SafarSync works.
   - PDF export works.
3. Test on your phone to confirm responsive design.

---

### Step 41 — Verify OCR.space on the deployed app

Your OCR.space API key should already be in the Streamlit secrets (added in Step 39).

If you do not have an OCR.space key yet:

1. Go to: **https://ocr.space/ocrapi**
2. Click **"Get Free API Key"**.
3. Enter your email.
4. You will receive an API key.
5. Add it to your Streamlit Cloud secrets:

```toml
OCR_SPACE_API_KEY = "your_key_here"
```

This gives you 25,000 free OCR calls per month.

---

## PHASE 6: Final Polish

### Step 42 — Full automated validation

```bash
pytest -q
python -m compileall .
streamlit run app.py
```

All three must succeed.

### Step 43 — Final complete test

Delete `safarsync.db`. Start fresh. Perform:

```text
1. Add vehicle
2. Add fuel
3. Add maintenance
4. Add insurance
5. Scan receipt
6. Correct AI result
7. Save
8. Open Dashboard
9. Open Maintenance
10. Open Logbook
11. Generate PDF
12. Ask SafarSync
13. Restart Streamlit
14. Verify demo data re-seeded
```

Do this twice.

### Step 44 — Bug audit

```text
PROJECT: SafarSync AI

Review the entire project for bugs.

DO NOT MODIFY ANY FILE.

Check:
1. Database bugs
2. SQL injection
3. Input validation
4. Divide-by-zero
5. Empty data
6. Vehicle isolation
7. Incorrect fuel calculations
8. Incorrect maintenance calculations
9. AI JSON parsing
10. API error handling
11. Secret exposure
12. Streamlit state
13. PDF generation
14. Duplicate demo data
15. Unnecessary dependencies
16. Dead code
17. Cloud deployment issues (ephemeral filesystem)
18. Secrets handling (works both locally and on Cloud)

For every problem return:
SEVERITY, FILE, PROBLEM, EXPECTED, RECOMMENDED FIX
```

Then fix issues one at a time.

---

# Part 8 — Deployment Checklist

## Before deploying

- [ ] All tests pass locally (`pytest -q`)
- [ ] App runs locally without errors
- [ ] `.env` is NOT in Git
- [ ] `requirements.txt` is updated (no `pytesseract`, has `requests`)
- [ ] `config.py` supports both `st.secrets` and `.env`
- [ ] `demo_data.py` auto-seeds when database is empty
- [ ] Receipt scanning works without Tesseract
- [ ] All code is committed and pushed to GitHub

## On Streamlit Community Cloud

- [ ] App deploys successfully
- [ ] Secrets are added in the Streamlit dashboard
- [ ] Demo data auto-seeds on first load
- [ ] Dashboard shows metrics
- [ ] Scan Receipt works (cloud OCR)
- [ ] Ask SafarSync works
- [ ] PDF export works
- [ ] No API keys visible anywhere in the UI
- [ ] App works on mobile browser

## Free-tier safety

- [ ] Alibaba Cloud: Free Quota Only is ON
- [ ] OCR.space: Using free tier (25K calls/month)
- [ ] Streamlit: Using Community Cloud (free)
- [ ] No paid services anywhere in the stack

---

# Part 9 — Complete Cost Breakdown

| Component | Technology | Cost |
|---|---|---|
| AI text interpretation | Alibaba Qwen Plus Character | Free (new-user quota) |
| OCR (receipt text extraction) | OCR.space | Free (25K calls/month) |
| Database | SQLite | Free (built into Python) |
| Frontend | Streamlit | Free (open-source) |
| Hosting | Streamlit Community Cloud | Free |
| Charts | Plotly | Free (open-source) |
| PDF | fpdf2 | Free (open-source) |
| Image processing | Pillow | Free (open-source) |
| Version control | GitHub | Free |
| IDE | Qoder | Your existing credits |
| **TOTAL** | | **$0** |

---

# Part 10 — Summary of ALL Changes from Original Plan

| # | Original Plan | Revised Plan | Reason |
|---|---|---|---|
| 1 | Tesseract OCR (local) | OCR.space (cloud OCR API) | Tesseract cannot run on Community Cloud |
| 2 | `pytesseract` in requirements | `requests` in requirements | Replace local OCR with cloud OCR API |
| 3 | `.env` file only | `st.secrets` on Cloud + `.env` locally | Community Cloud has no `.env` support |
| 4 | `config.py` reads `.env` only | `config.py` reads both `st.secrets` and `.env` | Works in both environments |
| 5 | Persistent SQLite | Ephemeral SQLite + auto-seed | Cloud containers reset on restart |
| 6 | `receipt_scanner.py` uses pytesseract | `receipt_scanner.py` uses OCR.space + Qwen text | No system binary on cloud; OCR and AI are separate stages |
| 7 | No `insights.py` | Added `insights.py` module | Dedicated AI insight generator |
| 8 | No `.streamlit/config.toml` | Added `.streamlit/config.toml` | App configuration for Cloud |
| 9 | No deployment steps | Added Streamlit Community Cloud deployment | Free hosting target |
| 10 | Manual database seeding | Auto-seed on empty database | Survives container restarts |

---

# Part 11 — The Revised Build Order (Quick Reference)

```text
PHASE 1: ENVIRONMENT
 1. Verify Python
 2. Activate venv
 3. Update requirements.txt (remove pytesseract, add requests)
 4. Verify .env
 5. Verify .gitignore
 6. Test Qwen text models
 7. Test OCR.space API

PHASE 2: BACKEND MODULES
 8. Create project structure + .streamlit/config.toml
 9. Build config.py (secrets-aware)
10. Build ai_client.py
11. Build database.py
12. Test database
13. Build receipt_scanner.py (OCR.space + Qwen text)
14. Build validation.py + tests
15. Build analytics.py + tests
16. Build maintenance.py + tests
17. Build anomaly.py
18. Build insights.py
19. Build pdf_report.py
20. Build demo_data.py

PHASE 3: STREAMLIT UI
21. Build app.py (all pages)

PHASE 4: LOCAL TESTING
22. Run pytest
23. Fresh install test
24. Test all features
25. Test AI failure

PHASE 5: DEPLOY
26. Push to GitHub
27. Deploy on Streamlit Community Cloud
28. Add secrets in Streamlit dashboard
29. Validate deployed app

PHASE 6: POLISH
30. Bug audit
31. Final complete test
32. Record demo video
33. Rehearse pitch
34. Freeze the code
```

---

## Final Architecture Rule

> **Python decides the numbers. OCR.space reads the receipts. Qwen explains the numbers. The cloud hosts it all — for free.**
