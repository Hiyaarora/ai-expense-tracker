# AI Expense Tracker — Complete Architecture & Code Walkthrough

> Read this top-to-bottom to fully understand the project. Sections build on each other.

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [Architecture & Data Flow](#2-architecture--data-flow)
3. [Tech Stack — Every Choice Explained](#3-tech-stack--every-choice-explained)
4. [Code Walkthrough — File by File](#4-code-walkthrough--file-by-file)
5. [Key Concepts](#5-key-concepts-you-need-to-know)
6. [End-to-End Flows](#6-end-to-end-flows)
7. [Interview Questions You'll Get](#7-interview-questions-youll-get)

---

# 1. The Big Picture

## What Are We Building?

A personal expense tracker app, but with three AI-powered superpowers:

1. **Natural language input** — Type "I spent 1000 on zomato food" → AI extracts title, amount, category
2. **AI insights** — AI writes a paragraph analyzing your spending patterns
3. **AI chatbot with tool use** — Ask "How much on food?" or "Delete that Uber expense" — AI calls the right database function

Plus: multi-currency support, monthly/yearly summaries, charts, edit/delete buttons.

## Why This Project?

It demonstrates **three modern AI engineering patterns** that real AI companies use every day:

| Pattern | Where in our app | Why it matters |
|---------|-----------------|----------------|
| **LLM-as-Classifier** | `/expenses/smart` picks category from title | Spam filters, content moderation, ticket routing |
| **Structured Data Extraction** | `/expenses/natural` parses sentence to JSON | Email→calendar, receipt OCR, document parsing |
| **Tool Use / Function Calling** | `/chat` lets AI read+write the database | AI agents (Cursor, Notion AI, ChatGPT plugins) |

If you understand these three, you understand 80% of what AI Product Engineers build.

---

# 2. Architecture & Data Flow

## High-Level View

```
┌─────────────────────┐
│   Web Browser       │  (You)
└──────────┬──────────┘
           │ HTTP
           ▼
┌─────────────────────────────────┐
│   Streamlit Frontend            │  Port 8501
│   (Python UI framework)         │
│                                 │
│   ┌─────────────────────┐       │
│   │ frontend/app.py     │       │  Dashboard
│   │ frontend/pages/...  │       │  4 other pages
│   └──────────┬──────────┘       │
│              │ httpx (HTTP)     │
└──────────────┼──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   FastAPI Backend               │  Port 8000
│   (Python web framework)        │
│                                 │
│   ┌──────────────────────────┐  │
│   │ main.py (entry point)    │  │
│   │  ├─ routes/expenses.py   │  │
│   │  ├─ routes/salary.py     │  │
│   │  ├─ routes/settings.py   │  │
│   │  └─ routes/ai.py ─────┐  │  │
│   └──────────────────────┼──┘  │
│                          │     │
│   ┌──────────────────────▼──┐  │
│   │ ai/llm_client.py        │  │  Wraps Groq SDK
│   │ ai/tools.py             │  │  8 functions for AI
│   │ ai/prompts.py           │  │  System prompts
│   └─────────┬───────────────┘  │
│             │ HTTP              │
│             ▼                   │
│   ┌──────────────────────┐     │
│   │ services/currency.py │     │  Exchange rates
│   └──────────────────────┘     │
└──────────┬──────────────────────┘
           │
           ▼ async/sync
┌─────────────────────┐    ┌──────────────────────┐
│  MongoDB Atlas      │    │  Groq API            │
│  (cloud database)   │    │  (Llama / GPT-OSS)   │
└─────────────────────┘    └──────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │ frankfurter.dev      │
                           │ (exchange rates)     │
                           └──────────────────────┘
```

## Why Split Into 2 Servers (Backend + Frontend)?

**You could** run everything in one Streamlit app. But splitting gives you:

1. **Separation of concerns** — UI changes don't touch business logic
2. **Reusability** — Tomorrow you can add a mobile app, a WhatsApp bot, or another website — all hitting the same backend
3. **Better testability** — Test the API with curl or Postman, no need for a browser
4. **Standard architecture** — This is how every real production app is built

This is called a **client-server architecture**, the foundation of modern web apps.

---

# 3. Tech Stack — Every Choice Explained

## Backend Framework: FastAPI

**What it is:** A Python library that lets you turn Python functions into web API endpoints with one decorator (`@router.get`).

**Why FastAPI?**

| Alternative | Why we didn't pick it |
|-------------|----------------------|
| **Flask** | Older, no built-in async, no auto-generated docs, no type validation |
| **Django** | Massive, designed for full websites with HTML templates — overkill for an API |
| **Express (Node.js)** | Would mean learning JavaScript on top of Python |

**FastAPI's superpowers:**
1. **Automatic Swagger docs** — Visit `http://localhost:8000/docs` → interactive UI for every endpoint, free
2. **Pydantic validation** — Define a model once (`class Expense`), FastAPI validates incoming JSON automatically
3. **Async-first** — Modern Python, scales well
4. **Type hints become documentation** — Your code IS the spec

Example in our code:
```python
@router.post("/expenses")
async def add_expense(expense: Expense):
    # FastAPI already validated `expense` matches the Expense schema
    # If user sends bad JSON, they get a 422 error automatically
    ...
```

## Database: MongoDB (via Motor for async, PyMongo for sync)

**What it is:** A NoSQL database — stores documents (like JSON) instead of tables with strict schemas.

**Why MongoDB over PostgreSQL/MySQL?**

| For our app | MongoDB | PostgreSQL |
|------------|---------|-----------|
| Adding optional fields (e.g., `original_currency`) | Just add it, no migration | Requires `ALTER TABLE` |
| JSON-shaped data (expenses) | Native fit | Needs JSONB columns |
| Schema evolution during dev | Flexible | Painful |
| Complex joins / transactions | Limited | Best in class |

**Trade-off:** MongoDB is faster to build with for a prototype, but less strict — you have to handle data consistency in code, not in the DB.

For our personal app where we keep iterating on the schema (adding `currency`, `original_amount`, etc.), MongoDB wins.

**Motor vs PyMongo:**
- **Motor** = async MongoDB client. We use it in FastAPI endpoints (so the server can handle multiple requests at once).
- **PyMongo** = sync MongoDB client. We use it in `ai/tools.py` because Groq's SDK is synchronous and we need to call DB ops from a sync context.

## AI Provider: Groq (Llama / GPT-OSS-120B)

**What it is:** A startup that runs open-source AI models on custom hardware. Free API tier, very fast.

**Why Groq and not Claude/OpenAI/Gemini?**

| Provider | Pros | Cons |
|---------|------|------|
| **Claude (Anthropic)** | Highest quality | Costs money |
| **OpenAI (GPT-4)** | Industry standard | Costs money |
| **Gemini (Google)** | Free, well-known | Your work-account quota was broken |
| **Groq (Llama)** | Free, super fast, **open-source models** = important AI engineering skill | Slightly less polished than Claude |

We picked Groq specifically because:
1. **Free** — Generous limits, no payment
2. **Llama is the most-used open-source model** in industry — knowing it helps your resume
3. **Speed** — Groq is the fastest LLM API available
4. **OpenAI-compatible API** — Same code shape as OpenAI/most others, so the pattern transfers

The specific model `openai/gpt-oss-120b` is OpenAI's open-weights model, served by Groq — best for **tool calling**.

## Frontend: Streamlit

**What it is:** A Python framework that turns Python scripts into web UIs. Run `streamlit run app.py` → get a website. No HTML/CSS/JS.

**Why Streamlit and not React?**

| Alternative | Pros | Cons (for you) |
|-------------|------|----------------|
| **React + Next.js** | Industry-standard UI library | Requires JavaScript, TypeScript, npm, build tools |
| **Plain HTML + CSS** | Simple | No interactivity without JS |
| **Streamlit** | **Pure Python**, ready in minutes | Less customizable than React |

For a **data/AI portfolio project**, Streamlit is the right choice because:
1. You're a Python beginner — sticking with one language matters
2. Data scientists use Streamlit at companies (Shopify, Uber, Snowflake) — it's a real industry tool
3. Built-in widgets for charts, forms, chat — perfect for our use case

If you were applying for a frontend role, you'd use React. For AI Product Engineering, Streamlit is fine.

## Exchange Rate API: Frankfurter.dev

**Why this and not openexchangerates.org / fixer.io?**
- **Frankfurter is free with no API key** — sign up not required
- Other free APIs require keys + signup
- Sourced from the European Central Bank — reliable

## Charts: Plotly

**Why Plotly over Matplotlib/Seaborn?**
- Plotly creates **interactive** HTML charts (hover, zoom, click)
- Streamlit integrates Plotly natively (`st.plotly_chart()`)
- Matplotlib creates static images — fine for reports, bad for web UIs

## Deployment: Railway + Streamlit Cloud (planned)

**Railway** — for the FastAPI backend. Free tier, one-click deploy from GitHub.
**Streamlit Cloud** — for the frontend. Free hosting specifically for Streamlit apps.

We split them because each platform is optimized for one role.

---

# 4. Code Walkthrough — File by File

## `main.py` — The Entry Point

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import expenses, salary, ai, settings

app = FastAPI(title="AI Expense Tracker API")

# CORS = Cross-Origin Resource Sharing
# Lets Streamlit (port 8501) call our backend (port 8000)
# Without this, browsers block the request
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # In prod, you'd list specific URLs
    allow_methods=["*"],
    allow_headers=["*"],
)

# "Plug in" our 4 route modules
app.include_router(expenses.router)
app.include_router(salary.router)
app.include_router(ai.router)
app.include_router(settings.router)

@app.get("/")
async def read_root():
    return {"message": "AI Expense Tracker API is running!"}
```

**Key concepts:**
- `FastAPI()` creates the app
- **Middleware** is code that runs for every request (CORS, logging, auth would all be middleware)
- `include_router()` is FastAPI's way of organizing endpoints into multiple files

## `database.py` — The MongoDB Connection

```python
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()                              # Reads .env file
MONGO_URL = os.getenv("MONGO_URL")         # Loads the connection string

client = AsyncIOMotorClient(MONGO_URL)     # One connection, reused
db = client.expense_tracker                # Pick the database
expense_collection = db.expenses           # Pick the "table"
salary_collection = db.salaries
settings_collection = db.settings
```

**Key concept:** Open ONE connection at app startup, share it across all endpoints. Opening a new connection per request would be terrible for performance.

## `models.py` — Pydantic Models

```python
from pydantic import BaseModel
from typing import Optional, List

class Expense(BaseModel):
    title: str                      # Required
    amount: float
    category: str
    currency: str
    date: Optional[str] = None      # Optional, default None
```

**Why Pydantic?**
- Validates incoming JSON automatically
- If user sends `{"title": "Coffee"}` without amount → FastAPI returns 422 error
- If `amount` is a string → FastAPI tries to coerce or rejects
- Auto-generates API docs

## `routes/expenses.py` — Expense CRUD

This file contains all expense-related endpoints. The pattern:

```python
@router.post("/expenses")                  # ① Decorator: HTTP method + URL
async def add_expense(expense: Expense):   # ② Function: receives validated data
    # ③ Business logic — convert currency, build doc
    base_currency = await get_base_currency()
    amount_fields = build_amount_fields(
        expense.amount, expense.currency.upper(), base_currency
    )

    # ④ Build the MongoDB document
    expense_dict = {
        "title": expense.title,
        "category": expense.category,
        "date": date_str,
        **amount_fields,                   # spreads currency + amount fields
    }

    # ⑤ Save to DB
    result = await expense_collection.insert_one(expense_dict)

    # ⑥ Return JSON response — FastAPI serializes automatically
    return {
        "message": "Expense added successfully!",
        "expense": {"id": str(result.inserted_id), **amount_fields},
    }
```

**Key concept:** Every REST endpoint follows this pattern:
1. **Define HTTP method + URL** (`@router.post("/expenses")`)
2. **Receive + validate input** (Pydantic model)
3. **Do business logic** (calculations, currency conversion, etc.)
4. **Persist to DB** (insert/update/delete)
5. **Return response**

## `routes/ai.py` — The AI Endpoints

```python
@router.post("/chat")
def chat_endpoint(req: ChatRequest):
    """Chat with the AI assistant. Gemini decides which tools to call."""
    try:
        history_dicts = [m.dict() for m in (req.history or [])]
        reply = chat_with_tools(req.message, history_dicts)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
```

**Why `def` (not `async def`)?** Because `chat_with_tools()` is synchronous (uses sync Groq SDK + sync PyMongo). FastAPI runs sync functions in a threadpool automatically — no problem.

## `ai/prompts.py` — System Prompts

These are the "instructions" we give the AI. The most important file for AI quality.

```python
CHAT_SYSTEM_PROMPT = """You are an AI assistant for a personal expense tracker app.
You help the user understand and manage their expenses through natural conversation.

You have tools that let you:
- Read expenses (by month, category, or all)
- Add new expenses
- Update existing expenses
- Delete expenses
- View salary and savings

Rules:
- Always use INR (Rs.) as currency
- When the user asks about their data, ALWAYS use the appropriate tool. Never guess numbers.
- ...
"""
```

**Key concept:** Prompt engineering = writing these system prompts well. The difference between a good and bad AI app often comes down to these strings.

Tips that we used:
1. **Be specific** — Tell AI exactly what tools it has
2. **Give rules** — "Never guess numbers" prevents hallucination
3. **Show examples** — In `PARSE_EXPENSE_PROMPT` we include 3 examples → AI follows the pattern

## `ai/tools.py` — Tools the AI Can Call

```python
def add_expense(title: str, amount: float, category: str) -> dict:
    """Adds a new expense to the database for today.

    Args:
        title: Short description like 'Zomato dinner' or 'Uber ride'.
        amount: How much was spent (a number, no currency symbol).
        category: One of Food, Transport, Shopping, Bills, Entertainment,
                  Health, Education, Miscellaneous.
    """
    doc = {
        "title": title,
        "amount": float(amount),
        "category": category,
        "currency": "INR",
        "date": datetime.now().strftime("%d %B %Y"),
    }
    result = _expenses.insert_one(doc)
    return {"status": "added", "id": str(result.inserted_id), ...}
```

**Important:** The **docstring is READ BY THE AI** to decide when to call this function. The AI doesn't see the code — only the function name, parameter names + types, and the docstring.

Then we expose tools to Groq in OpenAI-format:
```python
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Adds a new expense...",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "amount": {"type": "number"},
                    "category": {"type": "string"},
                },
                "required": ["title", "amount", "category"],
            },
        },
    },
    # ... 7 more tools
]

