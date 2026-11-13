"""Dashboard (summary, charts, forecast) and CSV report export."""
import csv
import io
from datetime import date

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from ..accounts import account_balances
from ..budgets import budget_progress
from ..transactions import filtered_query
from ..extensions import db
from ..utils import parse_month, shift_month
from . import services

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def home():
    uid = current_user.id
    year, month = parse_month(request.args.get("month"))
    income, expense = services.month_totals(uid, year, month)
    breakdown = services.category_breakdown(uid, year, month)
    day_labels, day_values = services.daily_trend(uid, year, month)
    m_labels, m_income, m_expense = services.monthly_trend(uid, year, month)
    balances = account_balances(uid)

    context = {
        "month_value": f"{year:04d}-{month:02d}",
        "month_label": date(year, month, 1).strftime("%B %Y"),
        "prev_month": "%04d-%02d" % shift_month(year, month, -1),
        "next_month": "%04d-%02d" % shift_month(year, month, 1),
        "income": income,
        "expense": expense,
        "net": income - expense,
        "total_balance": sum((b for _, b in balances), 0),
        "savings_rate": services.savings_rate(income, expense),
        "forecast": services.forecast_month_spend(expense, year, month),
        "budgets": budget_progress(uid, f"{year:04d}-{month:02d}"),
        "recent": services.recent_transactions(uid),
        # Chart.js data (plain lists -> |tojson in the template)
        "cat_labels": [name for name, _ in breakdown],
        "cat_values": [float(v) for _, v in breakdown],
        "day_labels": day_labels,
        "day_values": day_values,
        "m_labels": m_labels,
        "m_income": m_income,
        "m_expense": m_expense,
    }
    return render_template("dashboard/home.html", **context)


@bp.route("/reports/transactions.csv")
@login_required
def export_csv():
    """Download the user's transactions (same filters as the transactions page)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "type", "amount", "category", "account", "payment_mode", "note"])
    for t in db.session.execute(filtered_query(current_user.id, request.args)).scalars():
        writer.writerow([t.date.isoformat(), t.type, f"{t.amount:.2f}", t.category.name,
                         t.account.name, t.payment_mode, t.note or ""])
    filename = f"spendwise-{request.args.get('month') or 'all'}.csv"
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})
