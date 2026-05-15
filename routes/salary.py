from fastapi import APIRouter
from database import salary_collection
from models import Salary
from datetime import datetime

# ✅ Import helper functions
from routes.expenses import fetch_expenses_by_month, get_base_currency
from services.currency import convert as convert_currency

router = APIRouter()


async def _to_base_currency(amount: float, input_currency: str) -> dict:
    """Return (converted_amount, base_currency, original_amount, original_currency, rate)."""
    base = await get_base_currency()
    input_currency = (input_currency or base).upper()
    if input_currency == base:
        return {
            "amount": float(amount),
            "currency": base,
            "original_amount": None,
            "original_currency": None,
            "exchange_rate": None,
        }
    conv = convert_currency(amount, input_currency, base)
    return {
        "amount": conv["converted_amount"],
        "currency": base,
        "original_amount": conv["original_amount"],
        "original_currency": conv["original_currency"],
        "exchange_rate": conv["exchange_rate"],
    }

# POST /salary - Add to current month's salary (with currency conversion)
@router.post("/salary")
async def add_salary(salary: Salary):
    current_month = datetime.now().strftime("%B-%Y")
    conv = await _to_base_currency(salary.amount, salary.currency)

    existing_salary = await salary_collection.find_one({"month": current_month})

    if existing_salary:
        new_total = existing_salary["amount"] + conv["amount"]
        await salary_collection.update_one(
            {"month": current_month},
            {"$set": {"amount": new_total, "currency": conv["currency"]}},
        )
        return {
            "message": f"Salary updated for {current_month}",
            "previous_salary": existing_salary["amount"],
            "added_amount": conv["amount"],
            "total_salary": new_total,
            "currency": conv["currency"],
            "original_amount": conv["original_amount"],
            "original_currency": conv["original_currency"],
            "exchange_rate": conv["exchange_rate"],
        }
    else:
        salary_dict = {
            "amount": conv["amount"],
            "currency": conv["currency"],
            "month": current_month,
            "date_added": datetime.now().strftime("%d %B %Y"),
        }
        await salary_collection.insert_one(salary_dict)
        return {
            "message": f"Salary added for {current_month}",
            "total_salary": conv["amount"],
            "currency": conv["currency"],
            "original_amount": conv["original_amount"],
            "original_currency": conv["original_currency"],
            "exchange_rate": conv["exchange_rate"],
        }


# PUT /salary - Replace (set) salary for current month (with currency conversion)
@router.put("/salary")
async def set_salary(salary: Salary):
    current_month = datetime.now().strftime("%B-%Y")
    conv = await _to_base_currency(salary.amount, salary.currency)

    existing_salary = await salary_collection.find_one({"month": current_month})

    if existing_salary:
        await salary_collection.update_one(
            {"month": current_month},
            {"$set": {"amount": conv["amount"], "currency": conv["currency"]}},
        )
        return {
            "message": f"Salary set for {current_month}",
            "previous_salary": existing_salary["amount"],
            "total_salary": conv["amount"],
            "currency": conv["currency"],
            "original_amount": conv["original_amount"],
            "original_currency": conv["original_currency"],
            "exchange_rate": conv["exchange_rate"],
        }
    else:
        salary_dict = {
            "amount": conv["amount"],
            "currency": conv["currency"],
            "month": current_month,
            "date_added": datetime.now().strftime("%d %B %Y"),
        }
        await salary_collection.insert_one(salary_dict)
        return {
            "message": f"Salary set for {current_month}",
            "total_salary": conv["amount"],
            "currency": conv["currency"],
            "original_amount": conv["original_amount"],
            "original_currency": conv["original_currency"],
            "exchange_rate": conv["exchange_rate"],
        }


# GET /salary - Get salary for current month
@router.get("/salary")
async def get_salary():
    current_month = datetime.now().strftime("%B-%Y")

    salary = await salary_collection.find_one(
        {"month": current_month}
    )

    if salary:
        return {
            "month": current_month,
            "total_salary": salary["amount"],
            "currency": salary["currency"],
            "date_added": salary["date_added"]
        }
    else:
        return {
            "message": f"No salary added for {current_month} yet"
        }


# GET /savings - Get savings for current month
@router.get("/savings")
async def get_savings():
    current_month = datetime.now().strftime("%B-%Y")
    current_month_name = datetime.now().strftime("%B")

    salary = await salary_collection.find_one(
        {"month": current_month}
    )

    if not salary:
        return {
            "message": f"No salary added for {current_month} yet!"
        }

    salary_amount = salary["amount"]
    currency = salary["currency"]

    # ✅ Using helper function - no repeated code!
    all_expenses = await fetch_expenses_by_month(current_month_name)

    # Calculate total
    total_expenses = sum(expense["amount"] for expense in all_expenses)

    savings = salary_amount - total_expenses

    return {
        "month": current_month,
        "currency": currency,
        "summary": {
            "salary": salary_amount,
            "total_expenses": total_expenses,
            "savings": savings
        },
        "status": "✅ Saving well!" if savings > 0 else "⚠️ Overspending!"
    }