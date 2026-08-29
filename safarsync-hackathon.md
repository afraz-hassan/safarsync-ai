# SafarSync AI — Qoder + Alibaba Cloud Free-Tier Winning Build Playbook

### A beginner-safe, zero-cost implementation plan for the Alibaba Cloud AI Hackathon 2026
**Bano Qabil × Alkhidmat Foundation | Built with Qoder + Alibaba Cloud Model Studio + Qwen**

**Prepared for:** Afraz Hassan  
**Build constraint:** **$0 paid spend**  
**Available Qoder allowance:** **2,180 credits**  
**Primary app:** Streamlit  
**Primary database:** SQLite  
**AI platform:** Alibaba Cloud Model Studio  
**Document status:** Reworked for the current free-tier-first strategy — **29 August 2026**

---

# 0. Executive Decision: What We Are Building

SafarSync AI is not just a receipt scanner.

It is a **Pakistan-focused Vehicle Expense Intelligence & Maintenance Co-Pilot** that turns messy paper records into a useful digital vehicle history.

The winning demo should feel like this:

> **Photo → AI understands receipt → user verifies → record saved → dashboard updates → maintenance insight appears → user can ask SafarSync a question by typing or voice.**

The product must look simple to a judge while the implementation underneath is disciplined.

## The winning product promise

**“SafarSync turns every fuel and maintenance receipt into a living digital history of your vehicle.”**

## The three AI moments

1. **See:** Qwen vision reads a fuel/mechanic/insurance receipt.
2. **Think:** Qwen analyzes the vehicle’s accumulated data and explains useful actions.
3. **Talk:** User can ask questions such as:
   - “How much did I spend on fuel this month?”
   - “When is my next oil change due?”
   - “Why has my fuel efficiency dropped?”
   - “What was my most expensive maintenance visit?”

The calculations remain deterministic in Python. AI explains the results rather than inventing the underlying numbers.

---

# 1. The Most Important Constraint: Everything Must Stay Free

This project is designed around a **hard $0 budget**.

That means:

- No paid Alibaba Cloud subscription is required.
- No paid Qoder subscription is required beyond the **2,180 credits already available to you**.
- No Google Maps API.
- No paid database.
- No paid OCR service.
- No paid hosting is required for the demo.
- No fine-tuning.
- No vector database.
- No RAG.
- No paid monitoring platform.
- No paid third-party AI API.

## 1.0 Why you may only see these three models

You are **not necessarily doing anything wrong**.

Alibaba's current documentation says the new-user free quota is **model-specific** and that a model is eligible only when the console shows a remaining free-quota allocation for that account. The Singapore region with International deployment scope is the relevant free-quota environment. citeturn799488search1turn799488search2

For this build, treat your actual console as the source of truth:

```text
qwen-plus-character
qwen-flash-character
qwen-mt-image-2.0
```

Before changing anything else, verify:

```text
Region: Singapore
Deployment scope: International
Workspace: the same workspace where the free quota is displayed
```

Do **not** design the application around a model that is absent from your own free-quota allocation.

### Important capability distinction

The two Character models are **text-input/text-output role-playing models**. Alibaba documents `qwen-plus-character` and `qwen-flash-character` as text-only models. They are useful for conversational vehicle assistance, normalization, and explanations, but they are **not receipt-vision/OCR models**. citeturn446980search0turn446980search1

So the $0 receipt architecture becomes:

```text
Receipt image
   ↓
Free/local OCR OR confirmed image-translation step
   ↓
Extracted text
   ↓
Qwen Plus Character
   ↓
Normalization + classification + ambiguity handling
   ↓
Python validation
   ↓
Human review
   ↓
SQLite
```

This is technically stronger than pretending a text-only model can see a receipt.

## 1.1 Alibaba Cloud free quota strategy

As of August 2026, Alibaba Cloud Model Studio provides **new-user free quota in the Singapore region for International deployment scope** on eligible models. The official documentation says eligible models typically receive **1 million tokens per model**, with a 90-day validity period for the new-user quota. The quota is model-specific and cannot be transferred between models. citeturn643886search1turn138320search0

### Absolutely critical safety setting

Turn on **Free Quota Only** for the models you use.

Alibaba documents that this mode stops model requests when free quota is exhausted instead of continuing into paid usage. This is the single most important setting for your $0 requirement. citeturn643886search1turn643886search0

### Your actual free-quota model set

| Model | SafarSync role |
|---|---|
| `qwen-plus-character` | Main AI assistant, maintenance explanations, natural-language insights |
| `qwen-flash-character` | Fast/lightweight fallback for simple assistant responses |
| `qwen-mt-image-2.0` | Image-translation/visual preprocessing **only after a test confirms it is useful for your receipt workflow** |

The console's displayed free-quota allocation is the authoritative source for your account. citeturn799488search1turn799488search2

### Do not hard-code an obsolete endpoint

Alibaba still supports the older Singapore DashScope endpoint, but current documentation recommends workspace-specific endpoints for production:

`https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`

The older Singapore endpoint remains available:

`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

The project should therefore keep `DASHSCOPE_BASE_URL` configurable in `.env` rather than hard-coding one URL into business logic. citeturn643886search3turn643886search6

---

# 2. What Changes from the Original Playbook

The original idea is strong, but several implementation choices should be upgraded.

## Original → Winning version

| Original plan | Winning version |
|---|---|
| `qwen-plus-character` only | `qwen-plus-character` for OCR + `qwen-plus-character` for reasoning |
| Qwen Plus Character advisor | Prefer `qwen-plus-character` so the build uses a current model and separates vision from reasoning |
| Manual input mainly through receipt flow | Dedicated fast manual expense-entry workflow |
| Dashboard + OCR | Dashboard + OCR + validation + anomaly signals |
| Google Maps as stretch | Removed from the $0 plan |
| Alibaba ECS deployment | Optional; **Streamlit Community Cloud is the $0 deployment target** |
| 6 large files | Small, testable modules with one shared AI client |
| AI can be called repeatedly | Add caching, demo mode, and “call AI only when needed” rules |
| No explicit demo dataset | Seeded demo mode with polished realistic records |
| No voice plan | Optional free browser voice input for the showcase |
| Basic error handling | Demo-safe error handling + offline/demo fallback |
| “Build it and hope” | Build → test → commit → checkpoint after every module |

---

# 3. Product Vision

## 3.1 Problem

Vehicle owners in Pakistan often manage expenses through:

- handwritten mechanic bills,
- paper fuel receipts,
- informal notes,
- WhatsApp conversations,
- memory,
- scattered photos.

This makes it difficult to answer basic questions:

- How much did I spend on fuel?
- Which month was most expensive?
- What is my average fuel efficiency?
- When was the last oil change?
- Is a maintenance item overdue?
- How much have I spent on this vehicle overall?
- Can I show a buyer a clean maintenance history?

SafarSync turns these disconnected records into a structured vehicle history.

## 3.2 Target user

### Primary

A Pakistani private vehicle owner who wants simple expense tracking without becoming an accountant.

### Secondary

- Families managing multiple cars
- Drivers
- Small fleets
- Used-car sellers
- Buyers who want documented maintenance history
- Insurance companies
- Vehicle service businesses

## 3.3 The “why now”

The product becomes significantly more compelling when the user does not have to type every receipt manually.

The product’s UX should therefore make this the default mental model:

**“Take a photo. SafarSync does the boring data entry. You stay in control.”**

---

# 4. Core Features — The Version Judges Should See

## Feature 1 — Smart Receipt Scanner

User uploads or photographs:

- fuel receipt,
- mechanic bill,
- maintenance invoice,
- insurance document.

Qwen reads the image and extracts:

```json
{
  "record_type": "fuel",
  "date": "2026-08-24",
  "amount_pkr": 4500,
  "liters": 32.5,
  "odometer_km": 84520,
  "description": "Petrol",
  "vendor_name": "PSO",
  "confidence": "high"
}
```

The user then sees an **editable review form**.

This is essential.

### Design rule

Never silently save AI output.

Use:

**AI extraction → human review → explicit save**

This protects data quality and gives you a strong answer to the judge question:

> “What happens if the AI is wrong?”

---

# Feature 2 — Manual Expense Entry

The product must work even when the user does not have a receipt.

Provide a fast form:

### Add Fuel

- Date
- Amount
- Liters
- Odometer
- Station
- Notes

### Add Maintenance

- Date
- Amount
- Odometer
- Service type
- Vendor
- Notes

### Add Insurance

- Date
- Amount
- Provider
- Notes

This is not a secondary feature.

It makes the application genuinely usable rather than “only an OCR demo.”

---

# Feature 3 — Vehicle Dashboard

The dashboard should answer the owner’s most important questions at a glance.

### Top metrics

- Total spend
- Fuel spend
- Maintenance spend
- Average km/L
- Cost per km
- Last odometer reading

### Charts

1. Fuel efficiency over time
2. Monthly spending by category
3. Cumulative vehicle spending
4. Optional category distribution

### Empty-state behavior

Never show a broken chart.

Use friendly states such as:

> “Add two fuel records with odometer readings to calculate km/L.”

---

# Feature 4 — Maintenance Intelligence

This has two layers.

## Layer A — Deterministic maintenance rules

Example schedule:

```python
MAINTENANCE_SCHEDULE_KM = {
    "oil_change": 5000,
    "air_filter": 10000,
    "brake_check": 15000,
    "tire_rotation": 8000
}
```

These values are **product heuristics**, not universal manufacturer instructions.

The app should label them clearly:

> “SafarSync baseline schedule — always follow the vehicle manufacturer’s recommendations.”

The engine calculates:

- last service,
- current odometer,
- distance since service,
- due/not due status.

## Layer B — Qwen explanation

Only after the deterministic engine produces facts should Qwen explain them.

Example input:

```text
Current odometer: 84,520 km
Oil change interval: 5,000 km
Last oil change: 78,900 km
Distance since oil change: 5,620 km
Fuel efficiency trend: declining from 13.2 km/L to 11.8 km/L
```

Expected answer:

> “Your oil-change interval has been exceeded by about 620 km. Your recent fuel efficiency has also fallen from 13.2 to 11.8 km/L, so it would be reasonable to inspect the engine oil, tire pressure, air filter, and other basic causes.”

The AI should not diagnose mechanical faults.

---

# Feature 5 — Expense Anomaly Signals

This is a high-value, low-cost hackathon feature.

SafarSync can flag:

- unusually expensive fuel purchase,
- unusual fuel quantity,
- sudden efficiency drop,
- maintenance spending much higher than the vehicle’s recent average,
- suspiciously repeated vendor patterns.

Do this primarily with Python statistics/rules.

Example:

```text
⚠ Unusual Fuel Purchase