TOOL_FUNCTIONS = {
    "add_expense": add_expense,
    # ... map name → real Python function
}
```

## `ai/llm_client.py` — The Provider Layer

This is the **single file** where AI provider code lives. Swap Groq for Claude or OpenAI by editing only this file.

The key function — the **tool-use loop**:

```python
def chat_with_tools(user_message: str, history: list) -> str:
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for msg in history or []:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    # The tool-use loop — keep calling AI until it stops requesting tools
    for _ in range(8):                                    # Max 8 turns (safety)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_SCHEMAS,                           # ← Tell AI what's available
            tool_choice="auto",
        )

        msg = response.choices[0].message

        if not msg.tool_calls:                            # AI has final answer
            return msg.content.strip()

        # AI wants to call tools — execute them
        messages.append({"role": "assistant", ...})       # Append AI's request

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            result = TOOL_FUNCTIONS[fn_name](**fn_args)   # ← Actually call the function

            # Send result back to AI
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": fn_name,
                "content": json.dumps(result),
            })
        # Loop again — AI now has the result, decides next action
```

**This loop IS the magic.** It's how every AI agent works (Cursor, Claude Code, ChatGPT plugins). Understand this loop = understand AI agents.

## `services/currency.py` — Exchange Rate Service

```python
def get_rate(from_currency: str, to_currency: str) -> float:
    """Cached exchange rate fetcher."""
    if from_currency == to_currency:
        return 1.0

    # Check 1-hour memory cache first
    cache_key = f"{from_currency}->{to_currency}"
    cached = _rate_cache.get(cache_key)
    if cached and (time.time() - cached[1]) < 3600:
        return cached[0]

    # Hit Frankfurter API
    response = httpx.get(
        "https://api.frankfurter.dev/v1/latest",
        params={"base": from_currency, "symbols": to_currency},
    )
    rate = float(response.json()["rates"][to_currency])
    _rate_cache[cache_key] = (rate, time.time())          # Cache it
    return rate
