"""Tool functions the LLM can call to interact with the expense database.
Uses synchronous PyMongo because the LLM SDK's tool-call execution is sync.
"""
import os
import re
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

from services.currency import format_amount, symbol_for

load_dotenv()

_client = MongoClient(os.getenv("MONGO_URL"))
_db = _client.expense_tracker
_expenses = _db.expenses
_salaries = _db.salaries
_settings = _db.settings


def _base_currency() -> str:
    """Read the user's base currency from MongoDB settings."""
    doc = _settings.find_one({"_id": "user_settings"})
    return (doc or {}).get("base_currency", "INR")


def _fmt(amount, decimals: int = 0, currency: str = None) -> str:
    """Locale-aware display string for an amount in the base currency."""
    cur = currency or _base_currency()
    return f"{symbol_for(cur)}{format_amount(amount, cur, decimals)}"


def _current_month_name() -> str:
    return datetime.now().strftime("%B")


def _current_month_year() -> str:
    return datetime.now().strftime("%B-%Y")


def _find_month_expenses(month_name: str) -> list:
    return list(_expenses.find({"date": {"$regex": month_name}}))


# ===================== TOOL FUNCTIONS =====================
# Each function below is registered as a tool with Gemini.
# Docstrings are READ BY GEMINI to decide which tool to call,
# so they must be clear and accurate.

def get_all_expenses_this_month() -> dict:
    """Returns every expense the user has logged this month.

    Use this when the user asks 'show me my expenses', 'what did I spend on',
    'list my expenses', etc.
    """
    cur = _base_currency()
    expenses = _find_month_expenses(_current_month_name())
    total = sum(e.get("amount", 0) for e in expenses)
    return {
        "month": _current_month_year(),
        "currency": cur,
        "count": len(expenses),
        "total": total,
        "total_display": _fmt(total, 2, cur),
        "expenses": [
            {"title": e.get("title"), "amount": e.get("amount"),
             "amount_display": _fmt(e.get("amount"), 2, cur),
             "category": e.get("category"), "date": e.get("date")}
            for e in expenses
        ],
    }


def get_expenses_by_category(category: str) -> dict:
    """Returns expenses for a specific category in the current month.

    Args:
        category: One of Food, Transport, Shopping, Bills, Entertainment,
                  Health, Education, Miscellaneous.
    Use when the user asks 'how much on food', 'show shopping expenses', etc.
    """
    cur = _base_currency()
    expenses = _find_month_expenses(_current_month_name())
    filtered = [e for e in expenses
                if (e.get("category") or "").lower() == category.lower()]
    total = sum(e.get("amount", 0) for e in filtered)
    return {
        "category": category,
        "currency": cur,
        "count": len(filtered),
        "total": total,
        "total_display": _fmt(total, 2, cur),
        "items": [
            {"title": e["title"], "amount": e["amount"],
             "amount_display": _fmt(e["amount"], 2, cur)}
            for e in filtered
        ],
    }


def get_monthly_total() -> dict:
    """Returns the total amount spent this month across all categories."""
    cur = _base_currency()
    expenses = _find_month_expenses(_current_month_name())
    total = sum(e.get("amount", 0) for e in expenses)
    return {
        "month": _current_month_year(),
        "currency": cur,
        "total": total,
        "total_display": _fmt(total, 2, cur),
        "expense_count": len(expenses),
    }


def get_salary() -> dict:
    """Returns the user's salary for the current month."""
    cur = _base_currency()
    salary = _salaries.find_one({"month": _current_month_year()})
    if not salary:
        return {"message": "No salary recorded for this month yet"}
    amount = salary.get("amount")
    return {
        "month": _current_month_year(),
        "amount": amount,
        "amount_display": _fmt(amount, 2, cur),
        "currency": salary.get("currency", cur),
    }