This fill-up is 38% above your vehicle's recent average fuel cost.
```

Then let Qwen explain it only when the user opens the detail.

This reduces API calls and keeps the system trustworthy.

---

# Feature 6 — Vehicle Logbook

The logbook is the “memory” of SafarSync.

Every record should include:

- date,
- type,
- amount,
- odometer,
- liters,
- description,
- vendor,
- AI confidence (when applicable),
- source (AI scan/manual).

Add:

- search,
- filter by record type,
- date sorting,
- vehicle switching.

---

# Feature 7 — PDF Vehicle History

Generate a clean PDF containing:

- vehicle identity,
- registration number,
- generation date,
- expense summary,
- complete record table,
- maintenance status,
- fuel summary.

The PDF is a strong business feature because it changes the product from “dashboard” into a **portable vehicle record**.

Potential future use:

> “Show the buyer the vehicle’s documented maintenance history.”

---

# Feature 8 — Ask SafarSync

A chat/voice-style assistant can answer questions using the vehicle’s own data.

Examples:

> “How much did I spend on fuel in August?”

> “What was my average fuel efficiency?”

> “When did I last change my oil?”

> “Which category costs me the most?”

### Important architecture rule

Do **not** send the entire raw database blindly to the LLM.

Instead:

1. User asks question.
2. Python calculates/retrieves the relevant facts.
3. Qwen receives the compact verified context.
4. Qwen writes the natural-language answer.

That makes the assistant cheaper, faster, and less hallucination-prone.

---

# 5. Final MVP Scope

## MUST HAVE

These are non-negotiable:

- [ ] Add vehicle
- [ ] Switch active vehicle
- [ ] Manual fuel entry
- [ ] Manual maintenance entry
- [ ] Manual insurance entry
- [ ] Receipt image upload
- [ ] Qwen receipt extraction
- [ ] Editable review form
- [ ] Save extracted record
- [ ] Dashboard
- [ ] Fuel efficiency calculation
- [ ] Spending analytics
- [ ] Maintenance due calculation
- [ ] AI maintenance explanation
- [ ] Vehicle logbook
- [ ] PDF export
- [ ] Friendly error handling
- [ ] Seed/demo data
- [ ] Free-quota protection

## SHOULD HAVE

Build these after MVP is stable:

- [ ] Expense anomaly flags
- [ ] Natural-language Ask SafarSync
- [ ] Voice input
- [ ] Better visual polish
- [ ] Demo mode
- [ ] Data validation badges
- [ ] Delete/edit record

## DO NOT BUILD BEFORE THE CORE WORKS

- Google Maps
- Real-time GPS tracking
- Fleet management
- WhatsApp bot
- Resale-price ML
- OCR fine-tuning
- RAG
- Vector database
- User authentication
- Payments
- Multi-tenant architecture
- Kubernetes
- Complex backend microservices

A hackathon judge rewards a complete product far more than ten unfinished ideas.

---

# 6. Winning Architecture

Keep it simple and explainable.

```text
┌─────────────────────────────────────────────┐
│                 STREAMLIT UI                │
│                                             │
│ Dashboard | Scan | Add Expense | Logbook    │
│ Maintenance | Ask SafarSync | Vehicles      │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│               APPLICATION LOGIC             │
│                                             │
│ analytics.py   maintenance.py   insights.py│
│ validation.py  anomaly.py       pdf_report │
└───────────────┬─────────────────┬───────────┘
                │                 │
                ▼                 ▼
┌─────────────────────┐   ┌──────────────────────┐
│      SQLite DB      │   │   Alibaba Cloud AI   │
│                     │   │                      │
│ vehicles            │   │ Qwen Character + free image/OCR pipeline              │
│ records             │   │ Qwen3.7-plus         │
└─────────────────────┘   └──────────────────────┘
```

---

# 7. Final Project Structure

Use a slightly more professional structure than the original six-file approach.

```text
safarsync-ai/
│
├── .env
├── .gitignore
├── README.md
├── requirements.txt
│
├── app.py
├── config.py
├── ai_client.py
├── database.py
├── receipt_scanner.py
├── analytics.py
├── maintenance.py
├── anomaly.py
├── insights.py
├── validation.py
├── pdf_report.py
├── demo_data.py
│
├── tests/
│   ├── test_database.py
│   ├── test_analytics.py
│   ├── test_maintenance.py
│   └── test_validation.py
│
└── safarsync.db
```

### Why `ai_client.py` matters

Do not create multiple copies of Alibaba API setup.

All model calls should go through one place.

This gives you:

- one API key configuration,
- one base URL,
- one timeout policy,
- one error strategy,
- easier model switching,
- easier testing.

---

# 8. Environment Setup

## Step 1 — Python

Recommended:

**Python 3.11 or newer**

Check:

```bash
python --version
```

---

## Step 2 — Create the project

```bash
mkdir safarsync-ai
cd safarsync-ai
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

---

# 9. `.env` Design

Create:

```text
DASHSCOPE_API_KEY=your_key_here
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_VISION_MODEL=qwen-plus-character
QWEN_TEXT_MODEL=qwen-plus-character
```

If your Model Studio console provides a workspace-specific Singapore URL, use that instead.

The official OpenAI-compatible documentation supports the Singapore workspace-specific endpoint format. citeturn643886search3turn643886search6

Never commit `.env`.

---

# 10. `.gitignore`

```text
.env
venv/
__pycache__/
*.pyc
*.db
.streamlit/secrets.toml
```

Before your first Git commit:

```bash
git status
```

Confirm `.env` is not listed.

---

# 11. Python Dependencies

Use only what the application actually needs.

```text
streamlit
openai
pandas
plotly
fpdf2
pillow
python-dotenv
```

Install:

```bash
pip install -r requirements.txt
```

Do not add libraries merely because they sound impressive.

Every new dependency is another possible failure point.

---

# 12. Alibaba Cloud Setup — Exact Free-Tier Procedure

## Step 1 — Open Model Studio

Use the Singapore region.

## Step 2 — Activate Model Studio

The current Alibaba documentation states that the new-user free quota is available in Singapore and eligible models must use the International deployment scope. citeturn643886search1

## Step 3 — Check the model quota page

