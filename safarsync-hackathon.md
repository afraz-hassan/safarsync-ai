# SafarSync AI — Qoder Build Playbook
### Your step-by-step, beginner-safe guide to building and winning with SafarSync AI at the Alibaba Cloud AI Hackathon 2026 (Bano Qabil × Alkhidmat Foundation)

**Prepared for:** Afraz Hassan — 1st-Semester BS Software Engineering, FAST-NUCES Islamabad · 1 year freelance DevOps experience · Basic LLM knowledge (no RAG/fine-tuning yet) · Python, C++, HTML/CSS · MO-100, AZ-900 certified
**Build tool:** Qoder IDE (Agent Mode + Quest Mode), connected to Alibaba Cloud Model Studio (Qwen models)
**Document version:** 1.0 — written 21 August 2026

---

## 0. How to Use This Document

This is not a copy of your original SafarSync documentation — it replaces the "write every line of Python yourself in VS Code" plan with a plan built around **Qoder**, the actual tool the hackathon is giving you tomorrow. The idea, the problem, and the features stay the same (they were already good). What changes is *how* you build it.

Three rules for this whole document:

1. **You never write a file from a blank page.** For every file SafarSync needs, you will hand Qoder a precise, pre-written specification ("Quest Prompt"). Qoder writes the code. You read it, test it, and understand it — that's what makes you able to defend it in front of judges.
2. **You verify, you don't guess.** Every step below tells you exactly how to confirm it worked before moving to the next one. A hackathon project that "mostly works" is a project that fails live in front of judges.
3. **Scope is locked.** Section 5 below defines a Core Build (must work, 100%) and a Stretch Build (only if time remains). Do not touch Stretch features until every Core feature is tested and stable. This single rule is what separates hackathon teams that finish from teams that panic at hour 20 with five half-built features.

---

## 1. Hackathon Snapshot — Verified as of 21 August 2026

