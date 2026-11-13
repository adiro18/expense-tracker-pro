from datetime import date
from decimal import Decimal

from app.budgets import budget_progress
from app.extensions import db
from app.models import Budget

from .conftest import category, make_txn, make_user

PERIOD = date.today().strftime("%Y-%m")


def make_budget(user, cat="Food", amount="1000", period=PERIOD):
    b = Budget(user_id=user.id, category_id=category(cat).id, amount=Decimal(amount), period=period)
    db.session.add(b)
    db.session.commit()
    return b


def test_budget_progress_calculation(app, user, account):
    make_budget(user, "Food", "1000")
    make_budget(user, "Transport", "200")
    make_budget(user, "Shopping", "500")
    make_txn(user, account, "Food", "300")
    make_txn(user, account, "Food", "200")
    make_txn(user, account, "Transport", "250")
    make_txn(user, account, "Shopping", "400")
    make_txn(user, account, "Food", "999", day=date(2020, 1, 1))  # other month - ignored
    rows = {r["budget"].category.name: r for r in budget_progress(user.id, PERIOD)}

    assert rows["Food"]["spent"] == Decimal("500")
    assert rows["Food"]["percent"] == 50.0 and rows["Food"]["status"] == "ok"
    assert rows["Transport"]["percent"] == 125.0 and rows["Transport"]["status"] == "over"
    assert rows["Transport"]["remaining"] == Decimal("-50")
    assert rows["Shopping"]["status"] == "warn"  # 80%


def test_budget_index_page(auth_client, user, account):
    make_budget(user, "Food", "1000")
    make_txn(user, account, "Food", "1500")
    html = auth_client.get(f"/budgets/?month={PERIOD}").get_data(as_text=True)
    assert "Food" in html and "150.0%" in html and "over by" in html


def test_create_budget(auth_client, user):
    assert auth_client.get("/budgets/new").status_code == 200
    resp = auth_client.post("/budgets/new", data={
        "category_id": category("Food").id, "amount": "5000", "period": PERIOD})
    assert resp.status_code == 302
    assert db.session.execute(db.select(Budget)).scalar_one().amount == Decimal("5000.00")


def test_create_budget_validation(auth_client, user):
    html = auth_client.post("/budgets/new", data={
        "category_id": category("Food").id, "amount": "-5", "period": "2025-13"}).get_data(as_text=True)
    assert "Amount must be a positive number." in html
    assert "Use the format YYYY-MM." in html
    html = auth_client.post("/budgets/new", data={
        "category_id": category("Salary").id, "amount": "5", "period": PERIOD}).get_data(as_text=True)
    assert "is an income category" in html


def test_duplicate_budget_rejected(auth_client, user):
    make_budget(user)
    html = auth_client.post("/budgets/new", data={
        "category_id": category("Food").id, "amount": "10", "period": PERIOD}).get_data(as_text=True)
    assert "already exists" in html


def test_edit_and_delete_budget(auth_client, user):
    b = make_budget(user)
    assert auth_client.get(f"/budgets/{b.id}/edit").status_code == 200
    resp = auth_client.post(f"/budgets/{b.id}/edit", data={
        "category_id": category("Food").id, "amount": "2500", "period": PERIOD})
    assert resp.status_code == 302
    assert db.session.get(Budget, b.id).amount == Decimal("2500.00")
    assert auth_client.post(f"/budgets/{b.id}/delete").status_code == 302
    assert db.session.get(Budget, b.id) is None


def test_other_users_budget_is_404(auth_client):
    other = make_budget(make_user("mallory"))
    assert auth_client.get(f"/budgets/{other.id}/edit").status_code == 404
    assert auth_client.post(f"/budgets/{other.id}/delete").status_code == 404