Look for:

- `qwen-plus-character`
- `qwen-plus-character`

The free quota page shows remaining tokens and expiry.

## Step 4 — Turn on Free Quota Only

Do this for every eligible model you use.

This gives you an additional safety barrier against unexpected charges. Alibaba explicitly documents that model calls stop once the free quota is exhausted when this mode is enabled. citeturn643886search0turn643886search1

## Step 5 — Create a general API key

Use the regular Model Studio API key.

Do not use an API key intended exclusively for a paid Token Plan/Coding Plan workflow.

Alibaba’s API-key documentation distinguishes standard pay-as-you-go API keys from dedicated Token Plan/Coding Plan keys. citeturn643886search4

## Step 6 — Test one model before building the app

Do not build the entire app before confirming:

1. API key works.
2. Base URL works.
3. `qwen-plus-character` works with an image.
4. `qwen-plus-character` works with text.
5. Free quota is being consumed rather than paid balance.

---

# 13. Shared AI Client

Qoder should generate an `ai_client.py` that:

- loads environment variables,
- creates one OpenAI-compatible client,
- exposes a text-generation helper,
- exposes a vision helper,
- returns friendly exceptions,
- uses short timeouts,
- never prints API keys,
- never writes keys to logs.

Suggested interface:

```python
def get_client() -> OpenAI:
    ...

def ask_text(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 500
) -> str:
    ...

def ask_vision(
    image_data_url: str,
    prompt: str,
    model: str | None = None,
    max_tokens: int = 500
) -> str:
    ...
```

The exact implementation should be generated by Qoder from this specification.

---

# 14. Receipt Scanner Specification

Qoder should create `receipt_scanner.py`.

## Input

A local image file.

## Processing pipeline

```text
Image
  ↓
Pillow validation
  ↓
Resize/compress if necessary
  ↓
Convert to base64 data URL
  ↓
Qwen Character + free image/OCR pipeline
  ↓
JSON extraction
  ↓
Python schema validation
  ↓
Confidence + warnings
  ↓
Editable Streamlit form
```

Alibaba documents that the OpenAI-compatible interface accepts Base64-encoded Data URLs for image input. citeturn193555search0turn193555search2

## Prompt design

The prompt should instruct the model to:

- inspect the full receipt,
- support Urdu/English/mixed text,
- support handwriting,
- support low-light/blurry photos,
- never invent a value,
- return `null` when genuinely unreadable,
- set low confidence when uncertain,
- output JSON only.

### Strong extraction schema

```json
{
  "record_type": "fuel | maintenance | insurance | unknown",
  "date": "YYYY-MM-DD | null",
  "amount_pkr": 0,
  "liters": 0,
  "odometer_km": 0,
  "description": "string | null",
  "vendor_name": "string | null",
  "confidence": "high | medium | low"
}
```

Add:

```json
"warnings": []
```

Example:

```json
{
  "warnings": [
    "Odometer was partially obscured."
  ]
}
```

---

# 15. Validation Layer

AI output must never be trusted blindly.

Create `validation.py`.

Validate:

- date format,
- amount >= 0,
- liters > 0 when fuel,
- odometer >= 0,
- known record type,
- realistic numeric ranges,
- required fields.

Example:

```text
AI says:
amount_pkr = -45000

Python says:
Rejected — amount cannot be negative.
```

The UI then lets the user correct it.

---

# 16. Database Design

Use SQLite.

## Table: vehicles

```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
name TEXT NOT NULL
registration_number TEXT
created_at TEXT NOT NULL
```

## Table: records

```sql
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
```

`source` should be:

- `ai_scan`
- `manual`
- `demo`

This makes the provenance of every record visible.

---

# 17. Analytics Engine

`analytics.py` should calculate:

## Fuel efficiency

For consecutive fuel records:

```text
km/L =
(current odometer - previous odometer)
/
current fill liters
```

Skip invalid pairs.

Return warnings.

## Monthly spending

Group by:

```text
YYYY-MM
```

and:

```text
fuel
maintenance
insurance
```

## Total vehicle cost

```text
all expenses / total distance
```

Return `None` when there is insufficient data.

Never divide by zero.

---

# 18. Maintenance Engine

`maintenance.py` should produce structured status:

```json
{
  "type": "oil_change",
  "interval": 5000,
  "km_since_last": 5620,
  "status": "overdue",
  "overdue_by": 620
}
```

Possible statuses:

- `not_due`
- `due_soon`
- `overdue`
- `unknown`

A richer status model looks more professional than a simple yes/no flag.

---

# 19. AI Insight Engine

Create `insights.py`.

It should not calculate anything important.

Instead it receives already-calculated facts:

```text
Total fuel spend: PKR 31,400
Average fuel efficiency: 12.1 km/L
Previous month: 13.2 km/L
Oil service status: overdue by 620 km
Top expense category: fuel
```

Then Qwen writes a short user-friendly explanation.

### Prompt rules

The model must:

- use only supplied facts,
- not invent new measurements,
- not diagnose mechanical failures,
- not claim certainty,
- keep output under 120 words,
- mention specific numbers,
- prioritize actionable information.

---

# 20. Ask SafarSync Architecture

For a user question:

```text
User question
      ↓
Intent detection
      ↓
Python data retrieval
      ↓
Compact verified context
      ↓
Qwen3.7-plus
      ↓
Natural-language answer
```

Example:

### User

> “How much did I spend on fuel this month?”

### Python computes

```text
Fuel spending, August 2026 = PKR 27,450
```

### Qwen receives

```text
Question:
How much did I spend on fuel this month?

Verified answer:
PKR 27,450
```

### Qwen responds

> “You spent PKR 27,450 on fuel this month.”