```

**Why cache?** Frankfurter is free, but they ask you not to hammer it. Caching 1 hour = max 24 requests per day per pair, even if your app gets 1M users.

## `frontend/app.py` — The Dashboard

Streamlit code reads like a script that runs top to bottom each time the page renders:

```python
import streamlit as st
from api_client import get, post

# Load settings once at top
_settings = get("/settings")
BASE_SYMBOL = _settings["symbol"]

# Set page title and layout
st.set_page_config(page_title="AI Expense Tracker", page_icon="💰", layout="wide")
st.title("💰 AI Expense Tracker")

# Render salary metric
salary_data = get("/salary")
st.metric("This Month's Salary", f"{BASE_SYMBOL}{salary_data['total_salary']:,.0f}")

# Render form
with st.form("manual_form"):
    title = st.text_input("Title")
    amount = st.number_input("Amount")
    if st.form_submit_button("Add"):
        post("/expenses", {"title": title, "amount": amount, ...})
        st.rerun()    # Refresh the page after adding
```

**Key concept: Streamlit reruns the entire script on every interaction.** When you click a button, Streamlit runs `app.py` again top-to-bottom. State is managed via `st.session_state` or by re-fetching from the API.

## `frontend/api_client.py` — HTTP Wrapper

```python
import httpx

