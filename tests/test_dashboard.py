import csv
import io
from datetime import date
from decimal import Decimal

from app.dashboard import services

from .conftest import make_account, make_txn, make_user


def test_month_totals_and_savings_rate(app, user, account):
    make_txn(user, account, "Salary", "10000", "income", day=date(2025, 3, 1))
    make_txn(user, account, "Food", "2500", day=date(2025, 3, 5))
    make_txn(user, account, "Rent", "4000", day=date(2025, 3, 6))
    make_txn(user, account, "Food", "9999", day=date(2025, 4, 1))  # next month - excluded
    income, expense = services.month_totals(user.id, 2025, 3)
    assert income == Decimal("10000") and expense == Decimal("6500")
    assert services.savings_rate(income, expense) == 35.0
    assert services.savings_rate(Decimal("0"), Decimal("100")) == 0.0


def test_forecast():
    today = date(2025, 4, 10)  # April has 30 days
    assert services.forecast_month_spend(Decimal("1000"), 2025, 4, today) == Decimal("3000.00")
    assert services.forecast_month_spend(Decimal("1000"), 2025, 3, today) == Decimal("1000")  # past
    assert services.forecast_month_spend(Decimal("1000"), 2025, 5, today) == Decimal("0")  # future


def test_category_breakdown_and_trends(app, user, account):
    make_txn(user, account, "Food", "300", day=date(2025, 3, 2))
    make_txn(user, account, "Food", "200", day=date(2025, 3, 2))
    make_txn(user, account, "Transport", "100", day=date(2025, 3, 3))
    make_txn(user, account, "Salary", "5000", "income", day=date(2025, 2, 1))
    assert services.category_breakdown(user.id, 2025, 3) == [
        ("Food", Decimal("500")), ("Transport", Decimal("100"))]

    labels, values = services.daily_trend(user.id, 2025, 3)
    assert len(labels) == 31 and values[1] == 500.0 and values[2] == 100.0

    labels, income, expense = services.monthly_trend(user.id, 2025, 3)
    assert labels[-1] == "Mar 2025" and labels[0] == "Oct 2024"
    assert expense[-1] == 600.0 and income[-2] == 5000.0


def test_dashboard_page(auth_client, user, account):
    make_txn(user, account, "Salary", "50000", "income")
    make_txn(user, account, "Food", "1234.50")
    resp = auth_client.get("/")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "₹50,000.00" in html and "₹1,234.50" in html
    assert "categoryChart" in html and "Savings rate" in html
    assert auth_client.get("/?month=2020-01").status_code == 200
    assert auth_client.get("/?month=garbage").status_code == 200  # falls back to current month


def test_dashboard_empty_state(auth_client):
    html = auth_client.get("/").get_data(as_text=True)
    assert "No expenses this month." in html and "No transactions yet." in html


def test_csv_export(auth_client, user, account):
    make_txn(user, account, "Food", "99.90", day=date(2025, 3, 2))
    make_txn(user, account, "Transport", "15", day=date(2025, 4, 2))
    other = make_user("mallory")
    make_txn(other, make_account(other), "Food", "5555")

    resp = auth_client.get("/reports/transactions.csv")
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    rows = list(csv.reader(io.StringIO(resp.get_data(as_text=True))))
    assert rows[0][:3] == ["date", "type", "amount"]
    assert len(rows) == 3  # header + alice's 2 rows, nothing from mallory

    rows = list(csv.reader(io.StringIO(
        auth_client.get("/reports/transactions.csv?month=2025-03").get_data(as_text=True))))
    assert len(rows) == 2 and rows[1][2] == "99.90" and rows[1][3] == "Food"
