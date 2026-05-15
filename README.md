# 💰 AI Expense Tracker

A full-stack, AI-powered personal finance app. Track expenses, get AI-written spending insights, and chat naturally with your data — the chatbot can **read AND modify** your expenses through plain-English conversation.

> Built end-to-end as a portfolio project demonstrating modern AI engineering patterns: Tool Use / Function Calling, structured data extraction, and provider-agnostic LLM architecture.

---

## ✨ Features

| Feature | What it does |
|---------|--------------|
| **🪄 Natural-language expense input** | Type _"I spent 1000 on food at zomato"_ — AI extracts title, amount, and category as structured JSON |
| **🤖 AI chatbot with Tool Use** | Ask anything ("How much on food?"), edit anything ("Delete coffee", "Change Uber to ₹400"). AI autonomously decides which of 8 database functions to call |
| **📊 Monthly category breakdown** | Pie chart of spending by category for the current month |
| **📈 Yearly overview** | Month-by-month and category-wise bar charts from January to now |
| **📝 AI monthly insights** | Plain-English paragraph analyzing your spending patterns |
| **💡 AI budget advice** | 3 personalized, specific saving tips based on your real data |
| **💼 Salary tracking** | Set or add to monthly salary; auto-computed savings |
| **📅 Date-aware adds** | Backfill expenses for any past date — useful for month-wise records |

---

## 🛠 Tech Stack

| Layer | Tool |
|-------|------|
| Backend | **FastAPI** (Python, async) |
| Database | **MongoDB** (Atlas) via Motor (async) and PyMongo (sync) |
| LLM | **Llama-style** model via **Groq API** (currently `openai/gpt-oss-120b`) |
| LLM pattern | **Tool Use / Function Calling** (OpenAI tool-call schema) |
| Frontend | **Streamlit** + Plotly |
| Hosting | Local dev / Railway-ready |

The LLM provider is isolated in `ai/llm_client.py` — swappable with Claude, Gemini, or OpenAI by editing one file.

---

## 🧠 AI Engineering Concepts Used

This project is a working example of three modern LLM patterns:

1. **Tool Use / Function Calling** (`POST /chat`)
   The chatbot has 8 tools registered (read expenses, get totals, add/update/delete records). Llama autonomously picks tools, the backend executes them against MongoDB, and Llama writes the natural-language reply.

2. **Structured Data Extraction** (`POST /expenses/natural`)
   Free-form text → strict JSON `{title, amount, category}` via prompt engineering and JSON validation.

3. **LLM-as-Classifier** (`POST /expenses/smart`)
   Single-turn AI categorization with a constrained output vocabulary.

---

## 🏗 Architecture

```
┌─────────────────┐
│   Streamlit UI  │  http://localhost:8501
└────────┬────────┘
         │ HTTP (httpx)
         ▼
┌──────────────────────────────────┐
│  FastAPI                         │  http://localhost:8000
│  ├─ routes/expenses.py           │
│  ├─ routes/salary.py             │
│  └─ routes/ai.py                 │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  ai/llm_client.py  (Groq API)    │
│  ai/tools.py  (8 tools → Mongo)  │
└────────┬─────────────────────────┘
         │
         ▼
   MongoDB Atlas
```

---

## 📦 API Endpoints

### Expenses
- `POST /expenses` — Add expense (manual)
- `POST /expenses/smart` — Add with AI-picked category
- `POST /expenses/natural` — Add by parsing free-form sentence
- `GET /expenses` — List current-month expenses
- `PUT /expenses/{id}` — Update an expense
- `DELETE /expenses/{id}` — Delete an expense
- `GET /expenses/summary/monthly` — Category totals for this month
- `GET /expenses/summary/yearly` — Month-by-month totals from January

### Salary
- `POST /salary` — Add to existing salary
- `PUT /salary` — Replace salary value
- `GET /salary` — Current month's salary
- `GET /savings` — Savings = salary − expenses

### AI
- `GET /insights/monthly` — AI spending summary
- `GET /advice` — AI budget tips
- `POST /chat` — Conversational chatbot with tool use

---

## 🚀 Run Locally

### Prerequisites
- Python 3.9+
- MongoDB Atlas connection string
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Setup

```bash
# 1. Clone
git clone https://github.com/Hiyaarora/ai-expense-tracker.git
cd ai-expense-tracker

# 2. Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cat > .env <<EOF
MONGO_URL=mongodb+srv://YOUR_MONGO_URL
GROQ_API_KEY=gsk_YOUR_GROQ_KEY
BACKEND_URL=http://localhost:8000
EOF

# 4. Start the backend
uvicorn main:app --reload

# 5. In a second terminal, start the frontend
source venv/bin/activate
streamlit run frontend/app.py
```

Open http://localhost:8501

---

## 🗂 Project Structure

```
ai-expense-tracker/
├── main.py                    # FastAPI entry
├── database.py                # MongoDB Motor client
├── models.py                  # Pydantic request models
├── requirements.txt
├── routes/
│   ├── expenses.py            # CRUD + summary endpoints
│   ├── salary.py              # Salary + savings
│   └── ai.py                  # AI-powered endpoints
├── ai/
│   ├── llm_client.py          # Groq client (insights, advice, chat)
│   ├── tools.py               # 8 tool functions for chatbot
│   └── prompts.py             # System prompts
└── frontend/
    ├── app.py                 # Dashboard
    ├── api_client.py          # HTTP helper
    └── pages/
        ├── 1_Monthly_Summary.py
        ├── 2_Yearly_Summary.py
        ├── 3_AI_Insights.py
        └── 4_Chat.py
```

---

## 📚 What I Learned Building This

- **LLM provider abstraction:** Designing `ai/llm_client.py` as the single swap point taught me how production AI apps stay vendor-flexible.
- **Tool Use loop:** Implementing the multi-turn tool-call loop (call AI → AI requests tool → execute → return result → AI replies) is fundamental to every AI agent product.
- **Structured output reliability:** Forcing a model to return strict JSON requires explicit prompting + parsing + validation — not just asking nicely.
- **Sync vs async boundaries:** Used async MongoDB (Motor) for HTTP endpoints, sync PyMongo for the tool-call layer where the LLM SDK expects sync.

---

## 🔮 Roadmap

- [ ] Multi-currency with live exchange rates (frankfurter.app)
- [ ] RAG layer for financial-advice retrieval (combine with current Tool Use)
- [ ] Edit/delete expenses inline on Dashboard
- [ ] Monthly-view selector for past months
- [ ] Deploy backend on Railway + frontend on Streamlit Cloud
- [ ] WhatsApp / Telegram bot interface

---

## 👤 Author

**Hiya Arora** — transitioning from QA Engineering to AI Product Engineering.

Built solo as a portfolio project.
