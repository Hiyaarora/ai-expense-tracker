"""AI-powered endpoints: smart-add, monthly insights, budget advice, chat."""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from database import expense_collection, salary_collection
from models import SmartExpense, ChatRequest
from routes.expenses import fetch_expenses_by_month
from ai.llm_client import (
    generate_monthly_insights,
    generate_budget_advice,
    categorize_expense,
    chat_with_tools,
)

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
    doc = {
        "title": expense.title,
        "amount": expense.amount,
        "category": category,
        "currency": expense.currency,
        "date": datetime.now().strftime("%d %B %Y"),
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
