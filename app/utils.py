"""Small shared helpers: month ranges and money formatting."""
import calendar
from datetime import date
from decimal import Decimal

CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}


def parse_month(value, today=None):
    """'2025-03' -> (2025, 3). Falls back to the current month on bad input."""
    today = today or date.today()
    try:
        year, month = (int(p) for p in (value or "").split("-"))
        date(year, month, 1)
        return year, month
    except (ValueError, TypeError):
        return today.year, today.month


def month_bounds(year, month):
    """Return [first day, first day of next month) for range queries."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def days_in_month(year, month):
    return calendar.monthrange(year, month)[1]


def format_money(value, currency="INR"):
    """Format with the currency symbol. INR uses Indian digit grouping (12,34,567.89)."""
    value = Decimal(value or 0).quantize(Decimal("0.01"))
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):.2f}".split(".")
    if currency == "INR" and len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    elif currency != "INR":
        whole = f"{int(whole):,}"
    return f"{sign}{symbol}{whole}.{frac}"