BACKEND_URL = "http://localhost:8000"

def get(path):
    r = httpx.get(f"{BACKEND_URL}{path}", timeout=60.0)
    r.raise_for_status()           # Raise exception on 4xx/5xx
    return r.json()
```

Tiny but important — DRY principle. All HTTP calls go through 4 functions (get/post/put/delete) instead of repeating `httpx.get(...)` everywhere.

---

# 5. Key Concepts You Need to Know

## REST API Design

REST = a convention for designing web APIs using HTTP verbs:

| Verb | Means | Example |
|------|-------|---------|
| `GET` | Read | `GET /expenses` |
| `POST` | Create / Add | `POST /expenses` |
| `PUT` | Replace (full update) | `PUT /expenses/123` |
| `DELETE` | Remove | `DELETE /expenses/123` |
| `PATCH` | Partial update | `PATCH /expenses/123` (we don't use this) |

Why this matters: Recruiters expect you to know this. "Why did you use PUT vs POST for /salary?" is a typical interview question.

**Our answer:** `POST /salary` adds to existing total. `PUT /salary` replaces it. Different intents → different verbs.

## Async/Await

Python normally runs one line at a time. With `async`, when one task is waiting (e.g., for a database query), Python can work on other requests.

```python
async def get_expenses():
    expenses = await expense_collection.find().to_list(1000)  # ← yields here
    return expenses

