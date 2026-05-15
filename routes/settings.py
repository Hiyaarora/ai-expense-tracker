"""User settings endpoints — currently just the base currency."""
from fastapi import APIRouter, HTTPException
from database import settings_collection
from models import SettingsUpdate
from services.currency import CURRENCIES, symbol_for

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
    base = settings.base_currency.upper()
    if base not in CURRENCIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported currency: {base}. Supported: {list(CURRENCIES.keys())}",
        )
    await settings_collection.update_one(
        {"_id": SETTINGS_ID},
        {"$set": {"base_currency": base}},
        upsert=True,
    )
    return {
        "message": f"Base currency set to {base}",
        "base_currency": base,
        "symbol": symbol_for(base),
    }