| Item | Detail |
|---|---|
| Full name | Alibaba Cloud AI Hackathon 2026 |
| Organizers | Bano Qabil (Alkhidmat Foundation Pakistan's tech-education arm) + Alibaba Cloud, with Cognix Solutions / Cogniser Pakistan as technical partners |
| Scale | Described as Pakistan's first and largest hackathon of this kind, launched at a ceremony in Lahore in July 2026 |
| Registration | Closed 7 August 2026 — you're already in |
| Your onboarding city | Islamabad/Rawalpindi (one of only four physical onboarding cities — Lahore, Karachi, Islamabad, Rawalpindi) |
| Webinar 1 — "AI Hackathon Training: Qoder Quest" | Wed 19 Aug, 13:30–15:15 PKT. Covered: hackathon introduction, participant guide, and a first technical walkthrough of Qoder, how LLMs work, Qoder Quest, and prompting |
| Webinar 2 — "AI Hackathon Training: Qoder IDE" | Thu 20 Aug, 13:30–15:00 PKT. Covered: Qoder Skills, MCP, plug-ins, cost optimisation, and applied demos |
| Today (21 Aug) | Organizers issue your Qoder ID / access |
| Tomorrow (22 Aug) | Building officially begins |
| Community | Discord: `discord.gg/xfyUK45Ka` — this is where schedule changes, deadline confirmations, mentor Q&A, and troubleshooting happen. Check it daily. |
| Prizes | Cash + Alibaba Cloud credits + mentorship + investor exposure |

> **⚠️ One thing you must confirm yourself, today, on Discord:** the exact **submission deadline and demo-day date/time**. This document structures your build in *phases*, not fixed calendar days, precisely because that date isn't published in your source material. The moment you know it, write it at the top of this file and count backward to fix your phase timeline.

### 1.1 Why Alibaba Cloud usage is not optional

This is a **branded** hackathon — Alibaba Cloud is a co-organizer, not a sponsor logo. Judges are evaluating whether you meaningfully used their stack. For SafarSync that means:

- Your core AI feature (receipt OCR) must run on **Qwen-VL** (Alibaba's vision-language model), not OpenAI/Gemini/Claude.
- You build the whole thing *inside Qoder*, using Quest Mode for real work — not just as a glorified autocomplete.
- Your pitch explicitly names Qwen and Qoder and explains *why* they mattered (Section 11 gives you the exact language).

### 1.2 Likely judging weight (inferred from hackathon goals — not officially published; confirm on Discord if a rubric is released)

| Criterion | Est. Weight | What it means for you |
|---|---|---|
| Innovation & Originality | 25% | Receipt OCR for handwritten Urdu/English bills is a genuinely local, underserved problem |
| Technical Implementation | 30% | Does it *actually run*, live, using Qwen properly — this is your biggest scoring lever and the whole point of the Core Build in Section 5 |
| Real-World Impact | 20% | 28M+ registered vehicles in Pakistan, zero digital record-keeping — say this number in your pitch |
| Business Viability | 15% | Freemium + B2B (insurers, resale platforms) — Section 11 covers this |
| Presentation & Demo | 10% | A **live**, rehearsed, 5-minute demo beats a longer unrehearsed one |

---

## 2. Your Starting Position (and why it's a fine place to start from)

Be honest with yourself about this table — it's the actual reason this document is built around Qoder rather than around you typing raw Python for 30 hours straight.

| You have | You don't have yet | How this plan compensates |
|---|---|---|
| Python, C++, HTML/CSS fundamentals | Streamlit, SQLite, or REST API experience specifically | Qoder writes these; you read and learn them as you review its output — you're not blocked by not already knowing the library |
| 1 year DevOps freelancing | Deep backend architecture experience | You already understand `.env` files, servers, deployment, and version control better than most first-semester teammates will — lean on this for Section 10 |
| Basic LLM knowledge | RAG, fine-tuning | **Good news: SafarSync needs neither.** It calls Qwen-VL and Qwen-Max through a plain API, the same way you'd call any REST API. No RAG, no fine-tuning, no vector database anywhere in this build. |
| MO-100 (Microsoft Office Specialist) | — | Directly useful for your pitch deck and PDF export feature |
| AZ-900 (Azure Fundamentals) | Alibaba Cloud specifics | You already know cloud concepts (compute, storage, regions); Alibaba Cloud/ECS is the same concepts with different menu names — Section 10 maps them |
| 1 week into semester 1 | Large-scale team software experience | Qoder's Quest Mode is *designed* for exactly this gap — you specify precisely, it executes precisely, you don't need five years of engineering instinct to get production-shaped code |

**The one skill this plan actually demands of you:** writing a clear, specific instruction (a "spec") and then reading code carefully enough to test it. That's it. Section 8 gives you every spec pre-written — you'll paste, run, verify, and only then move on.

---

## 3. Understanding Qoder (read this before you open it tomorrow)

Qoder is Alibaba's agentic coding IDE. It is **not** Cursor-style autocomplete — it has two distinct modes, and knowing which one to use for which job is the single most important skill in this whole hackathon.

| Mode | What it does | When you use it in this build |
|---|---|---|
| **Agent Mode** | Conversational, chat-driven pair programming. You ask, it edits, you review each change before it's applied (checkpoints). Best for small, interactive changes and debugging. | Fixing bugs, tweaking UI, asking "why did this break," small edits |
| **Quest Mode** | You hand it a full specification. It plans, writes multi-file code, tests it, and delivers a finished feature — largely unattended. Best for building a whole module in one shot. | Building each of the 6 core files in Section 8 |

Other things you need to know before tomorrow:

- **Model:** Qoder is built around Qwen3-Coder for code generation, with the ability to route to other models for chat. For this hackathon, keep Qoder itself pointed at its default coding model — you'll call Qwen-VL and Qwen-Max *separately*, from inside your own Python code, using your own DashScope API key (Section 7). Don't confuse "the model Qoder uses to write code" with "the model your app calls at runtime" — they're two different things.
- **Skills / MCP / plug-ins:** covered in Webinar 2. Skills are reusable instruction packs Qoder can load (similar in spirit to the skill files professional coding agents use); MCP lets Qoder connect to external tools/services. You won't need custom MCP servers for the Core Build — Python, SQLite, and the Qwen API are all reachable with plain code.
- **Credits:** Qoder is credit-metered (chat/agent requests and Quest tasks consume credits at different rates; Quest tasks cost more per run because they do more work). This is why Section 8's prompts are written to be **complete and specific on the first try** — a vague prompt that needs three follow-up corrections burns three times the credits of one clear prompt.
- **Checkpoints:** Agent Mode changes are applied incrementally and can be reviewed/rolled back. Quest Mode delivers a finished result you review afterward. If a Quest run goes wrong, don't panic-prompt fixes on top of fixes — roll back and re-run the corrected spec.

> **✅ Today's action:** when you receive your Qoder ID/access from the organizers, log in, and immediately go to **Settings → Models** and confirm you can see and select a Qwen coding model. If it fails, ask on Discord immediately — don't wait until building day.

---

## 4. Today's Pre-Build Checklist (do this on 21 August, before you sleep)

Doing this tonight means you start building at full speed tomorrow instead of losing your first hour to setup.

- [ ] Received and activated your Qoder ID from the organizers; logged into Qoder successfully
- [ ] Joined the Discord (`discord.gg/xfyUK45Ka`) and confirmed the exact deadline/demo-day time — write it here: **______________**
- [ ] Installed **Python 3.11+** (check "Add to PATH" during install on Windows) — verify with `python --version` in a terminal
- [ ] Created an **Alibaba Cloud account** at alibabacloud.com using your student email
- [ ] Generated a **Qwen API key** from DashScope (dashscope.aliyuncs.com/api-doc) — Model Studio's console → API Keys. Save it somewhere private, not in any file you'll commit to Git.
- [ ] Created a private **GitHub repository** called `safarsync-ai` (your DevOps background means you already know why: version control from commit #1, not "I'll add Git later")
- [ ] Confirmed your phone camera can take clear photos in low light (you'll need 3 real receipt photos for testing and demo)
- [ ] Skimmed Section 5 and 8 below so you know what you're building before you sit down

---

## 5. Project Overview: SafarSync AI

**Tagline:** The AI Co-Pilot for Vehicle Expense Intelligence & Predictive Maintenance.

**Problem:** Pakistan has 28M+ registered vehicles, and vehicle expense records are almost entirely informal — handwritten mechanic bills, no digital history, no way to verify fair pricing, fuel theft going undetected, and no maintenance-history record to protect resale value. SafarSync turns a phone photo of any receipt into structured, searchable, analyzed data.

### 5.1 Core Build (must be 100% working and demo-able)

| # | Feature | What it does | Powered by |
|---|---|---|---|
| 1 | **Smart Receipt OCR Scanner** | User photographs a fuel/mechanic/insurance receipt (handwritten or printed, Urdu or English). Qwen-VL reads it and extracts date, amount (PKR), liters, odometer, services, and vendor name into structured JSON. User reviews before saving (human-in-the-loop). | Qwen-VL-Plus |
| 2 | **Fuel Intelligence Dashboard** | Charts of spending over time, fuel efficiency (km/L from odometer deltas), cost breakdown by category. | Pandas + Plotly |
| 3 | **Predictive Maintenance Advisor** | Rule-based schedule (oil change every ~5,000 km, etc.) combined with a Qwen-Max call that turns the numbers into a plain-language recommendation. | Rules + Qwen-Max |
| 4 | **Digital Vehicle Health Logbook** | Every record ever scanned, searchable/filterable, exportable to PDF (useful for resale — an actual selling point in your pitch). | SQLite + fpdf2 |
| 5 | **Streamlit Web App** | Ties all of the above into one live, demoable web interface. | Streamlit |

This alone, done well and bug-free, is a complete, judge-ready, Qwen-powered product. **Do not skip straight to stretch features before this is rock solid.**

### 5.2 Stretch Build (only after Core is fully tested — build in this order if time remains)

| # | Feature | Note |
|---|---|---|
| 6 | GPS Distance & Trip Tracker | Google Maps Distance Matrix API (needs its own key, Section 7) or the free Haversine-formula method for live GPS — upgrades km/L accuracy. Genuinely impressive but it's a second external API and second failure point; only add it once Core is stable. |
| 7 | Anomaly & Fraud Alert Engine | Flags a fuel-up or bill that's statistically out of line with the vehicle's history. Cheap to add once analytics.py exists — mostly a threshold check on data you already have. |
| 8 | Qwen-powered AI Chatbot | A chat box answering questions like "how much did I spend on fuel last month?" using the user's own logged data. Strong demo moment, but skip it if you're tired — a live crash here is worse than not having it. |
| 9 | CNG/multi-fuel tracker, mechanic price-checker, resale predictor, WhatsApp bot | Nice narrative additions, genuinely lowest priority — only mention as "roadmap" in your pitch if you don't build them (Section 11 gives you exact wording for this). |

> **Original idea validation:** the core concept — multimodal AI + receipt OCR + predictive maintenance — is a strong, well-scoped hackathon idea. This document doesn't change *what* you're building, only *how efficiently* you get there with the tool you actually have access to tomorrow.

### 5.3 Architecture (kept intentionally simple — 4 layers)

```
┌─────────────────────────────┐
│  Layer 1 — Streamlit UI      │  app.py: pages for Scan Receipt,
│                               │  Dashboard, Logbook, Maintenance
└──────────────┬────────────────┘
               │
┌──────────────▼────────────────┐
│  Layer 2 — Python Logic        │  analytics.py, maintenance.py
│  (calculations, orchestration) │
└──────────────┬────────────────┘
               │
┌──────────────▼────────────────┐
│  Layer 3 — AI Layer             │  receipt_scanner.py → Qwen-VL
│  (Alibaba Cloud DashScope API)  │  maintenance.py → Qwen-Max
└──────────────┬────────────────┘
               │
┌──────────────▼────────────────┐
│  Layer 4 — Data                 │  database.py → SQLite
│                                  │  (safarsync.db, auto-created)
└─────────────────────────────────┘
```

### 5.4 File structure (what you'll ask Qoder to create, in order)

```
safarsync-ai/
├── .env                  ← your DashScope API key — NEVER commit this to Git
├── .gitignore             ← must contain .env, venv/, __pycache__/, *.db
├── requirements.txt
├── database.py            ← Layer 4 — all read/write functions
├── receipt_scanner.py     ← Layer 3 — Qwen-VL OCR engine (build first, it's the core differentiator)
├── analytics.py           ← Layer 2 — fuel calculations
├── maintenance.py         ← Layer 2/3 — maintenance advisor
├── pdf_report.py           ← Layer 2 — PDF logbook export
├── app.py                  ← Layer 1 — the full Streamlit app, built last, ties everything together
└── safarsync.db             ← auto-created on first run — do not create manually
```

---

## 6. Account & Environment Setup — Step by Step

Do this before opening Qoder to build anything (most of it should already be done from Section 4).

### Step 1 — Confirm Python

```bash
python --version
```
Expect `Python 3.11` or higher. If it fails, reinstall from python.org and re-check "Add to PATH."

### Step 2 — Create the project and a virtual environment

```bash
mkdir safarsync-ai
cd safarsync-ai
python -m venv venv
```

Activate it:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

You'll know it worked because your terminal prompt now starts with `(venv)`. **Do this every time you reopen a terminal** — it's the single most common "why isn't my package installed" bug beginners hit.

### Step 3 — Open the folder in Qoder

Open Qoder → File → Open Folder → select `safarsync-ai`. Confirm the Qwen coding model is selected (Section 3's checklist).

### Step 4 — Create `.env` and `.gitignore` by hand (don't let Qoder touch secrets)

`.env`:
```
DASHSCOPE_API_KEY=your_key_here
```

`.gitignore`:
```
.env
venv/
__pycache__/
*.db
*.pyc
```

> **⚠️ Security note from your DevOps background, applied correctly:** commit `.gitignore` *before* your first commit that includes `.env`, or the key ends up in your Git history permanently even if you delete the file later. If you ever paste your key into a Qoder chat by accident, rotate it immediately in the DashScope console.

### Step 5 — Install dependencies

Create `requirements.txt`:
```
streamlit
openai
pandas
plotly
fpdf2
pillow
python-dotenv
```

Then:
```bash
pip install -r requirements.txt
```

> Why `openai`, not an Alibaba-specific package? Qwen models expose an **OpenAI-compatible API** — you use the standard `openai` Python library and just point it at Alibaba's endpoint (`https://dashscope-intl.aliyuncs.com/compatible-mode/v1` for the international DashScope endpoint — confirm the exact URL in your DashScope console under API docs, since Alibaba occasionally adjusts regional endpoints). This is exactly the kind of two-line change the hackathon materials point to as Qwen's beginner-friendliness.

### Step 6 (Stretch only) — Google Maps key

Only do this if/when you start Feature 6. Google Cloud Console → new project → enable **Distance Matrix API** → create credentials → API key → add `GOOGLE_MAPS_API_KEY=...` to `.env`.

---

## 7. The Qoder Quest Workflow — Master Build Plan

**How to use each block below:** open Qoder's **Quest** window, paste the entire prompt exactly as written, let it run to completion, then work through the verification checklist before moving to the next file. Do not start the next Quest until the current one is verified — a broken `database.py` breaks every file after it.

### 7.1 Quest 1 — `database.py` (build this first — everything depends on it)

```
Create a file called database.py for a Python + SQLite project called SafarSync AI.

Requirements:
1. Use Python's built-in sqlite3 module only — no ORM.
2. Create a function init_db() that connects to "safarsync.db" (creating it if it
   doesn't exist) and creates two tables if they don't already exist:

   TABLE vehicles:
     - id INTEGER PRIMARY KEY AUTOINCREMENT
     - name TEXT NOT NULL (e.g. "Honda Civic 2019")
     - registration_number TEXT
     - created_at TEXT (ISO timestamp, default to current time)

   TABLE records:
     - id INTEGER PRIMARY KEY AUTOINCREMENT
     - vehicle_id INTEGER (foreign key referencing vehicles.id)
     - record_type TEXT (one of: "fuel", "maintenance", "insurance")
     - date TEXT (ISO date, e.g. "2026-08-21")
     - amount_pkr REAL
     - liters REAL (nullable — only relevant for fuel records)
     - odometer_km INTEGER (nullable)
     - description TEXT (services performed, or notes)
     - vendor_name TEXT (mechanic/station/company name)
     - raw_ocr_json TEXT (nullable — stores the original AI extraction for audit)
     - created_at TEXT (ISO timestamp, default to current time)

3. Write these functions, each with a clear docstring, type hints, and try/except
   error handling that raises a clear, custom-message exception rather than
   letting sqlite3 errors leak unformatted to the caller:
   - add_vehicle(name: str, registration_number: str = "") -> int (returns new vehicle id)
   - get_vehicles() -> list[dict]
   - add_record(vehicle_id, record_type, date, amount_pkr, liters, odometer_km,
     description, vendor_name, raw_ocr_json) -> int (returns new record id)
   - get_records(vehicle_id: int, record_type: str = None) -> list[dict]
     (record_type optional filter)
   - get_record_by_id(record_id: int) -> dict | None
   - delete_record(record_id: int) -> bool

4. Every function that returns rows must return them as a list of plain Python
   dicts (use sqlite3.Row and dict(row) — not raw tuples), so other files can use
   record["amount_pkr"] instead of record[3].
5. At the bottom of the file, add:
   if __name__ == "__main__":
       init_db()
       print("Database initialized successfully!")
6. Add inline comments explaining each SQL statement in plain English, since I am
   a first-semester student and have not used SQLite before — assume no prior
   SQLite knowledge when writing comments.

Do not add any Streamlit, Qwen API, or UI code to this file — it is data-layer
only.
```

**Verify before moving on:**
```bash
python database.py
```
Expect to see `Database initialized successfully!` and a new `safarsync.db` file appear in your folder. Open it with any SQLite viewer (or ask Qoder in Agent Mode: *"write me a 5-line script to print all tables in safarsync.db"*) and confirm both tables exist with the right columns.

### 7.2 Quest 2 — `receipt_scanner.py` (your core differentiator — build this second)

```
Create a file called receipt_scanner.py that uses Alibaba Cloud's Qwen-VL vision
model to extract structured data from a photo of a vehicle-related receipt
(fuel receipt, mechanic bill, or insurance document), which may be handwritten
in Urdu, printed in English, or a mix of both.

Requirements:
1. Use the `openai` Python library, pointed at Alibaba Cloud's DashScope
   OpenAI-compatible endpoint. Load the API key from the DASHSCOPE_API_KEY
   environment variable using python-dotenv — never hard-code the key.
2. Use the model name "qwen-vl-plus".
3. Write a function:
   scan_receipt(image_path: str) -> dict
   that:
   a. Opens the image, converts it to base64.
   b. Sends it to Qwen-VL with a system/user prompt instructing the model to
      act as a receipt-reading assistant for Pakistani vehicle expense
      receipts, and to return ONLY a JSON object (no prose, no markdown code
      fences) with exactly these keys:
      {
        "record_type": "fuel" | "maintenance" | "insurance" | "unknown",
        "date": "YYYY-MM-DD or null if unreadable",
        "amount_pkr": number or null,
        "liters": number or null,
        "odometer_km": integer or null,
        "description": "short description of services/items, or null",
        "vendor_name": "station or mechanic or company name, or null",
        "confidence": "high" | "medium" | "low"
      }
      The prompt must explicitly tell the model that receipts may be
      handwritten, in Urdu, blurry, or low-light, and to make its best
      reasonable extraction rather than refusing, setting fields to null only
      when genuinely unreadable, and to set "confidence" to "low" whenever it
      had to guess.
   c. Parses the model's response as JSON. If parsing fails (e.g. the model
      added extra text), attempt to extract the first {...} JSON block with a
      regex before giving up.
   d. Returns the parsed dict, with the raw model response also included
      under a "raw_response" key for debugging/audit purposes.
   e. Wraps the whole API call in a try/except that catches network errors,
      auth errors, and JSON parse errors separately, and returns a dict like
      {"error": "<clear human-readable message>"} instead of crashing, so the
      calling Streamlit page can show the user a friendly error instead of a
      stack trace.
4. Add a __main__ block that, if run directly, takes a file path from
   sys.argv[1] and pretty-prints the result — this is how I will test this
   file standalone before wiring it into the app.
5. Add clear comments explaining what base64 encoding is and why it's needed,
   since this is a new concept for me.
```

**Verify before moving on:**
1. Take 1 real photo of any receipt (or any printed/handwritten note with a date and number on it, if you don't have a real receipt handy yet).
2. Run:
```bash
python receipt_scanner.py path/to/your/photo.jpg
```
3. Confirm you get back a clean JSON dict with plausible values — not a stack trace, not raw unparsed text.
4. **If you get an auth error:** re-check `.env` has no extra spaces around your key and that you restarted the terminal after creating `.env`.
5. **If JSON parsing fails often:** go into Agent Mode (not Quest) and ask Qoder to tighten the prompt inside `scan_receipt()` to more strongly enforce JSON-only output — this is a one-line prompt-engineering fix, not a rebuild.

### 7.3 Quest 3 — `analytics.py`

```
Create a file called analytics.py for SafarSync AI. It imports the get_records
function from database.py and computes fuel/expense analytics for a given
vehicle_id.

Requirements:
1. Function calculate_fuel_efficiency(vehicle_id: int) -> list[dict]
   For all "fuel" records of a vehicle sorted by date/odometer ascending,
   compute km/L between each consecutive pair of fuel records as:
   (odometer_km_current - odometer_km_previous) / liters_current
   Skip any pair where odometer_km is missing on either record, or where the
   distance is zero or negative (bad data) — do not crash, just skip and note
   it was skipped in a returned "warnings" list.
2. Function monthly_spending_summary(vehicle_id: int) -> dict
   Returns total amount_pkr grouped by month (YYYY-MM) and by record_type,
   using pandas. Return as a dict of DataFrame.to_dict('records') style, ready
   for a Plotly chart.
3. Function total_cost_per_km(vehicle_id: int) -> float | None
   Total spending across all record types divided by total distance driven
   (max odometer_km - min odometer_km across all records for that vehicle).
   Return None with no error if there isn't enough data yet (fewer than 2
   odometer readings) — never divide by zero.
4. All functions must handle the case of zero records for a vehicle gracefully
   (return empty lists/dicts, not exceptions) — a brand-new vehicle with no
   data yet must not break the dashboard.
5. Add a short comment above each function explaining what it calculates and
   why, in plain English, for someone new to pandas.
```

**Verify before moving on:** In a Python shell or a throwaway test script, add 2–3 fake fuel records via `database.py`'s `add_record()` with different odometer readings and dates, then call each analytics function and confirm the numbers are arithmetically correct by hand.

### 7.4 Quest 4 — `maintenance.py`

```
Create a file called maintenance.py for SafarSync AI.

Requirements:
1. A constant dict MAINTENANCE_SCHEDULE_KM mapping common maintenance types to
   recommended intervals in km, e.g.:
   {"oil_change": 5000, "air_filter": 10000, "brake_check": 15000,
    "tire_rotation": 8000}
2. Function check_due_maintenance(vehicle_id: int) -> list[dict]
   Using get_records() from database.py, find the vehicle's most recent
   odometer_km, and for each item in MAINTENANCE_SCHEDULE_KM, find the last
   maintenance record whose description mentions that type (simple case-
   insensitive substring match), and compute km since that service. If
   km_since >= the interval, or if there is no record of that service at all,
   mark it as due. Return a list of dicts like:
   {"type": "oil_change", "km_since_last": 5200, "interval": 5000, "status": "due"}
3. Function get_ai_maintenance_advice(vehicle_id: int) -> str
   Takes the output of check_due_maintenance() plus the vehicle's recent fuel
   efficiency (import from analytics.py), and sends a short, clearly-labeled
   summary of both to Qwen-Max (model name "qwen-max") via the same
   openai-compatible DashScope client pattern used in receipt_scanner.py,
   asking it to write 2-4 friendly, plain-language sentences of maintenance
   advice for a Pakistani vehicle owner — practical, not alarmist, and
   mentioning specific numbers from the data it was given. Wrap the API call
   in the same try/except pattern as receipt_scanner.py, returning a safe
   fallback string like "AI advisor unavailable right now — here is your raw
   maintenance status instead." if the call fails, so the app never crashes
   because of this feature.
4. Reuse the DashScope client setup pattern (env var, openai-compatible
   endpoint) exactly as done in receipt_scanner.py, don't invent a new one.
```

**Verify before moving on:** call `check_due_maintenance()` with your test data from 7.3 and confirm the due/not-due logic matches your manual expectation. Then call `get_ai_maintenance_advice()` and confirm you get a real, sensible sentence back from Qwen-Max — not an error string.

### 7.5 Quest 5 — `pdf_report.py`

```
Create a file called pdf_report.py for SafarSync AI using the fpdf2 library.

Requirements:
1. Function generate_logbook_pdf(vehicle_id: int, output_path: str) -> str
   Fetches vehicle info and all records for that vehicle via database.py,
   and generates a clean, professional single-column PDF report containing:
   - A header with the vehicle name, registration number, and generation date
   - A table of all records (date, type, amount PKR, description, vendor)
     sorted by date descending
   - A summary section at the bottom: total spent, record count, date range
2. Keep formatting simple and readable (default fpdf2 fonts are fine) — this
   does not need custom branding, just needs to look organized and be usable
   as a document a car buyer or insurer could review.
3. Return the output_path on success. Wrap file-writing in a try/except and
   raise a clear error message on failure (e.g. invalid path, no records).
4. Handle the zero-records case by still generating a valid PDF that says
   "No records yet for this vehicle" instead of crashing or producing a blank
   file.
```

**Verify before moving on:** run it against your test vehicle and open the resulting PDF — check it's readable and the totals match what you'd calculate by hand.

### 7.6 Quest 6 — `app.py` (build this last — it ties everything together)

```
Create app.py — the main Streamlit application for SafarSync AI, tying
together database.py, receipt_scanner.py, analytics.py, maintenance.py, and
pdf_report.py, all of which already exist in this project and should be
imported, not rewritten.

Requirements:
1. Call init_db() from database.py once at the top of the script (outside any
   function) so the database always exists before any page runs.
2. Use st.set_page_config with page_title "SafarSync AI" and a car emoji icon.
3. Build a sidebar navigation (st.sidebar.radio or st.sidebar.selectbox) with
   these pages: "Dashboard", "Scan Receipt", "Vehicle Logbook", "Maintenance",
   "Manage Vehicles".
4. On first run (no vehicles in the database), show only a friendly
   "Manage Vehicles" prompt to add a first vehicle before unlocking other
   pages — do not let the app show broken empty charts before any data
   exists.
5. "Manage Vehicles" page: a form to add a new vehicle (name, registration
   number) using add_vehicle() from database.py, and a selectbox at the top
   of the sidebar (visible on every page) to choose which vehicle is
   "active" — store the active vehicle_id in st.session_state so every other
   page uses it.
6. "Scan Receipt" page: st.camera_input or st.file_uploader for a receipt
   photo, saves it to a temp path, calls scan_receipt() from
   receipt_scanner.py, shows the extracted fields to the user in an editable
   form (st.form with pre-filled values from the AI extraction, all fields
   editable in case the AI got something wrong — this is the human-in-the-loop
   review step), and on submit calls add_record() from database.py, storing
   the original AI JSON in raw_ocr_json. Show a clear st.success message
   after saving, and show a clear st.error message (not a crash) if
   scan_receipt() returns an "error" key.
7. "Dashboard" page: uses analytics.py functions to show: a Plotly line chart
   of km/L over time, a Plotly bar chart of monthly spending by category, and
   st.metric widgets for total spent and cost per km. Handle the "not enough
   data yet" case with a friendly message, not a broken chart.
8. "Maintenance" page: calls check_due_maintenance() and
   get_ai_maintenance_advice() from maintenance.py, shows due items in a
   clear table (color-code or icon-flag anything overdue), and shows the AI
   advice text in an st.info box. Include a "Download Full Logbook PDF"
   button that calls generate_logbook_pdf() from pdf_report.py and offers it
   via st.download_button.
9. "Vehicle Logbook" page: a searchable/filterable st.dataframe of all
   records for the active vehicle (filter by record_type using
   st.multiselect), sorted by date descending.
10. Wrap every call to an external file's function in try/except at the
    Streamlit layer too, so an unexpected error anywhere shows a friendly
    st.error message instead of crashing the whole app during a live demo.
11. Add a short st.caption at the bottom of every page: "Powered by Qwen-VL
    and Qwen-Max on Alibaba Cloud" — this should be visible in every demo
    screenshot.
```

**Verify before moving on — full end-to-end test:**
1. `streamlit run app.py`
2. Add a real vehicle.
3. Scan a real receipt photo end to end — extraction → review form → save.
4. Confirm the record shows up in the Logbook page.
5. Add 2–3 more records so Dashboard and Maintenance have real data.
6. Check every page for a full minute each, deliberately trying to break it (empty fields, no vehicle selected, etc.) — see Section 8 for the full QA pass.

---

## 8. Bug-Free Checklist (run this before you consider the Core Build "done")

Work through this literally, ticking each box. This is what "production-grade" means in practice for a hackathon judge who will click around your app live.

- [ ] Fresh clone/fresh `safarsync.db` deleted and app restarted from zero — confirm "Manage Vehicles" prompt appears cleanly, no crash
- [ ] Add a vehicle with only required fields — confirm it saves
- [ ] Scan a clear, well-lit printed receipt — confirm accurate extraction
- [ ] Scan a blurry or handwritten receipt — confirm it still returns *something* usable and doesn't crash (Qwen-VL should degrade gracefully; if it returns nulls, the review form must still be usable)
- [ ] Manually edit a wrong field in the review form before saving — confirm the edited value, not the AI's, is what gets saved
- [ ] Switch between two vehicles using the sidebar selector — confirm each page correctly shows only that vehicle's data
- [ ] View Dashboard with only 1 fuel record — confirm no divide-by-zero crash on km/L
- [ ] View Maintenance with zero maintenance records — confirm it shows "all due" or equivalent instead of crashing
- [ ] Download the PDF logbook — confirm it opens and totals are correct
- [ ] Turn off your internet and try Scan Receipt — confirm you get a friendly error message, not a frozen app or raw traceback (this exact scenario is your Section 12 emergency backup plan — test it now, not live)
- [ ] Restart the whole app one final time and repeat the "scan → save → view on dashboard" flow exactly as you will during the live demo, timing yourself

**If any box fails:** go into Qoder **Agent Mode** (not Quest) and describe exactly what broke and what you expected instead. Agent Mode's checkpoint review means you can see precisely what it changes before accepting — use this for every bug fix so you understand your own codebase.

---

## 9. Deployment on Alibaba Cloud (do this only after Section 8 is fully checked)

Your AZ-900 knowledge maps directly here — same core concepts (virtual machines, security groups/firewall rules, SSH access), different console.

1. **Alibaba Cloud Console → ECS (Elastic Compute Service) → Create Instance.** Choose the smallest/cheapest instance type available under your hackathon credits (this is exactly analogous to an Azure VM size — you already know how to reason about this trade-off from AZ-900).
2. Choose an **Ubuntu** image (simplest for Python/Streamlit deployment).
3. In the **Security Group** settings, open inbound port **8501** (Streamlit's default port) in addition to port 22 (SSH) — this is the same mental model as an NSG rule in Azure.
4. SSH into the instance, install Python 3.11+, `git clone` your repository, recreate your `venv`, `pip install -r requirements.txt`, recreate `.env` on the server directly (never via `git push` — the `.gitignore` from Section 6 should already be keeping it out of your repo).
5. Run `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`.
6. Visit `http://<your-ecs-public-ip>:8501` from your own laptop to confirm it's live before demo day.
7. Keep this URL written down somewhere you can read it instantly during your pitch — judges being able to open your app on their own device is a strong signal.

> If ECS setup eats into time you need for polish and rehearsal, it is completely acceptable to demo locally (`streamlit run app.py` on your laptop, screen-shared) and mention the deployment plan verbally. A flawless local demo beats a live deployment that adds a new point of failure at hour 30.

---

## 10. Demo & Pitch Strategy

### 10.1 5-minute structure

| Time | Segment |
|---|---|
| 0:00–0:30 | Hook: "Pakistan has 28 million registered vehicles, and almost none of them have a digital expense record." |
| 0:30–1:15 | Problem, stated concretely — handwritten bills, no fraud protection, no maintenance history, resale value lost |
| 1:15–3:15 | **Live demo** — scan a real receipt on stage, show the extraction, show it land on the dashboard |
| 3:15–4:00 | Why Alibaba Cloud — name Qwen-VL, Qwen-Max, and Qoder explicitly, and say *why* (multimodal + Urdu handling + fast agentic build) |
| 4:00–4:40 | Business model — freemium for individual owners, B2B data licensing to insurers/resale platforms |
| 4:40–5:00 | Close with the impact number again and a confident final line |

### 10.2 Exact language for the Alibaba Cloud section (use this, it directly targets the judging weight in Section 1.2)

> "SafarSync is built on Alibaba Cloud's Qwen-VL for receipt vision, because it reads Urdu and English handwriting in the same image — that's the actual, local problem we needed solved. We also built the entire application inside Qoder, Alibaba's agentic IDE, which let us go from specification to a fully tested, working product in the time this hackathon gave us."

### 10.3 Prepared answers to likely judge questions

| Question | Answer |
|---|---|
| "How is this different from a spreadsheet?" | "A spreadsheet requires you to type every number yourself. SafarSync reads a photo of a handwritten bill and does it for you — that's the entire adoption barrier removed." |
| "How will you make money?" | "Freemium for individual users, and a B2B data-licensing model — insurers and resale platforms will pay for verified vehicle maintenance history, the same way Carfax works in other markets." |
| "What if the AI misreads a receipt?" | "Every extraction goes through a human-in-the-loop review step before it's saved — the user sees and can correct every field. We never silently trust the model." |
| "Why should this win?" | "Handwritten Urdu receipts, CNG-heavy fuel markets, and a resale culture where paper trails matter — this is a Pakistan-specific problem solved with a Pakistan-relevant model choice." |
| "You're a first-semester student — can you actually build this?" | "I already have — you're looking at it running live. I have a year of DevOps experience and basic LLM knowledge going in; Qoder's agentic build workflow let me focus on getting the product and the AI prompts right, and I own and can explain every line of the codebase." |

---

## 11. Final Checklists

### 11.1 Night Before Demo Day

- [ ] All Section 8 QA boxes still pass after any last-minute changes
- [ ] 3 real demo receipt photos ready (fuel, mechanic, insurance), tested and known-good
- [ ] At least 2 weeks of realistic sample data pre-loaded so Dashboard/Maintenance don't look empty
- [ ] Pitch rehearsed out loud, timed, at least 3 times — must fit in 5 minutes
- [ ] Live deployment URL (if used) tested from a phone on mobile data, not just your dev laptop's WiFi
- [ ] A **backup screen recording** of a full successful demo, saved locally on your phone

### 11.2 Day-of

- [ ] Laptop fully charged, charger packed
- [ ] `venv` activated, app running and tested one more time before judges arrive
- [ ] Sample data confirmed present
- [ ] Backup screen recording accessible in 2 taps if live demo fails

### 11.3 Emergency backups

| Problem | What to do |
|---|---|
| Qwen API unreachable | You already tested this in Section 8 — the app shows a friendly error, not a crash. Have one pre-scanned result saved to narrate over: "Here's a result from our earlier testing." |
| App crashes mid-demo | Immediately switch to the backup screen recording — don't debug live in front of judges |
| A judge asks something you don't know | "Great question — that's on our roadmap. Here's how I'd approach it: ..." then give a genuinely reasoned answer. Never just say "I don't know" and stop. |
| Another team has a similar idea | "We're aware similar tools exist globally, but none target Pakistan specifically — handwritten Urdu receipts and a CNG-heavy fuel market are our localization moat." |

---

## 12. Key Resources

| Resource | Link |
|---|---|
| Discord (schedule, deadlines, mentor help) | discord.gg/xfyUK45Ka |
| Webinar 1 recording/page | resource.alibabacloud.com/activity/webinar/detail.html?id=LS20260009 |
| Webinar 2 recording/page | resource.alibabacloud.com/activity/webinar/detail.html?id=LS20260010 |
| DashScope / Qwen API docs | dashscope.aliyuncs.com/api-doc |
| Alibaba Cloud console | alibabacloud.com |
| Streamlit docs | docs.streamlit.io |
| Plotly Python docs | plotly.com/python |
| fpdf2 docs | pypi.org/project/fpdf2 |

---

*SafarSync AI — Qoder Build Playbook. Written for Afraz Hassan, Alibaba Cloud AI Hackathon 2026. Good luck — you have the idea, the plan, and now a build workflow matched to exactly where you're starting from. Go build it.*
