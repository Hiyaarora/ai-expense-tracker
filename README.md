# AI Expense Tracker

A full-stack personal finance application that lets you track expenses, analyze spending with AI, and manage your records through natural conversation. Instead of filling out forms, you can type *"I spent 1000 on food at Zomato"* and the AI extracts the details — or ask the assistant *"How much did I spend on travel this month?"* and it answers directly from your data, and can even add, edit, or delete records on request.

Built as a portfolio project to demonstrate practical AI engineering: tool use / function calling, structured data extraction, and a provider-agnostic LLM architecture.

---

## Features

| Feature | Description |
|---|---|
| Natural-language expense entry | Type a plain sentence; the AI extracts the title, amount, and category as structured data. |
| Conversational AI assistant | Ask questions and issue commands in plain English. The assistant decides which database operations to run and replies in natural language. |
| Bank-statement import | Upload a PDF bank or passbook statement; the AI extracts the transactions for you to review and confirm before saving. |
| Monthly breakdown | Visual category-wise breakdown of the current month's spending. |
| Yearly overview | Month-by-month and category-wise charts across the year. |
| AI spending insights | A concise, plain-English summary of your spending patterns. |
| AI budget advice | Personalized saving suggestions based on your actual data. |
| Salary and savings tracking | Record monthly salary and automatically compute savings. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (async Python) |
| Frontend | Streamlit + Plotly |
| Database | MongoDB Atlas (Motor for async, PyMongo for sync) |
| LLM | Groq API (Llama-family models) |
| AI patterns | Tool use / function calling, structured extraction |

The LLM provider is isolated in `ai/llm_client.py`, so it can be swapped for another provider by editing a single file.

---

## Architecture

```
Streamlit UI  (http://localhost:8501)
      |  HTTP
      v
FastAPI backend  (http://localhost:8000)
   routes/  ->  expenses, salary, ai, settings, imports
      |
      v
ai/llm_client.py  (Groq API)
ai/tools.py       (database functions the assistant can call)
      |
      v
MongoDB Atlas
```

---

## Requirements

- Python 3.9 or higher
- A MongoDB Atlas connection string (free tier works)
- A Groq API key — free at [console.groq.com](https://console.groq.com)

---

## Setup

**1. Clone the repository and install dependencies**

```bash
git clone https://github.com/Hiyaarora/ai-expense-tracker.git
cd ai-expense-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment variables**

Create a `.env` file in the project root:

```env
MONGO_URL=mongodb+srv://your-mongodb-connection-string
GROQ_API_KEY=your-groq-api-key
BACKEND_URL=http://localhost:8000
```

**3. Start the backend**

```bash
uvicorn main:app --reload
```

**4. Start the frontend** (in a second terminal)

```bash
source venv/bin/activate
streamlit run frontend/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Project Structure

```
ai-expense-tracker/
├── main.py              # FastAPI entry point
├── database.py          # MongoDB client
├── models.py            # Pydantic request models
├── requirements.txt
├── routes/              # API endpoints (expenses, salary, ai, settings, imports)
├── ai/                  # LLM client, tool functions, prompts, PDF parser
└── frontend/            # Streamlit dashboard and pages
```

---

## Key Engineering Concepts

- **Tool use / function calling** — the assistant is given a set of database functions, decides which to call to satisfy a request, and the backend executes them and returns the results for a final natural-language reply.
- **Structured data extraction** — free-form text and PDF statements are converted into validated, structured records through careful prompting and parsing.
- **Provider-agnostic design** — all LLM access is routed through a single client module, keeping the application independent of any one provider.
- **Sync and async boundaries** — async MongoDB access for HTTP endpoints, with a synchronous path where the LLM tool-call layer requires it.
