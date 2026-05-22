"""Locale-aware number formatting helpers for the frontend.

Indian numbering uses '1,00,000' (lakh) grouping; most other currencies use
the Western '100,000' grouping. format_amount picks the right style based on
the currency code.
"""


def _format_indian(amount: float, decimals: int) -> str:
    """Format a number using the Indian lakh/crore comma style.

    Examples (decimals=0):
        100      -> '100'
        12345    -> '12,345'
        100000   -> '1,00,000'
        1000000  -> '10,00,000'
        12345678 -> '1,23,45,678'
    """
    if decimals > 0:
        s = f"{amount:.{decimals}f}"
        int_part, _, dec_part = s.partition(".")
    else:
        int_part = str(int(round(amount)))
        dec_part = ""

    negative = int_part.startswith("-")
    if negative:
        int_part = int_part[1:]

    if len(int_part) <= 3:
        grouped = int_part
    else:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last3

    if negative:
        grouped = "-" + grouped

    return f"{grouped}.{dec_part}" if dec_part else grouped


def format_amount(amount, currency: str, decimals: int = 0) -> str:
    """Format an amount using the right thousands-separator style for the currency.

    - INR -> Indian lakh style (1,00,000)
    - Anything else -> Western style (100,000)

    Always returns a string (no currency symbol). Caller is responsible for
    prepending the symbol.
    """
    if amount is None:
        return "0"
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return str(amount)

    if (currency or "").upper() == "INR":
        return _format_indian(amount, decimals)

    return f"{amount:,.{decimals}f}"