# Meanwhile, FastAPI can handle 100 other requests
```

Without async, your server could only handle ONE request at a time. With async, it handles thousands concurrently.

We use `async` everywhere in FastAPI for this reason.

## Pydantic & Type Hints

```python
class Expense(BaseModel):
    title: str
    amount: float
```

This `class` is both:
1. **Code** (a Python class)
2. **API specification** (FastAPI auto-generates OpenAPI/Swagger docs from it)
3. **Validation rules** (incoming data is validated automatically)

One source of truth → three uses. Powerful.

## Environment Variables (`.env`)

```
MONGO_URL=mongodb+srv://...
GROQ_API_KEY=gsk_...
```

Never hardcode secrets in code. The `.env` file is gitignored, so it never gets committed. In production (Railway/Streamlit Cloud), you set these as platform-level environment variables.

`dotenv` library loads them: `os.getenv("MONGO_URL")` reads from the OS environment.

## Tool Use / Function Calling

Three things make Tool Use work:

1. **Tool definitions** (schemas) — Tell the LLM what's available
2. **Tool execution** — When the LLM requests a tool, run the actual Python function
3. **Result passing** — Send the function's result BACK to the LLM
4. **Loop until done** — LLM may call multiple tools sequentially

We implemented all 4 in `ai/llm_client.py::chat_with_tools`.

## Structured Output / JSON Mode

Forcing an LLM to return clean JSON instead of prose:

```python
PARSE_EXPENSE_PROMPT = """...
Return ONLY a valid JSON object with EXACTLY these 3 keys.
No markdown. No code fence. No explanation. Just JSON.

Examples:
Input: "I spent 1000 rs on food with title zomato"
Output: {"title": "Zomato", "amount": 1000, "category": "Food"}
..."""
```

Then in code we `json.loads(response)` and validate. If parsing fails, we ask again or default.

## Caching

Exchange rates don't change every minute. We cache them in memory for 1 hour.

```python
_rate_cache = {}

