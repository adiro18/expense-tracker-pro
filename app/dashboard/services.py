"""Dashboard calculations, kept separate from the views so they are easy to unit-test."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func

from ..extensions import db
from ..models import Category, Transaction
from ..utils import days_in_month, month_bounds, shift_month

ZERO = Decimal("0")


def month_totals(user_id, year, month):
    """Total income and expense for one month -> (income, expense)."""
    start, end = month_bounds(year, month)
    rows = db.session.execute(
        db.select(Transaction.type, func.sum(Transaction.amount))
        .filter(Transaction.user_id == user_id, Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.type)
    ).all()
    totals = {t: Decimal(v or 0) for t, v in rows}
    return totals.get("income", ZERO), totals.get("expense", ZERO)


def savings_rate(income, expense):
    """Percentage of income that was not spent."""
    if not income:
        return 0.0
    return round(float((income - expense) / income * 100), 1)


def forecast_month_spend(spent, year, month, today=None):
    """Month-end forecast = spend so far / days elapsed x days in month.
    Past months return the actual spend; future months return 0."""
    today = today or date.today()
    total_days = days_in_month(year, month)
    if (year, month) < (today.year, today.month):
        return spent
    if (year, month) > (today.year, today.month):
        return ZERO
    return (spent / today.day * total_days).quantize(Decimal("0.01"))


def category_breakdown(user_id, year, month):
    """Expense per category for the doughnut chart, largest first."""
    start, end = month_bounds(year, month)
    rows = db.session.execute(
        db.select(Category.name, func.sum(Transaction.amount).label("total"))
        .join(Category, Transaction.category_id == Category.id)
        .filter(Transaction.user_id == user_id, Transaction.type == "expense",
                Transaction.date >= start, Transaction.date < end)
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()
    return [(name, Decimal(total)) for name, total in rows]


def daily_trend(user_id, year, month):
    """Expense per day of the month for the line chart -> (labels, values)."""
    start, end = month_bounds(year, month)
    rows = db.session.execute(
        db.select(Transaction.date, func.sum(Transaction.amount))
        .filter(Transaction.user_id == user_id, Transaction.type == "expense",
                Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.date)
    ).all()
    by_day = {d: Decimal(v) for d, v in rows}
    days = [start + timedelta(days=i) for i in range(days_in_month(year, month))]
    return [d.day for d in days], [float(by_day.get(d, ZERO)) for d in days]


def monthly_trend(user_id, year, month, months=6):
    """Income vs expense for the last `months` months ending at year-month."""
    first_y, first_m = shift_month(year, month, -(months - 1))
    start, _ = month_bounds(first_y, first_m)
    _, end = month_bounds(year, month)
    rows = db.session.execute(
        db.select(Transaction.date, Transaction.type, func.sum(Transaction.amount))
        .filter(Transaction.user_id == user_id, Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.date, Transaction.type)
    ).all()
    sums = defaultdict(lambda: {"income": ZERO, "expense": ZERO})
    for d, t, v in rows:
        sums[(d.year, d.month)][t] += Decimal(v)
    labels, income, expense = [], [], []
    for i in range(months):
        y, m = shift_month(first_y, first_m, i)
        labels.append(date(y, m, 1).strftime("%b %Y"))
        income.append(float(sums[(y, m)]["income"]))
        expense.append(float(sums[(y, m)]["expense"]))
    return labels, income, expense


def recent_transactions(user_id, limit=8):
    return db.session.execute(
        db.select(Transaction).filter_by(user_id=user_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit)
    ).scalars().all()
