"""Tool functions Gemini can call to interact with the expense database.
Uses synchronous PyMongo so it works cleanly with Gemini's function-calling pattern.
"""
import os
import re
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

_client = MongoClient(os.getenv("MONGO_URL"))
_db = _client.expense_tracker
_expenses = _db.expenses
_salaries = _db.salaries


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
    expenses = _find_month_expenses(_current_month_name())
    return {
        "month": _current_month_year(),
        "count": len(expenses),
        "expenses": [
            {"title": e.get("title"), "amount": e.get("amount"),
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
    expenses = _find_month_expenses(_current_month_name())
    filtered = [e for e in expenses
                if (e.get("category") or "").lower() == category.lower()]
    total = sum(e.get("amount", 0) for e in filtered)
    return {
        "category": category,
        "count": len(filtered),
        "total": total,
        "items": [{"title": e["title"], "amount": e["amount"]} for e in filtered],
    }


def get_monthly_total() -> dict:
    """Returns the total amount spent this month across all categories."""
    expenses = _find_month_expenses(_current_month_name())
    total = sum(e.get("amount", 0) for e in expenses)
    return {"month": _current_month_year(), "total": total,
            "expense_count": len(expenses)}


def get_salary() -> dict:
    """Returns the user's salary for the current month."""
    salary = _salaries.find_one({"month": _current_month_year()})
    if not salary:
        return {"message": "No salary recorded for this month yet"}
    return {"month": _current_month_year(),
            "amount": salary.get("amount"),
            "currency": salary.get("currency", "INR")}


def get_savings() -> dict:
    """Returns savings = salary minus total expenses for the current month."""
    expenses = _find_month_expenses(_current_month_name())
    total_spent = sum(e.get("amount", 0) for e in expenses)
    salary = _salaries.find_one({"month": _current_month_year()})
    if not salary:
        return {"message": "No salary set", "total_spent": total_spent}
    return {
        "salary": salary.get("amount"),
        "total_spent": total_spent,
        "savings": salary.get("amount", 0) - total_spent,
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
]