def get_rate(...):
    cached = _rate_cache.get(key)
    if cached and (time.time() - cached_time) < 3600:
        return cached_rate
    # else hit API
```

Production caching tools: **Redis** (in-memory distributed cache), **CDN** for HTTP responses.

---

# 6. End-to-End Flows

## Flow 1: User Adds an Expense via Natural Language

```
User types in browser: "I spent 1000 on zomato food"
        │
        ▼
┌──────────────────────────────────────────┐
│ Streamlit form on Dashboard              │
│ Calls: post("/expenses/natural", {       │
│   text: "I spent 1000 on zomato food",   │
│   date: "2026-05-15",                    │
│   currency: "INR"                        │
│ })                                       │
└──────────────────┬───────────────────────┘
                   │ HTTP POST
                   ▼
┌──────────────────────────────────────────┐
│ FastAPI: routes/ai.py::natural_add_expense │
│   1. Calls parse_expense_text()          │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ ai/llm_client.py::parse_expense_text     │
│   - Sends to Groq with PARSE_EXPENSE_PROMPT │
│   - Groq returns: '{"title":"Zomato",    │
│                     "amount":1000,        │
│                     "category":"Food"}'   │
│   - Parses JSON, validates                │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ Back in routes/ai.py:                    │
│   2. get_base_currency() → "INR"         │
│   3. build_amount_fields(1000, "INR",   │
│                          "INR")          │
│      → {amount: 1000, currency: "INR"}   │
│   4. Insert into MongoDB                 │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│ Return {expense: {...}} to Streamlit     │
└──────────────────┬───────────────────────┘
                   │
                   ▼
        User sees: "Added Zomato • ₹1,000 • Food"
```

## Flow 2: User Asks the Chatbot

```
User types: "How much have I spent on food?"
        │
        ▼
Streamlit Chat page → POST /chat → ai.py::chat_endpoint
                                        │
                                        ▼
chat_with_tools() in ai/llm_client.py:
  ┌──────────────────────────────────────┐
  │ Iteration 1:                         │
  │ Send to Groq:                        │
  │   System: "You're an AI assistant..." │
  │   Tools: [8 tool definitions]        │
  │   User: "How much have I spent..."   │
  │ Groq returns:                        │
  │   tool_calls: [get_expenses_by_      │
  │      category({category:"Food"})]    │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ Execute tool:                        │
  │   ai/tools.py::get_expenses_by_      │
  │   category("Food")                   │
  │   → Queries MongoDB                  │
  │   → Returns {total: 450, items:[...]}│
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ Iteration 2:                         │
  │ Send back to Groq:                   │
  │   ... previous messages ...          │
  │   Tool result: {total: 450, ...}     │
  │ Groq returns:                        │
  │   tool_calls: None                   │
  │   content: "You've spent ₹450 on     │
  │             food this month..."      │
  │ → Return this text                   │
  └──────────────┬───────────────────────┘
                 │
                 ▼
       Streamlit displays in chat bubble
```

## Flow 3: User Switches Base Currency

```
User picks "USD" in Settings page
        │
        ▼
PUT /settings {base_currency: "USD"}
        │
        ▼
routes/settings.py::update_settings:
  1. Old base = "INR" (read from settings collection)
  2. Get exchange rate INR→USD: 0.01044
  3. For each expense in DB:
       new_amount = old_amount × 0.01044
       Update document with new amount + currency="USD"
  4. Same for all salaries
  5. Update settings.base_currency = "USD"
  6. Return summary
        │
        ▼
