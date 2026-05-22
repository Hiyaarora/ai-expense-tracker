from fastapi import APIRouter, HTTPException
from database import expense_collection, settings_collection
from models import Expense, UpdateExpense
from datetime import datetime
from bson import ObjectId
from services.currency import build_amount_fields

router = APIRouter()


async def get_base_currency() -> str:
    """Fetch the user's configured base currency (defaults to INR)."""
    s = await settings_collection.find_one({"_id": "user_settings"})
    return (s or {}).get("base_currency", "INR")

# ✅ HELPER FUNCTION - reusable by any route
async def fetch_expenses_by_month(month_name: str):
    """
    Fetches all expenses for a given month name
    e.g. month_name = "April"
    """
    expenses = await expense_collection.find(
        {"date": {"$regex": month_name}}
    ).to_list(1000)

    return expenses


# POST /expenses - Add a new expense
@router.post("/expenses")
async def add_expense(expense: Expense):
    # Use provided date (YYYY-MM-DD) or default to today
    if expense.date:
        try:
            parsed = datetime.strptime(expense.date, "%Y-%m-%d")
            date_str = parsed.strftime("%d %B %Y")
        except ValueError:
            date_str = datetime.now().strftime("%d %B %Y")
    else:
        date_str = datetime.now().strftime("%d %B %Y")

    base_currency = await get_base_currency()
    try:
        amount_fields = build_amount_fields(
            expense.amount, expense.currency.upper(), base_currency
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    expense_dict = {
        "title": expense.title,
        "category": expense.category,
        "date": date_str,
        **amount_fields,
    }

    result = await expense_collection.insert_one(expense_dict)

    return {
        "message": "Expense added successfully!",
        "expense": {
            "id": str(result.inserted_id),
            "title": expense.title,
            "category": expense.category,
            "date": expense_dict["date"],
            **amount_fields,
        }
    }


# GET /expenses - Get all expenses
@router.get("/expenses")
async def get_expenses():

    # ✅ Using helper function instead of repeating query
    current_month_name = datetime.now().strftime("%B")
    all_expenses = await fetch_expenses_by_month(current_month_name)

    if not all_expenses:
        return {"message": "No expenses found!", "expenses": []}

    formatted = []
    for expense in all_expenses:
        formatted.append({
            "id": str(expense["_id"]),
            "title": expense["title"],
            "amount": expense["amount"],
            "category": expense["category"],
            "currency": expense["currency"],
            "date": expense["date"]
        })

    return {
        "total_count": len(formatted),
        "expenses": formatted
    }
# DELETE /expenses/{expense_id} - Delete an expense
@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str):

    # Step 1 - Check if the ID format is valid
    if not ObjectId.is_valid(expense_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid expense ID format"
        )

    # Step 2 - Try to delete the expense from MongoDB
    result = await expense_collection.delete_one(
        {"_id": ObjectId(expense_id)}
    )

    # Step 3 - Check if anything was actually deleted
    if result.deleted_count == 1:
        return {
            "message": "Expense deleted successfully! 🗑️",
            "deleted_id": expense_id
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="Expense not found! Please check the ID"
        )
    
    # PUT /expenses/{expense_id} - Update an expense
@router.put("/expenses/{expense_id}")
async def update_expense(expense_id: str, expense: UpdateExpense):

    # Step 1 - Validate ID format
    if not ObjectId.is_valid(expense_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid expense ID format"
        )

    # Step 2 - Collect only fields that were actually sent
    update_data = {}
    for field, value in expense.dict().items():
        if value is not None:
            update_data[field] = value

    # Step 3 - Check if there is anything to update
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided to update!"
        )

    # Step 4 - Update in MongoDB
    result = await expense_collection.update_one(
        {"_id": ObjectId(expense_id)},
        {"$set": update_data}
    )

    # Step 5 - Check if expense was found
    if result.matched_count == 1:
        return {
            "message": "Expense updated successfully! ✏️",
            "updated_fields": update_data
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="Expense not found! Please check the ID"
        )


# GET /expenses/summary/monthly - Category-wise totals
# Optional ?month=May&year=2026 to view a specific month (defaults to current)
@router.get("/expenses/summary/monthly")
async def get_monthly_summary(month: str = None, year: int = None):
    if month and year:
        target_month_name = month
        target_month_year = f"{month}-{year}"
    else:
        target_month_name = datetime.now().strftime("%B")
        target_month_year = datetime.now().strftime("%B-%Y")

    expenses = await fetch_expenses_by_month(target_month_name)

    # If a specific year was requested, also filter by year in the date string
    if year:
        expenses = [e for e in expenses if str(year) in str(e.get("date", ""))]

    if not expenses:
        return {
            "month": target_month_year,
            "summary": {},
            "total": 0,
            "message": "No expenses found for this month"
        }

    summary = {}
    total = 0
    currency = expenses[0].get("currency", "INR")

    for expense in expenses:
        category = expense.get("category", "Miscellaneous")
        amount = expense.get("amount", 0)
        summary[category] = summary.get(category, 0) + amount
        total += amount

    return {
        "month": target_month_year,
        "currency": currency,
        "summary": summary,
        "total": total,
        "expense_count": len(expenses)
    }


# GET /expenses/summary/yearly - Month-by-month totals from January to now
@router.get("/expenses/summary/yearly")
async def get_yearly_summary():
    current_year = datetime.now().year
    current_month_num = datetime.now().month

    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]

    monthly_totals = {}
    category_totals = {}
    grand_total = 0
    currency = "INR"

    for i in range(current_month_num):
        month_name = months[i]
        expenses = await fetch_expenses_by_month(month_name)

        month_total = 0
        for expense in expenses:
            amount = expense.get("amount", 0)
            category = expense.get("category", "Miscellaneous")
            month_total += amount
            category_totals[category] = category_totals.get(category, 0) + amount
            currency = expense.get("currency", currency)

        monthly_totals[month_name] = month_total
        grand_total += month_total

    return {
        "year": current_year,
        "currency": currency,
        "monthly_totals": monthly_totals,
        "category_totals": category_totals,
        "grand_total": grand_total
    }