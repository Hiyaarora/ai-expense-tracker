"""User settings endpoints — currently just the base currency."""
from fastapi import APIRouter, HTTPException
from database import settings_collection, expense_collection, salary_collection
from models import SettingsUpdate
from services.currency import CURRENCIES, symbol_for, get_rate

router = APIRouter()

DEFAULT_BASE_CURRENCY = "INR"
SETTINGS_ID = "user_settings"  # single-user app — one settings doc


@router.get("/settings")
async def get_settings():
    doc = await settings_collection.find_one({"_id": SETTINGS_ID})
    base = (doc or {}).get("base_currency", DEFAULT_BASE_CURRENCY)
    return {
        "base_currency": base,
        "symbol": symbol_for(base),
        "supported_currencies": [
            {"code": code, "name": name, "symbol": symbol_for(code)}
            for code, name in CURRENCIES.items()
        ],
    }


@router.put("/settings")
async def update_settings(settings: SettingsUpdate):
    """Change base currency AND bulk-convert all existing expenses + salaries.

    All stored data is currently in the old base currency. When base changes,
    we multiply every amount by the old→new exchange rate so the user sees
    consistent values in the new currency.
    """
    new_base = settings.base_currency.upper()
    if new_base not in CURRENCIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported currency: {new_base}. Supported: {list(CURRENCIES.keys())}",
        )

    doc = await settings_collection.find_one({"_id": SETTINGS_ID})
    old_base = (doc or {}).get("base_currency", DEFAULT_BASE_CURRENCY)

    if old_base == new_base:
        return {
            "message": f"Base currency is already {new_base}",
            "base_currency": new_base,
            "symbol": symbol_for(new_base),
            "expenses_converted": 0,
            "salaries_converted": 0,
        }

    # Fetch the exchange rate once
    try:
        rate = get_rate(old_base, new_base)
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch exchange rate {old_base}->{new_base}: {e}",
        )

    # Convert all expenses
    expenses = await expense_collection.find().to_list(10000)
    for exp in expenses:
        current_amount = exp.get("amount", 0)
        new_amount = round(current_amount * rate, 2)
        await expense_collection.update_one(
            {"_id": exp["_id"]},
            {"$set": {"amount": new_amount, "currency": new_base}},
        )

    # Convert all salaries
    salaries = await salary_collection.find().to_list(1000)
    for sal in salaries:
        current_amount = sal.get("amount", 0)
        new_amount = round(current_amount * rate, 2)
        await salary_collection.update_one(
            {"_id": sal["_id"]},
            {"$set": {"amount": new_amount, "currency": new_base}},
        )

    # Update settings
    await settings_collection.update_one(
        {"_id": SETTINGS_ID},
        {"$set": {"base_currency": new_base}},
        upsert=True,
    )

    return {
        "message": (
            f"Base currency changed from {old_base} to {new_base}. "
            f"Converted {len(expenses)} expenses and {len(salaries)} salaries "
            f"at rate {rate}."
        ),
        "base_currency": new_base,
        "symbol": symbol_for(new_base),
        "old_base_currency": old_base,
        "conversion_rate": rate,
        "expenses_converted": len(expenses),
        "salaries_converted": len(salaries),
    }
