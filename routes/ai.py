"""AI-powered endpoints: smart-add, monthly insights, budget advice, chat."""
from typing import Optional
from fastapi import APIRouter, HTTPException
from datetime import datetime

from database import expense_collection, salary_collection
from models import SmartExpense, NaturalExpense, ChatRequest
from routes.expenses import fetch_expenses_by_month
from ai.llm_client import (
    generate_monthly_insights,
    generate_budget_advice,
    categorize_expense,
    chat_with_tools,
    parse_expense_text,
)


def _resolve_date(date_iso: Optional[str]) -> str:
    """Convert YYYY-MM-DD to '15 May 2026' format, or use today."""
    if date_iso:
        try:
            parsed = datetime.strptime(date_iso, "%Y-%m-%d")
            return parsed.strftime("%d %B %Y")
        except ValueError:
            pass
    return datetime.now().strftime("%d %B %Y")

router = APIRouter()


async def _build_monthly_summary() -> dict:
    """Compose the same shape as /expenses/summary/monthly for AI inputs."""
    current_month_name = datetime.now().strftime("%B")
    current_month_year = datetime.now().strftime("%B-%Y")
    expenses = await fetch_expenses_by_month(current_month_name)

    summary = {}
    total = 0
    currency = "INR"
    for e in expenses:
        cat = e.get("category", "Miscellaneous")
        summary[cat] = summary.get(cat, 0) + e.get("amount", 0)
        total += e.get("amount", 0)
        currency = e.get("currency", currency)

    return {
        "month": current_month_year,
        "summary": summary,
        "total": total,
        "currency": currency,
    }


async def _get_salary_amount():
    current_month_year = datetime.now().strftime("%B-%Y")
    salary = await salary_collection.find_one({"month": current_month_year})
    return salary["amount"] if salary else None


# ===================== ENDPOINTS =====================

@router.get("/insights/monthly")
async def get_monthly_insights_endpoint():
    """AI-written paragraph summarizing the current month's spending."""
    summary = await _build_monthly_summary()
    if not summary["summary"]:
        return {"insights": "No expenses recorded this month yet. Add some to see insights."}
    salary = await _get_salary_amount()
    text = generate_monthly_insights(summary, salary)
    return {"month": summary["month"], "insights": text}


@router.get("/advice")
async def get_budget_advice_endpoint():
    """AI returns 3 personalized saving tips based on real spending data."""
    summary = await _build_monthly_summary()
    if not summary["summary"]:
        return {"advice": "Add some expenses first so I can give personalized advice."}
    salary = await _get_salary_amount()
    text = generate_budget_advice(summary, salary)
    return {"month": summary["month"], "advice": text}


@router.post("/expenses/smart")
async def smart_add_expense(expense: SmartExpense):
    """Add an expense with AI-picked category based on the title."""
    category = categorize_expense(expense.title)
    date_str = _resolve_date(expense.date)
    doc = {
        "title": expense.title,
        "amount": expense.amount,
        "category": category,
        "currency": expense.currency,
        "date": date_str,
    }
    result = await expense_collection.insert_one(doc)
    return {
        "message": "Expense added with AI-picked category",
        "expense": {
            "id": str(result.inserted_id),
            "title": expense.title,
            "amount": expense.amount,
            "category": category,
            "currency": expense.currency,
            "date": date_str,
        },
    }


@router.post("/expenses/natural")
async def natural_add_expense(nl: NaturalExpense):
    """Parse a free-form sentence into a full expense and insert it.

    Example input: 'I spent 1000 rs on food with title zomato'
    """
    try:
        parsed = parse_expense_text(nl.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Could not parse: {e}")

    date_str = _resolve_date(nl.date)
    doc = {
        "title": parsed["title"],
        "amount": parsed["amount"],
        "category": parsed["category"],
        "currency": "INR",
        "date": date_str,
    }
    result = await expense_collection.insert_one(doc)
    return {
        "message": "Expense parsed and added",
        "expense": {
            "id": str(result.inserted_id),
            "title": doc["title"],
            "amount": doc["amount"],
            "category": doc["category"],
            "currency": doc["currency"],
            "date": doc["date"],
        },
    }


@router.post("/chat")
def chat_endpoint(req: ChatRequest):
    """Chat with the AI assistant. Gemini decides which tools to call."""
    try:
        history_dicts = [m.dict() for m in (req.history or [])]
        reply = chat_with_tools(req.message, history_dicts)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