This is much safer than asking the LLM to do SQL arithmetic itself.

---

# 21. Free Voice Input

Treat voice as a **showcase feature**, not a dependency for the core product.

Use browser speech recognition where supported.

Concept:

```text
Microphone
   ↓
Browser speech-to-text
   ↓
Text question
   ↓
Python context retrieval
   ↓
Qwen3.7-plus
   ↓
Answer
```

This avoids adding another paid speech service.

Because browser speech recognition support can vary, the text-input path must always remain available.

For the final demo:

> “You can talk to your vehicle data instead of searching through spreadsheets.”

That is an excellent visual moment.

---

# 22. App Navigation

Sidebar:

```text
🚗 SafarSync AI

Active Vehicle
[Honda Civic 2019 ▼]

Dashboard
📊 Dashboard
📷 Scan Receipt
➕ Add Expense
📖 Vehicle Logbook
🔧 Maintenance
🤖 Ask SafarSync
🚘 Manage Vehicles
```

Always show:

```text
Powered by Alibaba Cloud Qwen
```

---

# 23. Dashboard Layout

## Header

```text
Honda Civic 2019
LEA-1234
```

## KPI row

```text
Total Spend     Fuel Spend     Avg km/L     Cost/km
PKR 86,540      PKR 51,200     12.1          PKR 8.4
```

## Main chart

Fuel efficiency trend.

## Secondary chart

Monthly spending.

## Insight card

```text
🤖 SafarSync Insight

Your fuel efficiency fell from 13.2 km/L
to 11.8 km/L over the last 3 fuel records.

Your next oil change is overdue by 620 km.
```

This card should feel like the “AI value” rather than another chart.

---

# 24. Scan Receipt UX

Do not make the page look like a developer console.

The flow should be:

### Step 1

```text
Take a photo or upload receipt
```

### Step 2

Show:

```text
Analyzing receipt with Qwen...
```

### Step 3

Show extraction:

```text
✓ Fuel
✓ PKR 4,500
✓ 32.5 liters
✓ 84,520 km
✓ PSO
```

### Step 4

Show:

```text
Review before saving
```

Every field editable.

### Step 5

After save:

```text
✓ Expense added to your vehicle history.
```

Then optionally show:

```text
View Dashboard
```

---

# 25. Demo Dataset

Do not depend on the judges waiting while you create ten records.

Create `demo_data.py`.

Seed realistic records for:

- 1 vehicle,
- 8–15 fuel entries,
- 4–6 maintenance entries,
- 1–2 insurance entries.

The dates should span several months.

Include:

- fuel efficiency changes,
- at least one maintenance item due,
- at least one anomaly,
- several vendors.

The dashboard should therefore look “alive” instantly.

---

# 26. Demo Mode

Add a simple environment variable:

```text
DEMO_MODE=true
```

When enabled:

- demo data can be loaded,
- sample records are immediately available,
- AI failures can fall back to a prepared explanation,
- the app remains visually demonstrable.

Do not fake AI calls.

If the API is unavailable, say:

> “Live AI service unavailable. Showing the last successful analysis.”

This is honest and keeps the demo functional.

---

# 27. $0 Deployment

Do **not** make Alibaba ECS a required part of the project.

ECS could introduce:

- billing complexity,
- setup time,
- another failure point,
- unnecessary infrastructure work.

For a zero-budget hackathon deployment, use **Streamlit Community Cloud**.

Streamlit documents Community Cloud as a free deployment platform connected to GitHub. citeturn193555search5turn193555search6

## Important limitation

SQLite on a hosted ephemeral environment is not the same as a production multi-user database.

Therefore:

- local demo = fully persistent during the local session,
- hosted hackathon demo = use seeded/demo data and understand that filesystem persistence is not a production guarantee.

For the hackathon this is acceptable because the scoring target is the product demonstration, not enterprise persistence.

---

# 28. Qoder Strategy — 2,180 Credits

Your Qoder credits are a limited engineering budget.

Treat them like one.

## Rule 1

Do not spend Quest credits on tiny edits.

Use:

- **Quest Mode** for large modules.
- **Agent Mode** for debugging and small changes.

## Rule 2

Give Qoder complete specifications.

Bad:

> “Make dashboard.”

Good:

> “Create the Streamlit dashboard page using these existing analytics functions, with four KPI cards, two Plotly charts, empty-state messages, active vehicle filtering, and graceful handling of insufficient data. Do not rewrite database.py.”

## Rule 3

Never ask Qoder to “fix everything.”

Give it one failure at a time.

---

# 29. Recommended Qoder Build Sequence

## QUEST 0 — Repository + skeleton

Create:

- app.py
- config.py
- ai_client.py
- database.py
- requirements.txt
- `.gitignore`
- tests folder

Do not implement the full UI.

Verify:

```bash
python -m compileall .
```

---

# QUEST 1 — Database

Build:

- schema,
- CRUD functions,
- vehicle functions,
- record functions,
- clean errors.

Test:

```bash
python database.py
```

Expected:

```text
Database initialized successfully!
```

---

# QUEST 2 — AI Client

Build:

- environment loading,
- OpenAI-compatible Alibaba client,
- model selection,
- text helper,
- vision helper,
- timeout,
- safe error handling.

Test with one text request.

Then stop.

Do not proceed until the AI connection is confirmed.

---

# QUEST 3 — Receipt Scanner

Build:

- Pillow image validation,
- Base64 conversion,
- Qwen Character + free image/OCR pipeline request,
- JSON extraction,
- fallback JSON parsing,
- validation,
- confidence handling.

Test three images:

1. printed receipt,
2. handwritten receipt,
3. poor-quality image.

---