def get_savings() -> dict:
    """Returns savings = salary minus total expenses for the current month."""
    cur = _base_currency()
    expenses = _find_month_expenses(_current_month_name())
    total_spent = sum(e.get("amount", 0) for e in expenses)
    salary = _salaries.find_one({"month": _current_month_year()})
    if not salary:
        return {
            "message": "No salary set",
            "total_spent": total_spent,
            "total_spent_display": _fmt(total_spent, 2, cur),
            "currency": cur,
        }
    salary_amount = salary.get("amount", 0)
    savings = salary_amount - total_spent
    return {
        "currency": cur,
        "salary": salary_amount,
        "salary_display": _fmt(salary_amount, 2, cur),
        "total_spent": total_spent,
        "total_spent_display": _fmt(total_spent, 2, cur),
        "savings": savings,
        "savings_display": _fmt(savings, 2, cur),
    }


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
    return {"status": "added", "id": str(result.inserted_id),
            "title": title, "amount": amount, "category": category}


def delete_expense_by_title(title: str) -> dict:
    """Deletes ALL expenses matching the given title (case-insensitive).

    Use when the user says 'delete my Zomato expense' or similar.
    Returns how many expenses were deleted.
    """
    safe_title = re.escape(title)
    result = _expenses.delete_many(
        {"title": {"$regex": f"^{safe_title}$", "$options": "i"}}
    )
    return {"status": "deleted", "title": title,
            "deleted_count": result.deleted_count}


def get_yearly_summary() -> dict:
    """Returns month-by-month spending totals for the current year plus
    category-wise totals.

    Use this for questions about the year as a whole, trends across months,
    or comparisons like 'which month did I spend the most'.
    """
    cur = _base_currency()
    current_year = datetime.now().year
    current_month_num = datetime.now().month
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    monthly_totals = {}
    monthly_totals_display = {}
    category_totals = {}
    category_totals_display = {}
    grand_total = 0
    for i in range(current_month_num):
        month_name = months[i]
        expenses = _find_month_expenses(month_name)
        expenses = [e for e in expenses if str(current_year) in str(e.get("date", ""))]
        month_total = 0
        for e in expenses:
            amt = e.get("amount", 0)
            cat = e.get("category", "Miscellaneous")
            month_total += amt
            category_totals[cat] = category_totals.get(cat, 0) + amt
        monthly_totals[month_name] = month_total
        monthly_totals_display[month_name] = _fmt(month_total, 2, cur)
        grand_total += month_total
    for cat, amt in category_totals.items():
        category_totals_display[cat] = _fmt(amt, 2, cur)
    return {
        "year": current_year,
        "currency": cur,
        "monthly_totals": monthly_totals,
        "monthly_totals_display": monthly_totals_display,
        "category_totals": category_totals,
        "category_totals_display": category_totals_display,
        "grand_total": grand_total,
        "grand_total_display": _fmt(grand_total, 2, cur),
    }


def get_expenses_for_month(month: str, year: int) -> dict:
    """Get all expenses for a specific month and year (any past or current month).

    Use this when the user mentions a specific month like 'April', 'last month',
    'in March', etc.
    """
    cur = _base_currency()
    expenses = _find_month_expenses(month)
    expenses = [e for e in expenses if str(year) in str(e.get("date", ""))]
    total = sum(e.get("amount", 0) for e in expenses)
    return {
        "month": month,
        "year": year,
        "currency": cur,
        "count": len(expenses),
        "total": total,
        "total_display": _fmt(total, 2, cur),
        "expenses": [
            {"title": e.get("title"), "amount": e.get("amount"),
             "amount_display": _fmt(e.get("amount"), 2, cur),
             "category": e.get("category"), "date": e.get("date")}
            for e in expenses
        ],
    }


def get_expenses_by_category_for_month(category: str, month: str, year: int) -> dict:
    """Get expenses filtered by category for a specific month and year."""
    cur = _base_currency()
    expenses = _find_month_expenses(month)
    expenses = [e for e in expenses if str(year) in str(e.get("date", ""))]
    filtered = [e for e in expenses
                if (e.get("category") or "").lower() == category.lower()]
    total = sum(e.get("amount", 0) for e in filtered)
    return {
        "month": month,
        "year": year,
        "currency": cur,
        "category": category,
        "count": len(filtered),
        "total": total,
        "total_display": _fmt(total, 2, cur),
        "items": [
            {"title": e["title"], "amount": e["amount"],
             "amount_display": _fmt(e["amount"], 2, cur)}
            for e in filtered
        ],
    }