Streamlit shows: "Converted 47 expenses and 1 salary at rate 0.01044"
All charts/metrics now display in USD when next loaded
```

---

# 7. Interview Questions You'll Get

Prepare answers for these — they're typical for AI Product Engineer interviews:

## Architecture Questions

**Q: Why did you split frontend and backend?**
A: Separation of concerns + reusability. The same backend can serve a Streamlit UI, a mobile app, or a Slack bot in the future. Also makes testing easier — I can curl the API without a browser.

**Q: Why MongoDB over PostgreSQL?**
A: For this project, fast iteration mattered more than schema rigor. Adding the `currency` field, then `original_amount`, then `exchange_rate` was zero-cost in MongoDB — no migrations. In a production app with strict consistency needs, I'd use PostgreSQL.

**Q: How would you scale this to 1M users?**
A:
- DB: MongoDB Atlas with sharding by user_id
- Backend: deploy multiple FastAPI instances behind a load balancer
- Cache hot data in Redis (recent expenses, exchange rates)
- Move heavy AI calls to a queue (Celery) so the API stays fast

## AI Questions

**Q: Explain Tool Use vs RAG.**
A: Tool Use = AI calls Python functions (best for structured data like our MongoDB). RAG = AI searches a vector database for relevant text (best for unstructured documents). We used Tool Use because expense data is structured. We could add RAG later for retrieving financial advice articles.

**Q: How do you prevent the AI from hallucinating numbers?**
A: Three layers:
1. System prompt explicitly says "ALWAYS use tools, never guess numbers"
2. The 8 tools return real DB data — AI summarizes, doesn't invent
3. For structured extraction (`/expenses/natural`), I validate the returned JSON before using it

**Q: Why did you use multiple AI providers in your design?**
A: Vendor lock-in is risky. Today I might use Groq for speed, tomorrow Claude for quality. My `ai/llm_client.py` is the only file that knows about Groq — swapping providers is a one-file change.

## Code Quality Questions

**Q: Walk me through your code organization.**
A:
- `routes/` — One file per API resource (REST best practice)
- `ai/` — All AI-related code (prompts, tools, LLM client)
- `services/` — Reusable services (currency, could add email, payment, etc.)
- `frontend/` — UI completely separate
- `models.py` — All Pydantic models in one place

**Q: How do you handle errors?**
A: FastAPI's `HTTPException` for expected errors (404 if expense not found). Try/except for AI calls (return a friendly error instead of 500). Pydantic auto-validates inputs.

**Q: What would you do differently if you started over?**
A: Add tests from day 1 (currently relying on manual testing). Use a proper migration tool even with MongoDB. Add proper authentication so it's not single-user. Maybe use Redis for the exchange rate cache instead of in-memory (survives restarts).

## Why-This-Choice Questions

**Q: Why Groq and not OpenAI?**
A: Free tier was important for a portfolio project. Llama on Groq is fast (faster than OpenAI for most tasks), and using Llama signals I can work with open-source models — important AI engineering skill.

**Q: Why Streamlit and not React?**
A: For AI/data tooling, Streamlit is industry standard (used at Snowflake, Uber, Shopify for internal tools). React would have been overkill for a single-user app. If I were building a consumer product, React would be the answer.

**Q: Why frankfurter.dev?**
A: Free, no API key required, sourced from European Central Bank. Other providers (openexchangerates.org) need accounts. For a hackathon-style project, zero-friction integration wins.

---

# Summary: One-Sentence Mental Models

- **FastAPI** = turns Python functions into REST endpoints
- **MongoDB** = JSON-shaped database with no migrations needed
- **Pydantic** = automatic validation + docs from type hints
- **Async** = the server keeps working while waiting for I/O
- **Streamlit** = Python code → web UI, with auto-refresh on every action
- **Tool Use** = AI describes what it wants to do; your code does it; AI summarizes
- **System Prompt** = the AI's job description
- **CORS** = "Yes, this other website is allowed to call me"
- **Caching** = "I already know the answer, don't ask again"
- **Modular providers** = swap Groq for Claude by changing one file

---

## Where to Go Next

If you want to deepen your understanding, study these in order:

1. **HTTP & REST** — MDN Web Docs has excellent guides
2. **Async Python** — Real Python's async tutorial
3. **FastAPI tutorial** — Official FastAPI docs are short and excellent
4. **Tool Use / Function Calling** — OpenAI docs on function calling (same concept)
5. **Prompt Engineering** — Anthropic's prompt engineering guide

Each of these is 1-2 hours of reading. Together, they're the foundation of modern AI product engineering.