# QUEST 4 — Analytics + Anomaly

Build:

- fuel efficiency,
- monthly spending,
- cost per km,
- trend detection,
- anomaly signals.

Write unit tests.

Run:

```bash
pytest
```

---

# QUEST 5 — Maintenance + AI Insights

Build:

- maintenance schedule logic,
- due/overdue status,
- verified context creation,
- Qwen explanation.

Test without AI first.

Then test with AI.

This prevents the LLM from becoming a hidden dependency in your business logic.

---

# QUEST 6 — Streamlit MVP UI

Build only:

- Manage Vehicles
- Add Expense
- Scan Receipt
- Dashboard
- Logbook
- Maintenance

Do not add voice yet.

---

# QUEST 7 — PDF + Demo Data

Build:

- PDF export,
- demo dataset,
- demo mode,
- polished empty states.

---

# QUEST 8 — Ask SafarSync + Voice Showcase

Only start after the entire MVP passes.

Build:

- question box,
- verified context retrieval,
- Qwen response,
- browser voice input if feasible.

---

# 30. Agent Mode Debugging Rules

When something breaks, use this format:

```text
Problem:
<what happened>

Expected:
<what should happen>

Observed:
<what actually happened>

Steps to reproduce:
<exact steps>

Relevant file:
<filename>

Constraints:
<what Qoder must not change>
```

Example:

> Problem: Dashboard crashes when there is only one fuel record.
>
> Expected: Show a friendly message that two valid odometer readings are required.
>
> Observed: ZeroDivisionError.
>
> Relevant file: analytics.py.
>
> Constraint: Do not modify database.py or app.py.

This style produces safer changes.

---

# 31. QA Checklist

Before calling the project “done,” test every item.

## Fresh start

- [ ] Delete database.
- [ ] Run app.
- [ ] No crash.
- [ ] Add first vehicle.

## Vehicle management

- [ ] Add vehicle.
- [ ] Switch vehicles.
- [ ] Correct records remain separated.

## Manual data

- [ ] Add fuel.
- [ ] Add maintenance.
- [ ] Add insurance.
- [ ] Edit values.
- [ ] Delete a record.

## OCR

- [ ] Upload clear receipt.
- [ ] Upload handwritten receipt.
- [ ] Upload blurry receipt.
- [ ] Verify extracted values.
- [ ] Correct one field manually.
- [ ] Save corrected result.

## Dashboard

- [ ] One record.
- [ ] Two fuel records.
- [ ] Many records.
- [ ] Missing odometer.
- [ ] No maintenance.
- [ ] Multiple months.

## Maintenance

- [ ] Not due.
- [ ] Due soon.
- [ ] Overdue.
- [ ] No maintenance history.

## AI

- [ ] Qwen vision works.
- [ ] Qwen text works.
- [ ] API error shows friendly message.
- [ ] No API key appears on screen.
- [ ] No raw traceback appears during normal use.

## PDF

- [ ] PDF generates.
- [ ] PDF opens.
- [ ] Totals are correct.
- [ ] Empty vehicle still generates a valid report.

## Voice

- [ ] Browser supports microphone.
- [ ] Text fallback works.
- [ ] Qwen answer is based on verified data.

---

# 32. Free-Tier Safety Checklist

Before the first serious demo:

- [ ] Model Studio is in Singapore.
- [ ] Deployment scope is International.
- [ ] `Free Quota Only` is ON.
- [ ] Remaining quotas are visible.
- [ ] Correct API key is being used.
- [ ] No Token Plan/Coding Plan key is accidentally used.
- [ ] App has no hidden background AI calls.
- [ ] AI calls only happen on explicit user actions.
- [ ] Demo mode avoids unnecessary API calls.
- [ ] AI prompts request concise outputs.

Alibaba notes that free quota is consumed by real-time model invocation and that each model has separate quota. citeturn643886search1

---

# 33. Cost Optimization

Even with free quota, act like every token matters.

## Receipt OCR

Call vision once per upload.

Do not re-call the model every time the user edits a field.

## Maintenance

Calculate rule-based status locally.

Call Qwen only when:

- the page is opened,
- the user asks for an explanation,
- or the underlying data has changed.

## Chat

Do not send the complete database.

Send only relevant verified facts.

## Dashboard

Charts should use Python calculations.

Do not ask Qwen to generate chart numbers.

---

# 34. AI Prompting Rules

Use prompts that are:

- explicit,
- narrow,
- structured,
- measurable.

Avoid:

> “Analyze this receipt.”

Prefer:

> “Extract only the fields listed below. Do not infer values that are not visible. If a field is genuinely unreadable return null. Return valid JSON only.”

For reasoning:

> “Use only the verified facts supplied below. Do not invent a measurement, service history, or mechanical diagnosis.”

---

# 35. Product Reliability Principle

This is the architecture sentence you should remember:

> **Python decides the numbers. Qwen explains the numbers.**

That line makes the technical story much stronger.

It also protects you from a judge asking:

> “What if the LLM hallucinates?”

Your answer:

> “The model is not our accounting engine. We calculate vehicle metrics deterministically in Python, then use Qwen to explain those verified results in natural language.”

---

# 36. Security Principles

Never:

- hard-code API keys,
- commit `.env`,
- print keys,
- send API keys to the browser,
- expose secrets in screenshots,
- put secrets into Qoder prompts.

For Streamlit Community Cloud, store the key using Streamlit secrets rather than committing it to Git.

---

# 37. UX Polish That Makes the Project Feel Expensive

The project should visually feel more like a polished product than a classroom assignment.

Use:

