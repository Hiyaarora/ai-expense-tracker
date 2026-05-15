"""Currency conversion service.

Uses frankfurter.app (free, no API key) to fetch live exchange rates.
Caches rates in memory for 1 hour to avoid hammering the API.
"""
import time
import httpx

# ===================== Supported currencies =====================
# (Frankfurter supports about 30 — these are the common ones)

CURRENCIES = {
    "INR": "Indian Rupee",
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "JPY": "Japanese Yen",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "SGD": "Singapore Dollar",
    "CHF": "Swiss Franc",
    "CNY": "Chinese Yuan",
    "HKD": "Hong Kong Dollar",
    "NZD": "New Zealand Dollar",
    "AED": "UAE Dirham",
}

SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "AUD": "A$",
    "CAD": "C$",
    "SGD": "S$",
    "CHF": "Fr",
    "CNY": "¥",
    "HKD": "HK$",
    "NZD": "NZ$",
    "AED": "د.إ",
}

# ===================== In-memory rate cache =====================
# Key: "FROM->TO", Value: (rate, timestamp)
_rate_cache: dict = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


def symbol_for(currency: str) -> str:
    """Return the display symbol for a currency code (defaults to the code itself)."""
    return SYMBOLS.get(currency, currency)


def supported(currency: str) -> bool:
    return currency in CURRENCIES


def get_rate(from_currency: str, to_currency: str) -> float:
    """Get the exchange rate from one currency to another.

    Returns 1.0 if from == to.
    Caches results for 1 hour.
    Raises ValueError if fetching fails and no cached value exists.
    """
    if from_currency == to_currency:
        return 1.0

    cache_key = f"{from_currency}->{to_currency}"
    cached = _rate_cache.get(cache_key)
    if cached and (time.time() - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]

    # Fetch from frankfurter.app
    try:
        url = "https://api.frankfurter.dev/v1/latest"
        params = {"base": from_currency, "symbols": to_currency}
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        rate = float(data["rates"][to_currency])
        _rate_cache[cache_key] = (rate, time.time())
        return rate
    except Exception as e:
        if cached:
            return cached[0]  # Fall back to stale cache if available
        raise ValueError(
            f"Could not fetch exchange rate {from_currency}->{to_currency}: {e}"
        )


def build_amount_fields(amount: float, input_currency: str, base_currency: str) -> dict:
    """Build the amount-related fields for an expense doc.

    If input and base currencies match: just amount + currency.
    If different: converts and also stores original amount + rate for transparency.
    """
    if input_currency == base_currency:
        return {"amount": float(amount), "currency": base_currency}

    conv = convert(amount, input_currency, base_currency)
    return {
        "amount": conv["converted_amount"],
        "currency": base_currency,
        "original_amount": conv["original_amount"],
        "original_currency": conv["original_currency"],
        "exchange_rate": conv["exchange_rate"],
    }


def convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount from one currency to another.

    Returns a dict with the converted amount and the rate used:
    {
        "original_amount": 50.0,
        "original_currency": "USD",
        "converted_amount": 4172.50,
        "converted_currency": "INR",
        "exchange_rate": 83.45,
    }
    """
    rate = get_rate(from_currency, to_currency)
    converted = round(amount * rate, 2)
    return {
        "original_amount": amount,
        "original_currency": from_currency,
        "converted_amount": converted,
        "converted_currency": to_currency,
        "exchange_rate": rate,
    }