def update_expense_by_title(title: str, new_amount: float = None,
                            new_category: str = None) -> dict:
    """Updates the amount and/or category of an expense matching the given title.

    Args:
        title: The title of the expense to update.
        new_amount: New amount (optional).
        new_category: New category (optional).
    Returns how many expenses were modified.
    """
    updates = {}
    if new_amount is not None:
        updates["amount"] = float(new_amount)
    if new_category:
        updates["category"] = new_category
    if not updates:
        return {"status": "no_changes_requested"}

    safe_title = re.escape(title)
    result = _expenses.update_many(
        {"title": {"$regex": f"^{safe_title}$", "$options": "i"}},
        {"$set": updates},
    )
    return {"status": "updated", "title": title,
            "matched": result.matched_count,
            "modified": result.modified_count, "updates": updates}


# Map function name -> Python function (used by chat loop)
TOOL_FUNCTIONS = {
    "get_all_expenses_this_month": get_all_expenses_this_month,
    "get_expenses_by_category": get_expenses_by_category,
    "get_monthly_total": get_monthly_total,
    "get_salary": get_salary,
    "get_savings": get_savings,
    "add_expense": add_expense,
    "delete_expense_by_title": delete_expense_by_title,
    "update_expense_by_title": update_expense_by_title,
    "get_yearly_summary": get_yearly_summary,
    "get_expenses_for_month": get_expenses_for_month,
    "get_expenses_by_category_for_month": get_expenses_by_category_for_month,
}

# OpenAI/Groq-style tool schemas
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_all_expenses_this_month",
            "description": "Returns every expense the user has logged this month. Use when the user asks 'show me my expenses', 'list my expenses', etc.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expenses_by_category",
            "description": "Returns expenses for a specific category in the current month. Use when the user asks 'how much on food', 'show shopping expenses', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "One of Food, Transport, Shopping, Bills, Entertainment, Health, Education, Miscellaneous.",
                    }
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_total",
            "description": "Returns the total amount spent this month across all categories.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_salary",
            "description": "Returns the user's salary for the current month.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_savings",
            "description": "Returns savings (salary minus total expenses) for the current month.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Adds a new expense to the database for today.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short description like 'Zomato dinner'"},
                    "amount": {"type": "number", "description": "How much was spent"},
                    "category": {
                        "type": "string",
                        "description": "One of Food, Transport, Shopping, Bills, Entertainment, Health, Education, Miscellaneous.",
                    },
                },
                "required": ["title", "amount", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_expense_by_title",
            "description": "Deletes ALL expenses matching the given title (case-insensitive). Returns how many were deleted.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"}
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_expense_by_title",
            "description": "Updates the amount and/or category of an expense matching the given title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "new_amount": {"type": "number"},
                    "new_category": {"type": "string"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_yearly_summary",
            "description": "Returns month-by-month spending totals for the current year plus category-wise totals. Use for questions about the year as a whole or trends across months.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expenses_for_month",
            "description": "Get all expenses for a specific month and year (e.g. April 2026, last month, March). Use when the user asks about a specific past month rather than the current one.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {"type": "string", "description": "Full month name like 'January', 'April', etc."},
                    "year": {"type": "integer", "description": "4-digit year like 2026"},
                },
                "required": ["month", "year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expenses_by_category_for_month",
            "description": "Get expenses for a specific category within a specific month and year. Use for questions like 'how much on food in April'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "One of Food, Transport, Shopping, Bills, Entertainment, Health, Education, Miscellaneous"},
                    "month": {"type": "string", "description": "Full month name"},
                    "year": {"type": "integer", "description": "4-digit year"},
                },
                "required": ["category", "month", "year"],
            },
        },
    },
]