- large KPI cards,
- consistent spacing,
- clear section headings,
- meaningful icons,
- human-readable dates,
- PKR currency formatting,
- badges for AI confidence,
- empty-state illustrations/messages,
- success notifications,
- confirmation before destructive actions.

Avoid:

- raw Python errors,
- giant tables on the home screen,
- excessive emoji,
- tiny fonts,
- unnecessary configuration controls.

---

# 38. Demo Script — 5 Minutes

## 0:00–0:25 — Hook

Say:

> “A vehicle owner can spend hundreds of thousands of rupees over the life of a car and still have the maintenance history scattered across paper receipts, photos, and memory.”

Pause.

> “SafarSync turns those records into a living digital history.”

---

## 0:25–1:20 — Receipt Scan

Show a real receipt.

Upload or photograph it.

Say:

> “This receipt is messy. Instead of typing every number, SafarSync asks Qwen to understand it.”

Show:

- record type,
- amount,
- liters,
- odometer,
- vendor.

Then say:

> “The AI is not trusted blindly. The owner reviews every field before saving.”

Click Save.

---

## 1:20–2:10 — Dashboard

Go to dashboard.

Show the record appearing in the charts.

Then point to:

- total spending,
- average km/L,
- cost/km.

Say:

> “Now the receipt is no longer a piece of paper. It becomes part of a structured vehicle history.”

---

## 2:10–3:00 — Maintenance

Open Maintenance.

Show:

> Oil change overdue by 620 km

Then show the Qwen explanation.

Say:

> “The maintenance status comes from deterministic rules. Qwen turns those verified numbers into plain-language advice.”

---

## 3:00–3:45 — Ask SafarSync

Ask:

> “How much did I spend on fuel this month?”

Then:

> “Why has my fuel efficiency dropped?”

If voice works:

Use the microphone.

This is your strongest “wow” moment.

---

## 3:45–4:25 — Logbook + PDF

Open Logbook.

Show:

- searchable records,
- manual entries,
- AI-scanned entries.

Generate PDF.

Say:

> “The same data can become a portable vehicle history for resale, insurance, or personal records.”

---

## 4:25–5:00 — Why Alibaba + closing

Say:

> “SafarSync uses Alibaba Cloud Model Studio and Qwen for multimodal receipt understanding and intelligent explanations, while Qoder helped us build and test the product quickly.”

Finish:

> “We are not trying to make vehicle ownership smarter by adding another spreadsheet. We are removing the spreadsheet step entirely.”

---

# 39. Judge Questions — Strong Answers

## “Isn’t this just expense tracking?”

> “The differentiator is the input. Traditional expense trackers require manual typing. SafarSync starts with a photo of the real-world document and turns it into structured data, then uses the accumulated history for vehicle-specific insights.”

## “What if OCR is wrong?”

> “The model output is reviewed by the user before it becomes a permanent record. We also validate values in Python.”

## “Why use AI?”

> “The difficult part is understanding messy real-world documents and making the resulting data conversational. AI solves the unstructured-to-structured and natural-language parts. Deterministic Python handles the accounting logic.”

## “Why Alibaba Cloud?”

> “Alibaba Cloud gives us access to the Qwen model family through Model Studio, including multimodal models for image understanding and OpenAI-compatible APIs for straightforward integration.” citeturn193555search3turn193555search0

## “How do you keep it free?”

> “We designed the entire prototype around free-tier services, use Alibaba Model Studio’s eligible free quota, and enable Free Quota Only so the app stops instead of silently creating paid usage.” citeturn643886search1turn643886search0

## “Why not use a database like Firebase?”

> “For the hackathon prototype we intentionally kept the architecture lightweight with SQLite. That reduces infrastructure failure points and lets us focus on the user-facing AI product.”

---

# 40. Roadmap — What Comes After the Hackathon

These are roadmap items, not excuses for unfinished MVP features.

### Phase 2

- cloud persistence,
- authentication,
- multi-device sync,
- family vehicles,
- fleet support,
- richer anomaly detection.

### Phase 3

- mechanic verification,
- vehicle resale reports,
- insurance integrations,
- WhatsApp interface,
- service reminders,
- location-aware service recommendations.

### Phase 4

- anonymized vehicle intelligence,
- predictive maintenance models trained on real usage data,
- fleet analytics.

---

# 41. Business Model

## Individual users

Freemium:

- free basic tracking,
- premium advanced history,
- expanded AI insights,
- cloud sync.

## B2B

Potential customers:

- insurers,
- used-car platforms,
- service centers,
- fleet operators.

The key asset is not simply the dashboard.

It is the **structured vehicle history**.

---

# 42. What Makes SafarSync Different

Do not pitch it as:

> “An AI app that tracks car expenses.”

Pitch it as:

> **“An AI vehicle memory for Pakistan.”**

The strongest differentiators are:

1. Real-world receipt capture.
2. Human-in-the-loop verification.
3. Vehicle-specific analytics.
4. Maintenance intelligence.
5. Conversational access to personal vehicle data.
6. PDF-ready vehicle history.
7. Pakistan-oriented workflows.
8. A zero-cost prototype architecture.

---

# 43. Git Workflow

After every stable module:

```bash
git add .
git commit -m "feat: add database layer"
```

Examples:

```text
feat: add Alibaba Qwen client
feat: add receipt OCR pipeline
feat: add fuel analytics
feat: add maintenance engine
feat: add dashboard UI
feat: add PDF vehicle logbook
feat: add demo mode
feat: add Ask SafarSync
```

Never keep the entire project as one giant final commit.

---

# 44. Final Pre-Demo Checklist

## Product

- [ ] All core features work.
- [ ] Manual entry works.
- [ ] Receipt OCR works.
- [ ] Dashboard is populated.
- [ ] Maintenance screen works.
- [ ] PDF export works.
- [ ] Ask SafarSync works if included.

