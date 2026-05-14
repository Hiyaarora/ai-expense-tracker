from fastapi import APIRouter
from database import salary_collection
from models import Salary
from datetime import datetime

# ✅ Import helper function from expenses.py
from routes.expenses import fetch_expenses_by_month

router = APIRouter()

# POST /salary - Add salary for current month
@router.post("/salary")
async def add_salary(salary: Salary):
    current_month = datetime.now().strftime("%B-%Y")

    existing_salary = await salary_collection.find_one(
        {"month": current_month}
    )

    if existing_salary:
        new_total = existing_salary["amount"] + salary.amount
        await salary_collection.update_one(
            {"month": current_month},
            {"$set": {"amount": new_total}}
        )
        return {
            "message": f"Salary updated for {current_month}",
            "previous_salary": existing_salary["amount"],
            "added_amount": salary.amount,
            "total_salary": new_total,
            "currency": salary.currency
        }
    else:
        salary_dict = {
            "amount": salary.amount,
            "currency": salary.currency,
            "month": current_month,
            "date_added": datetime.now().strftime("%d %B %Y")
        }
        await salary_collection.insert_one(salary_dict)
        return {
            "message": f"Salary added for {current_month}",
            "total_salary": salary.amount,
            "currency": salary.currency
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