## AI

- [ ] Qwen Character + free image/OCR pipeline works.
- [ ] Qwen text model works.
- [ ] Free Quota Only is enabled.
- [ ] Remaining quota has been checked.

## Security

- [ ] No API key in Git.
- [ ] No API key in screenshots.
- [ ] No API key in Qoder messages.
- [ ] No secret displayed in the app.

## Demo

- [ ] Three tested receipts.
- [ ] Demo vehicle ready.
- [ ] Demo data loaded.
- [ ] Backup screen recording ready.
- [ ] Pitch rehearsed at least three times.
- [ ] Demo fits inside five minutes.

---

# 45. Emergency Plan

## If Qwen API fails

Use the last successful test result.

Say:

> “The live model service is temporarily unavailable, so I’ll show the last successful extraction.”

Then continue the product flow.

## If Streamlit crashes

Use the backup recording.

Do not debug live.

## If a judge asks about an unbuilt feature

Say:

> “That is part of the post-hackathon roadmap. We intentionally prioritized a complete receipt-to-insight workflow rather than spreading the build across too many unfinished features.”

---

# 46. The One-Page Build Order

When you are tired, follow only this:

```text
1. Create Git repository
2. Create Python venv
3. Activate Alibaba Model Studio
4. Confirm Singapore + International
5. Enable Free Quota Only
6. Create API key
7. Test Qwen Character + free image/OCR pipeline
8. Test Qwen3.7-plus
9. Build database
10. Build AI client
11. Build receipt scanner
12. Build validation
13. Build analytics
14. Build maintenance logic
15. Build AI insights
16. Build manual entry
17. Build Streamlit UI
18. Build dashboard
19. Build logbook
20. Build PDF
21. Seed demo data
22. Run QA
23. Deploy to Streamlit Community Cloud
24. Add Ask SafarSync
25. Add voice showcase
26. Record backup demo
27. Rehearse
28. Freeze the code
29. Win the room
```

---

# 47. Final Architecture Rulebook

Remember these ten rules:

1. **$0 means $0.**
2. **Free Quota Only stays ON.**
3. **Use only the models actually allocated to your account.**
4. **Qwen handles AI; Python handles truth.**
5. **Never silently save model output.**
6. **Manual entry must work without OCR.**
7. **Every page must survive empty data.**
8. **No stretch feature before MVP stability.**
9. **Qoder Quest builds modules; Agent Mode fixes them.**
10. **Demo reliability beats infrastructure complexity.**
11. **The judge should understand the value in 30 seconds.**

---

# 48. Why This Version Has a Better Chance of Winning

The original concept was already good.

This version makes the strategy stronger because it turns SafarSync into a complete experience:

```text
UNSTRUCTURED WORLD
paper receipt
handwritten bill
memory
        ↓
FREE OCR / IMAGE PIPELINE
        ↓
QWEN CHARACTER
        ↓
STRUCTURED DATA
        ↓
DETERMINISTIC ANALYTICS
        ↓
VEHICLE INTELLIGENCE
        ↓
NATURAL-LANGUAGE INSIGHTS
        ↓
SEARCH / CHAT / VOICE
        ↓
PORTABLE VEHICLE HISTORY
```

That is much more compelling than:

> “We made an OCR app.”

You are demonstrating a complete AI workflow:

**Vision → Extraction → Validation → Data → Analytics → Reasoning → Conversation → Action**

And you can build the prototype with a zero-paid-spend architecture using Qoder, Alibaba Cloud’s eligible free model quota, open-source/free Python packages, SQLite, GitHub, and free Streamlit Community Cloud deployment. Alibaba’s current documentation confirms the free-quota mechanism, OpenAI-compatible multimodal API, and free Streamlit Community Cloud deployment. citeturn643886search1turn193555search0turn193555search5

---

# 49. Official References

- Alibaba Cloud Model Studio — Free quota for new users  
  https://www.alibabacloud.com/help/en/model-studio/new-free-quota

- Alibaba Cloud Model Studio — Model pricing and eligible free quotas  
  https://www.alibabacloud.com/help/en/model-studio/model-pricing

- Alibaba Cloud Model Studio — OpenAI-compatible API  
  https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope

- Alibaba Cloud Model Studio — Qwen vision/OpenAI-compatible chat  
  https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-chat-completions

- Streamlit Community Cloud  
  https://docs.streamlit.io/deploy/streamlit-community-cloud

---

# 50. Final Instruction to Qoder

At the top of every major Quest prompt, use this safety header:

```text
PROJECT: SafarSync AI

ROLE:
You are implementing one module of a beginner-owned hackathon project.

NON-NEGOTIABLE RULES:
1. Do not rewrite unrelated files.
2. Do not introduce paid services.
3. Do not add unnecessary dependencies.
4. Never expose secrets.
5. Keep Alibaba Qwen integration configurable.
6. Preserve existing interfaces unless absolutely necessary.
7. Add type hints and clear error handling.
8. Write beginner-friendly comments where the logic is non-obvious.
9. Run tests or compile checks before reporting completion.
10. If an assumption is required, make the smallest safe assumption and document it.

IMPORTANT:
Python must remain the source of truth for calculations.
Qwen should explain or extract information, not silently replace deterministic business logic.
```

This should be treated as the operating system for the entire build.

---

## Closing

**SafarSync AI is now scoped as a product, not a collection of features.**

The winning path is not to build the most complicated system.

It is to build the system that makes a judge think:

> **“This is immediately useful, the AI is genuinely involved, the product is polished, and the team clearly understands what they built.”**

Build the core until it is boringly reliable.

Then add the wow moments.

